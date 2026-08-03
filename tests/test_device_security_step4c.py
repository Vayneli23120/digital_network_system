"""Security Step 4C: Devices permissions and photo handling."""

import asyncio
import io
import inspect
from pathlib import Path

import pytest
from fastapi import HTTPException

import app.shared.models_jobs  # noqa: F401  Register jobs table in metadata.


def _jpeg_bytes(payload: bytes = b"photo") -> bytes:
    return b"\xff\xd8\xff\xe0" + payload + b"\xff\xd9"


def test_photo_storage_ignores_client_filename(tmp_path):
    from app.features.devices.photo_security import allocate_photo_path

    destination, public_url = allocate_photo_path(7, "image/jpeg", tmp_path)

    assert destination.parent == (tmp_path / "7").resolve()
    assert destination.suffix == ".jpg"
    assert ".." not in destination.name
    assert public_url == f"/photos/7/{destination.name}"


@pytest.mark.parametrize("content_type", [
    "application/octet-stream",
    "image/svg+xml",
    "text/html",
    "",
])
def test_photo_rejects_unsupported_content_types(content_type):
    from app.features.devices.photo_security import (
        DevicePhotoValidationError,
        extension_for_content_type,
    )

    with pytest.raises(DevicePhotoValidationError):
        extension_for_content_type(content_type)


def test_photo_saves_valid_image_atomically(tmp_path):
    from app.features.devices.photo_security import save_uploaded_photo

    destination = tmp_path / "1" / "photo.jpg"
    content = _jpeg_bytes()

    size = save_uploaded_photo(io.BytesIO(content), destination, "image/jpeg")

    assert size == len(content)
    assert destination.read_bytes() == content
    assert not destination.with_suffix(".jpg.uploading").exists()


def test_photo_rejects_signature_mismatch_and_cleans_temp(tmp_path):
    from app.features.devices.photo_security import (
        DevicePhotoValidationError,
        save_uploaded_photo,
    )

    destination = tmp_path / "1" / "photo.jpg"

    with pytest.raises(DevicePhotoValidationError, match="内容"):
        save_uploaded_photo(io.BytesIO(b"<script>alert(1)</script>"), destination, "image/jpeg")

    assert not destination.exists()
    assert not destination.with_suffix(".jpg.uploading").exists()


def test_photo_rejects_oversized_stream_without_leaving_file(tmp_path):
    from app.features.devices.photo_security import (
        DevicePhotoValidationError,
        save_uploaded_photo,
    )

    destination = tmp_path / "1" / "photo.jpg"

    with pytest.raises(DevicePhotoValidationError, match="10 MB"):
        save_uploaded_photo(
            io.BytesIO(_jpeg_bytes(b"x" * 64)),
            destination,
            "image/jpeg",
            max_bytes=16,
        )

    assert not destination.exists()


def test_photo_path_rejects_traversal_and_outside_absolute_path(tmp_path):
    from app.features.devices.photo_security import (
        DevicePhotoValidationError,
        resolve_stored_photo_path,
    )

    photo_root = tmp_path / "photos"
    photo_root.mkdir()
    outside = tmp_path / "secret.txt"
    outside.write_text("secret", encoding="utf-8")

    with pytest.raises(DevicePhotoValidationError):
        resolve_stored_photo_path("../secret.txt", photo_root)
    with pytest.raises(DevicePhotoValidationError):
        resolve_stored_photo_path(outside, photo_root)


def test_photo_path_rejects_symlink_escape_when_supported(tmp_path):
    from app.features.devices.photo_security import (
        DevicePhotoValidationError,
        resolve_stored_photo_path,
    )

    photo_root = tmp_path / "photos"
    photo_root.mkdir()
    outside = tmp_path / "secret.txt"
    outside.write_text("secret", encoding="utf-8")
    link = photo_root / "link.jpg"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("Symlink creation is unavailable")

    with pytest.raises(DevicePhotoValidationError):
        resolve_stored_photo_path(link, photo_root)


def test_public_photo_url_normalizes_legacy_path(tmp_path, monkeypatch):
    from app.features.devices.photo_security import public_photo_url

    photo_root = tmp_path / "assets" / "devices"
    legacy = photo_root / "SW-01" / "photos" / "front.jpg"
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(_jpeg_bytes())
    monkeypatch.chdir(tmp_path)

    assert public_photo_url(str(legacy.relative_to(tmp_path)), photo_root) == (
        "/photos/SW-01/photos/front.jpg"
    )


def test_photo_type_is_validated():
    from app.features.devices.photo_security import (
        DevicePhotoValidationError,
        validate_photo_type,
    )

    assert validate_photo_type("rack") == "rack"
    with pytest.raises(DevicePhotoValidationError):
        validate_photo_type("../../other")


def test_device_permission_matrix_is_declared_on_all_endpoints():
    from app.features.devices import router as device_router

    expected = {
        "test_device_reachability": "require_device_write",
        "test_device_connection": "require_device_write",
        "fetch_device_info": "require_device_write",
        "list_devices": "require_device_read",
        "export_devices": "require_device_export",
        "import_devices": "require_device_import",
        "list_vendors": "require_device_read",
        "get_vendor": "require_device_read",
        "manual_check_reachability": "require_device_write",
        "get_reachability_stats": "require_device_read",
        "get_monitor_status": "require_device_read",
        "get_monitor_diagnostics": "require_device_read",
        "get_trap_diagnostics": "require_device_read",
        "trigger_monitor_check_now": "require_device_write",
        "get_device_performance_metrics": "require_device_read",
        "get_device_performance_metric_history": "require_device_read",
        "diagnose_device_snmp": "require_device_read",
        "get_device": "require_device_read",
        "create_device": "require_device_write",
        "update_device": "require_device_write",
        "delete_device": "require_device_delete",
        "upload_device_photo": "require_device_photo",
        "get_device_photos": "require_device_read",
        "get_device_photo_content": "require_device_read",
        "delete_device_photo": "require_device_photo",
        "get_device_inventory": "require_device_read",
        "update_device_snmp": "require_device_write",
        "discover_device_interfaces": "require_device_write",
        "discover_device_neighbors": "require_device_write",
        "list_device_interfaces": "require_device_read",
        "update_device_interface": "require_device_write",
        "get_interface_traffic": "require_device_read",
        "discover_neighbors_all": "require_device_write",
        "list_neighbor_links": "require_device_read",
    }

    for function_name, dependency_name in expected.items():
        function = getattr(device_router, function_name)
        parameter = inspect.signature(function).parameters.get("_")
        assert parameter is not None, f"{function_name} is missing permission dependency"
        assert parameter.default.dependency is getattr(device_router, dependency_name)


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


def _device_client(current_user, db_session):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.features.auth.identity import Principal, get_current_principal
    from app.features.auth.router import get_current_user_from_token
    from app.features.devices import router as device_router
    from app.shared.database import get_db

    app = FastAPI()
    app.include_router(device_router.router)
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


def test_device_read_endpoint_enforces_permission(db_session, auth_config):
    reader = _create_user(db_session, "device-reader", permission="device:read")
    writer = _create_user(db_session, "device-writer", permission="device:write")
    admin = _create_user(db_session, "device-admin", superuser=True)

    with _device_client(None, db_session) as client:
        assert client.get("/api/devices/vendors").status_code == 401
    with _device_client(reader, db_session) as client:
        assert client.get("/api/devices/vendors").status_code == 200
    with _device_client(writer, db_session) as client:
        assert client.get("/api/devices/vendors").status_code == 403
    with _device_client(admin, db_session) as client:
        assert client.get("/api/devices/vendors").status_code == 200


def test_device_write_endpoint_denies_reader_before_probe(db_session, auth_config):
    reader = _create_user(db_session, "probe-reader", permission="device:read")

    with _device_client(reader, db_session) as client:
        response = client.post(
            "/api/devices/test-reachability",
            json={"ip": "192.0.2.1"},
        )

    assert response.status_code == 403


def test_device_permission_tiers_are_separated(db_session, auth_config):
    from app.features.devices.router import (
        require_device_delete,
        require_device_export,
        require_device_import,
        require_device_photo,
        require_device_read,
        require_device_write,
    )

    checkers = {
        "device:read": require_device_read,
        "device:write": require_device_write,
        "device:delete": require_device_delete,
        "device:import": require_device_import,
        "device:export": require_device_export,
        "device:photo": require_device_photo,
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


def test_photo_upload_requires_photo_permission(db_session, auth_config):
    from app.shared.models import Device

    device = Device(name="photo-device", ip="192.0.2.2")
    db_session.add(device)
    db_session.commit()
    reader = _create_user(db_session, "photo-reader", permission="device:read")

    with _device_client(reader, db_session) as client:
        response = client.post(
            f"/api/devices/{device.id}/photos",
            files={"photo": ("front.jpg", _jpeg_bytes(), "image/jpeg")},
            data={"photo_type": "front"},
        )

    assert response.status_code == 403


def test_photo_upload_generates_safe_name_and_trusted_uploader(
    db_session, auth_config, tmp_path, monkeypatch
):
    from app.features.devices import router as device_router
    from app.shared.models import Device, DevicePhoto

    device = Device(name="unsafe/../device", ip="192.0.2.3")
    db_session.add(device)
    db_session.commit()
    photographer = _create_user(
        db_session,
        "trusted-photographer",
        permission="device:photo",
    )
    destination = tmp_path / "photos" / str(device.id) / "safe.jpg"
    monkeypatch.setattr(
        device_router,
        "allocate_photo_path",
        lambda _device_id, _content_type: (
            destination,
            f"/photos/{device.id}/safe.jpg",
        ),
    )

    with _device_client(photographer, db_session) as client:
        response = client.post(
            f"/api/devices/{device.id}/photos",
            files={"photo": ("../../evil.jpg", _jpeg_bytes(), "image/jpeg")},
            data={"photo_type": "front", "uploader": "forged-admin"},
        )

    assert response.status_code == 200
    assert response.json()["filename"] == "safe.jpg"
    assert destination.read_bytes() == _jpeg_bytes()
    record = db_session.query(DevicePhoto).filter(DevicePhoto.device_id == device.id).one()
    assert record.photo_path == f"/photos/{device.id}/safe.jpg"
    assert record.uploader == photographer.username


def test_photo_upload_rejects_mime_signature_mismatch(
    db_session, auth_config, tmp_path, monkeypatch
):
    from app.features.devices import router as device_router
    from app.shared.models import Device

    device = Device(name="bad-photo-device", ip="192.0.2.4")
    db_session.add(device)
    db_session.commit()
    photographer = _create_user(
        db_session,
        "bad-photo-uploader",
        permission="device:photo",
    )
    destination = tmp_path / "photos" / str(device.id) / "bad.jpg"
    monkeypatch.setattr(
        device_router,
        "allocate_photo_path",
        lambda _device_id, _content_type: (
            destination,
            f"/photos/{device.id}/bad.jpg",
        ),
    )

    with _device_client(photographer, db_session) as client:
        response = client.post(
            f"/api/devices/{device.id}/photos",
            files={"photo": ("fake.jpg", b"<script>x</script>", "image/jpeg")},
            data={"photo_type": "front"},
        )

    assert response.status_code == 400
    assert not destination.exists()


def test_photo_content_requires_read_permission_and_returns_image(
    db_session, auth_config, tmp_path, monkeypatch
):
    from app.features.devices import router as device_router
    from app.shared.models import Device, DevicePhoto

    device = Device(name="content-device", ip="192.0.2.5")
    db_session.add(device)
    db_session.flush()
    photo_path = tmp_path / "photos" / str(device.id) / "content.jpg"
    photo_path.parent.mkdir(parents=True)
    photo_path.write_bytes(_jpeg_bytes())
    photo = DevicePhoto(
        device_id=device.id,
        device_name=device.name,
        photo_path=f"/photos/{device.id}/content.jpg",
        photo_type="front",
        uploader="test",
    )
    db_session.add(photo)
    db_session.commit()
    reader = _create_user(db_session, "content-reader", permission="device:read")
    writer = _create_user(db_session, "content-writer", permission="device:write")
    monkeypatch.setattr(
        device_router,
        "resolve_stored_photo_path",
        lambda _stored_path: photo_path,
    )

    with _device_client(reader, db_session) as client:
        response = client.get(f"/api/devices/{device.id}/photos/{photo.id}/content")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content == _jpeg_bytes()

    with _device_client(writer, db_session) as client:
        assert client.get(
            f"/api/devices/{device.id}/photos/{photo.id}/content"
        ).status_code == 403


def test_photo_content_rejects_unsafe_stored_path(
    db_session, auth_config, monkeypatch
):
    from app.features.devices import router as device_router
    from app.features.devices.photo_security import DevicePhotoValidationError
    from app.shared.models import Device, DevicePhoto

    device = Device(name="unsafe-content-device", ip="192.0.2.6")
    db_session.add(device)
    db_session.flush()
    photo = DevicePhoto(
        device_id=device.id,
        device_name=device.name,
        photo_path="../../secret.jpg",
        photo_type="front",
        uploader="test",
    )
    db_session.add(photo)
    db_session.commit()
    reader = _create_user(db_session, "unsafe-content-reader", permission="device:read")
    monkeypatch.setattr(
        device_router,
        "resolve_stored_photo_path",
        lambda _stored_path: (_ for _ in ()).throw(DevicePhotoValidationError("unsafe")),
    )

    with _device_client(reader, db_session) as client:
        response = client.get(f"/api/devices/{device.id}/photos/{photo.id}/content")

    assert response.status_code == 400


def test_device_import_rejects_oversized_file_before_parsing(
    db_session, auth_config, monkeypatch
):
    from app.features.devices import router as device_router

    importer = _create_user(db_session, "device-importer", permission="device:import")
    monkeypatch.setattr(device_router, "MAX_DEVICE_IMPORT_BYTES", 8)

    with _device_client(importer, db_session) as client:
        response = client.post(
            "/api/devices/import",
            files={
                "file": (
                    "devices.xlsx",
                    b"123456789",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )

    assert response.status_code == 413


def test_device_import_has_size_limit_and_threaded_parser_source():
    root = Path(__file__).resolve().parents[1]
    source = (root / "app/features/devices/router.py").read_text(encoding="utf-8")

    assert "MAX_DEVICE_IMPORT_BYTES" in source
    assert "file.read(MAX_DEVICE_IMPORT_BYTES + 1)" in source
    assert "await asyncio.to_thread(openpyxl.load_workbook" in source
    assert "await file.close()" in source


def test_photo_static_mount_is_removed_and_floor_plan_content_is_protected():
    root = Path(__file__).resolve().parents[1]
    main_source = (root / "app/main.py").read_text(encoding="utf-8")
    monitor_source = (
        root / "app/features/monitor_screen/router.py"
    ).read_text(encoding="utf-8")
    # 批次五 946 切片 9a：loadFloorPlanTexture 迁入 useThreeScene composable
    frontend_source = (
        root / "frontend/src/composables/useThreeScene.js"
    ).read_text(encoding="utf-8")

    assert 'app.mount("/photos"' not in main_source
    assert "get_floor_plan_content" in monitor_source
    assert "Depends(require_floor_plan_read)" in monitor_source
    assert "getFloorPlanContent(deps.currentPlan.value.id)" in frontend_source
    assert "'/photos/floor_plans/'" not in frontend_source


def test_legacy_device_components_use_authenticated_axios():
    root = Path(__file__).resolve().parents[1]
    component_paths = [
        root / "frontend/src/views/Monitor3D.vue",
        root / "frontend/src/views/Devices.vue",
        root / "frontend/src/components/ui/DeviceTrafficChart.vue",
    ]

    for component_path in component_paths:
        source = component_path.read_text(encoding="utf-8")
        assert "authenticatedAxios as axios" in source
        assert "from 'axios'" not in source


def test_floor_plan_content_rejects_path_outside_floor_plan_root(
    db_session, auth_config, tmp_path, monkeypatch
):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.features.auth.router import get_current_user_from_token
    from app.features.monitor_screen import router as monitor_router
    from app.shared.database import get_db
    from app.shared.models import FloorPlan

    reader = _create_user(db_session, "floor-reader", permission="floor_plan:read")
    outside = tmp_path / "secret.png"
    outside.write_bytes(b"\x89PNG\r\n\x1a\nsecret")
    plan = FloorPlan(name="unsafe-plan", image_path=str(outside))
    db_session.add(plan)
    db_session.commit()
    monkeypatch.setattr(
        monitor_router.config.storage,
        "photo_dir",
        str(tmp_path / "photos"),
    )

    app = FastAPI()
    app.include_router(monitor_router.router)
    app.dependency_overrides[get_current_user_from_token] = lambda: reader
    app.dependency_overrides[get_db] = lambda: db_session

    with TestClient(app) as client:
        response = client.get(f"/api/floor-plans/{plan.id}/content")

    assert response.status_code == 400


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


def _token_for(user):
    from app.features.auth.router import create_access_token

    return create_access_token({"sub": user.username, "user_id": user.id})


def test_device_status_websocket_rejects_missing_token(
    db_session, auth_config, monkeypatch
):
    from fastapi.testclient import TestClient
    from starlette.websockets import WebSocketDisconnect

    app = _websocket_app(db_session, monkeypatch)
    with TestClient(app).websocket_connect("/ws/device-status") as websocket:
        websocket.send_json({"action": "authenticate"})
        error = websocket.receive_json()
        assert error["event"] == "auth_error"
        assert error["status_code"] == 401
        with pytest.raises(WebSocketDisconnect) as exc:
            websocket.receive_json()
        assert exc.value.code == 4401


def test_device_status_websocket_rejects_user_without_read(
    db_session, auth_config, monkeypatch
):
    from fastapi.testclient import TestClient
    from starlette.websockets import WebSocketDisconnect

    writer = _create_user(db_session, "ws-device-writer", permission="device:write")
    app = _websocket_app(db_session, monkeypatch)
    with TestClient(app).websocket_connect("/ws/device-status") as websocket:
        websocket.send_json({"access_token": _token_for(writer)})
        error = websocket.receive_json()
        assert error["status_code"] == 403
        with pytest.raises(WebSocketDisconnect) as exc:
            websocket.receive_json()
        assert exc.value.code == 4403


def test_device_status_websocket_allows_reader(
    db_session, auth_config, monkeypatch
):
    from fastapi.testclient import TestClient

    reader = _create_user(db_session, "ws-device-reader", permission="device:read")
    app = _websocket_app(db_session, monkeypatch)
    with TestClient(app).websocket_connect("/ws/device-status") as websocket:
        websocket.send_json({"access_token": _token_for(reader)})
        authenticated = websocket.receive_json()
        websocket.send_text("ping")
        pong = websocket.receive_text()

    assert authenticated == {"event": "authenticated", "username": reader.username}
    assert pong == "pong"


def test_device_status_frontend_sends_access_token():
    root = Path(__file__).resolve().parents[1]
    source = (root / "frontend/src/views/Monitor3D.vue").read_text(encoding="utf-8")

    assert "deviceStatusWs.onopen" in source
    assert "access_token: authStore.accessToken" in source
