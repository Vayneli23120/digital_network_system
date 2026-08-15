"""告警治理服务（三期）：静默窗口 + 根因抑制 + 频控

- 静默：设备处于计划维护窗口（MaintenanceTask：scheduled_date ~ scheduled_end/estimated_hours）
  时，告警只落库不通知；窗口过后自动解除（下一次事件重算）。
- 抑制：拓扑根因——上联对端/本设备存在未关闭 critical/major 根因故障时，
  衍生告警标记 suppressed_by，不重复轰炸。
- 频控：同一 source_key 在窗口内最多 N 条外部通知（Redis 启用时走 Redis，
  否则进程内内存，通过 app.shared.cache 统一抽象）。
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from app.shared.models import Device, DeviceInterface, FaultRecord, MaintenanceTask

logger = logging.getLogger(__name__)

OPEN_STATUSES = ["open", "assigned", "accepted", "diagnosing", "resolving", "transferred"]

# 频控默认：窗口 300s；critical 10 条 / major 3 条 / 其余 1 条
FREQ_WINDOW_SECONDS = 300
FREQ_MAX_BY_SEVERITY = {"critical": 10, "major": 3, "minor": 1, "warning": 1}


def _task_window_end(task: MaintenanceTask) -> datetime:
    if task.scheduled_end:
        return task.scheduled_end
    hours = float(task.estimated_hours or 4)
    return task.scheduled_date + timedelta(hours=hours)


def check_silence(db: Session, device_id: int, at: Optional[datetime] = None) -> Optional[MaintenanceTask]:
    """设备是否处于计划维护窗口；返回命中的维护任务（静默凭据）。"""
    at = at or datetime.utcnow()
    tasks = (db.query(MaintenanceTask)
             .filter(MaintenanceTask.device_id == device_id,
                     MaintenanceTask.scheduled_date.isnot(None))
             .all())
    for task in tasks:
        window_end = _task_window_end(task)
        if task.scheduled_date <= at < window_end:
            return task
    return None


def find_suppressor(db: Session, device: Device, event_type: str,
                    if_index: Optional[int] = None) -> Optional[FaultRecord]:
    """查找抑制当前事件的根因故障单（拓扑/同设备根因）。"""
    # 1) 上联对端根因：对端有未关闭 critical/major 故障 → 抑制本设备衍生告警
    peer_ids: List[int] = []
    if if_index is not None:
        iface = db.query(DeviceInterface).filter(
            DeviceInterface.device_id == device.id,
            DeviceInterface.if_index == if_index,
        ).first()
        if iface and iface.is_uplink and iface.peer_device_id:
            peer_ids.append(iface.peer_device_id)
    if not peer_ids:
        uplinks = (db.query(DeviceInterface)
                   .filter(DeviceInterface.device_id == device.id,
                           DeviceInterface.is_uplink == True,  # noqa: E712
                           DeviceInterface.peer_device_id.isnot(None))
                   .all())
        peer_ids = [u.peer_device_id for u in uplinks if u.peer_device_id]

    for peer_id in dict.fromkeys(peer_ids):
        root = (db.query(FaultRecord)
                .filter(FaultRecord.device_id == peer_id,
                        FaultRecord.status.in_(OPEN_STATUSES),
                        FaultRecord.severity.in_(["critical", "major"]),
                        FaultRecord.suppressed_by.is_(None))
                .order_by(FaultRecord.created_at.desc())
                .first())
        if root:
            return root

    # 2) 本设备根因：本设备已 open 的 device_down 故障 → 抑制其 link_down/衍生告警
    if event_type in ("link_down", "prometheus_alert", "zabbix_alert", "generic_alert"):
        root = (db.query(FaultRecord)
                .filter(FaultRecord.device_id == device.id,
                        FaultRecord.status.in_(OPEN_STATUSES),
                        FaultRecord.severity.in_(["critical", "major"]),
                        FaultRecord.source_event == "device_unreachable",
                        FaultRecord.suppressed_by.is_(None))
                .order_by(FaultRecord.created_at.desc())
                .first())
        if root:
            return root
    return None


def freq_limited(source_key: str, severity: str, window_s: int = FREQ_WINDOW_SECONDS) -> bool:
    """频控：窗口内超过该级别上限返回 True（外部通知应被抑制）。"""
    max_count = FREQ_MAX_BY_SEVERITY.get(severity or "warning", 1)
    if max_count <= 0:
        return False
    from app.shared.cache import cache
    key = f"alert_freq:{source_key}"
    try:
        current = cache.get(key)
        count = int(current or 0)
    except Exception:
        count = 0
    if count >= max_count:
        return True
    try:
        cache.set(key, count + 1, ttl=window_s)
    except Exception:
        logger.exception("频控计数写入失败 key=%s", key)
    return False
