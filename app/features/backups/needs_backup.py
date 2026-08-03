"""需备份设备列表服务（批次二·步骤5）。

备份不再自动，改为提醒：
- 原因 config_changed：设备配置已变更（部署成功 / 手动标记，见 config_changed_at）
  且最近一次备份早于变更（或从未备份）。
- 原因 backup_overdue：超过 backup_reminder_days 天未备份（或从未备份）。

仅统计 deployment_status == 'in-use' 的设备，避免规划/退役设备进入提醒列表。
reason 返回语义码，展示文案由前端 i18n 映射（禁止后端硬编码界面文本）。
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List

from loguru import logger
from sqlalchemy.orm import Session

from app.shared.config import get_config
from app.shared.models import Device


def list_needs_backup(db: Session) -> List[Dict[str, Any]]:
    """返回需备份设备列表，每项含 reason（config_changed | backup_overdue）。"""
    now = datetime.utcnow()
    reminder_days = get_config().security.backup_reminder_days
    overdue_before = now - timedelta(days=reminder_days)

    devices = db.query(Device).filter(Device.deployment_status == "in-use").all()
    items: List[Dict[str, Any]] = []
    for d in devices:
        config_changed = (
            d.config_changed_at is not None
            and (d.last_backup_time is None or d.last_backup_time < d.config_changed_at)
        )
        overdue = d.last_backup_time is None or d.last_backup_time < overdue_before
        if not (config_changed or overdue):
            continue
        items.append({
            "device_id": d.id,
            "device_name": d.name,
            "ip": d.ip,
            "vendor": d.vendor,
            "credential_group": d.credential_group or "default",
            "last_backup_time": d.last_backup_time,
            "config_changed_at": d.config_changed_at,
            # 配置变更原因优先展示（未备份又超期的设备归因于配置变更）
            "reason": "config_changed" if config_changed else "backup_overdue",
        })
    return items


def mark_devices_config_changed(db: Session, device_ids: List[int], source: str = "manual") -> int:
    """将指定设备标记为配置已变更（置 config_changed_at = now），返回更新台数。"""
    now = datetime.utcnow()
    count = 0
    for device_id in device_ids:
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            continue
        device.config_changed_at = now
        count += 1
    db.commit()
    logger.info(f"标记设备配置已变更 source={source} device_ids={device_ids} count={count}")
    return count
