"""Security Step 4E-B5A: user administration RBAC and session revocation."""

import inspect
from datetime import datetime, timedelta
from pathlib import Path

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
        new_permissions = []
        for permission_name in permission_names:
            permission = db_session.query(Permission).filter(
                Permission.name == permission_name
            ).first()
            if permission is None:
                permission = Permission(
                    name=permission_name,
                    resource=permission_name.split(":", 1)[0],
                    action=permission_name.split(":", 1)[1],
                )
                new_permissions.append(permission)
            role.permissions.append(permission)
        user.roles.append(role)
        db_session.add_all([role, *new_permissions])
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


def _auth_client(current_user, db):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.features.auth.identity import get_current_principal
    from app.features.auth.router import get_current_user_from_token, router
    from app.shared.database import get_db

    app = FastAPI()
    app.include_router(router)
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


def _add_session(db_session, user, suffix: str):
    from app.shared.models import UserSession

    session = UserSession(
        user_id=user.id,
        token_jti=f"session-{user.id}-{suffix}",
        token_type="access",
        expires_at=datetime.utcnow() + timedelta(hours=1),
        revoked=False,
    )
    db_session.add(session)
    db_session.commit()
    return session


def test_auth_user_permission_matrix_is_declared():
    import app.features.auth.router as auth_router

    expected = {
        "require_user_read": ["list_users", "get_user"],
        "require_user_write": ["_create_user_endpoint", "update_user"],
        "require_user_delete": ["delete_user"],
        "require_role_read": ["list_roles"],
    }
    for dependency_name, function_names in expected.items():
        dependency = getattr(auth_router, dependency_name)
        for function_name in function_names:
            function = getattr(auth_router, function_name)
            parameter = inspect.signature(function).parameters.get("_")
            assert parameter is not None, f"{function_name} missing permission dependency"
            assert parameter.default.dependency is dependency


def test_auth_user_permission_tiers_are_separated(db_session, monkeypatch):
    _enable_auth(monkeypatch)
    reader = _create_user(db_session, "user-reader", permissions=["user:read"])
    writer = _create_user(db_session, "user-writer", permissions=["user:write"])
    deleter = _create_user(db_session, "user-deleter", permissions=["user:delete"])
    role_reader = _create_user(db_session, "role-reader", permissions=["role:read"])
    ordinary = _create_user(db_session, "ordinary-user")

    with _auth_client(None, db_session) as client:
        assert client.get("/api/auth/users").status_code == 401
    with _auth_client(ordinary, db_session) as client:
        assert client.get("/api/auth/users").status_code == 403
        assert client.post("/api/auth/users", json={
            "username": "forged-user",
            "password": "password123",
        }).status_code == 403
    with _auth_client(reader, db_session) as client:
        assert client.get("/api/auth/users").status_code == 200
        assert client.get("/api/auth/roles").status_code == 403
        assert client.post("/api/auth/users", json={
            "username": "reader-created",
            "password": "password123",
        }).status_code == 403
    with _auth_client(writer, db_session) as client:
        created = client.post("/api/auth/users", json={
            "username": "writer-created",
            "password": "password123",
        })
        assert created.status_code == 201
        created_id = created.json()["id"]
        assert client.get("/api/auth/users").status_code == 403
        assert client.delete(f"/api/auth/users/{created_id}").status_code == 403
    with _auth_client(role_reader, db_session) as client:
        assert client.get("/api/auth/roles").status_code == 200
        assert client.get("/api/auth/users").status_code == 403
    with _auth_client(deleter, db_session) as client:
        assert client.delete(f"/api/auth/users/{created_id}").status_code == 200
        assert client.get("/api/auth/users").status_code == 403


def test_delegated_user_manager_cannot_escalate_roles(db_session, monkeypatch):
    from app.shared.models import Permission, Role, User

    _enable_auth(monkeypatch)
    user_writer = _create_user(
        db_session,
        "delegated-user-writer",
        permissions=["user:write"],
    )
    role_manager = _create_user(
        db_session,
        "delegated-role-manager",
        permissions=["user:write", "role:write"],
    )
    target = _create_user(db_session, "delegated-target")
    privileged_permission = Permission(
        name="credential:read",
        resource="credential",
        action="read",
    )
    privileged_role = Role(name="privileged-target-role")
    privileged_role.permissions.append(privileged_permission)
    assignable_role = Role(name="assignable-user-role")
    assignable_role.permissions.append(
        db_session.query(Permission).filter(Permission.name == "user:write").one()
    )
    db_session.add_all([privileged_permission, privileged_role, assignable_role])
    db_session.commit()

    with _auth_client(user_writer, db_session) as client:
        assert client.put(
            f"/api/auth/users/{target.id}",
            json={"role_ids": [assignable_role.id]},
        ).status_code == 403
    with _auth_client(role_manager, db_session) as client:
        duplicate = client.put(
            f"/api/auth/users/{target.id}",
            json={"role_ids": [assignable_role.id, assignable_role.id]},
        )
        assert duplicate.status_code == 422
        elevated = client.put(
            f"/api/auth/users/{target.id}",
            json={"role_ids": [privileged_role.id]},
        )
        assert elevated.status_code == 403
        allowed = client.put(
            f"/api/auth/users/{target.id}",
            json={"role_ids": [assignable_role.id]},
        )
        assert allowed.status_code == 200

    db_session.expire_all()
    stored_target = db_session.query(User).filter(User.id == target.id).one()
    assert [role.id for role in stored_target.roles] == [assignable_role.id]


def test_delegated_manager_cannot_modify_or_delete_admin_target(
    db_session,
    monkeypatch,
):
    from app.shared.models import Permission, Role

    _enable_auth(monkeypatch)
    manager = _create_user(
        db_session,
        "delegated-admin-target-manager",
        permissions=["user:write", "user:delete", "role:write"],
    )
    admin_target = _create_user(db_session, "protected-admin-target")
    admin_permission = Permission(
        name="admin:all",
        resource="admin",
        action="all",
    )
    admin_role = Role(name="protected-admin-role")
    admin_role.permissions.append(admin_permission)
    admin_target.roles.append(admin_role)
    db_session.add_all([admin_permission, admin_role])
    db_session.commit()

    with _auth_client(manager, db_session) as client:
        update = client.put(
            f"/api/auth/users/{admin_target.id}",
            json={"full_name": "tampered"},
        )
        delete = client.delete(f"/api/auth/users/{admin_target.id}")

    assert update.status_code == 403
    assert delete.status_code == 403
    db_session.refresh(admin_target)
    assert admin_target.full_name is None


def test_password_reset_deactivation_and_self_change_revoke_sessions(
    db_session,
    monkeypatch,
):
    from app.features.auth.router import get_password_hash
    from app.shared.models import UserSession

    _enable_auth(monkeypatch)
    writer = _create_user(db_session, "session-user-writer", permissions=["user:write"])
    target = _create_user(db_session, "session-target")
    target.password_hash = get_password_hash("old-password")
    db_session.commit()
    reset_session = _add_session(db_session, target, "reset")

    with _auth_client(writer, db_session) as client:
        reset = client.put(
            f"/api/auth/users/{target.id}",
            json={"password": "new-password"},
        )
    assert reset.status_code == 200
    db_session.refresh(reset_session)
    assert reset_session.revoked is True
    assert reset_session.revoked_at is not None

    deactivate_session = _add_session(db_session, target, "deactivate")
    with _auth_client(writer, db_session) as client:
        deactivated = client.put(
            f"/api/auth/users/{target.id}",
            json={"is_active": False},
        )
    assert deactivated.status_code == 200
    db_session.refresh(deactivate_session)
    assert deactivate_session.revoked is True

    self_user = _create_user(db_session, "self-password-user")
    self_user.password_hash = get_password_hash("old-password")
    db_session.commit()
    self_session = _add_session(db_session, self_user, "self")
    with _auth_client(self_user, db_session) as client:
        changed = client.post("/api/auth/change-password", json={
            "old_password": "old-password",
            "new_password": "new-password",
        })
    assert changed.status_code == 200
    db_session.refresh(self_session)
    assert self_session.revoked is True
    assert db_session.query(UserSession).filter(
        UserSession.user_id == target.id,
        UserSession.revoked == False,
    ).count() == 0


def test_delete_user_removes_existing_sessions_and_role_links(db_session, monkeypatch):
    from app.shared.models import User, UserSession

    _enable_auth(monkeypatch)
    deleter = _create_user(
        db_session,
        "session-user-deleter",
        permissions=["user:delete"],
    )
    target = _create_user(
        db_session,
        "delete-session-target",
        permissions=["device:read"],
    )
    target_id = target.id
    _add_session(db_session, target, "delete")

    with _auth_client(deleter, db_session) as client:
        response = client.delete(f"/api/auth/users/{target_id}")

    assert response.status_code == 200
    assert db_session.query(User).filter(User.id == target_id).first() is None
    assert db_session.query(UserSession).filter(
        UserSession.user_id == target_id
    ).count() == 0


def test_user_inputs_are_strict_bounded_and_menu_uses_read_permission(
    db_session,
    monkeypatch,
):
    _enable_auth(monkeypatch)
    writer = _create_user(db_session, "input-user-writer", permissions=["user:write"])
    reader = _create_user(db_session, "input-user-reader", permissions=["user:read"])
    with _auth_client(writer, db_session) as client:
        assert client.post("/api/auth/users", json={
            "username": "bad-email",
            "password": "password123",
            "email": "not-an-email",
        }).status_code == 422
        assert client.post("/api/auth/users", json={
            "username": "short-password",
            "password": "1234567",
        }).status_code == 422
        assert client.post("/api/auth/users", json={
            "username": "extra-field",
            "password": "password123",
            "is_superuser": True,
        }).status_code == 422
    with _auth_client(reader, db_session) as client:
        assert client.get("/api/auth/users?skip=-1").status_code == 422
        assert client.get("/api/auth/users?limit=501").status_code == 422

    root = Path(__file__).resolve().parents[1]
    layout_source = (
        root / "frontend/src/views/Layout.vue"
    ).read_text(encoding="utf-8")
    users_source = (
        root / "frontend/src/views/Users.vue"
    ).read_text(encoding="utf-8")
    user_menu = next(
        line for line in layout_source.splitlines() if "path: '/users'" in line
    )
    assert "permission: 'user:read'" in user_menu
    assert "{ min: 8" in users_source