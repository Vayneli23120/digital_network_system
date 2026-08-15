"""升级扫描服务 —— 通知模块一期（v1.1）

后端进程内 APScheduler 定时扫描（物理机/容器部署都可用，无需依赖 Celery beat）：
- 未关闭 critical/major 故障：L2 15min 未认领 → 运维组全员 + admin；L3 30min 未处理 → 部门经理 + 复盘任务
- 未完成维修单：sla_deadline 超时 → 部门经理
每次升级经 dispatch() 落 notification_log（可追溯"谁在几点被升级通知"）。
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from app.features.groups.service import (
    group_leader_usernames,
    group_members,
    match_dispatch_rule,
    resolve_oncall,
)
from app.shared.database import get_db_manager
from app.shared.models import EscalationPolicy, FaultRecord, MaintenanceRecord

logger = logging.getLogger(__name__)

OPEN_STATUSES = ["open", "assigned", "accepted", "diagnosing", "resolving", "transferred"]

SCAN_INTERVAL_SECONDS = 60


def _load_levels(policy: EscalationPolicy) -> List[dict]:
    try:
        levels = json.loads(policy.levels_json) if policy.levels_json else []
        return sorted(levels, key=lambda x: int(x.get("level", 9)))
    except Exception:
        return []


def _default_policy(db: Session) -> Optional[EscalationPolicy]:
    return (db.query(EscalationPolicy)
            .filter(EscalationPolicy.name == "默认升级策略",
                    EscalationPolicy.enabled == True)  # noqa: E712
            .first())


def _targets_to_recipients(db: Session, targets: List[str], group_id: Optional[int]) -> List[str]:
    recipients: List[str] = []
    for target in targets:
        if target == "admin":
            recipients.append("admin")
        elif target == "group" and group_id:
            recipients += [m.username for m in group_members(db, group_id)]
        elif target == "leader" and group_id:
            recipients += group_leader_usernames(db, group_id)
        elif target == "oncall" and group_id:
            oncall = resolve_oncall(db, group_id)
            recipients.append(oncall if oncall else "")
            if not oncall:
                recipients += [m.username for m in group_members(db, group_id)]
    return [r for r in dict.fromkeys(recipients) if r]


def _escalate_fault(db: Session, fault: FaultRecord, level: dict) -> None:
    """按升级层级发送通知并推进 escalation_level。"""
    from app.services.notification_service import get_notification_service

    level_no = int(level.get("level", 2))
    recipients = _targets_to_recipients(db, level.get("targets", ["group"]), fault.group_id)
    fault.escalation_level = level_no
    fault.escalated_at = datetime.utcnow()

    timeout_minutes = level.get("timeout_minutes", 0)
    state_text = "未认领" if not fault.accepted_at else "未处理"
    get_notification_service().dispatch(
        db,
        event_type="escalation",
        title=f"[升级 L{level_no}] {fault.device_name or ''} - {fault.fault_no}",
        content=(
            f"故障 {fault.fault_no}（{fault.severity}）已超过 {timeout_minutes} 分钟{state_text}，请立即响应。\n"
            f"设备：{fault.device_name or '-'}\n负责人：{fault.assigned_to or '未指派（组内认领）'}"
        ),
        recipients=recipients,
        reference_type="fault",
        reference_id=fault.id,
        fault_id=fault.id,
    )
    if level.get("create_review"):
        # 复盘任务（一期为站内复盘通知，落 notification_log 可追溯）
        review_recipients = ["admin"]
        if fault.group_id:
            review_recipients += group_leader_usernames(db, fault.group_id)
        review_recipients = list(dict.fromkeys(review_recipients))
        get_notification_service().dispatch(
            db,
            event_type="escalation_review",
            title=f"复盘任务: {fault.fault_no}",
            content=f"故障 {fault.fault_no} 已升级到部门经理，请安排复盘并记录改进项。",
            recipients=review_recipients,
            reference_type="fault",
            reference_id=fault.id,
            fault_id=fault.id,
            use_email=False,
            use_im=False,
        )
    db.commit()


def scan_fault_escalations(db: Session, now: datetime) -> int:
    """扫描未关闭 critical/major 故障，按升级策略推进。返回本次升级数量。"""
    policy = _default_policy(db)
    if not policy:
        return 0
    levels = _load_levels(policy)
    if not levels:
        return 0

    # 静默（维护窗口）与被抑制（根因单未关闭）的故障不参与升级
    faults = (db.query(FaultRecord)
              .filter(FaultRecord.severity.in_(["critical", "major"]),
                      FaultRecord.status.in_(OPEN_STATUSES),
                      FaultRecord.silenced == False,  # noqa: E712
                      FaultRecord.suppressed_by.is_(None))
              .all())
    count = 0
    for fault in faults:
        start = fault.fault_time or fault.created_at
        if not start:
            continue
        elapsed_minutes = (now - start).total_seconds() / 60

        applicable = []
        for level in levels:
            if elapsed_minutes < float(level.get("timeout_minutes", 0)):
                continue
            level_no = int(level.get("level", 0))
            # L2 语义是"未认领"，已认领则不触发该级
            if level_no <= 2 and fault.accepted_at:
                continue
            applicable.append(level)
        if not applicable:
            continue

        target = max(applicable, key=lambda x: int(x.get("level", 0)))
        if (fault.escalation_level or 0) >= int(target.get("level", 0)):
            continue
        try:
            _escalate_fault(db, fault, target)
            count += 1
            logger.info("故障升级 fault=%s → L%s", fault.fault_no, target.get("level"))
        except Exception:
            db.rollback()
            logger.exception("故障升级失败 fault=%s", fault.fault_no)
    return count


def scan_maintenance_sla(db: Session, now: datetime) -> int:
    """扫描 SLA 超时的未完成维修单，升级通知部门经理。返回本次升级数量。"""
    rows = (db.query(MaintenanceRecord)
            .filter(MaintenanceRecord.sla_deadline.isnot(None),
                    MaintenanceRecord.sla_deadline < now,
                    MaintenanceRecord.status.notin_(["completed", "cancelled"]))
            .all())
    count = 0
    for maint in rows:
        if (maint.escalation_level or 0) >= 3:
            continue
        group_id = maint.group_id
        if not group_id:
            group = match_dispatch_rule(db)
            group_id = group.id if group else None
        recipients = list(dict.fromkeys(
            ["admin"] + (group_leader_usernames(db, group_id) if group_id else [])
        ))
        from app.services.notification_service import get_notification_service
        get_notification_service().dispatch(
            db,
            event_type="maintenance_sla_escalated",
            title=f"[SLA 超时] {maint.device_name or ''} - {maint.maint_no}",
            content=f"维修单 {maint.maint_no} 已超过 SLA 截止时间，请部门经理介入处理。",
            recipients=recipients,
            reference_type="maintenance",
            reference_id=maint.id,
            maintenance_id=maint.id,
        )
        maint.escalation_level = 3
        maint.escalated_at = now
        db.commit()
        count += 1
        logger.info("维修单 SLA 升级 maint=%s", maint.maint_no)
    return count


def run_escalation_scan() -> Dict[str, int]:
    """一次升级扫描（幂等：escalation_level 防重复）。"""
    now = datetime.utcnow()
    db_manager = get_db_manager()
    try:
        with db_manager.session_scope() as db:
            faults = scan_fault_escalations(db, now)
        with db_manager.session_scope() as db:
            maints = scan_maintenance_sla(db, now)
        return {"fault_escalated": faults, "maintenance_escalated": maints}
    except Exception:
        logger.exception("升级扫描失败")
        return {"fault_escalated": 0, "maintenance_escalated": 0}


_scheduler: Optional[BackgroundScheduler] = None


def start_escalation_scanner() -> BackgroundScheduler:
    """启动升级扫描调度器（幂等；进程内运行，物理机/Docker 均可用）。"""
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        run_escalation_scan,
        trigger=IntervalTrigger(seconds=SCAN_INTERVAL_SECONDS),
        max_instances=1,
        coalesce=True,
        misfire_grace_time=30,
        id="escalation_scan",
    )
    _scheduler.start()
    logger.info("升级扫描调度器已启动（每 %ss 一次）", SCAN_INTERVAL_SECONDS)
    return _scheduler
