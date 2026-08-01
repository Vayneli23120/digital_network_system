"""安全步骤 4A：告警设置权限、脱敏和秘密保留。"""

import asyncio
import inspect
from pathlib import Path

import pytest
import yaml
from fastapi import HTTPException
from pydantic import ValidationError

import app.shared.models_jobs  # noqa: F401  让 jobs 表进入 Base.metadata


@pytest.fixture
def alerts_with_secrets():
    from app.shared.config import AlertsConfig

    return AlertsConfig.model_validate({
        "enabled": True,
        "channels": ["email", "wechat_work", "dingtalk"],
        "email": {
            "enabled": True,
            "smtp_host": "smtp.internal.example",
            "smtp_port": 587,
            "use_tls": True,
            "username": "alerts-user",
            "password": "smtp-secret",
            "from_addr": "alerts@example.com",
            "recipients": ["noc@example.com"],
        },
        "wechat_work": {
            "enabled": True,
            "webhook_url": "https://qyapi.weixin.qq.com/webhook?key=wechat-secret",
        },
        "dingtalk": {
            "enabled": True,
            "webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=ding-token",
            "secret": "SEC-ding-secret",
        },
    })


@pytest.fixture
def existing_config_path(tmp_path: Path) -> Path:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump({
            "app": {"debug": False},
            "alerts": {
                "enabled": True,
                "channels": ["email", "wechat_work", "dingtalk"],
                "email": {
                    "enabled": True,
                    "smtp_host": "old.smtp.example",
                    "smtp_port": 465,
                    "use_tls": True,
                    "username": "saved-user",
                    "password": "saved-password",
                    "from_addr": "old@example.com",
                    "recipients": ["old-recipient@example.com"],
                },
                "wechat_work": {
                    "enabled": True,
                    "webhook_url": "saved-wechat-webhook",
                },
                "dingtalk": {
                    "enabled": True,
                    "webhook_url": "saved-dingtalk-webhook",
                    "secret": "saved-dingtalk-secret",
                },
            },
        }, allow_unicode=True),
        encoding="utf-8",
    )
    return config_path


def _read_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _alert_client(current_user, db_session):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.features.alerts import router as alerts_router
    from app.features.auth.router import get_current_user_from_token
    from app.shared.database import get_db

    app = FastAPI()
    app.include_router(alerts_router.router)
    app.dependency_overrides[get_current_user_from_token] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: db_session
    return TestClient(app)


def test_settings_response_never_returns_secrets(alerts_with_secrets):
    from app.features.alerts.router import _settings_response

    response = _settings_response(alerts_with_secrets)
    rendered = repr(response)

    assert "email_username" not in response
    assert "email_password" not in response
    assert "wechat_webhook_url" not in response
    assert "dingtalk_webhook_url" not in response
    assert "dingtalk_secret" not in response
    assert "alerts-user" not in rendered
    assert "smtp-secret" not in rendered
    assert "wechat-secret" not in rendered
    assert "ding-token" not in rendered
    assert "SEC-ding-secret" not in rendered
    assert response["has_email_username"] is True
    assert response["has_email_password"] is True
    assert response["has_wechat_webhook_url"] is True
    assert response["has_dingtalk_webhook_url"] is True
    assert response["has_dingtalk_secret"] is True


def test_blank_sensitive_fields_preserve_existing_values(existing_config_path):
    from app.features.alerts.router import AlertSettingsUpdate, persist_alert_settings

    settings = AlertSettingsUpdate(
        enabled=True,
        channels=["email", "wechat_work", "dingtalk"],
        email_enabled=True,
        email_smtp_host="new.smtp.example",
        email_smtp_port=587,
        email_use_tls=True,
        email_username="",
        email_password="",
        email_from_addr="new@example.com",
        email_recipients=["new-recipient@example.com"],
        wechat_enabled=True,
        wechat_webhook_url="",
        dingtalk_enabled=True,
        dingtalk_webhook_url="",
        dingtalk_secret="",
    )

    persist_alert_settings(settings, existing_config_path)
    alerts = _read_yaml(existing_config_path)["alerts"]

    assert alerts["email"]["username"] == "saved-user"
    assert alerts["email"]["password"] == "saved-password"
    assert alerts["wechat_work"]["webhook_url"] == "saved-wechat-webhook"
    assert alerts["dingtalk"]["webhook_url"] == "saved-dingtalk-webhook"
    assert alerts["dingtalk"]["secret"] == "saved-dingtalk-secret"
    assert alerts["email"]["smtp_host"] == "new.smtp.example"
    assert alerts["email"]["from_addr"] == "new@example.com"
    assert not existing_config_path.with_suffix(".yaml.tmp").exists()


def test_new_sensitive_values_replace_existing_values(existing_config_path):
    from app.features.alerts.router import AlertSettingsUpdate, persist_alert_settings

    settings = AlertSettingsUpdate(
        email_username="new-user",
        email_password="new-password",
        wechat_webhook_url="new-wechat-webhook",
        dingtalk_webhook_url="new-dingtalk-webhook",
        dingtalk_secret="new-dingtalk-secret",
    )

    persist_alert_settings(settings, existing_config_path)
    alerts = _read_yaml(existing_config_path)["alerts"]

    assert alerts["email"]["username"] == "new-user"
    assert alerts["email"]["password"] == "new-password"
    assert alerts["wechat_work"]["webhook_url"] == "new-wechat-webhook"
    assert alerts["dingtalk"]["webhook_url"] == "new-dingtalk-webhook"
    assert alerts["dingtalk"]["secret"] == "new-dingtalk-secret"


def test_explicit_clear_removes_saved_values(existing_config_path):
    from app.features.alerts.router import AlertSettingsUpdate, persist_alert_settings

    settings = AlertSettingsUpdate(
        clear_email_username=True,
        clear_email_password=True,
        clear_wechat_webhook_url=True,
        clear_dingtalk_webhook_url=True,
        clear_dingtalk_secret=True,
    )

    persist_alert_settings(settings, existing_config_path)
    alerts = _read_yaml(existing_config_path)["alerts"]

    assert alerts["email"]["username"] == ""
    assert alerts["email"]["password"] == ""
    assert alerts["wechat_work"]["webhook_url"] == ""
    assert alerts["dingtalk"]["webhook_url"] == ""
    assert alerts["dingtalk"]["secret"] == ""


def test_persist_resets_cached_config_and_notification_service(
    existing_config_path, monkeypatch
):
    from app.features.alerts.router import AlertSettingsUpdate, persist_alert_settings
    import app.features.alerts.router as alerts_router

    reset_calls = []
    monkeypatch.setattr(alerts_router, "reset_notification_service", lambda: reset_calls.append(True))
    alerts_router.config_module._config = object()

    persist_alert_settings(AlertSettingsUpdate(enabled=True), existing_config_path)

    assert alerts_router.config_module._config is None
    assert reset_calls == [True]


@pytest.mark.parametrize("payload", [
    {"email_smtp_port": 0},
    {"email_smtp_port": 65536},
    {"channels": ["sms"]},
    {"unknown_field": "not-allowed"},
])
def test_update_model_rejects_invalid_payload(payload):
    from app.features.alerts.router import AlertSettingsUpdate

    with pytest.raises(ValidationError):
        AlertSettingsUpdate.model_validate(payload)


def test_alert_management_endpoints_require_permission():
    from app.features.alerts import router as alerts_router

    for function_name in (
        "get_alert_settings",
        "update_alert_settings",
        "test_alert_channel",
    ):
        function = getattr(alerts_router, function_name)
        parameter = inspect.signature(function).parameters.get("_")
        assert parameter is not None, f"{function_name} 缺少 alert:manage 权限依赖"
        assert parameter.default is not inspect.Parameter.empty


def test_superuser_can_manage_alerts(db_session, monkeypatch):
    from app.features.alerts.router import require_alert_manage
    from app.shared.config import get_config
    from app.shared.models import User

    config = get_config()
    monkeypatch.setattr(config.security, "auth_enabled", True)
    monkeypatch.setattr(config.app, "debug", False)
    user = User(
        username="alert-admin",
        password_hash="unused",
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user)
    db_session.commit()

    result = asyncio.run(require_alert_manage(user, db_session))

    assert result.id == user.id


def test_user_without_alert_permission_gets_403(db_session, monkeypatch):
    from app.features.alerts.router import require_alert_manage
    from app.shared.config import get_config
    from app.shared.models import User

    config = get_config()
    monkeypatch.setattr(config.security, "auth_enabled", True)
    monkeypatch.setattr(config.app, "debug", False)
    user = User(
        username="alert-viewer",
        password_hash="unused",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        asyncio.run(require_alert_manage(user, db_session))

    assert exc.value.status_code == 403


def test_alert_settings_http_requires_authenticated_user(db_session):
    with _alert_client(None, db_session) as client:
        response = client.get("/api/alerts/settings")

    assert response.status_code == 401


def test_alert_settings_http_denies_user_without_permission(db_session):
    from app.shared.models import User

    user = User(
        username="alert-http-viewer",
        password_hash="unused",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()

    with _alert_client(user, db_session) as client:
        response = client.get("/api/alerts/settings")

    assert response.status_code == 403


def test_alert_settings_http_allows_admin_without_leaking_secrets(
    db_session, alerts_with_secrets, monkeypatch
):
    from app.features.alerts import router as alerts_router
    from app.shared.models import User

    user = User(
        username="alert-http-admin",
        password_hash="unused",
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user)
    db_session.commit()
    config = type("AlertConfig", (), {"alerts": alerts_with_secrets})()
    monkeypatch.setattr(alerts_router, "get_config", lambda: config)

    with _alert_client(user, db_session) as client:
        response = client.get("/api/alerts/settings")

    assert response.status_code == 200
    payload = response.json()
    assert payload["has_email_password"] is True
    assert payload["has_dingtalk_secret"] is True
    assert "email_password" not in payload
    assert "dingtalk_secret" not in payload
    assert "smtp-secret" not in response.text
    assert "SEC-ding-secret" not in response.text


def test_status_response_contains_no_configuration_details(alerts_with_secrets, monkeypatch):
    from app.features.alerts.router import get_alert_status
    from app.services.notification_service import NotificationService
    import app.services.notification_service as service_module

    service = NotificationService()
    service.config.alerts = alerts_with_secrets
    monkeypatch.setattr(service_module, "_notification_service", service)

    response = asyncio.run(get_alert_status())
    rendered = repr(response)

    assert set(response) == {"enabled", "channels", "email", "wechat_work", "dingtalk"}
    assert "smtp.internal.example" not in rendered
    assert "alerts-user" not in rendered
    assert "secret" not in rendered.lower()


def test_frontend_alert_settings_uses_functional_permission_and_redacted_fields():
    root = Path(__file__).resolve().parents[1]
    layout_source = (root / "frontend/src/views/Layout.vue").read_text(encoding="utf-8")
    settings_source = (
        root / "frontend/src/views/AlertSettings.vue"
    ).read_text(encoding="utf-8")

    alert_menu_line = next(
        line for line in layout_source.splitlines() if "path: '/alert-settings'" in line
    )
    assert "permission: 'alert:manage'" in alert_menu_line
    assert "has_email_password" in settings_source
    assert "clear_email_password" in settings_source
    assert "has_dingtalk_secret" in settings_source
    assert "clear_dingtalk_secret" in settings_source
