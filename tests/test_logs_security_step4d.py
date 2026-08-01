"""Security Step 4D: Logs paths, RBAC, and WebSocket authorization."""

import asyncio
import inspect
import os
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi import HTTPException

import app.shared.models_jobs  # noqa: F401  Register jobs table in metadata.


LOG_LINE = (
    "2026-08-02 01:02:03.004 | INFO | app.test:run:10 - secure log entry\n"
)


@pytest.fixture
def log_dir(tmp_path):
    root = tmp_path / "logs"
    root.mkdir()
    (root / "app.log").write_text(LOG_LINE, encoding="utf-8")
    return root


def test_log_path_allows_plain_log_file(log_dir):
    from app.features.logs.security import resolve_log_file

    assert resolve_log_file("app.log", log_dir) == (log_dir / "app.log").resolve()


@pytest.mark.parametrize("filename", [
    "../secret.log",
    "subdir/app.log",
    "app.txt",
])
def test_log_path_rejects_invalid_names(log_dir, filename):
    from app.features.logs.security import UnsafeLogPathError, resolve_log_file

    with pytest.raises(UnsafeLogPathError):
        resolve_log_file(filename, log_dir)


def test_log_path_rejects_outside_absolute_path(log_dir, tmp_path):
    from app.features.logs.security import UnsafeLogPathError, resolve_log_file

    outside = tmp_path / "secret.log"
    outside.write_text("secret", encoding="utf-8")

    with pytest.raises(UnsafeLogPathError):
        resolve_log_file(outside, log_dir)


def test_log_path_rejects_symlink_escape_when_supported(log_dir, tmp_path):
    from app.features.logs.security import UnsafeLogPathError, resolve_log_file

    outside = tmp_path / "secret.log"
    outside.write_text("secret", encoding="utf-8")
    link = log_dir / "link.log"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("Symlink creation is unavailable")

    with pytest.raises(UnsafeLogPathError):
        resolve_log_file("link.log", log_dir)


def test_log_file_listing_does_not_disclose_server_path(log_dir):
    from app.features.logs.log_service import LogService

    files = LogService(str(log_dir)).get_log_files(days=7)

    assert files
    assert "path" not in files[0]
    assert str(log_dir) not in repr(files)


def test_read_log_file_rejects_traversal(log_dir):
    from app.features.logs.log_service import LogService
    from app.features.logs.security import UnsafeLogPathError

    with pytest.raises(UnsafeLogPathError):
        LogService(str(log_dir)).read_log_file("../secret.log")


def test_nonblocking_log_poll_reads_only_new_lines(log_dir):
    from app.features.logs.log_service import LogService

    service = LogService(str(log_dir))
    filename, offset = service.create_stream_cursor()
    assert filename == "app.log"
    assert service.poll_log_updates(filename, offset)[0] == []

    with (log_dir / "app.log").open("a", encoding="utf-8") as log_file:
        log_file.write(
            "2026-08-02 01:02:04.004 | ERROR | app.test:run:11 - new entry\n"
        )

    updates, new_filename, new_offset = service.poll_log_updates(filename, offset)

    assert new_filename == "app.log"
    assert new_offset > offset
    assert updates[0]["level"] == "ERROR"
    assert updates[0]["message"] == "new entry"


def test_clear_old_logs_scans_all_safe_log_files(log_dir):
    from app.features.logs.log_service import LogService

    old_log = log_dir / "old.log"
    old_log.write_text(LOG_LINE, encoding="utf-8")
    old_timestamp = (datetime.now() - timedelta(days=90)).timestamp()
    os.utime(old_log, (old_timestamp, old_timestamp))

    cleared = LogService(str(log_dir)).clear_old_logs(days=30)

    assert cleared == 1
    assert not old_log.exists()
    assert (log_dir / "app.log").exists()


def test_logs_http_permission_matrix_is_declared():
    from app.features.logs import router as logs_router

    expected = {
        "list_logs": "require_log_read",
        "list_log_files": "require_log_read",
        "get_log_file_content": "require_log_read",
        "search_logs": "require_log_read",
        "clear_old_logs": "require_log_clear",
    }
    for function_name, dependency_name in expected.items():
        function = getattr(logs_router, function_name)
        parameter = inspect.signature(function).parameters.get("_")
        assert parameter is not None, f"{function_name} missing permission dependency"
        assert parameter.default.dependency is getattr(logs_router, dependency_name)


@pytest.fixture
def auth_config(monkeypatch):
    from app.shared.config import get_config

    config = get_config()
    monkeypatch.setattr(config.security, "auth_enabled", True)
    monkeypatch.setattr(config.app, "debug", False)
    return config


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


def _token_for(user):
    from app.features.auth.router import create_access_token

    return create_access_token({"sub": user.username, "user_id": user.id})


def _logs_client(current_user, db_session, log_dir, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.features.auth.router import get_current_user_from_token
    from app.features.logs import router as logs_router
    from app.features.logs.log_service import LogService
    from app.shared.database import get_db

    monkeypatch.setattr(logs_router, "get_log_service", lambda: LogService(str(log_dir)))
    app = FastAPI()
    app.include_router(logs_router.router)
    app.dependency_overrides[get_current_user_from_token] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: db_session
    return TestClient(app)


def test_logs_http_read_and_clear_permissions(db_session, auth_config, log_dir, monkeypatch):
    reader = _create_user(db_session, "log-reader", permission="log:read")
    clearer = _create_user(db_session, "log-clearer", permission="log:clear")
    admin = _create_user(db_session, "log-admin", superuser=True)

    with _logs_client(None, db_session, log_dir, monkeypatch) as client:
        assert client.get("/api/logs/files").status_code == 401
    with _logs_client(reader, db_session, log_dir, monkeypatch) as client:
        assert client.get("/api/logs/files").status_code == 200
        assert client.post("/api/logs/clear?days=30").status_code == 403
    with _logs_client(clearer, db_session, log_dir, monkeypatch) as client:
        assert client.get("/api/logs/files").status_code == 403
        assert client.post("/api/logs/clear?days=30").status_code == 200
    with _logs_client(admin, db_session, log_dir, monkeypatch) as client:
        assert client.get("/api/logs/files").status_code == 200
        assert client.post("/api/logs/clear?days=30").status_code == 200


def test_logs_http_bounds_and_safe_filename(db_session, auth_config, log_dir, monkeypatch):
    reader = _create_user(db_session, "bounded-log-reader", permission="log:read")

    with _logs_client(reader, db_session, log_dir, monkeypatch) as client:
        assert client.get("/api/logs?limit=0").status_code == 422
        assert client.get("/api/logs/search?keyword=&max_results=1").status_code == 422
        response = client.get("/api/logs/files/%2E%2E%2Fsecret.log")
        assert response.status_code in {400, 404}
        files = client.get("/api/logs/files").json()["items"]

    assert files
    assert "path" not in files[0]


def _websocket_app(db_session, log_dir, monkeypatch):
    from fastapi import FastAPI

    import app.features.logs.security as security_module
    import app.shared.database as database_module
    from app.features.logs import router as logs_router
    from app.features.logs.log_service import LogService
    from app.features.websocket.router import router as shared_websocket_router

    class Manager:
        @staticmethod
        def get_session():
            return db_session

    monkeypatch.setattr(security_module, "get_db_manager", lambda: Manager())
    monkeypatch.setattr(database_module, "get_db_manager", lambda: Manager())
    monkeypatch.setattr(logs_router, "get_log_service", lambda: LogService(str(log_dir)))
    app = FastAPI()
    app.include_router(logs_router.router)
    app.include_router(shared_websocket_router)
    return app


def test_file_log_websocket_rejects_missing_token(db_session, auth_config, log_dir, monkeypatch):
    from fastapi.testclient import TestClient
    from starlette.websockets import WebSocketDisconnect

    app = _websocket_app(db_session, log_dir, monkeypatch)
    with TestClient(app).websocket_connect("/api/logs/ws") as websocket:
        websocket.send_json({"action": "authenticate"})
        error = websocket.receive_json()
        assert error["status_code"] == 401
        with pytest.raises(WebSocketDisconnect) as exc:
            websocket.receive_json()
        assert exc.value.code == 4401


def test_file_log_websocket_allows_reader_and_ping(db_session, auth_config, log_dir, monkeypatch):
    from fastapi.testclient import TestClient

    reader = _create_user(db_session, "ws-log-reader", permission="log:read")
    app = _websocket_app(db_session, log_dir, monkeypatch)
    with TestClient(app).websocket_connect("/api/logs/ws") as websocket:
        websocket.send_json({"access_token": _token_for(reader)})
        authenticated = websocket.receive_json()
        websocket.send_text("ping")
        pong = websocket.receive_text()

    assert authenticated == {"event": "authenticated", "username": reader.username}
    assert pong == "pong"


@pytest.mark.parametrize("path", ["/ws/logs", "/ws/logs/test-operation"])
def test_callback_log_websockets_reject_user_without_read(
    path, db_session, auth_config, log_dir, monkeypatch
):
    from fastapi.testclient import TestClient
    from starlette.websockets import WebSocketDisconnect

    clearer = _create_user(db_session, f"ws-clearer-{path.count('/')}", permission="log:clear")
    app = _websocket_app(db_session, log_dir, monkeypatch)
    with TestClient(app).websocket_connect(path) as websocket:
        websocket.send_json({"access_token": _token_for(clearer)})
        error = websocket.receive_json()
        assert error["status_code"] == 403
        with pytest.raises(WebSocketDisconnect) as exc:
            websocket.receive_json()
        assert exc.value.code == 4403


@pytest.mark.parametrize("path", ["/ws/logs", "/ws/logs/test-operation"])
def test_callback_log_websockets_allow_reader(
    path, db_session, auth_config, log_dir, monkeypatch
):
    from fastapi.testclient import TestClient

    reader = _create_user(
        db_session,
        f"ws-reader-{path.count('/')}",
        permission="log:read",
    )
    app = _websocket_app(db_session, log_dir, monkeypatch)
    with TestClient(app).websocket_connect(path) as websocket:
        websocket.send_json({"access_token": _token_for(reader)})
        authenticated = websocket.receive_json()

        if path == "/ws/logs":
            websocket.send_text("ping")
            assert websocket.receive_text() == "pong"

    assert authenticated == {"event": "authenticated", "username": reader.username}


def test_logs_menu_uses_functional_read_permission():
    root = Path(__file__).resolve().parents[1]
    source = (root / "frontend/src/views/Layout.vue").read_text(encoding="utf-8")
    menu_line = next(line for line in source.splitlines() if "path: '/logs'" in line)

    assert "permission: 'log:read'" in menu_line


def test_logs_websocket_source_has_no_blocking_stream_loop():
    root = Path(__file__).resolve().parents[1]
    source = (root / "app/features/logs/router.py").read_text(encoding="utf-8")

    assert "stream_logs(" not in source
    assert "time.sleep(" not in source
    assert "asyncio.to_thread" in source
    assert '"message": str(' not in source


def test_log_service_does_not_disclose_absolute_paths():
    root = Path(__file__).resolve().parents[1]
    source = (root / "app/features/logs/log_service.py").read_text(encoding="utf-8")

    assert '"path": str(log_file)' not in source
    assert 'error: {e}' not in source
