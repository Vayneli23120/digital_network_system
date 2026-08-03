"""批次二·安全 切片 A · 长尾资源授权（item 78）

覆盖：
- 新增 10 个权限 code 进入 EXTENDED_PERMISSIONS（init 时增量补齐）
- PRESET_ROLES operator/viewer 获得对应授权
- require_permission checker 行为（无权限 403 / superuser 通过 / debug 绕过）
- shadowed route 修复（jobs 静态子路径、scan /sessions/active 注册顺序）
- 扫码枪侧端点保持开放（无登录终端）
"""

import asyncio
from pathlib import Path

import pytest
from fastapi import HTTPException

import app.shared.models_jobs  # noqa: F401  让 jobs 表进入 Base.metadata

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app"

NEW_PERMISSION_CODES = {
    "notification:read",
    "notification:write",
    "job:read",
    "job:cancel",
    "compliance:read",
    "compliance:write",
    "discovery:read",
    "discovery:scan",
    "scan:read",
    "scan:write",
}

OPERATOR_LONGTALL = {
    "notification:read", "notification:write",
    "job:read", "job:cancel",
    "compliance:check", "compliance:read", "compliance:write",
    "discovery:read", "discovery:scan",
    "scan:read", "scan:write",
    "ai:config",
}

VIEWER_LONGTALL = {
    "notification:read", "job:read",
    "compliance:check", "compliance:read",
    "discovery:read", "scan:read",
}


def _read(rel_path: str) -> str:
    return (APP_DIR / rel_path).read_text(encoding="utf-8")


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
        username="admin-batch2a",
        password_hash="unused",
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ==================== 静态：权限清单与角色 ====================


class TestPermissionCatalog:
    def test_new_codes_in_extended_permissions(self):
        src = _read("features/permissions/router.py")
        for code in sorted(NEW_PERMISSION_CODES):
            assert f'"{code}"' in src

    def test_operator_role_includes_longtail(self):
        src = _read("features/permissions/router.py")
        operator_block = src.split('"name": "operator"', 1)[1].split('"name": "viewer"', 1)[0]
        for code in sorted(OPERATOR_LONGTALL):
            assert f'"{code}"' in operator_block

    def test_viewer_role_includes_read_longtail(self):
        src = _read("features/permissions/router.py")
        viewer_block = src.split('"name": "viewer"', 1)[1].split('"name": "device_manager"', 1)[0]
        for code in sorted(VIEWER_LONGTALL):
            assert f'"{code}"' in viewer_block


# ==================== 运行时：require_permission checker ====================


def _check(permission: str, user, db):
    from app.shared.dependencies import require_permission

    return asyncio.run(require_permission(permission)(user, db))


class TestRequirePermissionBehavior:
    def test_denies_user_without_permission(self, db_session, security_config, monkeypatch):
        from app.shared.models import User

        monkeypatch.setattr(security_config.security, "auth_enabled", True)
        monkeypatch.setattr(security_config.app, "debug", False)
        user = User(
            username="viewer-batch2a",
            password_hash="unused",
            is_active=True,
            is_superuser=False,
        )
        db_session.add(user)
        db_session.commit()

        for permission in ("job:read", "notification:write", "compliance:read", "scan:write"):
            with pytest.raises(HTTPException) as exc:
                _check(permission, user, db_session)
            assert exc.value.status_code == 403

    def test_superuser_passes(self, db_session, active_admin, security_config, monkeypatch):
        monkeypatch.setattr(security_config.security, "auth_enabled", True)
        monkeypatch.setattr(security_config.app, "debug", False)

        for permission in ("job:read", "notification:write", "compliance:read", "scan:write"):
            result = _check(permission, active_admin, db_session)
            assert result.id == active_admin.id

    def test_debug_bypass_returns_none(self, db_session, security_config, monkeypatch):
        monkeypatch.setattr(security_config.security, "auth_enabled", False)
        monkeypatch.setattr(security_config.app, "debug", True)
        from app.shared.dependencies import require_permission

        result = asyncio.run(require_permission("job:read")(None, db_session))
        assert result is None


# ==================== 静态：shadowed route 修复 ====================


class TestShadowedRouteOrder:
    def test_jobs_static_paths_registered_before_job_id(self):
        src = _read("features/jobs/router.py")
        stats_pos = src.find('@router.get("/stats")')
        types_pos = src.find('@router.get("/types")')
        statuses_pos = src.find('@router.get("/statuses")')
        job_id_pos = src.find('@router.get("/{job_id}")')
        assert -1 not in (stats_pos, types_pos, statuses_pos, job_id_pos)
        assert stats_pos < job_id_pos
        assert types_pos < job_id_pos
        assert statuses_pos < job_id_pos

    def test_scan_active_registered_before_session_code(self):
        src = _read("features/scan/router.py")
        active_pos = src.find('@router.get("/sessions/active")')
        code_pos = src.find('@router.get("/sessions/{session_code}")')
        assert -1 not in (active_pos, code_pos)
        assert active_pos < code_pos


class TestScanGunEndpointsOpen:
    def test_gun_side_endpoints_have_no_require_dep(self):
        src = _read("features/scan/router.py")

        def endpoint(route: str) -> str:
            block = src.split(f'@router.{route}', 1)[1]
            return block.split("\n\n\n", 1)[0]

        join_block = endpoint('post("/sessions/join")')
        items_block = endpoint('post("/sessions/items")')
        remove_block = endpoint('delete("/sessions/{session_code}/items/{serial_number}")')
        assert "require_" not in join_block
        assert "require_" not in items_block
        assert "require_" not in remove_block


class TestRoutersUseRequireDeps:
    def test_notifications_router_has_require_deps(self):
        src = _read("features/notifications/router.py")
        assert "require_notification_read = require_permission(\"notification:read\")" in src
        assert "require_notification_write = require_permission(\"notification:write\")" in src
        assert src.count("Depends(require_notification_read)") == 2
        assert src.count("Depends(require_notification_write)") == 3

    def test_jobs_router_has_require_deps(self):
        src = _read("features/jobs/router.py")
        assert "require_job_read = require_permission(\"job:read\")" in src
        assert "require_job_cancel = require_permission(\"job:cancel\")" in src
        assert src.count("Depends(require_job_read)") == 6
        assert src.count("Depends(require_job_cancel)") == 1

    def test_compliance_router_has_require_deps(self):
        src = _read("features/compliance/router.py")
        assert "require_compliance_check = require_permission(\"compliance:check\")" in src
        assert "require_compliance_read = require_permission(\"compliance:read\")" in src
        assert "require_compliance_write = require_permission(\"compliance:write\")" in src
        assert "require_ai_config = require_permission(\"ai:config\")" in src
        assert src.count("Depends(require_compliance_check)") == 3
        assert src.count("Depends(require_compliance_read)") == 5
        assert src.count("Depends(require_compliance_write)") == 8
        assert src.count("Depends(require_ai_config)") == 4

    def test_discovery_router_has_require_deps(self):
        src = _read("features/discovery/router.py")
        assert "require_discovery_read = require_permission(\"discovery:read\")" in src
        assert "require_discovery_scan = require_permission(\"discovery:scan\")" in src
        assert src.count("Depends(require_discovery_scan)") == 2
        assert src.count("Depends(require_discovery_read)") == 1

    def test_scan_router_pc_side_has_require_deps(self):
        src = _read("features/scan/router.py")
        assert "require_scan_read = require_permission(\"scan:read\")" in src
        assert "require_scan_write = require_permission(\"scan:write\")" in src
        assert src.count("Depends(require_scan_read)") == 2
        assert src.count("Depends(require_scan_write)") == 3
