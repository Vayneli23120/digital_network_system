"""SSO 端点占位实现的行为约定

目标：Entra ID 应用注册批下来之前，登录页的 SSO 入口要能正确地"知道自己不可用"，
并且给出可操作的诊断信息，而不是 404/500。
"""

import asyncio

import pytest
from fastapi import HTTPException


def test_sso_disabled_by_default():
    from app.shared.config import SSOConfig

    cfg = SSOConfig()
    assert cfg.enabled is False
    assert cfg.provider == "entra"
    assert cfg.auto_provision is True
    assert cfg.default_role == "viewer"


def test_sso_status_reports_not_enabled():
    from app.features.auth.sso_router import sso_status

    status = asyncio.run(sso_status())

    assert status["enabled"] is False
    assert status["login_url"] == "/api/auth/sso/login"
    assert status["display_name"]


def test_sso_status_never_leaks_secrets(monkeypatch):
    from app.features.auth.sso_router import sso_status
    from app.shared.config import get_config

    cfg = get_config()
    monkeypatch.setattr(cfg.sso, "enabled", True)
    monkeypatch.setattr(cfg.sso, "tenant_id", "tenant-123")
    monkeypatch.setattr(cfg.sso, "client_id", "client-123")
    monkeypatch.setattr(cfg.sso, "client_secret", "super-secret-value")
    monkeypatch.setattr(cfg.sso, "redirect_uri", "https://nas.example.com/api/auth/sso/callback")

    status = asyncio.run(sso_status())

    assert status["enabled"] is True
    assert "super-secret-value" not in str(status)
    assert "client-123" not in str(status)


def test_sso_status_flags_incomplete_config(monkeypatch):
    """已启用但缺配置时，入口必须标为不可用并列出缺什么"""
    from app.features.auth.sso_router import sso_status
    from app.shared.config import get_config

    cfg = get_config()
    monkeypatch.setattr(cfg.sso, "enabled", True)
    monkeypatch.setattr(cfg.sso, "tenant_id", "tenant-123")

    status = asyncio.run(sso_status())

    assert status["enabled"] is False
    assert status["configured"] is False
    assert set(status["missing_fields"]) == {"client_id", "client_secret", "redirect_uri"}


def test_sso_login_returns_501_when_disabled():
    from app.features.auth.sso_router import sso_login

    with pytest.raises(HTTPException) as exc:
        asyncio.run(sso_login())

    assert exc.value.status_code == 501
    assert exc.value.detail["reason"] == "not_enabled"
    assert "hint" in exc.value.detail


def test_sso_callback_surfaces_idp_error():
    from app.features.auth.sso_router import sso_callback

    with pytest.raises(HTTPException) as exc:
        asyncio.run(sso_callback(error="access_denied", error_description="user cancelled", db=None))

    assert exc.value.status_code == 400
    assert exc.value.detail["error"] == "access_denied"


def test_sso_authority_url():
    from app.shared.config import SSOConfig

    assert SSOConfig().authority == ""
    assert SSOConfig(tenant_id="abc").authority == "https://login.microsoftonline.com/abc"
