"""
Router 层测试（批次八切片 A）：devices 端点。

覆盖设备 CRUD、列表过滤，以及批次一 bug 现场
POST /api/devices/monitor/discover-neighbors-all（total_aps 曾未初始化）的回归。
"""


def _create_device(client, name="SW-Core-01", ip="192.168.1.1", **overrides):
    payload = {"name": name, "ip": ip, "role": "core", "vendor": "Cisco"}
    payload.update(overrides)
    return client.post("/api/devices", json=payload)


class TestDeviceCrud:
    def test_create_and_get_device(self, router_client_factory):
        from app.features.devices import router as devices_router

        client = router_client_factory(devices_router.router)
        r = _create_device(client)
        assert r.status_code == 200
        device_id = r.json()["id"]

        detail = client.get(f"/api/devices/{device_id}").json()
        assert detail["name"] == "SW-Core-01"
        assert detail["ip"] == "192.168.1.1"
        assert "recent_backups" in detail  # GET 详情聚合了最近备份/故障/维修

    def test_create_duplicate_name_conflict(self, router_client_factory):
        from app.features.devices import router as devices_router

        client = router_client_factory(devices_router.router)
        assert _create_device(client).status_code == 200
        assert _create_device(client).status_code == 409

    def test_create_device_missing_name_422(self, router_client_factory):
        from app.features.devices import router as devices_router

        client = router_client_factory(devices_router.router)
        assert client.post("/api/devices", json={"ip": "10.0.0.1"}).status_code == 422

    def test_list_devices(self, router_client_factory):
        from app.features.devices import router as devices_router

        client = router_client_factory(devices_router.router)
        _create_device(client, name="sw-01", ip="10.0.0.1")
        _create_device(client, name="sw-02", ip="10.0.0.2")

        result = client.get("/api/devices").json()
        assert result["total"] == 2
        assert {i["name"] for i in result["items"]} == {"sw-01", "sw-02"}

    def test_list_devices_filter_status(self, router_client_factory):
        from app.features.devices import router as devices_router

        client = router_client_factory(devices_router.router)
        _create_device(client, name="online-01", ip="10.0.0.1")
        _create_device(client, name="offline-01", ip="10.0.0.2", status="offline")

        result = client.get("/api/devices", params={"status": "online"}).json()
        assert result["total"] == 1
        assert result["items"][0]["name"] == "online-01"

    def test_get_device_not_found(self, router_client_factory):
        from app.features.devices import router as devices_router

        client = router_client_factory(devices_router.router)
        assert client.get("/api/devices/999999").status_code == 404

    def test_update_device(self, router_client_factory):
        from app.features.devices import router as devices_router

        client = router_client_factory(devices_router.router)
        device_id = _create_device(client).json()["id"]

        r = client.put(f"/api/devices/{device_id}", json={"location": "Building B", "role": "distribution"})
        assert r.status_code == 200
        assert r.json()["message"] == "更新成功"

        detail = client.get(f"/api/devices/{device_id}").json()
        assert detail["location"] == "Building B"
        assert detail["role"] == "distribution"

    def test_delete_device(self, router_client_factory):
        from app.features.devices import router as devices_router

        client = router_client_factory(devices_router.router)
        device_id = _create_device(client).json()["id"]

        r = client.delete(f"/api/devices/{device_id}")
        assert r.status_code == 200
        assert r.json()["success"] is True
        assert client.get(f"/api/devices/{device_id}").status_code == 404


class TestDiscoverNeighborsAll:
    """批次一回归：POST /monitor/discover-neighbors-all（total_aps 曾未初始化）"""

    def _seed_snmp_devices(self, db_session, count=2):
        from app.shared.models import Device

        for i in range(count):
            db_session.add(Device(
                name=f"sw-snmp-{i}",
                ip=f"10.0.0.{i + 10}",
                snmp_enabled=True,
                snmp_community="public",
                deployment_status="in-use",
            ))
        db_session.commit()

    def test_aggregates_totals(self, router_client_factory, db_session, monkeypatch):
        from app.features.devices import router as devices_router

        client = router_client_factory(devices_router.router)
        self._seed_snmp_devices(db_session, count=2)

        def fake_discover_neighbors(device_id):
            return {
                "ok": True,
                "found": 2,
                "matched": 1,
                "uplinks_marked": 1,
                "aps_synced": 3,
                "cleared": 0,
                "error": None,
            }

        monkeypatch.setattr("app.services.snmp_discovery.discover_neighbors", fake_discover_neighbors)

        r = client.post("/api/devices/monitor/discover-neighbors-all")
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True
        assert body["devices"] == 2
        assert len(body["results"]) == 2
        assert body["total_found"] == 4
        assert body["total_aps_synced"] == 6  # 曾因 total_aps 未初始化而 NameError

    def test_empty_when_no_snmp_devices(self, router_client_factory, db_session):
        from app.features.devices import router as devices_router

        client = router_client_factory(devices_router.router)
        r = client.post("/api/devices/monitor/discover-neighbors-all")
        assert r.status_code == 200
        assert r.json() == {"ok": True, "devices": 0, "results": []}

    def test_failed_device_reported_in_results(self, router_client_factory, db_session, monkeypatch):
        from app.features.devices import router as devices_router

        client = router_client_factory(devices_router.router)
        self._seed_snmp_devices(db_session, count=1)

        def failing_discover_neighbors(device_id):
            return {"ok": False, "found": 0, "matched": 0, "uplinks_marked": 0,
                    "aps_synced": 0, "cleared": 0, "error": "snmp timeout"}

        monkeypatch.setattr("app.services.snmp_discovery.discover_neighbors", failing_discover_neighbors)

        r = client.post("/api/devices/monitor/discover-neighbors-all")
        body = r.json()
        assert body["ok"] is True
        assert body["results"][0]["ok"] is False
        assert body["results"][0]["error"] == "snmp timeout"
        assert body["total_aps_synced"] == 0
