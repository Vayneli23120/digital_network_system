"""Security Step 4E-A: Backups and Templates RBAC and input safety."""

import asyncio
import inspect
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

import app.shared.models_jobs  # noqa: F401  Register jobs table in metadata.


def _create_user(db_session, username: str, *, superuser=False, permission=None):
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


@pytest.fixture
def auth_config(monkeypatch):
    from app.shared.config import get_config

    config = get_config()
    monkeypatch.setattr(config.security, "auth_enabled", True)
    monkeypatch.setattr(config.app, "debug", False)
    return config


def _principal(user):
    from app.features.auth.identity import Principal

    return Principal(
        username=user.username,
        user_id=user.id,
        user=user,
        auth_source="test",
    )


def _backup_client(current_user, db_session):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.features.auth.identity import get_current_principal
    from app.features.auth.router import get_current_user_from_token
    from app.features.backups import router as backup_router
    from app.shared.database import get_db

    app = FastAPI()
    app.include_router(backup_router.router)
    app.dependency_overrides[get_current_user_from_token] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: db_session
    if current_user is not None:
        app.dependency_overrides[get_current_principal] = lambda: _principal(current_user)
    return TestClient(app)


def _template_client(current_user, db_session):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.features.auth.router import get_current_user_from_token
    from app.features.templates import router as template_router
    from app.shared.database import get_db

    app = FastAPI()
    app.include_router(template_router.router)
    app.dependency_overrides[get_current_user_from_token] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: db_session
    return TestClient(app)


def test_backup_path_confines_reads_and_returns_relative_reference(tmp_path, monkeypatch):
    from app.features.backups.security import (
        UnsafeBackupRecordPathError,
        read_backup_text,
        resolve_backup_record_file,
        safe_backup_reference,
    )

    root = tmp_path / "backups"
    backup_file = root / "switch-01" / "latest.cfg"
    backup_file.parent.mkdir(parents=True)
    backup_file.write_text("hostname SW-01", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert resolve_backup_record_file("switch-01/latest.cfg", root) == backup_file.resolve()
    assert resolve_backup_record_file("backups/switch-01/latest.cfg", root) == backup_file.resolve()
    assert safe_backup_reference(backup_file, root) == "switch-01/latest.cfg"
    assert read_backup_text(backup_file, root) == "hostname SW-01"

    outside = tmp_path / "secret.cfg"
    outside.write_text("secret", encoding="utf-8")
    with pytest.raises(UnsafeBackupRecordPathError):
        resolve_backup_record_file("../secret.cfg", root)
    with pytest.raises(UnsafeBackupRecordPathError):
        resolve_backup_record_file(outside, root)


def test_backup_write_path_ignores_untrusted_device_name(tmp_path, monkeypatch):
    from app.features.backups import netmiko_service

    monkeypatch.setattr(netmiko_service.NetmikoService, "connect", lambda *_: None)
    monkeypatch.setattr(
        netmiko_service.NetmikoService,
        "get_running_config",
        lambda *_: "hostname safe\n",
    )
    monkeypatch.setattr(netmiko_service.NetmikoService, "disconnect", lambda *_: None)
    device = SimpleNamespace(
        id=42,
        name="..\\..\\outside/escape",
        ip="192.0.2.42",
    )

    result = netmiko_service.backup_device_config(device, {}, str(tmp_path))

    assert result["success"] is True
    backup_path = Path(result["file_path"]).resolve()
    assert backup_path.is_relative_to(tmp_path.resolve())
    assert backup_path.parent.name == "device-42"
    assert backup_path.name.startswith("device-42_")


def test_backup_path_rejects_symlink_escape_when_supported(tmp_path):
    from app.features.backups.security import (
        UnsafeBackupRecordPathError,
        resolve_backup_record_file,
    )

    root = tmp_path / "backups"
    root.mkdir()
    outside = tmp_path / "secret.cfg"
    outside.write_text("secret", encoding="utf-8")
    link = root / "link.cfg"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("Symlink creation is unavailable")

    with pytest.raises(UnsafeBackupRecordPathError):
        resolve_backup_record_file(link, root)


def test_backup_text_size_is_bounded(tmp_path):
    from app.features.backups.security import read_backup_bytes, read_backup_text

    root = tmp_path / "backups"
    root.mkdir()
    backup_file = root / "large.cfg"
    backup_file.write_text("123456789", encoding="utf-8")

    with pytest.raises(ValueError, match="大小"):
        read_backup_text(backup_file, root, max_bytes=8)
    with pytest.raises(ValueError, match="大小"):
        read_backup_bytes(backup_file, root, max_bytes=8)


def test_backup_http_permission_matrix_is_declared():
    from app.features.backups import router as backup_router

    expected = {
        "backup_device": "require_backup_execute",
        "list_backups": "require_backup_read",
        "get_backup_content": "require_backup_read",
        "download_backup": "require_backup_read",
        "get_backup_diff": "require_backup_read",
        "list_needs_backup_endpoint": "require_backup_read",
        "mark_config_changed": "require_backup_execute",
        "batch_backup": "require_backup_batch",
        "delete_backup": "require_backup_delete",
    }
    for function_name, dependency_name in expected.items():
        function = getattr(backup_router, function_name)
        parameter = inspect.signature(function).parameters.get("_")
        assert parameter is not None, f"{function_name} missing permission dependency"
        assert parameter.default.dependency is getattr(backup_router, dependency_name)


def test_backup_permission_tiers_are_separated(db_session, auth_config):
    from app.features.backups.router import (
        require_backup_batch,
        require_backup_delete,
        require_backup_execute,
        require_backup_read,
    )

    checkers = {
        "backup:read": require_backup_read,
        "backup:execute": require_backup_execute,
        "backup:batch": require_backup_batch,
        "backup:delete": require_backup_delete,
    }
    users = {
        permission: _create_user(
            db_session,
            f"tier-{permission.replace(':', '-')}",
            permission=permission,
        )
        for permission in checkers
    }

    for permission, checker in checkers.items():
        assert asyncio.run(checker(users[permission], db_session)).id == users[permission].id
        other_permission = next(name for name in users if name != permission)
        with pytest.raises(HTTPException) as exc:
            asyncio.run(checker(users[other_permission], db_session))
        assert exc.value.status_code == 403


def test_backup_list_api_redacts_absolute_path(
    db_session, auth_config, tmp_path, monkeypatch
):
    from app.shared.config import get_config
    from app.shared.models import BackupRecord, Device

    root = tmp_path / "backups"
    backup_file = root / "sw-01" / "config.cfg"
    backup_file.parent.mkdir(parents=True)
    backup_file.write_text("hostname SW-01", encoding="utf-8")
    monkeypatch.setattr(get_config().storage, "backup_dir", str(root))
    device = Device(name="backup-list-device", ip="192.0.2.10")
    db_session.add(device)
    db_session.flush()
    db_session.add(BackupRecord(
        device_id=device.id,
        device_name=device.name,
        backup_file=str(backup_file),
    ))
    db_session.commit()
    reader = _create_user(db_session, "backup-reader", permission="backup:read")

    with _backup_client(reader, db_session) as client:
        response = client.get("/api/backups")

    assert response.status_code == 200
    reference = response.json()["items"][0]["backup_file"]
    assert reference == "sw-01/config.cfg"
    assert str(tmp_path) not in response.text


def test_backup_content_rejects_record_outside_root(
    db_session, auth_config, tmp_path, monkeypatch
):
    from app.shared.config import get_config
    from app.shared.models import BackupRecord, Device

    root = tmp_path / "backups"
    root.mkdir()
    outside = tmp_path / "secret.cfg"
    outside.write_text("secret", encoding="utf-8")
    monkeypatch.setattr(get_config().storage, "backup_dir", str(root))
    device = Device(name="outside-backup-device", ip="192.0.2.11")
    db_session.add(device)
    db_session.flush()
    record = BackupRecord(
        device_id=device.id,
        device_name=device.name,
        backup_file=str(outside),
    )
    db_session.add(record)
    db_session.commit()
    reader = _create_user(db_session, "outside-backup-reader", permission="backup:read")

    with _backup_client(reader, db_session) as client:
        response = client.get(f"/api/backups/{record.id}/content")

    assert response.status_code == 400
    assert str(outside) not in response.text


def test_backup_download_is_authenticated_bounded_and_path_safe(
    db_session, auth_config, tmp_path, monkeypatch
):
    from app.shared.config import get_config
    from app.shared.models import BackupRecord, Device

    root = tmp_path / "backups"
    backup_file = root / "device-15" / "config.cfg"
    backup_file.parent.mkdir(parents=True)
    backup_file.write_bytes(b"hostname SW-15\n")
    monkeypatch.setattr(get_config().storage, "backup_dir", str(root))
    device = Device(name="download-backup-device", ip="192.0.2.15")
    db_session.add(device)
    db_session.flush()
    record = BackupRecord(
        device_id=device.id,
        device_name=device.name,
        backup_file=str(backup_file),
    )
    db_session.add(record)
    db_session.commit()
    reader = _create_user(db_session, "download-backup-reader", permission="backup:read")

    with _backup_client(None, db_session) as client:
        denied = client.get(f"/api/backups/{record.id}/download")
    with _backup_client(reader, db_session) as client:
        response = client.get(f"/api/backups/{record.id}/download")

    assert denied.status_code == 401
    assert response.status_code == 200
    assert response.content == b"hostname SW-15\n"
    assert response.headers["content-disposition"] == (
        f'attachment; filename="backup-{record.id}.cfg"'
    )
    assert str(root) not in response.text


def test_backup_diff_uses_record_ids_not_server_paths(
    db_session, auth_config, tmp_path, monkeypatch
):
    from app.shared.config import get_config
    from app.shared.models import BackupRecord, Device

    root = tmp_path / "backups"
    old_file = root / "sw-02" / "old.cfg"
    new_file = root / "sw-02" / "new.cfg"
    old_file.parent.mkdir(parents=True)
    old_file.write_text("hostname old\n", encoding="utf-8")
    new_file.write_text("hostname new\n", encoding="utf-8")
    monkeypatch.setattr(get_config().storage, "backup_dir", str(root))
    device = Device(name="diff-backup-device", ip="192.0.2.14")
    db_session.add(device)
    db_session.flush()
    old_record = BackupRecord(
        device_id=device.id,
        device_name=device.name,
        backup_file=str(old_file),
        backup_time=datetime.utcnow() - timedelta(minutes=1),
    )
    new_record = BackupRecord(
        device_id=device.id,
        device_name=device.name,
        backup_file=str(new_file),
        backup_time=datetime.utcnow(),
    )
    db_session.add_all([old_record, new_record])
    db_session.commit()
    reader = _create_user(db_session, "diff-backup-reader", permission="backup:read")

    with _backup_client(reader, db_session) as client:
        response = client.get(f"/api/backups/{new_record.id}/diff")

    assert response.status_code == 200
    diff = response.json()["diff"]
    assert f"backup-{old_record.id}" in diff
    assert f"backup-{new_record.id}" in diff
    assert str(root) not in diff


def test_backup_uses_principal_as_operator(
    db_session, auth_config, tmp_path, monkeypatch
):
    from app.features.backups import router as backup_router
    from app.shared.config import get_config
    from app.shared.models import BackupRecord, CredentialGroup, Device, LogEntry

    root = tmp_path / "backups"
    root.mkdir()
    monkeypatch.setattr(get_config().storage, "backup_dir", str(root))
    device = Device(
        name="principal-backup-device",
        ip="192.0.2.12",
        credential_group="default",
    )
    credential = CredentialGroup(
        name="default",
        username="netops",
        password_encrypted="encrypted",
    )
    db_session.add_all([device, credential])
    db_session.commit()
    executor = _create_user(db_session, "trusted-backup-operator", permission="backup:execute")
    backup_path = root / "principal-backup-device" / "config.cfg"
    backup_path.parent.mkdir(parents=True)

    def fake_backup(*_args):
        backup_path.write_text("hostname SW-01", encoding="utf-8")
        return {
            "success": True,
            "file_path": str(backup_path),
            "file_size": backup_path.stat().st_size,
            "md5_hash": "abc",
            "has_change": True,
            "message": "ok",
        }

    monkeypatch.setattr(backup_router, "decrypt_password", lambda _value: "secret")
    monkeypatch.setattr(backup_router, "backup_device_config", fake_backup)
    monkeypatch.setattr(
        "app.shared.git_config_service.get_git_config_service",
        lambda: type("GitService", (), {"available": False})(),
    )

    # 批次二·步骤5：备份必须携带操作者会话级凭证（密码不落服务器）
    from app.features.backups.schemas import BackupRequest

    result = asyncio.run(
        backup_router.backup_device(
            device.id,
            BackupRequest(username="netops", password="secret"),
            _principal(executor),
            db_session,
            None,
        )
    )

    assert result["success"] is True
    record = db_session.query(BackupRecord).filter(BackupRecord.device_id == device.id).one()
    log = db_session.query(LogEntry).filter(LogEntry.target == device.name).one()
    assert record.operator == executor.username
    assert log.created_by == executor.username


def test_backup_api_redacts_internal_failure_details(
    db_session, auth_config, monkeypatch
):
    from app.features.backups import router as backup_router
    from app.shared.models import CredentialGroup, Device

    device = Device(
        name="failed-backup-device",
        ip="192.0.2.16",
        credential_group="default",
    )
    credential = CredentialGroup(
        name="default",
        username="netops",
        password_encrypted="encrypted",
    )
    db_session.add_all([device, credential])
    db_session.commit()
    admin = _create_user(db_session, "failed-backup-admin", superuser=True)
    secret_detail = r"Permission denied: C:\private\backups\secret.cfg"

    monkeypatch.setattr(backup_router, "decrypt_password", lambda _value: "secret")
    monkeypatch.setattr(
        backup_router,
        "backup_device_config",
        lambda *_args: {
            "success": False,
            "file_path": "",
            "file_size": 0,
            "md5_hash": "",
            "has_change": False,
            "message": secret_detail,
        },
    )
    monkeypatch.setattr(
        "app.services.notification_service.get_notification_service",
        lambda: type("Notifier", (), {"notify_backup_failure": lambda *_args: None})(),
    )

    # 批次二·步骤5：备份必须携带操作者会话级凭证（密码不落服务器）
    creds = {"username": "netops", "password": "secret"}
    with _backup_client(admin, db_session) as client:
        single = client.post(f"/api/backups/backup/{device.id}", json=creds)
        batch = client.post("/api/backups/batch", json={"device_ids": [device.id], **creds})

    assert single.status_code == 500
    assert single.json()["detail"] == "备份失败，请查看服务端日志"
    assert batch.status_code == 200
    assert batch.json()["results"][0]["message"] == "备份失败，请查看服务端日志"
    assert secret_detail not in single.text
    assert secret_detail not in batch.text


def test_backup_sync_redacts_paths_and_failure_details(
    db_manager, db_session, sample_device_data, tmp_path, monkeypatch
):
    """同步备份（HTTP 路径）不泄露落盘绝对路径与内部失败详情

    批次二·步骤5：celery 异步备份任务已下线（无法携带操作者会话级凭证），原异步 job
    结果脱敏测试改写为同步等价覆盖：成功响应与 LogEntry 不含绝对路径；失败被归一封皮
    为通用消息且不含内部详情。
    """
    from app.features.backups import router as backup_router
    from app.shared.config import get_config
    from app.shared.models import Device, LogEntry

    root = tmp_path / "backups"
    backup_file = root / "device-17" / "config.cfg"
    backup_file.parent.mkdir(parents=True)
    backup_file.write_text("hostname sync-safe\n", encoding="utf-8")
    monkeypatch.setattr(get_config().storage, "backup_dir", str(root))
    device = Device(**sample_device_data)
    db_session.add(device)
    db_session.commit()
    admin = _create_user(db_session, "backup-sync-redact", superuser=True)

    monkeypatch.setattr(
        backup_router,
        "backup_device_config",
        lambda *_args: {
            "success": True,
            "file_path": str(backup_file),
            "file_size": backup_file.stat().st_size,
            "md5_hash": "abc123",
            "has_change": True,
            "message": "备份成功",
        },
    )

    creds = {"username": "netops", "password": "secret"}
    with _backup_client(admin, db_session) as client:
        resp = client.post(f"/api/backups/backup/{device.id}", json=creds)

    assert resp.status_code == 200
    assert "file_path" not in resp.json()
    assert str(root) not in resp.text
    assert "config.cfg" not in resp.text

    log_entry = (
        db_session.query(LogEntry)
        .filter(LogEntry.operation == "备份配置")
        .order_by(LogEntry.id.desc())
        .first()
    )
    assert log_entry is not None
    assert str(root) not in log_entry.log_content
    assert "config.cfg" not in log_entry.log_content

    # 失败路径：内部错误详情被归一封皮为通用消息
    secret_detail = f"Permission denied: {tmp_path / 'private.cfg'}"
    monkeypatch.setattr(
        backup_router,
        "backup_device_config",
        lambda *_args: {
            "success": False,
            "file_path": "",
            "file_size": 0,
            "md5_hash": "",
            "has_change": False,
            "message": secret_detail,
        },
    )

    with _backup_client(admin, db_session) as client:
        resp2 = client.post(f"/api/backups/backup/{device.id}", json=creds)

    assert resp2.status_code == 500
    assert resp2.json()["detail"] == "备份失败，请查看服务端日志"
    assert secret_detail not in resp2.text


def test_backup_delete_removes_record_and_managed_file(
    db_session, auth_config, tmp_path, monkeypatch
):
    from app.shared.config import get_config
    from app.shared.models import BackupRecord, Device

    root = tmp_path / "backups"
    backup_file = root / "delete-device" / "config.cfg"
    backup_file.parent.mkdir(parents=True)
    backup_file.write_text("hostname delete", encoding="utf-8")
    monkeypatch.setattr(get_config().storage, "backup_dir", str(root))
    device = Device(name="delete-backup-device", ip="192.0.2.13")
    db_session.add(device)
    db_session.flush()
    record = BackupRecord(
        device_id=device.id,
        device_name=device.name,
        backup_file=str(backup_file),
    )
    db_session.add(record)
    db_session.commit()
    backup_id = record.id
    deleter = _create_user(db_session, "backup-deleter", permission="backup:delete")

    with _backup_client(deleter, db_session) as client:
        response = client.delete(f"/api/backups/{backup_id}")

    assert response.status_code == 200
    assert db_session.query(BackupRecord).filter(BackupRecord.id == backup_id).first() is None
    assert not backup_file.exists()


def test_batch_backup_model_rejects_empty_negative_and_too_many_ids():
    from app.features.backups.schemas import BatchBackupRequest

    for payload in (
        {"device_ids": []},
        {"device_ids": [0]},
        {"device_ids": list(range(1, 102))},
    ):
        with pytest.raises(ValidationError):
            BatchBackupRequest.model_validate(payload)


def test_template_models_reject_extra_fields_and_invalid_variables():
    from app.features.templates.schemas import (
        MAX_TEMPLATE_VARIABLES_BYTES,
        TemplateCreateRequest,
        TemplateRenderRequest,
        TemplateUpdateRequest,
    )

    valid = TemplateCreateRequest(
        name=" safe ",
        template_content="hostname {{ HOSTNAME }}",
        variables='{"HOSTNAME":"SW-01"}',
    )
    assert valid.name == "safe"
    assert valid.to_service_dict()["variables"] == '{"HOSTNAME":"SW-01"}'

    with pytest.raises(ValidationError):
        TemplateCreateRequest(
            name="unsafe",
            template_content="x",
            id=999,
        )
    with pytest.raises(ValidationError):
        TemplateUpdateRequest.model_validate({"created_at": "2020-01-01"})
    with pytest.raises(ValidationError):
        TemplateCreateRequest(name="bad", template_content="x", variables="not-json")
    with pytest.raises(ValidationError):
        TemplateCreateRequest(name="bad", template_content="x", variables="123")
    oversized = {"value": "x" * MAX_TEMPLATE_VARIABLES_BYTES}
    with pytest.raises(ValidationError, match="大小"):
        TemplateCreateRequest(name="bad", template_content="x", variables=oversized)
    with pytest.raises(ValidationError, match="大小"):
        TemplateUpdateRequest(variables=oversized)
    with pytest.raises(ValidationError, match="大小"):
        TemplateRenderRequest.model_validate(oversized)


def test_template_service_whitelists_model_fields(db_session):
    from app.features.templates.template_service import create_template, update_template
    from app.shared.models import ConfigTemplate

    created = create_template(db_session, {
        "name": "whitelist-template",
        "template_content": "hostname {{ HOSTNAME }}",
        "variables": "{}",
        "id": 999,
        "created_at": datetime(1999, 1, 1),
    })
    template = db_session.query(ConfigTemplate).filter(ConfigTemplate.id == created["id"]).one()
    assert template.id != 999
    original_created_at = template.created_at

    update_template(db_session, template.id, {
        "name": "whitelist-template-updated",
        "created_at": datetime(2000, 1, 1),
        "id": 777,
    })
    db_session.refresh(template)
    assert template.name == "whitelist-template-updated"
    assert template.id == created["id"]
    assert template.created_at == original_created_at


def test_template_http_permission_matrix_is_declared():
    from app.features.templates import router as template_router

    expected = {
        "api_list_templates": "require_template_read",
        "api_get_template": "require_template_read",
        "api_create_template": "require_template_write",
        "api_update_template": "require_template_write",
        "api_delete_template": "require_template_delete",
        "api_render_template": "require_template_render",
    }
    for function_name, dependency_name in expected.items():
        function = getattr(template_router, function_name)
        parameter = inspect.signature(function).parameters.get("_")
        assert parameter is not None, f"{function_name} missing permission dependency"
        assert parameter.default.dependency is getattr(template_router, dependency_name)


def test_template_http_permissions_are_separated(db_session, auth_config):
    reader = _create_user(db_session, "template-reader", permission="template:read")
    writer = _create_user(db_session, "template-writer", permission="template:write")
    renderer = _create_user(db_session, "template-renderer", permission="template:render")
    admin = _create_user(db_session, "template-admin", superuser=True)

    with _template_client(reader, db_session) as client:
        assert client.get("/api/templates").status_code == 200
        assert client.post(
            "/api/templates",
            json={"name": "denied", "template_content": "x"},
        ).status_code == 403
    with _template_client(writer, db_session) as client:
        assert client.get("/api/templates").status_code == 403
        response = client.post(
            "/api/templates",
            json={"name": "writer-created", "template_content": "hostname {{ HOSTNAME }}"},
        )
        assert response.status_code == 200
        template_id = response.json()["id"]
    with _template_client(renderer, db_session) as client:
        response = client.post(
            f"/api/templates/{template_id}/render",
            json={"HOSTNAME": "SW-01"},
        )
        assert response.status_code == 200
        assert "hostname SW-01" in response.json()["content"]
    with _template_client(admin, db_session) as client:
        assert client.delete(f"/api/templates/{template_id}").status_code == 200


def test_frontend_does_not_send_backup_operator():
    root = Path(__file__).resolve().parents[1]
    api_source = (root / "frontend/src/api/index.js").read_text(encoding="utf-8")
    caller_sources = [
        root / "frontend/src/views/Backups.vue",
        root / "frontend/src/views/DeviceDetail.vue",
        root / "frontend/src/views/Devices.vue",
    ]

    assert "backupDevice(deviceId, operator)" not in api_source
    assert "batchBackup(deviceIds, operator)" not in api_source
    assert "params: { operator }" not in api_source
    for caller_path in caller_sources:
        source = caller_path.read_text(encoding="utf-8")
        assert "backupDevice(route.params.id, 'Web')" not in source
        assert "backupDeviceApi(row.id, 'Web')" not in source
        assert "batchBackup(selectedDeviceIds.value, 'Web')" not in source
        assert "batchBackupApi(selectedDevices.value, 'Web')" not in source

        backups_source = caller_sources[0].read_text(encoding="utf-8")
        assert "downloadBackupFile(row.id)" in backups_source
        assert "link.href = `/api/backups/" not in backups_source


def test_backup_network_operations_are_threaded_and_menus_use_read_permissions():
    root = Path(__file__).resolve().parents[1]
    router_source = (
        root / "app/features/backups/router.py"
    ).read_text(encoding="utf-8")
    layout_source = (
        root / "frontend/src/views/Layout.vue"
    ).read_text(encoding="utf-8")

    assert "await run_device_op(\n            backup_device_config" in router_source
    backup_menu = next(line for line in layout_source.splitlines() if "path: '/backups'" in line)
    template_menu = next(line for line in layout_source.splitlines() if "path: '/templates'" in line)
    assert "permission: 'backup:read'" in backup_menu
    assert "permission: 'template:read'" in template_menu
