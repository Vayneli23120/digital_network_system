"""Security Step 4B: Deploy permissions, models, paths, and WebSocket identity."""

import asyncio
import inspect
from pathlib import Path

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

import app.shared.models_jobs  # noqa: F401  Register jobs table in metadata.


def test_deploy_model_accepts_current_frontend_payload_with_empty_inactive_fields():
    from app.features.deploy.schemas import DeployRequest

    request = DeployRequest.model_validate({
        "mode": "snippet",
        "engine": "netmiko",
        "napalm_mode": "merge",
        "transfer_mode": "inline",
        "backup_file": "",
        "template_id": "",
        "snippet": "ntp server 192.0.2.1",
        "snippet_position": "smart",
        "base_backup_file": "",
        "target_devices": [1, 2],
        "variables": {"SITE": "DC1"},
        "dry_run": True,
        "parallel_limit": 2,
    })

    assert request.backup_file is None
    assert request.template_id is None
    assert request.base_backup_file is None
    assert request.target_devices == [1, 2]


@pytest.mark.parametrize("payload", [
    {"mode": "backup", "target_devices": [1]},
    {"mode": "template", "target_devices": [1]},
    {"mode": "snippet", "snippet": "", "target_devices": [1]},
    {"mode": "snippet", "snippet": "x", "target_devices": []},
    {"mode": "snippet", "snippet": "x", "target_devices": [1], "parallel_limit": 6},
    {"mode": "snippet", "snippet": "x", "target_devices": [1], "engine": "shell"},
    {"mode": "snippet", "snippet": "x", "target_devices": [0]},
    {"mode": "snippet", "snippet": "x", "target_devices": [1], "unknown": True},
])
def test_deploy_model_rejects_invalid_payload(payload):
    from app.features.deploy.schemas import DeployRequest

    with pytest.raises(ValidationError):
        DeployRequest.model_validate(payload)


def test_schedule_window_format_is_validated():
    from app.features.deploy.schemas import ScheduleDeployRequest

    valid = ScheduleDeployRequest.model_validate({
        "window_id": "20260802_morning",
        "deploy_data": {
            "mode": "snippet",
            "snippet": "ntp server 192.0.2.1",
            "target_devices": [1],
        },
    })
    assert valid.window_id == "20260802_morning"

    with pytest.raises(ValidationError):
        ScheduleDeployRequest.model_validate({
            "window_id": "tomorrow_anytime",
            "deploy_data": {
                "mode": "snippet",
                "snippet": "x",
                "target_devices": [1],
            },
        })


def test_deploy_model_limits_variable_count_and_key_length():
    from app.features.deploy.schemas import DeployRequest

    with pytest.raises(ValidationError, match="变量数量"):
        DeployRequest.model_validate({
            "mode": "snippet",
            "snippet": "x",
            "target_devices": [1],
            "variables": {f"key_{index}": index for index in range(501)},
        })

    with pytest.raises(ValidationError, match="变量名"):
        DeployRequest.model_validate({
            "mode": "snippet",
            "snippet": "x",
            "target_devices": [1],
            "variables": {"x" * 129: "value"},
        })


def test_backup_path_allows_files_inside_root(tmp_path, monkeypatch):
    from app.features.deploy.security import resolve_backup_file

    backup_root = tmp_path / "backups"
    backup_file = backup_root / "switch-01" / "latest.cfg"
    backup_file.parent.mkdir(parents=True)
    backup_file.write_text("hostname SW-01", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert resolve_backup_file("switch-01/latest.cfg", backup_root) == backup_file.resolve()
    assert resolve_backup_file("backups/switch-01/latest.cfg", backup_root) == backup_file.resolve()
    assert resolve_backup_file(backup_file, backup_root) == backup_file.resolve()


def test_backup_path_rejects_traversal_and_outside_absolute_path(tmp_path):
    from app.features.deploy.security import UnsafeBackupPathError, resolve_backup_file

    backup_root = tmp_path / "backups"
    backup_root.mkdir()
    outside = tmp_path / "secret.txt"
    outside.write_text("secret", encoding="utf-8")

    with pytest.raises(UnsafeBackupPathError):
        resolve_backup_file("../secret.txt", backup_root)
    with pytest.raises(UnsafeBackupPathError):
        resolve_backup_file(outside, backup_root)


def test_backup_path_rejects_symlink_escape_when_supported(tmp_path):
    from app.features.deploy.security import UnsafeBackupPathError, resolve_backup_file

    backup_root = tmp_path / "backups"
    backup_root.mkdir()
    outside = tmp_path / "secret.txt"
    outside.write_text("secret", encoding="utf-8")
    link = backup_root / "link.cfg"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("Symlink creation is not available in this environment")

    with pytest.raises(UnsafeBackupPathError):
        resolve_backup_file(link, backup_root)


def test_deploy_http_endpoints_have_expected_permission_dependencies():
    from app.features.deploy import router as deploy_router

    expected = {
        "preview_deploy": "require_config_read",
        "get_compatible_variables": "require_config_read",
        "get_maintenance_windows": "require_config_read",
        "get_deploy_history": "require_config_read",
        "get_deploy_history_detail": "require_config_read",
        "execute_deploy": "require_config_deploy",
        "schedule_deploy": "require_config_deploy",
        "rollback_deploy": "require_config_rollback",
    }
    for function_name, dependency_name in expected.items():
        function = getattr(deploy_router, function_name)
        parameter = inspect.signature(function).parameters.get("_")
        assert parameter is not None, f"{function_name} is missing permission dependency"
        assert parameter.default.dependency is getattr(deploy_router, dependency_name)


@pytest.fixture
def auth_config(monkeypatch):
    from app.shared.config import get_config

    config = get_config()
    monkeypatch.setattr(config.security, "auth_enabled", True)
    monkeypatch.setattr(config.app, "debug", False)
    return config


def _create_user(db_session, username: str, *, superuser: bool = False, permission=None):
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


def _token_for(user):
    from app.features.auth.router import create_access_token

    return create_access_token({"sub": user.username, "user_id": user.id})


def _deploy_client(current_user, db_session):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.features.auth.identity import Principal, get_current_principal
    from app.features.auth.router import get_current_user_from_token
    from app.features.deploy import router as deploy_router
    from app.shared.database import get_db

    app = FastAPI()
    app.include_router(deploy_router.router)
    app.dependency_overrides[get_current_user_from_token] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: db_session
    if current_user is not None:
        principal = Principal(
            username=current_user.username,
            user_id=current_user.id,
            user=current_user,
            auth_source="test",
        )
        app.dependency_overrides[get_current_principal] = lambda: principal
    return TestClient(app)


def test_http_deploy_read_endpoint_enforces_permission(db_session, auth_config):
    reader = _create_user(db_session, "http-config-reader", permission="config:read")
    deployer = _create_user(db_session, "http-config-deployer", permission="config:deploy")
    admin = _create_user(db_session, "http-deploy-admin", superuser=True)

    with _deploy_client(None, db_session) as client:
        assert client.get("/api/deploy/compatible-variables").status_code == 401
    with _deploy_client(reader, db_session) as client:
        assert client.get("/api/deploy/compatible-variables").status_code == 200
    with _deploy_client(deployer, db_session) as client:
        assert client.get("/api/deploy/compatible-variables").status_code == 403
    with _deploy_client(admin, db_session) as client:
        assert client.get("/api/deploy/compatible-variables").status_code == 200


def test_http_deploy_execute_denies_reader_before_business_logic(db_session, auth_config):
    reader = _create_user(db_session, "http-execute-reader", permission="config:read")
    payload = {
        "mode": "snippet",
        "snippet": "ntp server 192.0.2.1",
        "target_devices": [999],
        "dry_run": True,
    }

    with _deploy_client(reader, db_session) as client:
        response = client.post("/api/deploy/execute", json=payload)

    assert response.status_code == 403


def test_websocket_deploy_requires_config_deploy(db_session, auth_config):
    from app.features.deploy.security import authorize_deploy_token

    viewer = _create_user(db_session, "deploy-viewer", permission="config:read")

    with pytest.raises(HTTPException) as exc:
        authorize_deploy_token(_token_for(viewer), db_session)

    assert exc.value.status_code == 403


def test_deploy_permission_tiers_are_separated(db_session, auth_config):
    from app.features.deploy.router import (
        require_config_deploy,
        require_config_read,
        require_config_rollback,
    )

    reader = _create_user(db_session, "config-reader", permission="config:read")
    deployer = _create_user(db_session, "config-deployer", permission="config:deploy")
    rollback_operator = _create_user(
        db_session,
        "config-rollback-operator",
        permission="config:rollback",
    )

    assert asyncio.run(require_config_read(reader, db_session)).id == reader.id
    assert asyncio.run(require_config_deploy(deployer, db_session)).id == deployer.id
    assert asyncio.run(require_config_rollback(rollback_operator, db_session)).id == rollback_operator.id

    for checker, user in (
        (require_config_deploy, reader),
        (require_config_rollback, reader),
        (require_config_read, deployer),
        (require_config_deploy, rollback_operator),
    ):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(checker(user, db_session))
        assert exc.value.status_code == 403


def test_websocket_deploy_allows_deployer_and_admin(db_session, auth_config):
    from app.features.deploy.security import authorize_deploy_token

    deployer = _create_user(db_session, "deployer", permission="config:deploy")
    admin = _create_user(db_session, "deploy-admin", superuser=True)

    assert authorize_deploy_token(_token_for(deployer), db_session).username == "deployer"
    assert authorize_deploy_token(_token_for(admin), db_session).username == "deploy-admin"


def test_websocket_deploy_rejects_missing_token(db_session, auth_config):
    from app.features.deploy.security import authorize_deploy_token

    with pytest.raises(HTTPException) as exc:
        authorize_deploy_token(None, db_session)

    assert exc.value.status_code == 401


def _websocket_app(db_session, monkeypatch):
    from fastapi import FastAPI

    import app.shared.database as database_module
    from app.features.websocket.router import router

    def test_get_db():
        yield db_session

    monkeypatch.setattr(database_module, "get_db", test_get_db)
    app = FastAPI()
    app.include_router(router)
    return app


def test_websocket_route_rejects_missing_token_before_device_lookup(
    db_session, auth_config, monkeypatch
):
    from fastapi.testclient import TestClient
    from starlette.websockets import WebSocketDisconnect

    app = _websocket_app(db_session, monkeypatch)
    payload = {
        "action": "start_deploy",
        "mode": "snippet",
        "snippet": "ntp server 192.0.2.1",
        "target_devices": [999],
        "dry_run": True,
    }

    with TestClient(app).websocket_connect("/ws/deploy/test-missing-token") as websocket:
        websocket.send_json(payload)
        error = websocket.receive_json()
        assert error["type"] == "deploy_error"
        assert error["status_code"] == 401
        with pytest.raises(WebSocketDisconnect) as exc:
            websocket.receive_json()
        assert exc.value.code == 4401


def test_websocket_route_rejects_reader_before_device_lookup(
    db_session, auth_config, monkeypatch
):
    from fastapi.testclient import TestClient
    from starlette.websockets import WebSocketDisconnect

    reader = _create_user(db_session, "ws-config-reader", permission="config:read")
    app = _websocket_app(db_session, monkeypatch)
    payload = {
        "action": "start_deploy",
        "access_token": _token_for(reader),
        "mode": "snippet",
        "snippet": "ntp server 192.0.2.1",
        "target_devices": [999],
        "dry_run": True,
    }

    with TestClient(app).websocket_connect("/ws/deploy/test-reader") as websocket:
        websocket.send_json(payload)
        error = websocket.receive_json()
        assert error["type"] == "deploy_error"
        assert error["status_code"] == 403
        with pytest.raises(WebSocketDisconnect) as exc:
            websocket.receive_json()
        assert exc.value.code == 4403


def test_websocket_route_allows_deployer_then_runs_business_validation(
    db_session, auth_config, monkeypatch
):
    from fastapi.testclient import TestClient

    deployer = _create_user(db_session, "ws-config-deployer", permission="config:deploy")
    app = _websocket_app(db_session, monkeypatch)
    payload = {
        "action": "start_deploy",
        "access_token": _token_for(deployer),
        "mode": "snippet",
        "snippet": "ntp server 192.0.2.1",
        "target_devices": [999],
        "dry_run": True,
    }

    with TestClient(app).websocket_connect("/ws/deploy/test-deployer") as websocket:
        websocket.send_json(payload)
        error = websocket.receive_json()

    assert error["type"] == "deploy_error"
    assert error["message"] == "未找到指定的设备"
    assert "status_code" not in error


def test_stream_history_uses_authenticated_username_source():
    root = Path(__file__).resolve().parents[1]
    stream_source = (
        root / "app/features/deploy/deploy_stream_service.py"
    ).read_text(encoding="utf-8")
    websocket_source = (
        root / "app/features/websocket/router.py"
    ).read_text(encoding="utf-8")
    # 批次五 946 切片 5：deploy WS 报文构造随执行逻辑迁入 useDeployExecution composable
    frontend_source = (
        root / "frontend/src/composables/useDeployExecution.js"
    ).read_text(encoding="utf-8")

    assert 'username="Web"' not in stream_source
    assert 'created_by="Web"' not in stream_source
    assert "username=principal.username" in websocket_source
    assert "user_id=principal.user_id" in websocket_source
    assert "access_token: authStore.accessToken" in frontend_source


def test_all_product_template_paths_use_shared_renderer():
    root = Path(__file__).resolve().parents[1]
    product_files = [
        root / "app/features/deploy/router.py",
        root / "app/features/deploy/deploy_service.py",
        root / "app/features/templates/template_service.py",
        root / "app/features/websocket/router.py",
    ]

    for file_path in product_files:
        source = file_path.read_text(encoding="utf-8")
        assert "render_network_template" in source
        assert "from jinja2 import Template" not in source
        assert "tmpl = Template(" not in source


def test_http_audit_uses_authenticated_principal_source():
    root = Path(__file__).resolve().parents[1]
    source = (root / "app/features/deploy/router.py").read_text(encoding="utf-8")

    assert 'operator="Web"' not in source
    assert 'created_by="Web"' not in source
    assert "operator=current_username" in source
    assert "created_by=current_username" in source


def test_stream_netmiko_blocks_dangerous_command_before_connect(monkeypatch):
    import netmiko

    import app.features.deploy.deploy_stream_service as stream_module

    monkeypatch.setattr(stream_module, "NETMIKO_AVAILABLE", True)
    monkeypatch.setattr(
        netmiko,
        "ConnectHandler",
        lambda **kwargs: pytest.fail("ConnectHandler must not run for blocked commands"),
    )
    service = stream_module.DeployStreamService()

    result = service._deploy_single_device_netmiko(
        {"id": 1, "name": "SW-01", "ip": "192.0.2.1", "vendor": "cisco"},
        "reload",
        {"username": "test", "password": "test"},
    )

    assert result["success"] is False
    assert "安全守卫拒绝" in result["message"]


def test_stream_napalm_blocks_dangerous_command_before_connect(monkeypatch):
    import app.features.deploy.deploy_stream_service as stream_module

    monkeypatch.setattr(stream_module, "NAPALM_AVAILABLE", True)
    monkeypatch.setattr(
        stream_module,
        "get_network_driver",
        lambda _driver: pytest.fail("NAPALM driver must not run for blocked commands"),
    )
    service = stream_module.DeployStreamService()

    result = service._deploy_single_device_napalm(
        {"id": 1, "name": "SW-01", "ip": "192.0.2.1", "vendor": "cisco"},
        "write erase",
        {"username": "test", "password": "test"},
    )

    assert result["success"] is False
    assert "安全守卫拒绝" in result["message"]


def test_http_engine_independent_preflight_blocks_dangerous_commands():
    from app.core.command_guard import CommandGuardError
    from app.features.deploy.security import validate_deploy_config

    devices = [
        {"name": "SW-01", "vendor": "cisco"},
        {"name": "SW-02", "vendor": "juniper"},
    ]

    with pytest.raises(CommandGuardError):
        validate_deploy_config("hostname safe\nreload", devices)


def test_http_engine_independent_preflight_accepts_safe_commands():
    from app.features.deploy.security import validate_deploy_config

    validate_deploy_config(
        "hostname SW-01\ninterface Gi0/1\ndescription uplink",
        [{"name": "SW-01", "vendor": "cisco"}],
    )
