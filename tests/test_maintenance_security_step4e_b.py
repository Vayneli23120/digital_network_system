"""Security Step 4E-B2: Maintenance RBAC, identity, and input safety."""

import inspect
from pathlib import Path

import app.shared.models_jobs  # noqa: F401  Register jobs table in metadata.


def _create_user(db_session, username: str, *, permission=None, superuser=False):
    from app.shared.models import Permission, Role, User

    user = User(
        username=username,
        password_hash="unused",
        is_active=True,
        is_superuser=superuser,
    )
    if permission:
        role = Role(name=f"role-{username}", description="test role")
        permission_record = Permission(
            name=permission,
            resource=permission.split(":", 1)[0],
            action=permission.split(":", 1)[1],
        )
        role.permissions.append(permission_record)
        user.roles.append(role)
        db_session.add_all([role, permission_record])
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _principal(user):
    from app.features.auth.identity import Principal

    return Principal(
        username=user.username,
        user_id=user.id,
        user=user,
        auth_source="test",
    )


def _maintenance_client(current_user, db):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.features.auth.identity import get_current_principal
    from app.features.auth.router import get_current_user_from_token
    from app.features.maintenance import router as maintenance_router
    from app.shared.database import get_db

    app = FastAPI()
    app.include_router(maintenance_router.router)
    app.dependency_overrides[get_current_user_from_token] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: db
    if current_user is not None:
        app.dependency_overrides[get_current_principal] = lambda: _principal(current_user)
    return TestClient(app)


def _enable_auth(monkeypatch):
    from app.shared.config import get_config

    config = get_config()
    monkeypatch.setattr(config.security, "auth_enabled", True)
    monkeypatch.setattr(config.app, "debug", False)


def test_maintenance_http_permission_matrix_is_declared():
    from app.features.maintenance import router as maintenance_router

    expected = {
        "require_maintenance_read": [
            "get_maintenance",
            "get_maintenance_events",
            "suggest_status",
            "list_maintenances",
        ],
        "require_maintenance_write": [
            "assign_maintenance",
            "add_work_note",
            "create_maintenance",
            "update_maintenance",
        ],
        "require_maintenance_transition": [
            "transition_maintenance_status",
            "submit_for_verification",
            "verify_pass",
            "auto_transition_status",
        ],
        "require_maintenance_delete": ["delete_maintenance"],
    }
    assert sum(len(functions) for functions in expected.values()) == 13
    for dependency_name, function_names in expected.items():
        dependency = getattr(maintenance_router, dependency_name)
        for function_name in function_names:
            function = getattr(maintenance_router, function_name)
            parameter = inspect.signature(function).parameters.get("_")
            assert parameter is not None, f"{function_name} missing permission dependency"
            assert parameter.default.dependency is dependency

    collection_routes = [
        (route.path, tuple(sorted(route.methods or ())))
        for route in maintenance_router.router.routes
        if route.path == "/api/maintenance"
    ]
    assert collection_routes.count(("/api/maintenance", ("GET",))) == 1
    assert collection_routes.count(("/api/maintenance", ("POST",))) == 1


def test_maintenance_permission_tiers_are_separated(db_session, monkeypatch):
    _enable_auth(monkeypatch)
    reader = _create_user(
        db_session,
        "maintenance-reader",
        permission="maintenance:read",
    )
    writer = _create_user(
        db_session,
        "maintenance-writer",
        permission="maintenance:write",
    )
    transitioner = _create_user(
        db_session,
        "maintenance-transitioner",
        permission="maintenance:transition",
    )
    deleter = _create_user(
        db_session,
        "maintenance-deleter",
        permission="maintenance:delete",
    )

    with _maintenance_client(None, db_session) as client:
        assert client.get("/api/maintenance").status_code == 401
    with _maintenance_client(reader, db_session) as client:
        assert client.get("/api/maintenance").status_code == 200
        assert client.post("/api/maintenance/999/transition", json={
            "status": "repairing",
        }).status_code == 403
    with _maintenance_client(writer, db_session) as client:
        assert client.get("/api/maintenance").status_code == 403
        assert client.delete("/api/maintenance/999").status_code == 403
    with _maintenance_client(transitioner, db_session) as client:
        assert client.post("/api/maintenance/999/transition", json={
            "status": "repairing",
        }).status_code == 404
        assert client.delete("/api/maintenance/999").status_code == 403
    with _maintenance_client(deleter, db_session) as client:
        assert client.delete("/api/maintenance/999").status_code == 404
        assert client.get("/api/maintenance").status_code == 403


def test_maintenance_events_use_principal_operator(db_session, monkeypatch):
    from app.shared.models import Device, MaintenanceEvent, MaintenanceRecord

    _enable_auth(monkeypatch)
    device = Device(name="maintenance-actor-device", ip="192.0.2.41")
    db_session.add(device)
    db_session.commit()
    writer = _create_user(
        db_session,
        "trusted-maintenance-writer",
        permission="maintenance:write",
    )
    transitioner = _create_user(
        db_session,
        "trusted-maintenance-transitioner",
        permission="maintenance:transition",
    )

    with _maintenance_client(writer, db_session) as client:
        rejected_actor = client.post("/api/maintenance", json={
            "device_id": device.id,
            "description": "forged actor",
            "operator": "forged-admin",
        })
        assert rejected_actor.status_code == 422
        created = client.post("/api/maintenance", json={
            "device_id": device.id,
            "device_name": device.name,
            "description": "principal actor test",
            "current_owner": "field-engineer",
        })
        assert created.status_code == 200
        maintenance_id = created.json()["id"]
        assigned = client.put(
            f"/api/maintenance/{maintenance_id}/assign",
            json={"owner": "replacement-engineer"},
        )
        assert assigned.status_code == 200
        note = client.post(
            f"/api/maintenance/{maintenance_id}/work-note",
            json={"note": " principal work note "},
        )
        assert note.status_code == 200

    with _maintenance_client(transitioner, db_session) as client:
        assert client.post(
            f"/api/maintenance/{maintenance_id}/transition",
            json={"status": "repairing", "operator": "forged-admin"},
        ).status_code == 422
        transitioned = client.post(
            f"/api/maintenance/{maintenance_id}/transition",
            json={"status": "repairing"},
        )
        assert transitioned.status_code == 200
        submitted = client.post(
            f"/api/maintenance/{maintenance_id}/submit-verification",
            json={},
        )
        assert submitted.status_code == 200
        verified = client.post(
            f"/api/maintenance/{maintenance_id}/verify-pass",
            json={"verification_notes": "verified"},
        )
        assert verified.status_code == 200

    db_session.expire_all()
    maintenance = db_session.query(MaintenanceRecord).filter(
        MaintenanceRecord.id == maintenance_id
    ).one()
    assert maintenance.operator == writer.username
    assert maintenance.current_owner == "replacement-engineer"
    events = db_session.query(MaintenanceEvent).filter(
        MaintenanceEvent.maintenance_id == maintenance_id
    ).order_by(MaintenanceEvent.id).all()
    assert [event.operator for event in events] == [
        writer.username,
        writer.username,
        writer.username,
        transitioner.username,
        transitioner.username,
        transitioner.username,
    ]
    assert next(event.notes for event in events if event.event_type == "work_note") == (
        "principal work note"
    )


def test_maintenance_models_and_pagination_reject_unsafe_input(
    db_session,
    monkeypatch,
):
    from app.shared.models import Device, MaintenanceRecord

    _enable_auth(monkeypatch)
    device = Device(name="maintenance-input-device", ip="192.0.2.42")
    maintenance = MaintenanceRecord(
        maint_no="MAINT-INPUT-BOUNDS",
        device_id=None,
        device_name=device.name,
        status="created",
        description="bounds test",
    )
    db_session.add_all([device, maintenance])
    db_session.commit()
    writer = _create_user(
        db_session,
        "maintenance-input-writer",
        permission="maintenance:write",
    )
    reader = _create_user(
        db_session,
        "maintenance-input-reader",
        permission="maintenance:read",
    )

    with _maintenance_client(writer, db_session) as client:
        assert client.put(
            f"/api/maintenance/{maintenance.id}",
            json={"status": "completed"},
        ).status_code == 422
        assert client.put(
            f"/api/maintenance/{maintenance.id}",
            json={"id": 999},
        ).status_code == 422
        assert client.post(
            f"/api/maintenance/{maintenance.id}/work-note",
            json={"note": "", "operator": "forged"},
        ).status_code == 422
        assert client.post(
            f"/api/maintenance/{maintenance.id}/work-note",
            json={"note": "x" * 501},
        ).status_code == 422
        assert client.post(
            "/api/maintenance",
            json={"device_id": device.id, "parts_cost": -1},
        ).status_code == 422

    with _maintenance_client(reader, db_session) as client:
        assert client.get("/api/maintenance?skip=-1").status_code == 422
        assert client.get("/api/maintenance?limit=0").status_code == 422
        assert client.get("/api/maintenance?limit=501").status_code == 422


def test_maintenance_completion_paths_resolve_linked_faults(
    db_session,
    monkeypatch,
):
    from app.features.maintenance import router as maintenance_router
    from app.shared.models import Device, FaultRecord, MaintenanceRecord

    _enable_auth(monkeypatch)

    async def no_notification(*_args, **_kwargs):
        return None

    monkeypatch.setattr(
        maintenance_router,
        "send_maintenance_completed_notification",
        no_notification,
    )
    device = Device(name="maintenance-completion-device", ip="192.0.2.43")
    db_session.add(device)
    db_session.flush()
    transitioner = _create_user(
        db_session,
        "maintenance-completion-transitioner",
        permission="maintenance:transition",
    )

    created = MaintenanceRecord(
        maint_no="MAINT-AUTO-START",
        device_id=device.id,
        device_name=device.name,
        status="created",
    )
    db_session.add(created)
    db_session.commit()
    with _maintenance_client(transitioner, db_session) as client:
        started = client.post(
            f"/api/maintenance/{created.id}/auto-transition",
            json={"status": "repairing"},
        )
    assert started.status_code == 200
    assert started.json()["status"] == "repairing"

    routes = (
        ("transition", {"status": "completed"}),
        ("verify-pass", {}),
        ("auto-transition", {"status": "completed"}),
    )
    linked_records = []
    for index, (route, _payload) in enumerate(routes):
        fault = FaultRecord(
            device_id=device.id,
            device_name=device.name,
            fault_no=f"FAULT-MAINT-COMPLETE-{index}",
            status="transferred",
            severity="major",
            description="linked completion test",
        )
        db_session.add(fault)
        db_session.flush()
        maintenance = MaintenanceRecord(
            maint_no=f"MAINT-COMPLETE-{index}",
            device_id=device.id,
            device_name=device.name,
            fault_id=fault.id,
            status="verifying",
        )
        db_session.add(maintenance)
        db_session.commit()
        linked_records.append((fault.id, maintenance.id, route, _payload))

    with _maintenance_client(transitioner, db_session) as client:
        for _fault_id, maintenance_id, route, payload in linked_records:
            response = client.post(
                f"/api/maintenance/{maintenance_id}/{route}",
                json=payload,
            )
            assert response.status_code == 200
            assert response.json()["status"] == "completed"

    db_session.expire_all()
    for fault_id, maintenance_id, _route, _payload in linked_records:
        fault = db_session.query(FaultRecord).filter(FaultRecord.id == fault_id).one()
        maintenance = db_session.query(MaintenanceRecord).filter(
            MaintenanceRecord.id == maintenance_id
        ).one()
        assert fault.status == "resolved"
        assert fault.resolved_at is not None
        assert maintenance.status == "completed"
        assert maintenance.verify_passed is True


def test_maintenance_internal_errors_are_redacted(db_session, monkeypatch):
    _enable_auth(monkeypatch)
    admin = _create_user(db_session, "maintenance-error-admin", superuser=True)
    secret_detail = r"database failed at C:\private\maintenance.db"

    class ExplodingSession:
        def query(self, *_args, **_kwargs):
            raise RuntimeError(secret_detail)

    with _maintenance_client(admin, ExplodingSession()) as client:
        response = client.get("/api/maintenance")

    assert response.status_code == 500
    assert response.json()["detail"] == "维修操作失败，请查看服务端日志"
    assert secret_detail not in response.text


def test_maintenance_uses_dependency_managed_sessions_and_frontend_has_no_operator():
    root = Path(__file__).resolve().parents[1]
    router_source = (
        root / "app/features/maintenance/router.py"
    ).read_text(encoding="utf-8")
    frontend_sources = [
        root / "frontend/src/views/FaultDetail.vue",
        root / "frontend/src/views/Maintenance.vue",
        root / "frontend/src/views/MaintenanceDetail.vue",
    ]
    layout_source = (
        root / "frontend/src/views/Layout.vue"
    ).read_text(encoding="utf-8")

    assert "next(get_db())" not in router_source
    assert "detail=str(" not in router_source
    for source_path in frontend_sources:
        source = source_path.read_text(encoding="utf-8")
        assert "submit-verification`, { operator: 'Web' }" not in source
        assert "verify-pass`, { operator: 'Web' }" not in source
        assert "auto-transition`, { status: nextAction, operator: 'Web' }" not in source
    maintenance_menu = next(
        line for line in layout_source.splitlines() if "path: '/maintenance'" in line
    )
    assert "permission: 'maintenance:read'" in maintenance_menu