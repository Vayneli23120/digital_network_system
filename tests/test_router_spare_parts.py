"""
Router 层测试（批次八切片 A）：spare_parts 端点。

通过 conftest 的 router_client_factory 构建 mini FastAPI + TestClient，
覆盖备件 CRUD、统计、手动出入库。备件服务层零外部依赖，是最容易证明
「mini-app + dependency_overrides」模式的入口。
"""

import pytest


def _create_part(client, **overrides):
    payload = {
        "name": "核心交换机模块",
        "part_number": "WS-C9300-MOD",
        "category": "module",  # service 会归一化为中文「模块」
        "manufacturer": "Cisco",
        "quantity_in_stock": 5,
        "min_quantity": 2,
        "unit_price": 1200.00,
        "location": "A-1",
    }
    payload.update(overrides)
    return client.post("/api/spare-parts/", json=payload)


class TestSparePartCrud:
    def test_create_and_get_part(self, router_client_factory):
        from app.features.spare_parts import router as spare_router

        client = router_client_factory(spare_router.router)
        r = _create_part(client)
        assert r.status_code == 200
        part_id = r.json()["id"]

        detail = client.get(f"/api/spare-parts/{part_id}").json()
        assert detail["name"] == "核心交换机模块"
        assert detail["part_number"] == "WS-C9300-MOD"
        # 分类经 normalize_category 归一化为中文
        assert detail["category"] == "模块"

    def test_create_part_extra_field_rejected(self, router_client_factory):
        from app.features.spare_parts import router as spare_router

        client = router_client_factory(spare_router.router)
        r = _create_part(client, evil_internal_field="x")
        assert r.status_code == 422

    def test_list_parts_and_filter(self, router_client_factory):
        from app.features.spare_parts import router as spare_router

        client = router_client_factory(spare_router.router)
        _create_part(client, name="模块A", category="module")
        _create_part(client, name="电源B", part_number="PWR-9300-PSU", category="power")

        all_parts = client.get("/api/spare-parts/").json()
        assert all_parts["total"] == 2
        assert {i["name"] for i in all_parts["items"]} == {"模块A", "电源B"}

        # 英文分类输入也命中中文存储
        filtered = client.get("/api/spare-parts/", params={"category": "module"}).json()
        assert filtered["total"] == 1
        assert filtered["items"][0]["category"] == "模块"

    def test_get_part_not_found(self, router_client_factory):
        from app.features.spare_parts import router as spare_router

        client = router_client_factory(spare_router.router)
        assert client.get("/api/spare-parts/999999").status_code == 404

    def test_update_part(self, router_client_factory):
        from app.features.spare_parts import router as spare_router

        client = router_client_factory(spare_router.router)
        part_id = _create_part(client).json()["id"]

        r = client.put(f"/api/spare-parts/{part_id}", json={"location": "B-2", "status": "active"})
        assert r.status_code == 200
        assert r.json()["message"] == "更新成功"

        detail = client.get(f"/api/spare-parts/{part_id}").json()
        assert detail["location"] == "B-2"

    def test_delete_part(self, router_client_factory):
        from app.features.spare_parts import router as spare_router

        client = router_client_factory(spare_router.router)
        part_id = _create_part(client).json()["id"]

        r = client.delete(f"/api/spare-parts/{part_id}")
        assert r.status_code == 200
        assert r.json()["success"] is True
        assert client.get(f"/api/spare-parts/{part_id}").status_code == 404


class TestSparePartStats:
    def test_stats_summary_shape(self, router_client_factory, db_session):
        from app.shared.models import SparePartInstance
        from app.features.spare_parts import router as spare_router

        client = router_client_factory(spare_router.router)
        part_id = _create_part(client).json()["id"]
        db_session.add_all([
            SparePartInstance(part_id=part_id, serial_number="SN-001", unit_price=100.0, status="in_stock"),
            SparePartInstance(part_id=part_id, serial_number="SN-002", unit_price=200.0, status="in_stock"),
        ])
        db_session.commit()

        stats = client.get("/api/spare-parts/stats/summary").json()
        assert stats["total_parts"] == 1
        assert stats["total_value"] == 300.0
        assert "by_category" in stats


class TestSparePartManualStock:
    def test_manual_in_then_out(self, router_client_factory):
        from app.features.spare_parts import router as spare_router

        client = router_client_factory(spare_router.router)
        part_id = _create_part(client).json()["id"]

        r_in = client.post(f"/api/spare-parts/{part_id}/manual-in", json={
            "serial_number": "SN-A100",
            "reason": "新购入库",
        })
        assert r_in.status_code == 200
        assert r_in.json()["new_stock"] == 1

        by_serial = client.get("/api/spare-parts/by-serial/SN-A100").json()
        assert by_serial["status"] == "in_stock"
        assert by_serial["history"][0]["movement_type"] == "in"

        r_out = client.post(f"/api/spare-parts/{part_id}/manual-out", json={
            "serial_number": "SN-A100",
            "reason": "更换故障设备",
        })
        assert r_out.status_code == 200
        assert r_out.json()["new_stock"] == 0

        by_serial = client.get("/api/spare-parts/by-serial/SN-A100").json()
        assert by_serial["status"] == "out"

    def test_manual_in_duplicate_in_stock_rejected(self, router_client_factory):
        from app.features.spare_parts import router as spare_router

        client = router_client_factory(spare_router.router)
        part_id = _create_part(client).json()["id"]

        payload = {"serial_number": "SN-DUP", "reason": "入库"}
        assert client.post(f"/api/spare-parts/{part_id}/manual-in", json=payload).status_code == 200
        assert client.post(f"/api/spare-parts/{part_id}/manual-in", json=payload).status_code == 400

    def test_manual_out_unknown_serial_404(self, router_client_factory):
        from app.features.spare_parts import router as spare_router

        client = router_client_factory(spare_router.router)
        part_id = _create_part(client).json()["id"]

        r = client.post(f"/api/spare-parts/{part_id}/manual-out", json={
            "serial_number": "SN-MISSING",
            "reason": "出库",
        })
        assert r.status_code == 404
