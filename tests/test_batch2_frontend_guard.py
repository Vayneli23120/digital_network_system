"""批次二·安全 切片 C · 前端守卫缺权限（item 133）

覆盖：
- 受保护路由挂载 meta.permission（功能权限 code）
- router guard 含 admin:all 短路、fetchMyPermissions 拉取、空/未加载放行约定
- auth store 含 permissions / permissionsLoaded 状态与 fetchMyPermissions action
"""

from pathlib import Path

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"
ROUTER_SRC = (FRONTEND_DIR / "src/router/index.js").read_text(encoding="utf-8")
AUTH_SRC = (FRONTEND_DIR / "src/stores/auth.js").read_text(encoding="utf-8")


class TestRouteMetaPermission:
    """受保护页面路由须声明 meta.permission"""

    GUARDED = [
        ("/users", "user:read"),
        ("/credentials", "credential:read"),
        ("/system-settings", "system_config:read"),
        ("/permissions", "role:read"),
        ("/logs", "log:read"),
        ("/notification-settings", "notification:manage"),
        ("/notifications", "notification:read"),
        ("/discovery", "discovery:read"),
        ("/compliance", "compliance:read"),
    ]

    def test_guard_routes_carry_permission(self):
        for route, code in self.GUARDED:
            block_start = ROUTER_SRC.find(f"path: '{route}'")
            assert block_start != -1, f"{route} 未注册"
            meta_pos = ROUTER_SRC.find("meta: {", block_start)
            assert meta_pos != -1, f"{route} 缺 meta"
            meta_line_end = ROUTER_SRC.find("}", meta_pos)
            meta_line = ROUTER_SRC[meta_pos:meta_line_end + 1]
            assert code in meta_line, f"{route} 缺 permission: '{code}'"


class TestGuardLogic:
    def test_guard_shortcircuits_admin_all(self):
        """超管（my-permissions 只回 admin:all 不展开）须放行"""
        assert "permissions.includes('admin:all')" in ROUTER_SRC

    def test_guard_fetches_permissions(self):
        assert "await auth.fetchMyPermissions()" in ROUTER_SRC
        assert "permissionsLoaded" in ROUTER_SRC

    def test_guard_allows_empty_permissions(self):
        """空/未加载 = 放行（体验层兜底，后端才是真拦截）"""
        assert "permissions.length > 0" in ROUTER_SRC

    def test_guard_redirects_home_when_missing(self):
        assert "includes(required)" in ROUTER_SRC
        assert "next('/')" in ROUTER_SRC


class TestAuthStore:
    def test_has_permissions_state(self):
        assert "permissions: []" in AUTH_SRC
        assert "permissionsLoaded: false" in AUTH_SRC

    def test_has_fetch_my_permissions_action(self):
        assert "async fetchMyPermissions()" in AUTH_SRC
        assert "/permissions/my-permissions" in AUTH_SRC

    def test_clear_auth_resets_permissions(self):
        assert "this.permissions = []" in AUTH_SRC
        assert "this.permissionsLoaded = false" in AUTH_SRC
