"""
Streaming 层测试（批次八切片 B）：DeployStreamService.stream_batch_deploy。

直测 `asyncio.run(service.stream_batch_deploy(...))`：fake websocket 收集
send_json 消息，实例属性覆盖 `_deploy_single_device_netmiko` 作 seam
（:497 经 loop.run_in_executor 调用），_db_manager monkeypatch 让 stream
内部 next(get_db()) 写 DeployHistory/DeployDeviceResult/LogEntry/Device 命中测试库。
"""

import asyncio


class FakeWebSocket:
    """最小 websocket 替身：只收集 send_json 消息"""

    def __init__(self):
        self.messages = []

    async def send_json(self, message):
        self.messages.append(message)


def _ok_payload(device, config, credentials, dry_run):
    return {
        "device_id": device.get("id"),
        "device_name": device.get("name"),
        "device_ip": device.get("ip"),
        "success": True,
        "message": "预览模式，配置未实际部署" if dry_run else "配置部署成功",
        "cli_output": "configure terminal\nend\n",
        "log_content": "[INFO] fake deploy",
        "errors": [],
        "duration_ms": 12,
        "diff": "",
        "rollback_available": False,
    }


def _run_stream(service, ws, **kwargs):
    asyncio.run(service.stream_batch_deploy(websocket=ws, **kwargs))


def _stream_kwargs(device, session_id="sess-1", **overrides):
    kwargs = {
        "devices": [device],
        "config": "hostname SW-01\n",
        "credential_groups": [{"name": "default", "username": "admin", "password": "p", "enable_password": ""}],
        "engine": "netmiko",
        "dry_run": False,
        "session_id": session_id,
        "username": "tester",
        "user_id": 1,
    }
    kwargs.update(overrides)
    return kwargs


class TestStreamBatchDeploy:
    def test_success_message_sequence_and_history(self, db_manager, db_session, monkeypatch):
        from app.features.deploy.deploy_stream_service import DeployStreamService
        from app.shared import database
        from app.shared.models import Device, DeployDeviceResult, DeployHistory, User

        user = User(id=1, username="tester", password_hash="x", is_active=True, is_superuser=True)
        dev = Device(name="SW-01", ip="10.0.0.1", deployment_status="in-use")
        db_session.add_all([user, dev])
        db_session.commit()
        db_session.refresh(dev)

        monkeypatch.setattr(database, "_db_manager", db_manager)

        service = DeployStreamService()
        service._deploy_single_device_netmiko = _ok_payload  # 实例属性覆盖 seam

        ws = FakeWebSocket()
        _run_stream(service, ws, **_stream_kwargs({"id": dev.id, "name": "SW-01", "ip": "10.0.0.1"}, user_id=1))

        # 消息序列：deploy_started → device_started → device_progress → deploy_complete
        assert [m["type"] for m in ws.messages] == [
            "deploy_started", "device_started", "device_progress", "deploy_complete",
        ]
        assert ws.messages[0]["session_id"] == "sess-1"
        assert ws.messages[0]["dry_run"] is False

        complete = ws.messages[-1]
        assert complete["success_count"] == 1
        assert complete["failed_count"] == 0
        assert complete["history_id"] is not None

        # DeployHistory / DeployDeviceResult / Device.config_changed_at 已落库
        history = db_session.query(DeployHistory).filter_by(id=complete["history_id"]).first()
        assert history is not None
        assert history.total_devices == 1
        assert history.success is True
        assert history.username == "tester"
        result_row = db_session.query(DeployDeviceResult).filter_by(deploy_id=history.id).first()
        assert result_row is not None
        assert result_row.device_name == "SW-01"

        db_session.expire_all()
        updated = db_session.query(Device).filter_by(id=dev.id).first()
        assert updated.config_changed_at is not None  # 成功后标记「需备份」

    def test_dry_run_passthrough(self, db_manager, monkeypatch):
        from app.features.deploy.deploy_stream_service import DeployStreamService
        from app.shared import database

        monkeypatch.setattr(database, "_db_manager", db_manager)

        captured = {}

        def fake_deploy(device, config, credentials, dry_run):
            captured["dry_run"] = dry_run
            return _ok_payload(device, config, credentials, dry_run)

        service = DeployStreamService()
        service._deploy_single_device_netmiko = fake_deploy

        ws = FakeWebSocket()
        _run_stream(
            service, ws,
            **_stream_kwargs({"id": 1, "name": "SW-01", "ip": "10.0.0.1"}, dry_run=True),
        )

        assert captured["dry_run"] is True
        assert ws.messages[0]["dry_run"] is True
        progress = ws.messages[-2]
        assert progress["message"] == "预览模式，配置未实际部署"
        assert ws.messages[-1]["success_count"] == 1

    def test_device_exception_reported_failed(self, db_manager, monkeypatch):
        from app.features.deploy.deploy_stream_service import DeployStreamService
        from app.shared import database

        monkeypatch.setattr(database, "_db_manager", db_manager)

        def exploding_deploy(device, config, credentials, dry_run):
            raise RuntimeError("ssh boom")

        service = DeployStreamService()
        service._deploy_single_device_netmiko = exploding_deploy

        ws = FakeWebSocket()
        _run_stream(service, ws, **_stream_kwargs({"id": 1, "name": "SW-01", "ip": "10.0.0.1"}))

        progress = [m for m in ws.messages if m["type"] == "device_progress"][0]
        assert progress["success"] is False
        assert "执行异常" in progress["message"]
        assert "ssh boom" in progress["message"]

        complete = ws.messages[-1]
        assert complete["success_count"] == 0
        assert complete["failed_count"] == 1
