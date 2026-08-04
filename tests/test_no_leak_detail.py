"""
回归测试：catch-all 异常处理器不得回显内部异常文本（CODE_REVIEW_ISSUES.md item 134）。

此前 5 个 router 共 12 处 `except Exception as e: raise HTTPException(detail=str(e) / detail=f"...{e}")`
会向客户端泄露内部异常细节。修复后统一改为「面向用户的中文通用文案 + 服务端 logger.error」。

本文件对每个被改 router 取一条最易触发的 catch-all 路径，monkeypatch 内部函数抛
RuntimeError("LEAK-MARKER-...")，断言响应：
1. 状态码符合该路径（大多 500，devices 导入为 400）
2. detail 为通用文案，且不含 marker（不回显原始异常文本）

不覆盖所有 12 处（部分路径需要 seed 复杂依赖），覆盖全部 5 个 router 即可守住该模式。
"""

MARKER = "LEAK-MARKER-7f3a"


def _assert_generic_no_leak(response, expected_detail):
    assert response.status_code in (400, 500)
    body = response.json()
    assert body.get("detail") == expected_detail
    assert MARKER not in body.get("detail", "")


class TestDiscoveryCatchAll:
    """discovery/router.py：Ping Sweep 与综合发现 catch-all"""

    def test_ping_sweep_hides_raw_exception(self, router_client_factory, monkeypatch):
        from app.features.discovery import router as discovery_router

        async def raiser(*args, **kwargs):
            raise RuntimeError(MARKER)

        monkeypatch.setattr(discovery_router, "run_device_op", raiser)
        client = router_client_factory(discovery_router.router)

        r = client.post("/api/discovery/ping-sweep", json={"subnet": "10.0.0.0/24"})
        _assert_generic_no_leak(r, "Ping Sweep 失败，请查看服务端日志")

    def test_discover_hides_raw_exception(self, router_client_factory, monkeypatch):
        from app.features.discovery import router as discovery_router

        def raiser(*args, **kwargs):
            raise RuntimeError(MARKER)

        monkeypatch.setattr(discovery_router, "NETMIKO_AVAILABLE", True)
        monkeypatch.setattr(discovery_router, "get_discovery_service", raiser)
        client = router_client_factory(discovery_router.router)

        r = client.post("/api/discovery/discover", json={"subnet": "10.0.0.0/24"})
        _assert_generic_no_leak(r, "设备发现失败，请查看服务端日志")


class TestComplianceCatchAll:
    """compliance/router.py：AI 配置创建/更新 catch-all（内部 next(get_db())，需 _db_manager 路由到测试库）"""

    def test_create_ai_config_hides_raw_exception(self, router_client_factory, db_manager, monkeypatch):
        from app.shared import database
        from app.features.compliance import router as compliance_router

        monkeypatch.setattr(database, "_db_manager", db_manager)

        def raiser(value):
            raise RuntimeError(MARKER)

        monkeypatch.setattr(compliance_router, "encrypt_text", raiser)
        client = router_client_factory(compliance_router.router)

        r = client.post("/api/compliance/ai-config", json={
            "provider": "openai",
            "api_key": "sk-test-123",
            "model_name": "gpt-4",
            "is_default": False,
        })
        _assert_generic_no_leak(r, "创建 AI 配置失败，请查看服务端日志")

    def test_update_ai_config_hides_raw_exception(self, router_client_factory, db_manager, db_session, monkeypatch):
        from app.shared import database
        from app.features.compliance import router as compliance_router
        from app.shared.models import AIConfig

        monkeypatch.setattr(database, "_db_manager", db_manager)
        config = AIConfig(name="openai-gpt-4", provider="openai")
        db_session.add(config)
        db_session.commit()

        def raiser(value):
            raise RuntimeError(MARKER)

        monkeypatch.setattr(compliance_router, "encrypt_text", raiser)
        client = router_client_factory(compliance_router.router)

        r = client.put(f"/api/compliance/ai-config/{config.id}", json={
            "provider": "openai",
            "api_key": "sk-new-456",
        })
        _assert_generic_no_leak(r, "更新 AI 配置失败，请查看服务端日志")


class TestDeployCatchAll:
    """deploy/router.py：部署历史详情 catch-all（Depends(get_db) 可注入，seed 一条历史记录后触发）"""

    def test_history_detail_hides_raw_exception(self, router_client_factory, db_session, monkeypatch):
        from app.features.deploy import router as deploy_router
        from app.shared.models import DeployHistory

        history = DeployHistory(operation_type="deploy", engine="netmiko", success=True)
        db_session.add(history)
        db_session.commit()

        def raiser(value, *args, **kwargs):
            raise RuntimeError(MARKER)

        monkeypatch.setattr(deploy_router, "utc_iso", raiser)
        client = router_client_factory(deploy_router.router)

        r = client.get(f"/api/deploy/history/{history.id}")
        _assert_generic_no_leak(r, "获取部署详情失败，请查看服务端日志")


class TestPermissionsCatchAll:
    """permissions/router.py：权限系统初始化 catch-all"""

    def test_init_hides_raw_exception(self, router_client_factory, monkeypatch):
        from app.features.permissions import router as permissions_router

        def raiser(db, reset_system_roles=False):
            raise RuntimeError(MARKER)

        monkeypatch.setattr(permissions_router, "init_permissions_and_roles", raiser)
        client = router_client_factory(permissions_router.router)

        r = client.post("/api/permissions/init")
        _assert_generic_no_leak(r, "权限系统初始化失败，请查看服务端日志")


class TestDevicesCatchAll:
    """devices/router.py：Excel 导入 catch-all（400，解析失败通用文案）"""

    def test_import_hides_raw_exception(self, router_client_factory, monkeypatch):
        from app.features.devices import router as devices_router

        def raiser(*args, **kwargs):
            raise RuntimeError(MARKER)

        monkeypatch.setattr(devices_router, "EXCEL_AVAILABLE", True)
        monkeypatch.setattr(devices_router.openpyxl, "load_workbook", raiser)
        client = router_client_factory(devices_router.router)

        r = client.post(
            "/api/devices/import",
            files={"file": ("devices.xlsx", b"payload-bytes",
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        _assert_generic_no_leak(r, "导入失败：文件解析失败，请检查 Excel 格式")
