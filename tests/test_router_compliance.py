"""
Router 层测试（批次八切片 A）：compliance 端点。

覆盖配置审核的核心链路：内置规则列表、基础审核（use_ai=False）、
空配置 400 校验。compliance 服务内部全部经 next(get_db()) 访问数据库，
因此用 _db_manager monkeypatch 路由到测试库；/check 还需重置
_compliance_service 单例，让 ComplianceService.__init__ 在本测试库执行
init_builtin_rules() 幂等播种内置规则。
"""


class TestComplianceRules:
    def test_list_rules_returns_builtin_rules(self, router_client_factory, db_manager, monkeypatch):
        from app.features.compliance import router as compliance_router
        from app.features.compliance.builtin_rules import init_builtin_rules
        from app.shared import database

        monkeypatch.setattr(database, "_db_manager", db_manager)
        init_builtin_rules()  # 在测试库播种内置规则

        client = router_client_factory(compliance_router.router)
        r = client.get("/api/compliance/rules")
        assert r.status_code == 200
        rules = r.json()["rules"]
        assert len(rules) >= 10
        rule_ids = {rule["rule_id"] for rule in rules}
        assert {"SEC-001", "SEC-002", "SEC-010"} <= rule_ids

    def test_list_rules_empty_without_seed(self, router_client_factory, db_manager, monkeypatch):
        from app.features.compliance import router as compliance_router
        from app.shared import database

        monkeypatch.setattr(database, "_db_manager", db_manager)

        client = router_client_factory(compliance_router.router)
        r = client.get("/api/compliance/rules")
        assert r.status_code == 200
        assert r.json()["rules"] == []


class TestComplianceCheck:
    def _patch_service(self, db_manager, monkeypatch):
        from app.features.compliance import router as compliance_router
        from app.shared import database

        monkeypatch.setattr(database, "_db_manager", db_manager)
        # 强制重建单例，使 ComplianceService.__init__ 在本测试库播种内置规则
        monkeypatch.setattr(compliance_router, "_compliance_service", None)
        return compliance_router

    def test_check_without_ai_returns_report(self, router_client_factory, db_manager, monkeypatch):
        compliance_router = self._patch_service(db_manager, monkeypatch)
        client = router_client_factory(compliance_router.router)

        r = client.post("/api/compliance/check", json={
            "config_text": "enable secret 5 $1$abc\ndefault gateway 10.0.0.1\n",
            "device_name": "SW-01",
            "device_ip": "10.0.0.1",
            "use_ai": False,
        })
        assert r.status_code == 200
        body = r.json()
        assert body["device_name"] == "SW-01"
        assert body["total_checks"] >= 10
        assert len(body["results"]) == body["total_checks"]
        assert 0 <= body["compliance_score"] <= 100
        assert body["results"][0]["check_id"]  # CheckResultResponse 形状
        assert "config_analysis" in body

    def test_check_failing_config_scores_lower(self, router_client_factory, db_manager, monkeypatch):
        compliance_router = self._patch_service(db_manager, monkeypatch)
        client = router_client_factory(compliance_router.router)

        r = client.post("/api/compliance/check", json={
            "config_text": "hostname BAD-SW\n",  # 无任何安全配置
            "use_ai": False,
        })
        assert r.status_code == 200
        body = r.json()
        assert body["failed"] > 0
        assert body["compliance_score"] < 100

    def test_check_empty_config_400(self, router_client_factory, db_manager, monkeypatch):
        compliance_router = self._patch_service(db_manager, monkeypatch)
        client = router_client_factory(compliance_router.router)

        r = client.post("/api/compliance/check", json={"config_text": "   \n", "use_ai": False})
        assert r.status_code == 400
        assert "不能为空" in r.json()["detail"]
