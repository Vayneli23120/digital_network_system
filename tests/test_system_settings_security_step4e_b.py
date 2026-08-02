"""Security Step 4E-B5B: system settings, SLO, and system operations."""

import inspect
import json
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
    if permissions:
        role = Role(name=f"role-{username}", description="test role")
        new_permissions = []
        for permission_name in permissions:
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


def _router_client(router, current_user, db):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.features.auth.identity import (
        get_current_principal,
        get_current_user_from_token,
    )
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


def test_system_config_permission_matrix_and_allowlist(db_session, monkeypatch):
    from app.features.system_settings import router as settings_module
    from app.shared.models import SystemConfig

    _enable_auth(monkeypatch)
    reader = _create_user(
        db_session,
        "system-config-reader",
        permissions=["system_config:read"],
    )
    writer = _create_user(
        db_session,
        "system-config-writer",
        permissions=["system_config:write"],
    )
    db_session.add(SystemConfig(
        key="secret_internal_key",
        value="must-not-be-returned",
    ))
    db_session.commit()

    assert inspect.signature(settings_module.list_config).parameters["_"].default.dependency is (
        settings_module.require_system_config_read
    )
    assert inspect.signature(settings_module.update_config).parameters["_"].default.dependency is (
        settings_module.require_system_config_write
    )

    with _router_client(settings_module.router, None, db_session) as client:
        assert client.get("/api/system/config").status_code == 401
    with _router_client(settings_module.router, reader, db_session) as client:
        response = client.get("/api/system/config")
        assert response.status_code == 200
        assert {item["key"] for item in response.json()["items"]} == {
            "timezone",
            "grafana_url",
        }
        assert "must-not-be-returned" not in response.text
        assert client.put("/api/system/config", json={
            "timezone": "UTC",
        }).status_code == 403
    with _router_client(settings_module.router, writer, db_session) as client:
        assert client.get("/api/system/config").status_code == 403
        invalid_key = client.put("/api/system/config", json={
            "jwt_secret": "forged",
        })
        assert invalid_key.status_code == 422
        assert client.put("/api/system/config", json={
            "timezone": "Not/AZone",
        }).status_code == 422
        assert client.put("/api/system/config", json={
            "grafana_url": "http://user:pass@internal:3001",
        }).status_code == 422
        updated = client.put("/api/system/config", json={
            "timezone": "UTC",
            "grafana_url": "http://192.0.2.10:3001/",
        })
        assert updated.status_code == 200

    db_session.expire_all()
    timezone_row = db_session.query(SystemConfig).filter(
        SystemConfig.key == "timezone"
    ).one()
    grafana_row = db_session.query(SystemConfig).filter(
        SystemConfig.key == "grafana_url"
    ).one()
    assert timezone_row.value == "UTC"
    assert grafana_row.value == "http://192.0.2.10:3001"
    assert timezone_row.updated_by == writer.username
    assert grafana_row.updated_by == writer.username


def test_slo_permission_matrix_and_validation(db_session, monkeypatch):
    from app.features.dashboard import router as dashboard_module

    _enable_auth(monkeypatch)
    reader = _create_user(db_session, "slo-reader", permissions=["slo:read"])
    writer = _create_user(db_session, "slo-writer", permissions=["slo:write"])

    expected = {
        "list_slo": dashboard_module.require_slo_read,
        "create_slo": dashboard_module.require_slo_write,
        "update_slo": dashboard_module.require_slo_write,
        "delete_slo": dashboard_module.require_slo_write,
    }
    for function_name, dependency in expected.items():
        parameter = inspect.signature(getattr(dashboard_module, function_name)).parameters["_"]
        assert parameter.default.dependency is dependency

    with _router_client(dashboard_module.router, reader, db_session) as client:
        assert client.get("/api/dashboard/slo").status_code == 200
        assert client.post("/api/dashboard/slo", json={
            "service_key": "core",
            "service_name": "Core",
            "slo_target": 99.9,
        }).status_code == 403
    with _router_client(dashboard_module.router, writer, db_session) as client:
        assert client.get("/api/dashboard/slo").status_code == 403
        for payload in (
            {"service_key": "UPPER", "service_name": "Bad", "slo_target": 99.9},
            {"service_key": "low", "service_name": "Low", "slo_target": 89.9},
            {"service_key": "window", "service_name": "Window", "slo_target": 99.9, "window_days": 366},
            {"service_key": "extra", "service_name": "Extra", "slo_target": 99.9, "operator": "forged"},
        ):
            assert client.post("/api/dashboard/slo", json=payload).status_code == 422
        created = client.post("/api/dashboard/slo", json={
            "service_key": "core_room",
            "service_name": " Core Room ",
            "slo_target": 99.9,
            "device_types": "core_switch,router,core_switch",
            "window_days": 30,
        })
        assert created.status_code == 200
        slo_id = created.json()["id"]
        assert created.json()["service_name"] == "Core Room"
        assert created.json()["device_types"] == "core_switch,router"
        assert client.delete(f"/api/dashboard/slo/{slo_id}").status_code == 200


def _ops_app(current_user, db):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import app.main as main_module
    from app.features.auth.identity import (
        get_current_principal,
        get_current_user_from_token,
    )
    from app.shared.database import get_db

    app = FastAPI()
    app.add_api_route("/api/cache/stats", main_module.cache_stats, methods=["GET"])
    app.add_api_route("/api/cache/clear", main_module.cache_clear, methods=["POST"])
    app.add_api_route(
        "/api/system/diagnostics",
        main_module.system_diagnostics,
        methods=["GET"],
    )
    app.add_api_route(
        "/grafana/{path:path}",
        main_module.grafana_proxy_read,
        methods=["GET"],
    )
    app.add_api_route(
        "/grafana/{path:path}",
        main_module.grafana_proxy_write,
        methods=["POST", "PUT", "DELETE", "PATCH"],
    )
    app.dependency_overrides[get_current_user_from_token] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: db
    if current_user is not None:
        app.dependency_overrides[get_current_principal] = lambda: _principal(current_user)
    return TestClient(app), main_module


def test_system_ops_permission_matrix_and_request_bounds(db_session, monkeypatch):
    _enable_auth(monkeypatch)
    reader = _create_user(
        db_session,
        "system-ops-reader",
        permissions=["system_ops:read"],
    )
    writer = _create_user(
        db_session,
        "system-ops-writer",
        permissions=["system_ops:write"],
    )

    client, main_module = _ops_app(reader, db_session)
    with client:
        assert client.get("/api/cache/stats").status_code == 200
        assert client.get("/api/system/diagnostics").status_code == 200
        assert client.post("/api/cache/clear").status_code == 403
        assert client.post("/grafana/api/test", content=b"x").status_code == 403
    client, _ = _ops_app(writer, db_session)
    with client:
        assert client.get("/api/cache/stats").status_code == 403
        assert client.post("/api/cache/clear?prefix=" + "x" * 201).status_code == 422
        oversized = client.post(
            "/grafana/api/test",
            headers={"Content-Length": str(5 * 1024 * 1024 + 1)},
            content=b"",
        )
        assert oversized.status_code == 413

    assert inspect.signature(main_module.cache_stats).parameters["_"].default.dependency is (
        main_module.require_system_ops_read
    )
    assert inspect.signature(main_module.cache_clear).parameters["_"].default.dependency is (
        main_module.require_system_ops_write
    )
    assert inspect.signature(main_module.grafana_proxy_read).parameters["_"].default.dependency is (
        main_module.require_system_ops_read
    )
    assert inspect.signature(main_module.grafana_proxy_write).parameters["_"].default.dependency is (
        main_module.require_system_ops_write
    )


def test_grafana_proxy_strips_nas_credentials(monkeypatch):
    import app.main as main_module
    from fastapi import FastAPI, Request

    captured = {}

    class FakeResponse:
        status_code = 200
        headers = {"content-type": "text/plain"}

        async def aiter_bytes(self):
            yield b"ok"

        async def aclose(self):
            captured["response_closed"] = True

    class FakeClient:
        def __init__(self, *args, **kwargs):
            captured["client_kwargs"] = kwargs

        def build_request(self, method, url, headers, content):
            captured.update({
                "method": method,
                "url": str(url),
                "headers": headers,
                "content": content,
            })
            return object()

        async def send(self, request, stream):
            captured["stream"] = stream
            return FakeResponse()

        async def aclose(self):
            captured["client_closed"] = True

    monkeypatch.setattr("httpx.AsyncClient", FakeClient)

    proxy_app = FastAPI()

    @proxy_app.get("/grafana/{path:path}")
    async def proxy(request: Request, path: str):
        return await main_module._proxy_grafana(request, path)

    from fastapi.testclient import TestClient

    client = TestClient(proxy_app)
    response = client.get(
        "/grafana/api/search?query=test",
        headers={"Authorization": "Bearer nas-secret", "Cookie": "nas=session"},
    )

    assert response.status_code == 200
    assert response.content == b"ok"
    lowered_headers = {key.lower() for key in captured["headers"]}
    assert "authorization" not in lowered_headers
    assert "cookie" not in lowered_headers
    assert captured["stream"] is True
    assert captured["response_closed"] is True
    assert captured["client_closed"] is True


def test_readiness_returns_real_503_and_redacts_errors(monkeypatch):
    import app.main as main_module

    class BrokenEngine:
        def connect(self):
            raise RuntimeError(r"database at C:\private\nas.db")

    class BrokenManager:
        engine = BrokenEngine()

    monkeypatch.setattr(main_module, "get_db_manager", lambda: BrokenManager())
    response = __import__("asyncio").run(main_module.readiness_check())

    assert response.status_code == 503
    payload = json.loads(response.body)
    assert payload["status"] == "degraded"
    assert payload["checks"]["database"] == {"status": "error"}
    assert "private" not in response.body.decode()


def test_system_settings_frontend_uses_authenticated_atomic_api():
    root = Path(__file__).resolve().parents[1]
    source = (
        root / "frontend/src/views/SystemSettings.vue"
    ).read_text(encoding="utf-8")
    layout_source = (
        root / "frontend/src/views/Layout.vue"
    ).read_text(encoding="utf-8")

    assert "import axios from 'axios'" not in source
    assert "await updateSystemConfig({" in source
    assert "await axios.put('/api/system/config'" not in source
    assert "getServiceSlos()" in source
    system_menu = next(
        line for line in layout_source.splitlines() if "path: '/system-settings'" in line
    )
    assert "permission: 'system_config:read'" in system_menu