"""批次一（必然故障）回归测试

对应 docs/CODE_REVIEW_ISSUES.md 批次一。这些用例锁住的都是曾经"每次调用都失败"
的路径，其中最关键的一条是：Netmiko 部署必须真的执行命令安全守卫。
"""

import asyncio

import pytest

# 必须在 db_manager fixture 调用 init_db() 之前导入，否则 jobs 表不在
# Base.metadata 里（models_jobs 只在 app/shared/models_jobs.py 中定义，
# 见 docs/CODE_REVIEW_ISSUES.md 批次三「migrations/env.py 未注册 models_jobs」）
import app.shared.models_jobs  # noqa: F401


# ---------------------------------------------------------------------------
# P0-1 / P0-2：deploy_config 未定义 device → 命令守卫从未执行
# ---------------------------------------------------------------------------

class _FakeConnection:
    """最小可用的 Netmiko 连接替身"""

    device_type = "cisco_ios"

    def __init__(self, current_config="hostname OLD\n"):
        self._current = current_config
        self.sent_commands = None
        self.saved = False

    def send_command(self, command, *args, **kwargs):
        if "running-config" in command:
            return self._current
        return ""

    def send_config_set(self, commands):
        self.sent_commands = list(commands)
        return "config term\n" + "\n".join(self.sent_commands) + "\nend\n"

    def save_config(self):
        self.saved = True
        return "[OK]"


@pytest.fixture
def deploy_svc():
    from app.features.deploy.deploy_service import get_deploy_service
    return get_deploy_service()


def test_deploy_config_safe_commands_are_deployed(deploy_svc):
    """安全命令应能部署成功，说明守卫段落被执行且未误杀"""
    conn = _FakeConnection()
    device = {"id": 1, "name": "SW-01", "ip": "10.0.0.1", "vendor": "cisco"}

    result = deploy_svc.deploy_config(
        conn,
        "hostname NEW\ninterface Gi0/1\n description uplink\n",
        dry_run=False,
        device=device,
    )

    assert result["success"] is True, result
    assert conn.sent_commands, "配置命令未下发"
    assert conn.saved is True


def test_deploy_config_blocks_dangerous_command(deploy_svc):
    """核心回归：含 reload 的配置必须被命令守卫拦住，且不下发任何命令

    修复前 deploy_config 引用未定义的 device，NameError 被上层宽泛 except 吞掉，
    守卫实际从未生效。
    """
    conn = _FakeConnection()
    device = {"id": 1, "name": "SW-01", "ip": "10.0.0.1", "vendor": "cisco"}

    result = deploy_svc.deploy_config(
        conn, "hostname NEW\nreload\n", dry_run=False, device=device
    )

    assert result["success"] is False
    assert result.get("blocked_command") is not None
    assert conn.sent_commands is None, "被拦截的配置不应下发任何命令"


def test_deploy_config_without_device_still_runs_guard(deploy_svc):
    """device 缺省时不应崩溃，守卫仍要生效（vendor 从 connection 推断）"""
    conn = _FakeConnection()

    result = deploy_svc.deploy_config(conn, "hostname NEW\nwrite erase\n", dry_run=False)

    assert result["success"] is False
    assert result.get("blocked_command") is not None
    assert conn.sent_commands is None


def test_deploy_to_device_passes_device_down(deploy_svc, monkeypatch):
    """deploy_to_device 必须把 device 透传给 deploy_config"""
    captured = {}

    def fake_deploy_config(connection, config, dry_run=False, device=None):
        captured["device"] = device
        return {"success": True, "message": "ok"}

    monkeypatch.setattr(deploy_svc, "connect_device", lambda d, c: _FakeConnection())
    monkeypatch.setattr(deploy_svc, "deploy_config", fake_deploy_config)

    device = {"id": 7, "name": "SW-07", "ip": "10.0.0.7", "credential_group": "default"}
    deploy_svc.deploy_to_device(
        device,
        "hostname X\n",
        [{"name": "default", "username": "admin", "password": "pw"}],
    )

    assert captured.get("device") is device


# ---------------------------------------------------------------------------
# P0-4 / P0-5：缺失导入（tool_executor / asyncio）
# ---------------------------------------------------------------------------

def test_websocket_router_has_tool_executor():
    """/ws/logs 用到的 tool_executor 必须在模块作用域内可解析"""
    from app.features.websocket import router as ws_router

    assert hasattr(ws_router, "tool_executor")
    assert callable(ws_router.tool_executor.register_callback)


def test_napalm_service_module_has_asyncio():
    """NapalmStreamService 全程依赖 asyncio，模块必须导入它"""
    from app.features.deploy import napalm_service

    assert getattr(napalm_service, "asyncio", None) is not None


# ---------------------------------------------------------------------------
# P0-6：ai/router.py 读 FaultRecord.title（该字段不存在）
# ---------------------------------------------------------------------------

def test_fault_record_has_no_title_field():
    """契约说明：FaultRecord 只有 fault_no / description，没有 title"""
    from app.shared.models import FaultRecord

    assert not hasattr(FaultRecord, "title")
    assert hasattr(FaultRecord, "fault_no")
    assert hasattr(FaultRecord, "description")


def test_get_fault_analysis_builds_title_from_description(db_session):
    from app.features.ai.router import get_fault_analysis
    from app.shared.models import FaultRecord

    fault = FaultRecord(
        fault_no="F-20260728-001",
        description="核心交换机 Gi1/0/24 端口反复 up/down，疑似光模块劣化",
        severity="major",
        status="open",
    )
    db_session.add(fault)
    db_session.commit()

    resp = asyncio.run(get_fault_analysis(fault.id, db_session))

    assert resp["fault_id"] == fault.id
    assert resp["has_analysis"] is False
    assert resp["fault_title"] == fault.description[:50]


def test_get_fault_analysis_falls_back_to_fault_no(db_session):
    """description 为空时回退到 fault_no，不能是 None"""
    from app.features.ai.router import get_fault_analysis
    from app.shared.models import FaultRecord

    fault = FaultRecord(fault_no="F-20260728-002", severity="minor", status="open")
    db_session.add(fault)
    db_session.commit()

    resp = asyncio.run(get_fault_analysis(fault.id, db_session))

    assert resp["fault_title"] == "F-20260728-002"


# ---------------------------------------------------------------------------
# P0-7：Celery 备份任务 —— 凭证解析与备份调用
# ---------------------------------------------------------------------------

def test_netmiko_service_has_no_backup_device_method():
    """契约说明：备份是模块级函数 backup_device_config，不是 NetmikoService 的方法"""
    from app.features.backups import netmiko_service

    assert not hasattr(netmiko_service.NetmikoService, "backup_device")
    assert callable(netmiko_service.backup_device_config)


def _make_credential_group(db_session, name="default", username="admin", password="pw"):
    from app.features.credentials.credential_service import encrypt_password
    from app.shared.models import CredentialGroup

    group = CredentialGroup(
        name=name,
        username=username,
        password_encrypted=encrypt_password(password),
    )
    db_session.add(group)
    db_session.commit()
    return group


def test_resolve_device_credentials_returns_netmiko_fields(db_session, sample_device_data):
    from app.features.credentials.credential_service import resolve_device_credentials
    from app.shared.models import Device

    _make_credential_group(db_session, name="default", username="netadmin", password="s3cret")
    device = Device(**sample_device_data)
    db_session.add(device)
    db_session.commit()

    creds = resolve_device_credentials(db_session, device)

    assert creds["username"] == "netadmin"
    assert creds["password"] == "s3cret"
    assert "secret" in creds


def test_resolve_device_credentials_falls_back_to_default(db_session, sample_device_data):
    """设备指定的凭证组不存在时回退到 default"""
    from app.features.credentials.credential_service import resolve_device_credentials
    from app.shared.models import Device

    _make_credential_group(db_session, name="default", username="fallback", password="pw")
    data = dict(sample_device_data)
    data["credential_group"] = "not-exist"
    device = Device(**data)
    db_session.add(device)
    db_session.commit()

    assert resolve_device_credentials(db_session, device)["username"] == "fallback"


def test_resolve_device_credentials_raises_when_missing(db_session, sample_device_data):
    from app.features.credentials.credential_service import resolve_device_credentials
    from app.shared.models import Device

    device = Device(**sample_device_data)
    db_session.add(device)
    db_session.commit()

    with pytest.raises(ValueError):
        resolve_device_credentials(db_session, device)


def test_backup_task_persists_backup_record(db_manager, db_session, monkeypatch, sample_device_data):
    """备份任务成功后必须落 BackupRecord 并更新设备备份时间

    修复前该任务在获取凭证与调用备份两处都会抛异常，从不产生任何记录。
    """
    from app.shared import database as database_module
    from app.shared.models import BackupRecord, Device
    from app.shared.models_jobs import Job, JobStatus, create_job, JobType

    # 让任务内部的 get_db_manager() 指向测试库
    monkeypatch.setattr(database_module, "_db_manager", db_manager)

    _make_credential_group(db_session)
    device = Device(**sample_device_data)
    db_session.add(device)
    db_session.commit()
    job = create_job(db_session, JobType.BACKUP, device_id=device.id, operator="tester")
    job_id, device_id = job.id, device.id

    # 不真的连设备
    monkeypatch.setattr(
        "app.features.backups.netmiko_service.backup_device_config",
        lambda dev, creds, backup_dir: {
            "success": True,
            "file_path": "",          # 留空以跳过 RAG 读文件分支
            "file_size": 1234,
            "md5_hash": "abc123",
            "has_change": True,
            "message": "备份成功",
        },
    )

    from app.tasks.backup_tasks import backup_device

    result = backup_device.apply(args=[job_id, device_id, "tester"]).get()
    assert result["success"] is True

    verify = db_manager.get_session()
    try:
        record = verify.query(BackupRecord).filter(BackupRecord.device_id == device_id).first()
        assert record is not None, "备份成功却没有落 BackupRecord"
        assert record.file_size == 1234
        assert record.md5_hash == "abc123"
        assert verify.query(Job).filter(Job.id == job_id).first().status == JobStatus.SUCCESS
        assert verify.query(Device).filter(Device.id == device_id).first().last_backup_time is not None
    finally:
        verify.close()


# ---------------------------------------------------------------------------
# 门禁：静态检查必须零告警（覆盖整类 undefined-name 回归）
# ---------------------------------------------------------------------------

def test_ruff_static_analysis_is_clean():
    """ruff 规则见 ruff.toml；批次一的 4 处未定义变量都属于该门禁范围"""
    import subprocess
    import sys
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent
    proc = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "app", "scripts", "migrations", "tests",
         "--output-format", "concise"],
        cwd=repo_root, capture_output=True, text=True,
    )
    if proc.returncode == 2 and "No module named" in (proc.stderr or ""):
        pytest.skip("ruff 未安装（pip install -r requirements.txt）")

    assert proc.returncode == 0, f"ruff 检查未通过：\n{proc.stdout}\n{proc.stderr}"
