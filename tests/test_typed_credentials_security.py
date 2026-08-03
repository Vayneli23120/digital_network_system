"""批次二·步骤5 · 会话级 SSH 凭证 + 备份提醒（切片 A）+ 部署凭证/二次确认/下线异步（切片 B）。

运行时（db_session + monkeypatch）覆盖：
- 备份单台/批量：无操作者凭证 + credential_session_required=True → 400；
  带操作者凭证 → 落 BackupRecord + last_backup_time；认证失败 → 401/auth_failed 且响应不含口令。
- needs-backup：config_changed 与 backup_overdue 两类原因都列出；mark-config-changed 生效。
- credential_session_required=False → 显式降级回退服务器存储的 CredentialGroup。
- 部署/回滚凭证解析：build_operator_credential_groups 构建单个 default 组、拒绝部分填写；
  resolve_operator_credentials 开关开→400、开关关→None 降级；回滚端点无凭证→400。
静态断言：异步备份端点、定时部署端点 / schedule schema 已下线；celery 不再注册 backup/deploy_tasks。
"""

from datetime import datetime, timedelta

import pytest

import app.shared.models_jobs  # noqa: F401  Register jobs table in metadata.


def _create_user(db_session, username, *, superuser=False, permission=None):
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
    monkeypatch.setattr(config.security, "credential_session_required", True)
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


def _patch_backup_success(monkeypatch, root, message="备份成功"):
    """将 backup_device_config 打桩为成功，并把备份文件写到 root 下受管目录。"""
    from app.features.backups import router as backup_router

    def fake_backup(device, credentials, backup_dir):
        from pathlib import Path

        backup_path = Path(backup_dir) / f"device-{device.id}" / "config.cfg"
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        backup_path.write_text("hostname SW-01\n", encoding="utf-8")
        return {
            "success": True,
            "file_path": str(backup_path),
            "file_size": backup_path.stat().st_size,
            "md5_hash": "abc123",
            "has_change": True,
            "message": message,
        }

    monkeypatch.setattr(backup_router, "backup_device_config", fake_backup)
    monkeypatch.setattr(
        "app.shared.git_config_service.get_git_config_service",
        lambda: type("GitService", (), {"available": False})(),
    )


def _patch_backup_auth_failure(monkeypatch):
    """将 backup_device_config 打桩为抛 NetmikoAuthenticationException。"""
    from app.features.backups import router as backup_router
    from app.features.backups.netmiko_service import NetmikoAuthenticationException

    def raise_auth(*_args, **_kwargs):
        raise NetmikoAuthenticationException("authentication failed")

    monkeypatch.setattr(backup_router, "backup_device_config", raise_auth)


def _patch_decrypt(monkeypatch):
    from app.features.backups import router as backup_router

    monkeypatch.setattr(backup_router, "decrypt_password", lambda _value: "secret")


def _make_device(db_session, name, *, deployment_status="in-use", credential_group="default"):
    from app.shared.models import Device

    device = Device(
        name=name,
        ip=f"192.0.2.{abs(hash(name)) % 200 + 1}",
        deployment_status=deployment_status,
        credential_group=credential_group,
    )
    db_session.add(device)
    db_session.commit()
    db_session.refresh(device)
    return device


def test_backup_requires_operator_credentials_when_flag_on(db_session, auth_config):
    from app.shared.models import CredentialGroup

    device = _make_device(db_session, "cred-required-device")
    db_session.add(CredentialGroup(name="default", username="netops", password_encrypted="encrypted"))
    db_session.commit()
    admin = _create_user(db_session, "cred-required-admin", superuser=True)

    with _backup_client(admin, db_session) as client:
        missing = client.post(f"/api/backups/backup/{device.id}")
        partial = client.post(
            f"/api/backups/backup/{device.id}", json={"username": "netops"}
        )

    assert missing.status_code == 400
    assert missing.json()["detail"] == "请使用操作者 SSH 凭证（密码不存储在服务器上）"
    assert partial.status_code == 400
    assert partial.json()["detail"] == "请完整填写操作者 SSH 凭证（用户名与密码必填）"


def test_backup_with_operator_credentials_records_backup(
    db_session, auth_config, tmp_path, monkeypatch
):
    from app.shared.config import get_config
    from app.shared.models import BackupRecord, Device

    device = _make_device(db_session, "cred-success-device")
    admin = _create_user(db_session, "cred-success-admin", superuser=True)
    monkeypatch.setattr(get_config().storage, "backup_dir", str(tmp_path / "backups"))
    _patch_backup_success(monkeypatch, tmp_path)
    password = "s3cret-P@ss-0perator"

    with _backup_client(admin, db_session) as client:
        response = client.post(
            f"/api/backups/backup/{device.id}",
            json={"username": "netops", "password": password},
        )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert password not in response.text

    db_session.expire_all()
    record = db_session.query(BackupRecord).filter(BackupRecord.device_id == device.id).one()
    assert record.operator == admin.username
    updated = db_session.query(Device).filter(Device.id == device.id).one()
    assert updated.last_backup_time is not None


def test_backup_auth_failure_returns_401_and_redacts_password(
    db_session, auth_config, tmp_path, monkeypatch
):
    from app.shared.config import get_config

    device = _make_device(db_session, "cred-auth-fail-device")
    admin = _create_user(db_session, "cred-auth-fail-admin", superuser=True)
    monkeypatch.setattr(get_config().storage, "backup_dir", str(tmp_path / "backups"))
    _patch_backup_auth_failure(monkeypatch)
    password = "wR0ng-P@ss"

    with _backup_client(admin, db_session) as client:
        response = client.post(
            f"/api/backups/backup/{device.id}",
            json={"username": "netops", "password": password},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "SSH 认证失败，请检查操作者凭证"
    assert password not in response.text


def test_batch_backup_requires_credentials_when_flag_on(db_session, auth_config):
    device = _make_device(db_session, "batch-cred-required-device")
    admin = _create_user(db_session, "batch-cred-required-admin", superuser=True)

    with _backup_client(admin, db_session) as client:
        missing = client.post("/api/backups/batch", json={"device_ids": [device.id]})

    assert missing.status_code == 400
    assert missing.json()["detail"] == "请使用操作者 SSH 凭证（密码不存储在服务器上）"


def test_batch_backup_marks_auth_failure_and_continues(
    db_session, auth_config, tmp_path, monkeypatch
):
    from app.features.backups import router as backup_router
    from app.features.backups.netmiko_service import NetmikoAuthenticationException
    from app.shared.config import get_config
    from app.shared.models import BackupRecord

    good = _make_device(db_session, "batch-good-device")
    bad = _make_device(db_session, "batch-bad-device")
    admin = _create_user(db_session, "batch-mixed-admin", superuser=True)
    monkeypatch.setattr(get_config().storage, "backup_dir", str(tmp_path / "backups"))
    monkeypatch.setattr(
        "app.shared.git_config_service.get_git_config_service",
        lambda: type("GitService", (), {"available": False})(),
    )
    password = "s3cret-Batch-P@ss"

    def fake_backup(device, credentials, backup_dir):
        if device.id == bad.id:
            raise NetmikoAuthenticationException("authentication failed")
        backup_path = tmp_path / "backups" / f"device-{device.id}" / "config.cfg"
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        backup_path.write_text("hostname OK\n", encoding="utf-8")
        return {
            "success": True,
            "file_path": str(backup_path),
            "file_size": backup_path.stat().st_size,
            "md5_hash": "abc",
            "has_change": False,
            "message": "备份成功",
        }

    monkeypatch.setattr(backup_router, "backup_device_config", fake_backup)

    with _backup_client(admin, db_session) as client:
        response = client.post(
            "/api/backups/batch",
            json={"device_ids": [good.id, bad.id], "username": "netops", "password": password},
        )

    assert response.status_code == 200
    results = {r["device_id"]: r for r in response.json()["results"]}
    assert results[good.id]["success"] is True
    assert results[bad.id]["auth_failed"] is True
    assert results[bad.id]["message"] == "SSH 认证失败，请检查操作者凭证"
    assert password not in response.text

    db_session.expire_all()
    records = db_session.query(BackupRecord).filter(BackupRecord.device_id == good.id).all()
    assert len(records) == 1
    assert db_session.query(BackupRecord).filter(BackupRecord.device_id == bad.id).count() == 0


def test_backup_falls_back_to_credential_group_when_flag_off(
    db_session, auth_config, tmp_path, monkeypatch
):
    from app.features.credentials.credential_service import encrypt_password
    from app.shared.config import get_config
    from app.shared.models import BackupRecord, CredentialGroup

    monkeypatch.setattr(get_config().security, "credential_session_required", False)
    device = _make_device(db_session, "cred-fallback-device")
    credential = CredentialGroup(
        name="default",
        username="netops",
        password_encrypted=encrypt_password("fallback-secret"),
    )
    db_session.add(credential)
    db_session.commit()
    admin = _create_user(db_session, "cred-fallback-admin", superuser=True)
    monkeypatch.setattr(get_config().storage, "backup_dir", str(tmp_path / "backups"))
    _patch_backup_success(monkeypatch, tmp_path)

    # 不带操作者凭证，仅依赖降级开关 + 服务器凭证组
    with _backup_client(admin, db_session) as client:
        response = client.post(f"/api/backups/backup/{device.id}")

    assert response.status_code == 200
    assert response.json()["success"] is True
    db_session.expire_all()
    assert db_session.query(BackupRecord).filter(BackupRecord.device_id == device.id).count() == 1


def test_needs_backup_lists_config_changed_and_overdue(db_session, auth_config):
    from app.shared.models import Device

    now = datetime.utcnow()
    overdue = _make_device(db_session, "needs-overdue-device")
    overdue.last_backup_time = now - timedelta(days=30)
    changed = _make_device(db_session, "needs-changed-device")
    changed.last_backup_time = now - timedelta(days=2)
    changed.config_changed_at = now - timedelta(days=1)
    fresh = _make_device(db_session, "needs-fresh-device")
    fresh.last_backup_time = now
    retired = _make_device(
        db_session, "needs-retired-device", deployment_status="un-used"
    )
    db_session.commit()
    reader = _create_user(db_session, "needs-reader", permission="backup:read")

    with _backup_client(reader, db_session) as client:
        response = client.get("/api/backups/needs-backup")

    assert response.status_code == 200
    items = {i["device_id"]: i for i in response.json()["items"]}
    assert items[overdue.id]["reason"] == "backup_overdue"
    assert items[changed.id]["reason"] == "config_changed"
    assert fresh.id not in items
    assert retired.id not in items


def test_mark_config_changed_endpoint(db_session, auth_config):
    from app.shared.models import Device

    device = _make_device(db_session, "mark-changed-device")
    admin = _create_user(db_session, "mark-changed-admin", superuser=True)

    with _backup_client(admin, db_session) as client:
        response = client.post(
            "/api/backups/mark-config-changed", json={"device_ids": [device.id]}
        )

    assert response.status_code == 200
    assert response.json()["marked"] == 1
    db_session.expire_all()
    updated = db_session.query(Device).filter(Device.id == device.id).one()
    assert updated.config_changed_at is not None


def test_async_backup_endpoint_is_removed():
    from app.features.backups import router as backup_router

    assert not hasattr(backup_router, "backup_device_async")
    assert not hasattr(backup_router, "backup_device_job")


def test_async_backup_route_is_not_declared():
    from app.features.backups import router as backup_router

    for route in backup_router.router.routes:
        if getattr(route, "path", "").endswith("/async"):
            pytest.fail(f"异步备份路由未下线: {route.path}")


# ---------------------------------------------------------------------------
# 切片 B：部署 / 回滚操作者凭证 + 定时部署下线
# ---------------------------------------------------------------------------

def _deploy_client(current_user, db_session):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.features.auth.identity import get_current_principal
    from app.features.auth.router import get_current_user_from_token
    from app.features.deploy import router as deploy_router
    from app.shared.database import get_db

    app = FastAPI()
    app.include_router(deploy_router.router)
    app.dependency_overrides[get_current_user_from_token] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: db_session
    if current_user is not None:
        app.dependency_overrides[get_current_principal] = lambda: _principal(current_user)
    return TestClient(app)


def test_build_operator_credential_groups_builds_single_default_group():
    from app.features.deploy.operator_credentials import build_operator_credential_groups

    groups = build_operator_credential_groups(
        {"username": "netops", "password": "s3cret", "secret": "enable-secret"}
    )

    assert groups == [{
        "name": "default",
        "username": "netops",
        "password": "s3cret",
        "enable_password": "enable-secret",
    }]


def test_build_operator_credential_groups_rejects_partial_fill():
    from fastapi import HTTPException

    from app.features.deploy.operator_credentials import build_operator_credential_groups

    with pytest.raises(HTTPException) as exc:
        build_operator_credential_groups({"username": "netops"})
    assert exc.value.status_code == 400
    assert "完整" in exc.value.detail


def test_build_operator_credential_groups_returns_none_when_empty():
    from app.features.deploy.operator_credentials import build_operator_credential_groups

    assert build_operator_credential_groups(None) is None
    assert build_operator_credential_groups({}) is None


def test_resolve_operator_credentials_rejects_when_flag_on(auth_config):
    from fastapi import HTTPException

    from app.features.deploy.operator_credentials import resolve_operator_credentials

    with pytest.raises(HTTPException) as exc:
        resolve_operator_credentials(None)
    assert exc.value.status_code == 400
    assert exc.value.detail == "请使用操作者 SSH 凭证（密码不存储在服务器上）"


def test_resolve_operator_credentials_falls_back_when_flag_off(monkeypatch):
    from app.shared.config import get_config

    from app.features.deploy.operator_credentials import resolve_operator_credentials

    monkeypatch.setattr(get_config().security, "credential_session_required", False)

    assert resolve_operator_credentials(None) is None


def test_resolve_operator_credentials_passes_through_full_credentials(auth_config):
    from app.features.deploy.operator_credentials import resolve_operator_credentials

    groups = resolve_operator_credentials({"username": "netops", "password": "pw"})
    assert groups == [
        {"name": "default", "username": "netops", "password": "pw", "enable_password": None}
    ]


def test_deploy_rollback_requires_operator_credentials(db_session, auth_config):
    device = _make_device(db_session, "rollback-cred-required")
    admin = _create_user(db_session, "rollback-cred-admin", superuser=True)

    with _deploy_client(admin, db_session) as client:
        response = client.post("/api/deploy/rollback", json={"target_devices": [device.id]})

    assert response.status_code == 400
    assert response.json()["detail"] == "请使用操作者 SSH 凭证（密码不存储在服务器上）"


def test_schedule_deploy_endpoint_is_removed():
    from app.features.deploy import router as deploy_router

    for route in deploy_router.router.routes:
        if getattr(route, "path", "").endswith("/schedule") and "post" in route.methods:
            pytest.fail(f"定时部署端点未下线: {route.path}")


def test_schedule_deploy_request_schema_is_removed():
    import app.features.deploy.schemas as schemas

    assert not hasattr(schemas, "ScheduleDeployRequest")


def test_celery_app_no_longer_registers_backup_or_deploy_tasks():
    from app.core.celery_app import get_celery_app

    app = get_celery_app()
    imports = tuple(app.conf.get("imports", ()))
    task_routes = tuple(app.conf.get("task_routes", {}))
    assert not any("backup_tasks" in item for item in imports)
    assert not any("deploy_tasks" in item for item in imports)
    assert not any("backup_tasks" in item for item in task_routes)
    assert not any("deploy_tasks" in item for item in task_routes)


def test_tasks_all_excludes_backup_and_deploy():
    import app.tasks as tasks

    assert "backup_tasks" not in tasks.__all__
    assert "deploy_tasks" not in tasks.__all__
