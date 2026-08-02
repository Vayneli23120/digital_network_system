"""Security Step 4E-C1: spare parts & movements permission guards.

Covers the 11 Spare Parts routes and 5 Spare Movements routes:
dependency matrix, unauthenticated 401, cross-permission 403, admin
pass-through, and Principal operator persistence in movement records.
"""

import inspect

import app.shared.models_jobs  # noqa: F401  Register jobs table in metadata.


def _create_user(db_session, username: str, *, permissions=None, superuser=False):
    from app.shared.models import Permission, Role, User

    user = User(
        username=username,
        password_hash="unused",
        is_active=True,
        is_superuser=superuser,
    )
    permission_names = list(permissions or [])
    if permission_names:
        role = Role(name=f"role-{username}", description="test role")
        records = []
        for permission_name in permission_names:
            record = db_session.query(Permission).filter(
                Permission.name == permission_name
            ).first()
            if record is None:
                record = Permission(
                    name=permission_name,
                    resource=permission_name.split(":", 1)[0],
                    action=permission_name.split(":", 1)[1],
                )
                records.append(record)
            role.permissions.append(record)
        user.roles.append(role)
        db_session.add_all([role, *records])
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _enable_auth(monkeypatch):
    from app.shared.config import get_config

    config = get_config()
    monkeypatch.setattr(config.security, "auth_enabled", True)
    monkeypatch.setattr(config.app, "debug", False)


def _spare_client(current_user, db_session):
    from fastapi import FastAPI, HTTPException
    from fastapi.testclient import TestClient

    from app.features.auth.identity import Principal, get_current_principal
    from app.features.spare_movements import router as movements_router
    from app.features.spare_parts import router as parts_router
    from app.shared.database import get_db

    app = FastAPI()
    app.include_router(parts_router.router)
    app.include_router(movements_router.router)
    app.dependency_overrides[get_db] = lambda: db_session

    def principal_override():
        if current_user is None:
            raise HTTPException(status_code=401, detail="需要认证")
        return Principal(
            username=current_user.username,
            user_id=current_user.id,
            user=current_user,
            auth_source="test",
        )

    app.dependency_overrides[get_current_principal] = principal_override
    return TestClient(app)


PARTS_ROUTE_DEPS = {
    "api_list_parts": "require_spare_read",
    "api_create_part": "require_spare_write",
    "api_get_part_by_serial": "require_spare_read",
    "api_search_in_stock_instances": "require_spare_read",
    "api_get_part": "require_spare_read",
    "api_get_part_instances": "require_spare_read",
    "api_manual_stock_in": "require_spare_write",
    "api_manual_stock_out": "require_spare_write",
    "api_update_part": "require_spare_write",
    "api_delete_part": "require_spare_delete",
    "api_get_stats": "require_spare_read",
}

MOVEMENT_ROUTE_DEPS = {
    "api_create_movement": "require_movement_write",
    "api_list_movements": "require_movement_read",
    "api_get_movement": "require_movement_read",
    "api_update_movement": "require_movement_write",
    "api_delete_movement": "require_movement_write",
}

# Part/create and movement/create bodies that pass validation so auth is
# the first thing evaluated (resource ids are bogus: never reached).
_CREATE_PART = {"name": "Test Part", "part_number": "P-SEC-1"}
_MANUAL_IN = {"serial_number": "SN-SEC-1"}
_MANUAL_OUT = {"serial_number": "SN-SEC-1", "reason": "test"}
_UPDATE_PART = {"name": "Updated Part"}
_CREATE_MOVEMENT = {"part_id": 999999, "movement_type": "in", "quantity": 1}
_UPDATE_MOVEMENT = {"reason": "updated"}


def test_spare_route_permission_matrix_is_declared():
    from app.features.spare_movements import router as movements_router
    from app.features.spare_parts import router as parts_router

    for function_name, dependency_name in PARTS_ROUTE_DEPS.items():
        function = getattr(parts_router, function_name)
        parameter = inspect.signature(function).parameters.get("_")
        assert parameter is not None, f"{function_name} missing permission dependency"
        assert parameter.default.dependency is getattr(
            parts_router, dependency_name
        )

    for function_name, dependency_name in MOVEMENT_ROUTE_DEPS.items():
        function = getattr(movements_router, function_name)
        parameter = inspect.signature(function).parameters.get("_")
        assert parameter is not None, f"{function_name} missing permission dependency"
        assert parameter.default.dependency is getattr(
            movements_router, dependency_name
        )


def _all_route_calls():
    return [
        ("GET", "/api/spare-parts/", None),
        ("POST", "/api/spare-parts/", _CREATE_PART),
        ("GET", "/api/spare-parts/by-serial/SN-NOT-EXIST", None),
        ("GET", "/api/spare-parts/search-in-stock?keyword=x", None),
        ("GET", "/api/spare-parts/999999", None),
        ("GET", "/api/spare-parts/999999/instances", None),
        ("POST", "/api/spare-parts/999999/manual-in", _MANUAL_IN),
        ("POST", "/api/spare-parts/999999/manual-out", _MANUAL_OUT),
        ("PUT", "/api/spare-parts/999999", _UPDATE_PART),
        ("DELETE", "/api/spare-parts/999999", None),
        ("POST", "/api/spare-movements/", _CREATE_MOVEMENT),
        ("GET", "/api/spare-movements/", None),
        ("GET", "/api/spare-movements/999999", None),
        ("PUT", "/api/spare-movements/999999", _UPDATE_MOVEMENT),
        ("DELETE", "/api/spare-movements/999999", None),
    ]


def test_spare_unauthenticated_returns_401(db_session, monkeypatch):
    _enable_auth(monkeypatch)
    with _spare_client(None, db_session) as client:
        for method, path, body in _all_route_calls():
            response = client.request(method, path, json=body)
            assert response.status_code == 401, f"{method} {path} -> {response.status_code}"


def test_spare_cross_permission_matrix(db_session, monkeypatch):
    _enable_auth(monkeypatch)
    reader = _create_user(db_session, "spare-reader", permissions=["spare_part:read"])
    writer = _create_user(db_session, "spare-writer", permissions=["spare_part:write"])
    deleter = _create_user(db_session, "spare-deleter", permissions=["spare_part:delete"])
    mvmt_reader = _create_user(
        db_session, "mvmt-reader", permissions=["spare_movement:read"]
    )
    mvmt_writer = _create_user(
        db_session, "mvmt-writer", permissions=["spare_movement:write"]
    )

    with _spare_client(reader, db_session) as client:
        assert client.get("/api/spare-parts/").status_code == 200
        assert client.post("/api/spare-parts/", json=_CREATE_PART).status_code == 403
        assert client.put(
            "/api/spare-parts/999999", json=_UPDATE_PART
        ).status_code == 403
        assert client.delete("/api/spare-parts/999999").status_code == 403
        assert client.post(
            "/api/spare-parts/999999/manual-in", json=_MANUAL_IN
        ).status_code == 403
        assert client.get("/api/spare-movements/").status_code == 403
        assert client.post("/api/spare-movements/", json=_CREATE_MOVEMENT).status_code == 403

    with _spare_client(writer, db_session) as client:
        # write passes on create; delete requires spare_part:delete -> 403
        assert client.post("/api/spare-parts/", json=_CREATE_PART).status_code == 200
        assert client.delete("/api/spare-parts/999999").status_code == 403
        # movement write is a separate permission -> 403
        assert client.post("/api/spare-movements/", json=_CREATE_MOVEMENT).status_code == 403

    with _spare_client(deleter, db_session) as client:
        # delete permission passes; 404 because the part does not exist
        assert client.delete("/api/spare-parts/999999").status_code == 404
        # read not held -> 403
        assert client.get("/api/spare-parts/").status_code == 403

    with _spare_client(mvmt_reader, db_session) as client:
        assert client.get("/api/spare-movements/").status_code == 200
        assert client.post(
            "/api/spare-movements/", json=_CREATE_MOVEMENT
        ).status_code == 403
        assert client.get("/api/spare-parts/").status_code == 403

    with _spare_client(mvmt_writer, db_session) as client:
        # write permission passes; 404 because the part does not exist
        assert client.post(
            "/api/spare-movements/", json=_CREATE_MOVEMENT
        ).status_code == 404
        assert client.delete("/api/spare-movements/999999").status_code == 404
        assert client.put(
            "/api/spare-movements/999999", json=_UPDATE_MOVEMENT
        ).status_code == 404


def test_spare_admin_passes_all_routes(db_session, monkeypatch):
    _enable_auth(monkeypatch)
    admin = _create_user(db_session, "spare-admin", superuser=True)
    with _spare_client(admin, db_session) as client:
        assert client.get("/api/spare-parts/").status_code == 200
        assert client.post("/api/spare-parts/", json=_CREATE_PART).status_code == 200
        assert client.get("/api/spare-movements/").status_code == 200
        # nonexistent resources -> 404 (permission already passed)
        assert client.delete("/api/spare-parts/999999").status_code == 404
        assert client.get("/api/spare-parts/999999").status_code == 404
        assert client.delete("/api/spare-movements/999999").status_code == 404


def test_spare_manual_operator_persists_from_principal(db_session, monkeypatch):
    from app.shared.models import SparePart, SparePartInstance, SparePartMovement

    _enable_auth(monkeypatch)
    admin = _create_user(db_session, "spare-admin", superuser=True)
    writer = _create_user(db_session, "spare-operator", permissions=["spare_part:write"])

    with _spare_client(admin, db_session) as client:
        created = client.post("/api/spare-parts/", json=_CREATE_PART).json()
    part_id = created["id"]

    with _spare_client(writer, db_session) as client:
        in_resp = client.post(
            f"/api/spare-parts/{part_id}/manual-in", json=_MANUAL_IN
        )
        assert in_resp.status_code == 200, in_resp.text
        assert in_resp.json()["new_stock"] == 1

    db_session.expire_all()
    movement = db_session.query(SparePartMovement).filter(
        SparePartMovement.part_id == part_id
    ).one()
    assert movement.operator == "spare-operator"
    instance = db_session.query(SparePartInstance).filter(
        SparePartInstance.part_id == part_id
    ).one()
    assert instance.serial_number == "SN-SEC-1"
    assert instance.status == "in_stock"
    part = db_session.query(SparePart).filter(SparePart.id == part_id).one()
    assert part.quantity_in_stock == 1

    with _spare_client(writer, db_session) as client:
        out_resp = client.post(
            f"/api/spare-parts/{part_id}/manual-out",
            json={"serial_number": "SN-SEC-1", "reason": "issue to device"},
        )
        assert out_resp.status_code == 200, out_resp.text
        assert out_resp.json()["new_stock"] == 0

    db_session.expire_all()
    out_movement = db_session.query(SparePartMovement).filter(
        SparePartMovement.part_id == part_id,
        SparePartMovement.movement_type == "out",
    ).one()
    assert out_movement.operator == "spare-operator"
    part = db_session.query(SparePart).filter(SparePart.id == part_id).one()
    assert part.quantity_in_stock == 0


def test_spare_cross_serial_rejected_before_stock_change(db_session, monkeypatch):
    from app.shared.models import SparePart, SparePartInstance

    _enable_auth(monkeypatch)
    admin = _create_user(db_session, "spare-admin", superuser=True)

    with _spare_client(admin, db_session) as client:
        part_a = client.post(
            "/api/spare-parts/", json={"name": "Part A", "part_number": "P-A"}
        ).json()["id"]
        part_b = client.post(
            "/api/spare-parts/", json={"name": "Part B", "part_number": "P-B"}
        ).json()["id"]
        assert client.post(
            f"/api/spare-parts/{part_a}/manual-in",
            json={"serial_number": "SN-SHARED"},
        ).status_code == 200

        # serial belongs to part A; manual-out from part B must be rejected
        out = client.post(
            f"/api/spare-parts/{part_b}/manual-out",
            json={"serial_number": "SN-SHARED", "reason": "test"},
        )
        assert out.status_code == 422, out.text

    db_session.expire_all()
    part_a_row = db_session.query(SparePart).filter(SparePart.id == part_a).one()
    part_b_row = db_session.query(SparePart).filter(SparePart.id == part_b).one()
    assert part_a_row.quantity_in_stock == 1
    assert part_b_row.quantity_in_stock == 0
    instance = db_session.query(SparePartInstance).filter(
        SparePartInstance.serial_number == "SN-SHARED"
    ).one()
    assert instance.part_id == part_a
    assert instance.status == "in_stock"


def test_spare_movement_history_is_not_physically_deleted(db_session, monkeypatch):
    from app.shared.models import SparePartMovement

    _enable_auth(monkeypatch)
    admin = _create_user(db_session, "spare-admin", superuser=True)

    with _spare_client(admin, db_session) as client:
        part_id = client.post(
            "/api/spare-parts/", json=_CREATE_PART
        ).json()["id"]
        created = client.post(
            "/api/spare-movements/",
            json={"part_id": part_id, "movement_type": "in", "quantity": 1},
        )
        assert created.status_code == 200, created.text
        movement_id = created.json()["id"]

        deleted = client.delete(f"/api/spare-movements/{movement_id}")
        assert deleted.status_code == 409, deleted.text

    db_session.expire_all()
    assert db_session.query(SparePartMovement).filter(
        SparePartMovement.id == movement_id
    ).count() == 1
