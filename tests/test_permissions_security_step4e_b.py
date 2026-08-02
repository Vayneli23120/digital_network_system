"""Security Step 4E-B0: permission-management mutation guards."""

import inspect

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


def _permissions_client(current_user, db_session):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.features.auth.router import get_current_user_from_token
    from app.features.permissions import router as permissions_router
    from app.shared.database import get_db

    app = FastAPI()
    app.include_router(permissions_router.router)
    app.dependency_overrides[get_current_user_from_token] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: db_session
    return TestClient(app)


def _enable_auth(monkeypatch):
    from app.shared.config import get_config

    config = get_config()
    monkeypatch.setattr(config.security, "auth_enabled", True)
    monkeypatch.setattr(config.app, "debug", False)


def test_permission_mutation_matrix_is_declared():
    from app.features.permissions import router as permissions_router

    expected = {
        "create_permission": "require_role_write",
        "delete_permission": "require_role_delete",
        "create_role": "require_role_write",
        "update_role": "require_role_write",
        "delete_role": "require_role_delete",
        "clone_role": "require_role_write",
        "update_user_roles": "require_user_write",
        "add_role_to_user": "require_user_write",
        "remove_role_from_user": "require_user_write",
    }
    for function_name, dependency_name in expected.items():
        function = getattr(permissions_router, function_name)
        parameter = inspect.signature(function).parameters.get("_")
        assert parameter is not None, f"{function_name} missing permission dependency"
        assert parameter.default.dependency is getattr(
            permissions_router,
            dependency_name,
        )


def test_authenticated_user_cannot_create_role_or_self_assign_admin(
    db_session, monkeypatch
):
    from app.shared.models import Permission, Role, User

    _enable_auth(monkeypatch)
    user = _create_user(db_session, "ordinary-permissions-user")
    admin_permission = Permission(
        name="admin:all",
        resource="admin",
        action="all",
    )
    admin_role = Role(
        name="target-admin-role",
        description="privileged test role",
        is_system=True,
    )
    admin_role.permissions.append(admin_permission)
    db_session.add_all([admin_permission, admin_role])
    db_session.commit()

    with _permissions_client(user, db_session) as client:
        create_permission = client.post(
            "/api/permissions/permissions",
            json={
                "name": "forged:permission",
                "resource": "forged",
                "action": "permission",
            },
        )
        create_role = client.post(
            "/api/permissions/roles",
            json={"name": "forged-admin-role", "permission_ids": [admin_permission.id]},
        )
        self_assign = client.put(
            f"/api/permissions/users/{user.id}/roles",
            json={"role_ids": [admin_role.id]},
        )

    assert create_permission.status_code == 403
    assert create_role.status_code == 403
    assert self_assign.status_code == 403
    db_session.expire_all()
    stored_user = db_session.query(User).filter(User.id == user.id).one()
    assert stored_user.roles == []
    assert db_session.query(Role).filter(Role.name == "forged-admin-role").first() is None


def test_role_and_user_writers_cannot_cross_responsibility(db_session, monkeypatch):
    from app.shared.models import Role

    _enable_auth(monkeypatch)
    role_writer = _create_user(
        db_session,
        "role-writer",
        permission="role:write",
    )
    user_writer = _create_user(
        db_session,
        "user-writer",
        permission="user:write",
    )
    target_user = _create_user(db_session, "role-assignment-target")
    assignable_role = Role(name="assignable-role", description="benign role")
    db_session.add(assignable_role)
    db_session.commit()

    with _permissions_client(role_writer, db_session) as client:
        create_role = client.post(
            "/api/permissions/roles",
            json={"name": "writer-created-role", "permission_ids": []},
        )
        assign_user = client.put(
            f"/api/permissions/users/{target_user.id}/roles",
            json={"role_ids": [assignable_role.id]},
        )

    with _permissions_client(user_writer, db_session) as client:
        forbidden_role_create = client.post(
            "/api/permissions/roles",
            json={"name": "user-writer-created-role", "permission_ids": []},
        )
        allowed_assignment = client.put(
            f"/api/permissions/users/{target_user.id}/roles",
            json={"role_ids": [assignable_role.id]},
        )

    assert create_role.status_code == 201
    assert assign_user.status_code == 403
    assert forbidden_role_create.status_code == 403
    assert allowed_assignment.status_code == 200
    db_session.refresh(target_user)
    assert [role.id for role in target_user.roles] == [assignable_role.id]