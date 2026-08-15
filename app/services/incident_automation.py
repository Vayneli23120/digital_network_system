"""
监控事件自动化：监控告警 -> FaultRecord 工单闭环（MVP）

第一版目标：
- Trap linkDown / 设备不可达 自动创建或更新 FaultRecord
- linkUp / 设备恢复 自动标记相关故障 resolved
- 按规则判断故障类型、严重级别、处理建议、负责人
- 发送系统通知和邮件（若告警通道已启用）
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger
from sqlalchemy.orm import Session

from app.shared.models import Device, DeviceInterface, FaultRecord, User


OPEN_STATUSES = ["open", "assigned", "diagnosing", "resolving", "transferred"]
SEVERITY_RANK = {"minor": 1, "warning": 2, "major": 3, "critical": 4}

# 抖动抑制：故障在该秒数内自动恢复，判定为瞬时抖动误报（如链路重收敛丢包），
# 标记 false_positive 且不发送告警通知。设为 0 可关闭抑制。
FLAP_SUPPRESS_SECONDS = int(os.getenv("INCIDENT_FLAP_SUPPRESS_SECONDS", "90"))


@dataclass
class MonitorEvent:
    """来自监控/Trap/SNMP 轮询的标准化事件"""

    source_type: str
    event_type: str
    device_id: int
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    device_name: Optional[str] = None
    ip: Optional[str] = None
    if_index: Optional[int] = None
    if_name: Optional[str] = None
    peer_device_id: Optional[int] = None
    peer_device_name: Optional[str] = None
    peer_if_name: Optional[str] = None
    severity_hint: Optional[str] = None
    is_recovery: bool = False  # 恢复类事件（与 event_type 配合，source_key 保持与触发时一致）
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IncidentDecision:
    """事件分类/派单决策"""

    fault_type: str
    incident_type: str
    severity: str
    source_key: str
    title: str
    description: str
    impact: Optional[str]
    recommendation: str
    owner: str
    owner_email: Optional[str]
    should_notify: bool = True


def _severity_max(a: str, b: str) -> str:
    return a if SEVERITY_RANK.get(a, 0) >= SEVERITY_RANK.get(b, 0) else b


def _device_tier(device: Device) -> str:
    return (getattr(device, "device_type", None) or "switch").lower()


def _format_device(device: Device) -> str:
    return f"{device.name} ({device.ip or 'N/A'})"


def _link_down_recommendation() -> str:
    return (
        "建议处理：\n"
        "1. 检查本端接口 admin/oper 状态。\n"
        "2. 检查对端接口状态与最近 Trap。\n"
        "3. 查看 CRC、input errors、output errors 是否增长。\n"
        "4. 检查光模块、跳线、ODF/配线架。\n"
        "5. 若持续 down 超过阈值，建议转维修单安排现场检查。"
    )


def _device_down_recommendation() -> str:
    return (
        "建议处理：\n"
        "1. 检查设备电源、管理地址、网关和上联链路。\n"
        "2. 查看其上游设备接口状态。\n"
        "3. 若同路径多设备同时离线，优先检查共同上游链路。\n"
        "4. 若设备为核心/防火墙，立即升级为 P1 并通知对应管理员。"
    )


def classify_event(db: Session, event: MonitorEvent) -> IncidentDecision:
    """规则优先的事件分类（AI 后续作为增强接入）。"""
    device = db.query(Device).filter(Device.id == event.device_id).first()
    if not device:
        raise ValueError(f"device {event.device_id} not found")

    device_name = event.device_name or device.name
    device_label = _format_device(device)
    device_type = _device_tier(device)

    iface = None
    if event.if_index is not None:
        iface = db.query(DeviceInterface).filter(
            DeviceInterface.device_id == device.id,
            DeviceInterface.if_index == event.if_index,
        ).first()

    if event.event_type in ("link_down", "link_up"):
        if_name = event.if_name or (iface.if_name if iface else f"if{event.if_index}")
        source_key = f"device:{device.id}:if:{event.if_index}:link_down"
        is_uplink = bool(iface.is_uplink) if iface else bool(event.raw.get("is_uplink"))
        peer_name = event.peer_device_name or (iface.peer_device_name if iface else None)
        peer_if_name = event.peer_if_name or (iface.peer_if_name if iface else None)

        severity = event.severity_hint or ("major" if is_uplink else "warning")
        if is_uplink and device_type in ("core_switch", "router", "firewall"):
            severity = "critical"

        title = f"{device_name} {if_name} 上行链路中断" if is_uplink else f"{device_name} {if_name} 接口中断"
        peer_text = f"\n对端：{peer_name or '-'} {peer_if_name or ''}" if (peer_name or peer_if_name) else ""
        description = (
            f"监控检测到接口 linkDown。\n设备：{device_label}\n接口：{if_name}{peer_text}\n"
            f"来源：{event.source_type}\n时间：{event.occurred_at.isoformat()}"
        )
        impact = "上行口中断，可能影响下游设备或业务链路。" if is_uplink else "接入口中断，影响范围可能局限于单端口。"
        owner, owner_email = None, None  # v1.1：派发目标由 dispatch_rule/运维组解析，不再用伪账号
        return IncidentDecision(
            fault_type="network",
            incident_type="uplink_down" if is_uplink else "access_port_down",
            severity=severity,
            source_key=source_key,
            title=title,
            description=description,
            impact=impact,
            recommendation=_link_down_recommendation(),
            owner=owner,
            owner_email=owner_email,
        )

    if event.event_type in ("device_unreachable", "device_recovered"):
        source_key = f"device:{device.id}:unreachable"
        if device_type in ("core_switch", "router", "firewall"):
            severity = "critical"
        elif device_type in ("office_switch", "server_switch", "wlc", "switch"):
            severity = "major"
        else:
            severity = "warning"
        severity = event.severity_hint or severity

        title = f"{device_name} 设备不可达"
        description = (
            f"监控检测到设备不可达。\n设备：{device_label}\n"
            f"来源：{event.source_type}\n时间：{event.occurred_at.isoformat()}"
        )
        impact = "设备不可达，可能影响其下联业务或管理能力。"
        owner, owner_email = None, None  # v1.1：派发目标由 dispatch_rule/运维组解析，不再用伪账号
        return IncidentDecision(
            fault_type="network",
            incident_type="device_down",
            severity=severity,
            source_key=source_key,
            title=title,
            description=description,
            impact=impact,
            recommendation=_device_down_recommendation(),
            owner=owner,
            owner_email=owner_email,
        )

    source_key = f"device:{device.id}:{event.event_type}"
    owner, owner_email = None, None  # v1.1：派发目标由 dispatch_rule/运维组解析，不再用伪账号
    return IncidentDecision(
        fault_type="other",
        incident_type=event.event_type,
        severity=event.severity_hint or "warning",
        source_key=source_key,
        title=f"{device_name} 监控事件：{event.event_type}",
        description=f"监控事件：{event.event_type}\n设备：{device_label}\n时间：{event.occurred_at.isoformat()}",
        impact=None,
        recommendation="建议处理：请查看设备状态、接口状态、最近告警和拓扑路径。",
        owner=owner,
        owner_email=owner_email,
    )


def _append_note(existing: Optional[str], note: str) -> str:
    if not existing:
        return note
    return f"{existing}\n\n--- {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} ---\n{note}"


def _is_flap_recovery(fault: FaultRecord, event: MonitorEvent) -> bool:
    """判断本次恢复是否属于瞬时抖动（故障存续时间短于抑制阈值）。"""
    if FLAP_SUPPRESS_SECONDS <= 0:
        return False
    start = fault.fault_time or fault.created_at
    if not start:
        return False
    duration = (event.occurred_at - start).total_seconds()
    return 0 <= duration < FLAP_SUPPRESS_SECONDS


def _mark_flap_suppressed(db: Session, fault: FaultRecord, event: MonitorEvent) -> None:
    """标记抖动误报：置 false_positive、取消复核、跳过恢复通知。"""
    start = fault.fault_time or fault.created_at
    duration = int((event.occurred_at - start).total_seconds()) if start else 0
    fault.false_positive = True
    fault.review_required = False
    fault.resolution = _append_note(
        fault.resolution,
        f"抖动抑制：故障在 {duration}s 内自动恢复（阈值 {FLAP_SUPPRESS_SECONDS}s），"
        "判定为瞬时抖动误报（如链路重收敛丢包），未发送告警通知。"
    )
    fault.updated_at = datetime.utcnow()
    db.commit()
    logger.info(f"抖动抑制 fault={fault.fault_no} 存续 {duration}s，标记 false_positive")


def _resolve_existing_fault(db: Session, decision: IncidentDecision, event: MonitorEvent) -> Optional[FaultRecord]:
    fault = db.query(FaultRecord).filter(
        FaultRecord.source_key == decision.source_key,
        FaultRecord.status.in_(OPEN_STATUSES),
    ).order_by(FaultRecord.created_at.desc()).first()
    if not fault:
        return None

    fault.status = "resolved"
    fault.resolved_at = datetime.utcnow()
    fault.resolution = _append_note(
        fault.resolution,
        f"监控检测到恢复事件：{event.event_type}，时间：{event.occurred_at.isoformat()}"
    )
    fault.last_event_at = event.occurred_at
    fault.event_count = (fault.event_count or 1) + 1
    fault.updated_at = datetime.utcnow()
    db.commit()
    return fault


def upsert_fault_from_monitor_event(db: Session, event: MonitorEvent) -> Optional[FaultRecord]:
    """监控事件创建/更新 FaultRecord。恢复事件会把对应未关闭故障标记 resolved。"""
    decision = classify_event(db, event)

    if event.event_type in ("link_up", "device_recovered") or event.is_recovery:
        fault = _resolve_existing_fault(db, decision, event)
        if fault:
            if _is_flap_recovery(fault, event):
                _mark_flap_suppressed(db, fault, event)
            else:
                notify_incident(db, fault, decision, recovered=True)
        return fault

    fault = db.query(FaultRecord).filter(
        FaultRecord.source_key == decision.source_key,
        FaultRecord.status.in_(OPEN_STATUSES),
    ).order_by(FaultRecord.created_at.desc()).first()

    if fault:
        fault.event_count = (fault.event_count or 1) + 1
        fault.last_event_at = event.occurred_at
        fault.severity = _severity_max(fault.severity or "minor", decision.severity)
        # 三期：窗口结束自动解除静默（重新检查，无窗口则释放）
        from app.services.alert_governance import check_silence
        fault.silenced = check_silence(db, fault.device_id, event.occurred_at) is not None
        fault.description = decision.description
        fault.impact = decision.impact
        fault.recommendation = decision.recommendation
        fault.diagnosis_text = _append_note(
            fault.diagnosis_text,
            f"监控事件重复触发（第 {fault.event_count} 次）：{event.event_type}"
        )
        fault.updated_at = datetime.utcnow()
        db.commit()
        return fault

    device = db.query(Device).filter(Device.id == event.device_id).first()
    if not device:
        return None

    # v1.1：派发目标解析（dispatch_rule → 运维组 → 值班人/组名），通知 admin + 运维组
    from app.features.groups.service import resolve_fault_targets
    assigned_to, notify_usernames, notify_emails, group = resolve_fault_targets(
        db,
        source_type=event.source_type,
        device_type=_device_tier(device),
        severity=decision.severity,
    )
    is_real_user = bool(group and assigned_to and assigned_to != group.name)

    # 三期治理：静默窗口 / 根因抑制 / 频控
    from app.services.alert_governance import check_silence, find_suppressor, freq_limited
    silence_task = check_silence(db, device.id, event.occurred_at)
    suppressor = find_suppressor(db, device, event.event_type, if_index=event.if_index)
    rate_limited = False
    if not silence_task and not suppressor:
        # 频控键 = 设备 × 事件类型（同一设备同类告警风暴抑制；单故障重复由去重分支兜底）
        rate_limited = freq_limited(
            f"device:{device.id}:{decision.incident_type or event.event_type}",
            decision.severity)
    governance = {
        "silenced": silence_task is not None,
        "silenced_by_task": silence_task.task_no if silence_task else None,
        "suppressed_by": suppressor.fault_no if suppressor else None,
        "rate_limited": rate_limited,
    }

    fault_no = f"INC-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
    fault = FaultRecord(
        fault_no=fault_no,
        device_id=device.id,
        device_name=device.name,
        severity=decision.severity,
        status="assigned" if is_real_user else "open",
        description=decision.description,
        impact=decision.impact,
        reporter="Monitor Automation",
        fault_time=event.occurred_at,
        fault_type=decision.fault_type,
        incident_type=decision.incident_type,
        assigned_to=assigned_to,
        assigned_at=datetime.utcnow() if is_real_user else None,
        source_type=event.source_type,
        source_key=decision.source_key,
        source_event=event.event_type,
        if_index=event.if_index,
        if_name=event.if_name,
        peer_device_id=event.peer_device_id,
        peer_if_name=event.peer_if_name,
        event_count=1,
        last_event_at=event.occurred_at,
        recommendation=decision.recommendation,
        assigned_email=notify_emails[0] if notify_emails else None,
        group_id=group.id if group else None,
        silenced=governance["silenced"],
        suppressed_by=governance["suppressed_by"],
        review_required=True,
        false_positive=False,
    )
    db.add(fault)
    db.commit()
    db.refresh(fault)

    if governance["silenced"] or governance["suppressed_by"] or governance["rate_limited"]:
        from app.services.notification_service import record_notification_log
        reason = ("静默(维护窗口)" if governance["silenced"]
                  else f"抑制(根因 {governance['suppressed_by']})" if governance["suppressed_by"]
                  else "频控")
        record_notification_log(
            db, event_type="fault_auto_created", channel="all",
            recipient="governance", title=fault.fault_no, status="suppressed",
            fault_id=fault.id, error=reason)
        try:
            db.commit()
        except Exception:
            logger.exception("治理日志提交失败")
        logger.info("告警治理：fault=%s %s", fault.fault_no, reason)
    else:
        notify_incident(db, fault, decision, recovered=False,
                        notify_usernames=notify_usernames, notify_emails=notify_emails)
    return fault


def notify_incident(
    db: Session,
    fault: FaultRecord,
    decision: IncidentDecision,
    recovered: bool = False,
    notify_usernames: Optional[List[str]] = None,
    notify_emails: Optional[List[str]] = None,
) -> None:
    """v1.1：统一经 dispatch() 通知 admin + 运维组（真实账号），全量落 notification_log。"""
    try:
        # 三期治理防御：静默/被抑制的故障不发任何通知
        if fault.silenced or fault.suppressed_by:
            return
        if notify_usernames is None or notify_emails is None:
            from app.features.groups.service import group_members
            usernames = ["admin"]
            if fault.group_id:
                usernames += [m.username for m in group_members(db, fault.group_id)]
            usernames = list(dict.fromkeys(usernames))
            emails: List[str] = []
            for user in db.query(User).filter(User.username.in_(usernames)).all():
                if user.email:
                    emails.append(user.email)
            if notify_usernames is None:
                notify_usernames = usernames
            if notify_emails is None:
                notify_emails = emails

        from app.services.notification_service import get_notification_service
        prefix = "[恢复]" if recovered else f"[{fault.severity.upper()}]"
        external = recovered or fault.severity in ("critical", "major")
        get_notification_service().dispatch(
            db,
            event_type="fault_recovered" if recovered else "fault_auto_created",
            title=f"{prefix} {fault.device_name or ''} - {fault.fault_no}",
            content=(fault.recommendation or decision.recommendation
                     or (fault.description or "")[:800]),
            recipients=notify_usernames,
            emails=notify_emails,
            reference_type="fault",
            reference_id=fault.id,
            fault_id=fault.id,
            use_email=external,
            use_im=external,
        )
    except Exception as e:
        logger.warning(f"故障通知发送失败 fault={fault.id}: {e}")
