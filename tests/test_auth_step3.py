"""安全批次步骤 3：统一身份解析与 X-User 旁路收口。"""

import asyncio
from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from starlette.responses import JSONResponse
from starlette.requests import Request

import app.shared.models_jobs  # noqa: F401  让 jobs 表进入 Base.metadata


def _request(path: str = "/api/devices", headers: dict | None = None) -> Request:
    raw_headers = [
        (name.lower().encode("latin-1"), value.encode("latin-1"))
        for name, value in (headers or {}).items()
    ]
    return Request({
        "type": "http",
        "method": "GET",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": raw_headers,
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "scheme": "http",
    })


@pytest.fixture
def security_config(monkeypatch):
    import app.features.auth.router as auth_router
    from app.shared.config import get_config

    config = get_config()
    monkeypatch.setattr(config.security, "jwt_secret", "s" * 40)
    monkeypatch.setattr(auth_router, "config", config)
    return config


@pytest.fixture
def active_admin(db_session):
    from app.shared.models import User

    user = User(
        username="admin-step3",
        password_hash="unused",
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_x_user_cannot_impersonate_when_auth_enabled(
    db_session, active_admin, security_config, monkeypatch
):
    from app.features.auth.identity import resolve_principal

    monkeypatch.setattr(security_config.security, "auth_enabled", True)
    monkeypatch.setattr(security_config.app, "debug", False)

    with pytest.raises(HTTPException) as exc:
        resolve_principal(
            _request(headers={"X-User": active_admin.username}),
            None,
            db_session,
        )

    assert exc.value.status_code == 401
    assert exc.value.headers == {"WWW-Authenticate": "Bearer"}


def test_valid_access_token_resolves_principal(
    db_session, active_admin, security_config, monkeypatch
):
    from app.features.auth.identity import resolve_principal
    from app.features.auth.router import create_access_token

    monkeypatch.setattr(security_config.security, "auth_enabled", True)
    monkeypatch.setattr(security_config.app, "debug", False)
    token = create_access_token({"sub": active_admin.username, "user_id": active_admin.id})

    principal = resolve_principal(_request(), _bearer(token), db_session)

    assert principal.username == active_admin.username
    assert principal.user_id == active_admin.id
    assert principal.auth_source == "jwt"
    assert principal.is_authenticated is True


@pytest.mark.parametrize("token", ["not-a-token", "header.payload.signature"])
def test_invalid_token_returns_401(db_session, security_config, monkeypatch, token):
    from app.features.auth.identity import resolve_principal

    monkeypatch.setattr(security_config.security, "auth_enabled", True)
    monkeypatch.setattr(security_config.app, "debug", False)

    with pytest.raises(HTTPException) as exc:
        resolve_principal(_request(), _bearer(token), db_session)

    assert exc.value.status_code == 401
    assert exc.value.headers == {"WWW-Authenticate": "Bearer"}


def test_refresh_token_is_rejected(db_session, active_admin, security_config, monkeypatch):
    from jose import jwt
    from app.features.auth.identity import resolve_principal

    monkeypatch.setattr(security_config.security, "auth_enabled", True)
    monkeypatch.setattr(security_config.app, "debug", False)
    token = jwt.encode(
        {
            "sub": active_admin.username,
            "type": "refresh",
            "exp": datetime.utcnow() + timedelta(minutes=5),
        },
        security_config.security.jwt_secret,
        algorithm=security_config.security.jwt_algorithm,
    )

    with pytest.raises(HTTPException) as exc:
        resolve_principal(_request(), _bearer(token), db_session)

    assert exc.value.status_code == 401


def test_disabled_auth_without_debug_does_not_bypass(db_session, security_config, monkeypatch):
    from app.features.auth.identity import resolve_principal

    monkeypatch.setattr(security_config.security, "auth_enabled", False)
    monkeypatch.setattr(security_config.app, "debug", False)

    with pytest.raises(HTTPException) as exc:
        resolve_principal(_request(), None, db_session)

    assert exc.value.status_code == 401


def test_debug_bypass_resolves_existing_x_user(
    db_session, active_admin, security_config, monkeypatch
):
    from app.features.auth.identity import resolve_principal

    monkeypatch.setattr(security_config.security, "auth_enabled", False)
    monkeypatch.setattr(security_config.app, "debug", True)

    principal = resolve_principal(
        _request(headers={"X-User": active_admin.username}),
        None,
        db_session,
    )

    assert principal.username == active_admin.username
    assert principal.auth_source == "development_header"
    assert principal.is_development is True


def test_debug_bypass_without_header_is_explicit_developer(
    db_session, security_config, monkeypatch
):
    from app.features.auth.identity import resolve_principal

    monkeypatch.setattr(security_config.security, "auth_enabled", False)
    monkeypatch.setattr(security_config.app, "debug", True)

    principal = resolve_principal(_request(), None, db_session)

    assert principal.username == "developer"
    assert principal.user is None
    assert principal.auth_source == "development_bypass"


def test_public_path_matching_is_exact():
    from app.shared.middleware.auth_middleware import is_public_path

    assert is_public_path("/api/auth/login") is True
    assert is_public_path("/api/auth/sso/status") is True
    assert is_public_path("/health") is True
    assert is_public_path("/api/auth/login-evil") is False
    assert is_public_path("/health/private") is False
    assert is_public_path("/api/devices") is False


def test_middleware_rejects_devices_with_only_x_user(security_config, monkeypatch):
    from app.shared.middleware.auth_middleware import auth_middleware

    monkeypatch.setattr(security_config.security, "auth_enabled", True)
    monkeypatch.setattr(security_config.app, "debug", False)
    called = False

    async def call_next(_request):
        nonlocal called
        called = True
        raise AssertionError("protected request must not reach downstream")

    response = asyncio.run(
        auth_middleware(
            _request(headers={"X-User": "Admin"}),
            call_next,
        )
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert called is False


def test_middleware_accepts_access_token_and_sets_principal(
    db_manager, active_admin, security_config, monkeypatch
):
    from app.features.auth.router import create_access_token
    import app.shared.middleware.auth_middleware as middleware_module

    monkeypatch.setattr(security_config.security, "auth_enabled", True)
    monkeypatch.setattr(security_config.app, "debug", False)
    monkeypatch.setattr(middleware_module, "get_db_manager", lambda: db_manager)
    token = create_access_token({"sub": active_admin.username, "user_id": active_admin.id})
    request = _request(headers={"Authorization": f"Bearer {token}"})

    async def call_next(inner_request):
        assert inner_request.state.principal.username == active_admin.username
        assert inner_request.state.user_id == active_admin.id
        return JSONResponse({"ok": True})

    response = asyncio.run(middleware_module.auth_middleware(request, call_next))

    assert response.status_code == 200


def test_middleware_rejects_expired_token(security_config, monkeypatch):
    from jose import jwt
    from app.shared.middleware.auth_middleware import auth_middleware

    monkeypatch.setattr(security_config.security, "auth_enabled", True)
    monkeypatch.setattr(security_config.app, "debug", False)
    token = jwt.encode(
        {
            "sub": "expired-user",
            "type": "access",
            "exp": datetime.utcnow() - timedelta(seconds=1),
        },
        security_config.security.jwt_secret,
        algorithm=security_config.security.jwt_algorithm,
    )

    async def call_next(_request):
        raise AssertionError("expired token must not reach downstream")

    response = asyncio.run(
        auth_middleware(
            _request(headers={"Authorization": f"Bearer {token}"}),
            call_next,
        )
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_revoked_token_is_rejected(db_session, active_admin, security_config, monkeypatch):
    from app.features.auth.identity import resolve_principal
    from app.features.auth.router import create_access_token, decode_token
    from app.shared.models import UserSession

    monkeypatch.setattr(security_config.security, "auth_enabled", True)
    monkeypatch.setattr(security_config.app, "debug", False)
    token = create_access_token({"sub": active_admin.username, "user_id": active_admin.id})
    payload = decode_token(token)
    db_session.add(UserSession(
        user_id=active_admin.id,
        token_jti=payload["jti"],
        token_type="access",
        expires_at=datetime.utcfromtimestamp(payload["exp"]),
        revoked=True,
    ))
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        resolve_principal(_request(), _bearer(token), db_session)

    assert exc.value.status_code == 401


def test_cors_preflight_is_allowed_without_token(security_config, monkeypatch):
    from app.shared.middleware.auth_middleware import auth_middleware

    monkeypatch.setattr(security_config.security, "auth_enabled", True)
    monkeypatch.setattr(security_config.app, "debug", False)
    request = _request(path="/api/devices")
    request.scope["method"] = "OPTIONS"

    async def call_next(_request):
        return JSONResponse({"preflight": True})

    response = asyncio.run(auth_middleware(request, call_next))

    assert response.status_code == 200


def test_security_environment_overrides(monkeypatch):
    from app.shared.config import Config

    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("APP_DEBUG", "false")
    monkeypatch.setenv("JWT_SECRET", "z" * 40)
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://nas.example, https://ops.example")
    config = Config()

    config._apply_security_env_overrides()

    assert config.security.auth_enabled is True
    assert config.app.debug is False
    assert config.security.jwt_secret == "z" * 40
    assert config.security.cors_allowed_origins == [
        "https://nas.example",
        "https://ops.example",
    ]


def test_invalid_boolean_environment_value_is_rejected(monkeypatch):
    from app.shared.config import Config

    monkeypatch.setenv("AUTH_ENABLED", "sometimes")

    with pytest.raises(ValueError, match="AUTH_ENABLED"):
        Config()._apply_security_env_overrides()


def test_identity_consumers_do_not_reintroduce_x_user_or_admin_fallback():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    deploy_source = (root / "app/features/deploy/router.py").read_text(encoding="utf-8")
    notifications_source = (
        root / "app/features/notifications/router.py"
    ).read_text(encoding="utf-8")
    frontend_source = (root / "frontend/src/api/request.js").read_text(encoding="utf-8")
    search_source = (
        root / "frontend/src/views/layout/SearchDropdown.vue"
    ).read_text(encoding="utf-8")

    assert "X-User" not in deploy_source
    assert "X-User" not in notifications_source
    assert 'return "Admin"' not in notifications_source
    assert "X-User" not in frontend_source
    assert "get_current_principal" in deploy_source
    assert "get_current_principal" in notifications_source
    assert "fetch('/api" not in search_source
    assert "fetch(`/api" not in search_source
    assert "@/api/request.js" in search_source


def test_superuser_passes_protected_permission_dependency(
    db_session, active_admin, security_config, monkeypatch
):
    from app.shared.dependencies import require_permission

    monkeypatch.setattr(security_config.security, "auth_enabled", True)
    monkeypatch.setattr(security_config.app, "debug", False)
    checker = require_permission("config:deploy")

    result = asyncio.run(checker(active_admin, db_session))

    assert result.id == active_admin.id


def test_user_without_permission_gets_403(db_session, security_config, monkeypatch):
    from app.shared.dependencies import require_permission
    from app.shared.models import User

    monkeypatch.setattr(security_config.security, "auth_enabled", True)
    monkeypatch.setattr(security_config.app, "debug", False)
    user = User(
        username="viewer-step3",
        password_hash="unused",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    checker = require_permission("config:deploy")

    with pytest.raises(HTTPException) as exc:
        asyncio.run(checker(user, db_session))

    assert exc.value.status_code == 403


def test_missing_password_hash_dependency_fails_fast(monkeypatch):
    import app.features.auth.router as auth_router

    monkeypatch.setattr(auth_router, "PWD_CONTEXT_AVAILABLE", False)

    with pytest.raises(RuntimeError, match=r"passlib\[bcrypt\]"):
        auth_router.validate_auth_runtime_dependencies()
