"""Maintenance management router"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy.orm import Session
from typing import Any, Optional
from datetime import datetime, timedelta
import uuid

from app.features.auth.identity import Principal, get_current_principal
from app.shared.database import get_db
from app.shared.dependencies import require_permission
from app.shared.models import MaintenanceRecord, MaintenanceEvent, FaultRecord
from app.features.faults.router import send_maintenance_completed_notification
from .schemas import (
    MaintenanceAssignRequest,
    MaintenanceCreateRequest,
    MaintenanceStatusContextRequest,
    MaintenanceSubmitVerificationRequest,
    MaintenanceTransitionRequest,
    MaintenanceUpdateRequest,
    MaintenanceVerifyPassRequest,
    MaintenanceWorkNoteRequest,
)

router = APIRouter(prefix="/api/maintenance", tags=["maintenance"])
require_maintenance_read = require_permission("maintenance:read")
require_maintenance_write = require_permission("maintenance:write")
require_maintenance_delete = require_permission("maintenance:delete")
require_maintenance_transition = require_permission("maintenance:transition")
MAINTENANCE_INTERNAL_ERROR = "维修操作失败，请查看服务端日志"


def _actor_username(principal: Any) -> str:
    return principal.username if isinstance(principal, Principal) else "system"


def _internal_error(operation: str) -> HTTPException:
    logger.exception("Maintenance operation failed: {}", operation)
    return HTTPException(status_code=500, detail=MAINTENANCE_INTERNAL_ERROR)


def _resolve_linked_fault(db: Session, maintenance: MaintenanceRecord) -> None:
    if not maintenance.fault_id:
        return
    fault = db.query(FaultRecord).filter(
        FaultRecord.id == maintenance.fault_id
    ).first()
    if fault and fault.status == "transferred":
        fault.status = "resolved"
        fault.resolved_at = datetime.utcnow()
        fault.resolution = f"维修完成 - 维修单号: {maintenance.maint_no}"
        fault.updated_at = datetime.utcnow()

# 状态流转规则（4步流程：创建→维修→验证→完成）
VALID_TRANSITIONS = {
    'created': ['repairing', 'cancelled'],  # 直接进入维修
    'pending': ['repairing', 'cancelled'],  # pending 视为初始状态，直接进入维修
    'repairing': ['verifying', 'cancelled'],
    'verifying': ['completed', 'cancelled'],
    'completed': [],
    'cancelled': []
}

STATUS_LABELS = {
    'created': '创建',
    'pending': '待处理',
    'repairing': '维修',
    'verifying': '验证',
    'completed': '完成',
    'cancelled': '取消'
}

STATUS_PERCENT = {
    'created': 25,
    'pending': 25,  # pending 视为初始状态
    'repairing': 50,
    'verifying': 75,
    'completed': 100,
    'cancelled': 0
}


def calculate_sla_remaining(maintenance):
    """计算 SLA 剩余时间"""
    sla_remaining = None
    sla_deadline = maintenance.sla_deadline

    # 如果没有设置 sla_deadline，使用 created_at + 24h 作为默认
    if not sla_deadline and maintenance.created_at:
        sla_deadline = maintenance.created_at + timedelta(hours=24)

    if sla_deadline:
        remaining = sla_deadline - datetime.utcnow()
        if remaining.total_seconds() > 0:
            sla_remaining = f"{int(remaining.total_seconds() // 3600)}h {int((remaining.total_seconds() % 3600) // 60)}m"
        else:
            sla_remaining = "已超期"

    return sla_remaining, sla_deadline


def suggest_next_status(maintenance, data=None):
    """根据内容变化建议下一步状态

    返回: (建议状态, 建议原因, 是否需要用户确认)
    """
    current_status = maintenance.status or "created"
    data = data or {}

    # 规则1: created/pending -> repairing（直接进入维修）
    if current_status in ('created', 'pending'):
        # 检查是否有维修动作或备件信息
        repair_actions = data.get('repair_actions') or maintenance.repair_actions
        parts_replaced = data.get('parts_replaced') or maintenance.parts_replaced
        spare_parts_list = data.get('spare_parts_list') or getattr(
            maintenance,
            'spare_parts_list',
            None,
        )

        has_content = bool(repair_actions or parts_replaced or spare_parts_list)
        if has_content:
            return ('repairing', '检测到已添加维修内容', True)

    # 规则2: repairing -> verifying（提交验证）
    if current_status == 'repairing':
        verification_result = data.get('verification_result') or maintenance.verification_result
        if verification_result:
            return ('verifying', '检测到已提交验证结果', True)

    # 规则3: verifying -> completed（验证通过）
    if current_status == 'verifying':
        verify_passed = data.get('verify_passed') or maintenance.verify_passed
        if verify_passed:
            return ('completed', '验证已通过', True)

    # 无建议
    return (None, None, False)


def get_next_action_button(current_status):
    """根据当前状态返回下一步操作按钮文案（简化4步流程）"""
    ACTION_BUTTONS = {
        'created': {'action': 'repairing', 'label': '开始维修', 'icon': 'Setting'},
        'pending': {'action': 'repairing', 'label': '开始维修', 'icon': 'Setting'},
        'repairing': {'action': 'verifying', 'label': '提交验证', 'icon': 'CircleCheck'},
        'verifying': {'action': 'completed', 'label': '完成维修', 'icon': 'SuccessFilled'},
        'completed': {'action': None, 'label': '查看详情', 'icon': 'View'},
        'cancelled': {'action': None, 'label': '查看详情', 'icon': 'View'}
    }
    return ACTION_BUTTONS.get(current_status, {'action': None, 'label': '查看详情', 'icon': 'View'})




def add_utc_suffix(dt_iso: str) -> str:
    """Add 'Z' suffix to datetime ISO string to indicate UTC timezone"""
    if dt_iso and not dt_iso.endswith('Z'):
        return dt_iso + 'Z'
    return dt_iso


def build_events_from_record(maintenance):
    """从维修记录构建事件时间线"""
    events = []

    # 创建事件
    events.append({
        "event_type": "created",
        "event_time": add_utc_suffix(maintenance.created_at.isoformat()) if maintenance.created_at else None,
        "operator": maintenance.operator or "System",
        "notes": f"创建维修单 {maintenance.maint_no}"
    })

    # 各阶段事件（简化4步流程）
    if maintenance.repairing_at:
        events.append({
            "event_type": "repairing",
            "event_time": add_utc_suffix(maintenance.repairing_at.isoformat()),
            "operator": maintenance.current_owner or maintenance.operator,
            "notes": "开始维修作业"
        })

    if maintenance.verifying_at:
        events.append({
            "event_type": "verifying",
            "event_time": add_utc_suffix(maintenance.verifying_at.isoformat()),
            "operator": maintenance.current_owner or maintenance.operator,
            "notes": "提交验证"
        })

    if maintenance.completed_at:
        events.append({
            "event_type": "completed",
            "event_time": add_utc_suffix(maintenance.completed_at.isoformat()),
            "operator": maintenance.current_owner or maintenance.operator,
            "notes": "维修完成"
        })

    if maintenance.cancelled_at:
        events.append({
            "event_type": "cancelled",
            "event_time": add_utc_suffix(maintenance.cancelled_at.isoformat()),
            "operator": maintenance.current_owner or maintenance.operator,
            "notes": "维修取消"
        })

    return events


@router.get("/{maint_id}")
async def get_maintenance(
    maint_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_maintenance_read),
):
    """获取单个维修详情"""
    try:
        maintenance = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == maint_id).first()
        if not maintenance:
            raise HTTPException(status_code=404, detail="维修记录不存在")

        # 获取关联的故障信息（增强版，包含工作日志）
        fault_info = None
        fault_work_notes = []  # 故障的工作日志
        if maintenance.fault_id:
            fault = db.query(FaultRecord).filter(FaultRecord.id == maintenance.fault_id).first()
            if fault:
                fault_info = {
                    "id": fault.id,
                    "fault_no": fault.fault_no,
                    "severity": fault.severity,
                    "status": fault.status,
                    "description": fault.description,
                    "assigned_to": fault.assigned_to if hasattr(fault, 'assigned_to') else None,
                    "diagnosis_text": fault.diagnosis_text if hasattr(fault, 'diagnosis_text') else None,
                    "diagnosis_result": fault.diagnosis_result if hasattr(fault, 'diagnosis_result') else None
                }

                # 构建故障工作日志事件（标记来源为 fault）
                # 解析 diagnosis_text，分割成多条独立日志
                if fault.diagnosis_text:
                    # 格式：第一条日志\n\n--- 2026-05-19 21:59 ---\n第二条日志
                    import re
                    # 匹配时间分隔符
                    pattern = r'\n\n--- (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) ---\n'
                    parts = re.split(pattern, fault.diagnosis_text)

                    # 第一部分是最早的日志（没有时间分隔符）
                    if parts and parts[0].strip():
                        first_note_time = add_utc_suffix(fault.diagnosing_at.isoformat()) if hasattr(fault, 'diagnosing_at') and fault.diagnosing_at else add_utc_suffix(fault.created_at.isoformat() if fault.created_at else maintenance.created_at.isoformat())
                        fault_work_notes.append({
                            "event_type": "fault_diagnosis",
                            "event_time": first_note_time,
                            "operator": fault.assigned_to or fault.reporter or "Unknown",
                            "notes": parts[0].strip(),
                            "source": "fault"
                        })

                    # 后续部分是带时间分隔符的日志
                    # parts 格式：[第一条, 时间1, 第二条, 时间2, 第三条, ...]
                    # 奇数索引是时间，偶数索引是内容
                    for i in range(1, len(parts), 2):
                        if i + 1 < len(parts) and parts[i + 1].strip():
                            time_str = parts[i]  # 格式：2026-05-19 21:59
                            # 转换为 ISO 格式并添加 UTC 标记
                            event_time = time_str + ":00Z"  # 添加秒和 UTC 标记
                            fault_work_notes.append({
                                "event_type": "fault_diagnosis",
                                "event_time": event_time,
                                "operator": fault.assigned_to or "Unknown",
                                "notes": parts[i + 1].strip(),
                                "source": "fault"
                            })

        # 构建事件时间线（包含故障工作日志）
        # 故障工作日志放在最前面，然后是维修事件
        events = fault_work_notes + build_events_from_record(maintenance)

        # 查询 MaintenanceEvent 表中的实际事件（包括 work_note）
        db_events = db.query(MaintenanceEvent).filter(
            MaintenanceEvent.maintenance_id == maint_id
        ).order_by(MaintenanceEvent.event_time).all()

        for e in db_events:
            events.append({
                "event_type": e.event_type,
                "event_time": add_utc_suffix(e.event_time.isoformat()) if e.event_time else None,
                "operator": e.operator or "System",
                "notes": e.notes or ""
            })

        # 按时间排序，旧的在最上面（工作流程时间线：创建 -> 诊断 -> 维修 -> 验证 -> 完成）
        events.sort(key=lambda e: e.get('event_time') or '', reverse=False)

        # 计算SLA剩余时间
        sla_remaining = None
        if maintenance.sla_deadline:
            remaining = maintenance.sla_deadline - datetime.utcnow()
            if remaining.total_seconds() > 0:
                sla_remaining = f"{int(remaining.total_seconds() // 3600)}h {int((remaining.total_seconds() % 3600) // 60)}m"
            else:
                sla_remaining = "已超期"

        return {
            "id": maintenance.id,
            "maint_no": maintenance.maint_no,
            "device_id": maintenance.device_id,
            "device_name": maintenance.device_name,
            "maint_type": maintenance.maint_type,
            "parts_replaced": maintenance.parts_replaced,
            "parts_cost": float(maintenance.parts_cost) if maintenance.parts_cost else 0,
            "labor_hours": maintenance.labor_hours,
            "labor_cost": float(maintenance.labor_cost) if maintenance.labor_cost else 0,
            "vendor": maintenance.vendor,
            "description": maintenance.description,
            "fault_id": maintenance.fault_id,
            "fault": fault_info,
            "maint_time": add_utc_suffix(maintenance.maint_time.isoformat()) if maintenance.maint_time else None,
            "created_at": add_utc_suffix(maintenance.created_at.isoformat()),
            # 新增状态系统字段
            "status": maintenance.status or "created",
            "status_label": STATUS_LABELS.get(maintenance.status, "创建"),
            "progress_percent": STATUS_PERCENT.get(maintenance.status, 20),
            "priority": maintenance.priority or "P3",
            "current_owner": maintenance.current_owner,
            "sla_deadline": add_utc_suffix(maintenance.sla_deadline.isoformat()) if maintenance.sla_deadline else None,
            "sla_remaining": sla_remaining,
            "diagnosing_at": add_utc_suffix(maintenance.diagnosing_at.isoformat()) if maintenance.diagnosing_at else None,
            "repairing_at": add_utc_suffix(maintenance.repairing_at.isoformat()) if maintenance.repairing_at else None,
            "verifying_at": add_utc_suffix(maintenance.verifying_at.isoformat()) if maintenance.verifying_at else None,
            "completed_at": add_utc_suffix(maintenance.completed_at.isoformat()) if maintenance.completed_at else None,
            "cancelled_at": add_utc_suffix(maintenance.cancelled_at.isoformat()) if maintenance.cancelled_at else None,
            # 诊断信息字段
            "diagnosis_text": maintenance.diagnosis_text,
            "diagnosis_result": maintenance.diagnosis_result,
            # 验证信息字段
            "verification_result": maintenance.verification_result,
            "verification_notes": maintenance.verification_notes,
            "verify_passed": maintenance.verify_passed,
            # 工作日志
            "events": events,
            "fault_work_notes": fault_work_notes,  # 故障工作日志（单独字段供前端使用）
            "has_fault_work_notes": len(fault_work_notes) > 0  # 是否有故障工作日志
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise _internal_error("get maintenance") from exc


@router.get("/{maint_id}/events")
async def get_maintenance_events(
    maint_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_maintenance_read),
):
    """获取维修事件时间线"""
    try:
        maintenance = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == maint_id).first()
        if not maintenance:
            raise HTTPException(status_code=404, detail="维修记录不存在")

        # 从维修记录构建事件
        events = build_events_from_record(maintenance)

        # 从事件表获取额外事件（如果有）
        db_events = db.query(MaintenanceEvent).filter(
            MaintenanceEvent.maintenance_id == maint_id
        ).order_by(MaintenanceEvent.event_time).all()

        for e in db_events:
            events.append({
                "id": e.id,
                "event_type": e.event_type,
                "event_time": e.event_time.isoformat(),
                "operator": e.operator,
                "notes": e.notes
            })

        return {"events": events}
    except HTTPException:
        raise
    except Exception as exc:
        raise _internal_error("get maintenance events") from exc


@router.post("/{maint_id}/transition")
async def transition_maintenance_status(
    maint_id: int,
    data: MaintenanceTransitionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: None = Depends(require_maintenance_transition),
    principal: Principal = Depends(get_current_principal),
):
    """状态流转"""
    try:
        maintenance = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == maint_id).first()
        if not maintenance:
            raise HTTPException(status_code=404, detail="维修记录不存在")

        new_status = data.status
        operator = _actor_username(principal)
        notes = data.notes

        # 验证状态流转是否合法
        current_status = maintenance.status or "created"
        if new_status not in VALID_TRANSITIONS.get(current_status, []):
            raise HTTPException(status_code=400, detail=f"不能从 {current_status} 转换到 {new_status}")

        # 更新状态和时间戳
        maintenance.status = new_status

        if new_status == "repairing":
            maintenance.repairing_at = datetime.utcnow()
        elif new_status == "verifying":
            maintenance.verifying_at = datetime.utcnow()
        elif new_status == "completed":
            maintenance.completed_at = datetime.utcnow()
            maintenance.verify_passed = True
            _resolve_linked_fault(db, maintenance)
            # 维修完成时通知故障负责人去确认解决
            if maintenance.fault_id:
                from app.features.faults.router import send_maintenance_completed_notification
                # 在后台发送通知
                background_tasks.add_task(
                    send_maintenance_completed_notification,
                    maintenance.fault_id,
                    maintenance.id
                )
        elif new_status == "cancelled":
            maintenance.cancelled_at = datetime.utcnow()

        # 创建事件记录
        event = MaintenanceEvent(
            maintenance_id=maint_id,
            event_type=new_status,
            event_time=datetime.utcnow(),
            operator=operator,
            notes=notes or f"状态流转: {STATUS_LABELS.get(current_status)} → {STATUS_LABELS.get(new_status)}"
        )
        db.add(event)

        db.commit()

        # 清除 Dashboard 缓存
        from app.shared.cache import cache
        cache.invalidate_prefix("dashboard:")

        return {
            "id": maint_id,
            "status": new_status,
            "status_label": STATUS_LABELS.get(new_status),
            "progress_percent": STATUS_PERCENT.get(new_status),
            "message": f"状态已更新为 {STATUS_LABELS.get(new_status)}"
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise _internal_error("transition maintenance") from exc


@router.put("/{maint_id}/assign")
async def assign_maintenance(
    maint_id: int,
    data: MaintenanceAssignRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_maintenance_write),
    principal: Principal = Depends(get_current_principal),
):
    """分配负责人"""
    try:
        maintenance = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == maint_id).first()
        if not maintenance:
            raise HTTPException(status_code=404, detail="维修记录不存在")

        owner = data.owner

        maintenance.current_owner = owner

        # 创建事件记录
        event = MaintenanceEvent(
            maintenance_id=maint_id,
            event_type="assigned",
            event_time=datetime.utcnow(),
            operator=_actor_username(principal),
            notes=f"分配给 {owner}"
        )
        db.add(event)

        db.commit()

        return {"id": maint_id, "owner": owner, "message": f"已分配给 {owner}"}
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise _internal_error("assign maintenance") from exc


@router.post("/{maint_id}/work-note")
async def add_work_note(
    maint_id: int,
    data: MaintenanceWorkNoteRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_maintenance_write),
    principal: Principal = Depends(get_current_principal),
):
    """添加工作日志（Note）

    用于维修过程中记录工作进展
    """
    try:
        maintenance = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == maint_id).first()
        if not maintenance:
            raise HTTPException(status_code=404, detail="维修记录不存在")

        if maintenance.status in ['completed', 'cancelled']:
            raise HTTPException(status_code=400, detail="已完成或已取消的维修单不能添加日志")

        note_text = data.note
        operator = _actor_username(principal)

        # 创建工作日志事件
        event = MaintenanceEvent(
            maintenance_id=maint_id,
            event_type="work_note",
            event_time=datetime.utcnow(),
            operator=operator,
            notes=note_text
        )
        db.add(event)
        db.commit()

        return {
            "id": maint_id,
            "event_id": event.id,
            "message": "工作日志已添加"
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise _internal_error("add maintenance work note") from exc


@router.post("/{maint_id}/submit-verification")
async def submit_for_verification(
    maint_id: int,
    data: MaintenanceSubmitVerificationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: None = Depends(require_maintenance_transition),
    principal: Principal = Depends(get_current_principal),
):
    """提交验证（维修完成，进入验证阶段）

    必须在 repairing 状态才能提交
    """
    try:
        maintenance = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == maint_id).first()
        if not maintenance:
            raise HTTPException(status_code=404, detail="维修记录不存在")

        if maintenance.status != 'repairing':
            raise HTTPException(status_code=400, detail=f"只有维修中状态才能提交验证，当前状态: {maintenance.status}")

        # 更新备件和返回件信息（如果有）
        if data.spare_parts is not None:
            maintenance.parts_replaced = data.spare_parts
        if data.parts_cost is not None:
            maintenance.parts_cost = data.parts_cost

        # 状态流转到 verifying
        maintenance.status = 'verifying'
        maintenance.verifying_at = datetime.utcnow()

        # 创建事件记录
        event = MaintenanceEvent(
            maintenance_id=maint_id,
            event_type="verifying",
            event_time=datetime.utcnow(),
            operator=_actor_username(principal),
            notes="提交验证"
        )
        db.add(event)
        db.commit()

        # 清除 Dashboard 缓存
        from app.shared.cache import cache
        cache.invalidate_prefix("dashboard:")

        return {
            "id": maint_id,
            "status": "verifying",
            "status_label": STATUS_LABELS.get("verifying"),
            "progress_percent": STATUS_PERCENT.get("verifying"),
            "message": "已提交验证，等待运行确认"
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise _internal_error("submit maintenance verification") from exc


@router.post("/{maint_id}/verify-pass")
async def verify_pass(
    maint_id: int,
    data: MaintenanceVerifyPassRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: None = Depends(require_maintenance_transition),
    principal: Principal = Depends(get_current_principal),
):
    """验证通过（维修完成）

    必须在 verifying 状态才能验证通过
    验证通过后自动更新关联故障状态为 resolved
    """
    try:
        maintenance = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == maint_id).first()
        if not maintenance:
            raise HTTPException(status_code=404, detail="维修记录不存在")

        if maintenance.status != 'verifying':
            raise HTTPException(status_code=400, detail=f"只有验证中状态才能通过验证，当前状态: {maintenance.status}")

        # 状态流转到 completed
        maintenance.status = 'completed'
        maintenance.completed_at = datetime.utcnow()
        maintenance.verify_passed = True
        if data.verification_notes:
            maintenance.verification_notes = data.verification_notes

        # 创建事件记录
        event = MaintenanceEvent(
            maintenance_id=maint_id,
            event_type="completed",
            event_time=datetime.utcnow(),
            operator=_actor_username(principal),
            notes="验证通过，维修完成"
        )
        db.add(event)

        _resolve_linked_fault(db, maintenance)

        db.commit()

        # 维修完成时通知故障负责人
        if maintenance.fault_id:
            background_tasks.add_task(
                send_maintenance_completed_notification,
                maintenance.fault_id,
                maintenance.id
            )

        # 清除 Dashboard 缓存
        from app.shared.cache import cache
        cache.invalidate_prefix("dashboard:")

        return {
            "id": maint_id,
            "status": "completed",
            "status_label": STATUS_LABELS.get("completed"),
            "progress_percent": STATUS_PERCENT.get("completed"),
            "message": "维修已完成，故障已自动解决"
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise _internal_error("verify maintenance") from exc


@router.post("/{maint_id}/suggest-status")
async def suggest_status(
    maint_id: int,
    data: Optional[MaintenanceStatusContextRequest] = None,
    db: Session = Depends(get_db),
    _: None = Depends(require_maintenance_read),
):
    """根据当前内容建议下一步状态

    返回建议的状态变更，用于前端智能提示弹窗
    """
    try:
        maintenance = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == maint_id).first()
        if not maintenance:
            raise HTTPException(status_code=404, detail="维修记录不存在")

        # 获取建议
        context = data.to_context_dict() if data else {}
        suggested_status, reason, need_confirm = suggest_next_status(
            maintenance,
            context,
        )

        # 获取下一步操作按钮
        next_action = get_next_action_button(maintenance.status)

        return {
            "id": maint_id,
            "current_status": maintenance.status,
            "current_status_label": STATUS_LABELS.get(maintenance.status, "创建"),
            "suggested_status": suggested_status,
            "suggested_status_label": STATUS_LABELS.get(suggested_status, "") if suggested_status else None,
            "reason": reason,
            "need_confirm": need_confirm,
            "next_action": next_action,
            "valid_transitions": VALID_TRANSITIONS.get(maintenance.status, [])
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise _internal_error("suggest maintenance status") from exc


@router.post("/{maint_id}/auto-transition")
async def auto_transition_status(
    maint_id: int,
    data: MaintenanceStatusContextRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: None = Depends(require_maintenance_transition),
    principal: Principal = Depends(get_current_principal),
):
    """自动状态推进（用户确认后调用）

    检查内容是否满足条件，然后自动推进状态
    """
    try:
        maintenance = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == maint_id).first()
        if not maintenance:
            raise HTTPException(status_code=404, detail="维修记录不存在")

        context = data.to_context_dict()
        suggested_status = context.get("status")
        reason = "用户确认状态流转" if suggested_status else None
        if not suggested_status:
            suggested_status, reason, _ = suggest_next_status(
                maintenance,
                context,
            )

        if not suggested_status:
            return {"id": maint_id, "message": "无需推进状态", "status": maintenance.status}

        # 验证状态流转是否合法
        current_status = maintenance.status
        if suggested_status not in VALID_TRANSITIONS.get(current_status, []):
            return {"id": maint_id, "message": f"不能从 {current_status} 转换到 {suggested_status}", "status": maintenance.status}

        # 更新状态和时间戳
        maintenance.status = suggested_status

        if suggested_status == "repairing":
            maintenance.repairing_at = datetime.utcnow()
            # 更新维修动作
            if context.get('repair_actions'):
                maintenance.repair_actions = context['repair_actions']
            if context.get('parts_replaced'):
                maintenance.parts_replaced = context['parts_replaced']
        elif suggested_status == "verifying":
            maintenance.verifying_at = datetime.utcnow()
            # 更新验证结果
            if context.get('verification_result'):
                maintenance.verification_result = context['verification_result']
            if context.get('verification_notes'):
                maintenance.verification_notes = context['verification_notes']
        elif suggested_status == "completed":
            maintenance.completed_at = datetime.utcnow()
            maintenance.verify_passed = True
            _resolve_linked_fault(db, maintenance)

        # 创建事件记录
        event = MaintenanceEvent(
            maintenance_id=maint_id,
            event_type=suggested_status,
            event_time=datetime.utcnow(),
            operator=_actor_username(principal),
            notes=f"自动推进: {STATUS_LABELS.get(current_status)} → {STATUS_LABELS.get(suggested_status)}"
        )
        db.add(event)

        db.commit()

        if suggested_status == "completed" and maintenance.fault_id:
            background_tasks.add_task(
                send_maintenance_completed_notification,
                maintenance.fault_id,
                maintenance.id,
            )

        # 清除 Dashboard 缓存
        from app.shared.cache import cache
        cache.invalidate_prefix("dashboard:")

        return {
            "id": maint_id,
            "status": suggested_status,
            "status_label": STATUS_LABELS.get(suggested_status),
            "progress_percent": STATUS_PERCENT.get(suggested_status),
            "reason": reason,
            "message": f"状态已自动推进为 {STATUS_LABELS.get(suggested_status)}"
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise _internal_error("auto-transition maintenance") from exc


@router.get("")
async def list_maintenances(
    device_id: Optional[int] = None,
    fault_id: Optional[int] = None,
    maint_type: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    has_fault: Optional[bool] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: None = Depends(require_maintenance_read),
):
    """获取维修记录列表（带分页和状态筛选）"""
    try:
        query = db.query(MaintenanceRecord)

        if device_id:
            query = query.filter(MaintenanceRecord.device_id == device_id)

        if fault_id:
            query = query.filter(MaintenanceRecord.fault_id == fault_id)

        if maint_type:
            query = query.filter(MaintenanceRecord.maint_type == maint_type)

        if status:
            query = query.filter(MaintenanceRecord.status == status)

        if priority:
            query = query.filter(MaintenanceRecord.priority == priority)

        if has_fault is True:
            query = query.filter(MaintenanceRecord.fault_id.isnot(None))
        elif has_fault is False:
            query = query.filter(MaintenanceRecord.fault_id.is_(None))

        total = query.count()
        maintenances = query.order_by(MaintenanceRecord.created_at.desc()).offset(skip).limit(limit).all()

        return {
            "total": total,
            "items": [
                {
                    "id": m.id,
                    "maint_no": m.maint_no,
                    "device_id": m.device_id,
                    "device_name": m.device_name,
                    "maint_type": m.maint_type,
                    "fault_id": m.fault_id,
                    "parts_replaced": m.parts_replaced,
                    "parts_cost": float(m.parts_cost) if m.parts_cost else 0,
                    "labor_cost": float(m.labor_cost) if m.labor_cost else 0,
                    "total_cost": float((m.parts_cost or 0) + (m.labor_cost or 0)),
                    "maint_time": m.maint_time.isoformat() if m.maint_time else None,
                    "description": m.description,
                    "created_at": m.created_at.isoformat(),
                    "status": m.status or "created",
                    "status_label": STATUS_LABELS.get(m.status, "创建"),
                    "priority": m.priority or "P3",
                    "current_owner": m.current_owner,
                    "sla_deadline": (m.sla_deadline or (m.created_at + timedelta(hours=24) if m.created_at else None)).isoformat() if (m.sla_deadline or m.created_at) else None,
                    "sla_remaining": calculate_sla_remaining(m)[0]
                }
                for m in maintenances
            ]
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise _internal_error("list maintenances") from exc


@router.post("")
async def create_maintenance(
    request: MaintenanceCreateRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_maintenance_write),
    principal: Principal = Depends(get_current_principal),
):
    """创建维修记录"""
    try:
        maint_no = f"MAINT-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
        filtered_data = request.to_record_dict()
        filtered_data["maint_no"] = maint_no
        filtered_data["status"] = "created"
        filtered_data["operator"] = _actor_username(principal)

        # 设置维修时间为当前时间（如果未提供）
        if "maint_time" not in filtered_data or not filtered_data["maint_time"]:
            filtered_data["maint_time"] = datetime.utcnow()

        # 设置 SLA 截止时间（默认24小时）
        if "sla_deadline" not in filtered_data:
            filtered_data["sla_deadline"] = datetime.utcnow() + timedelta(hours=24)

        maint = MaintenanceRecord(**filtered_data)
        db.add(maint)
        db.flush()  # 先 flush 获取自增 ID

        # 创建事件记录
        event = MaintenanceEvent(
            maintenance_id=maint.id,
            event_type="created",
            event_time=datetime.utcnow(),
            operator=_actor_username(principal),
            notes=f"创建维修单 {maint_no}"
        )
        db.add(event)

        db.commit()
        db.refresh(maint)

        # 清除 Dashboard 缓存
        from app.shared.cache import cache
        cache.invalidate_prefix("dashboard:")

        return {
            "id": maint.id,
            "maint_no": maint_no,
            "status": "created",
            "message": "维修记录创建成功"
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise _internal_error("create maintenance") from exc


@router.put("/{maint_id}")
async def update_maintenance(
    maint_id: int,
    request: MaintenanceUpdateRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_maintenance_write),
    principal: Principal = Depends(get_current_principal),
):
    """更新维修记录"""
    try:
        maint = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == maint_id).first()
        if not maint:
            raise HTTPException(status_code=404, detail="维修记录不存在")

        maint_data = request.to_record_dict()
        old_diagnosis = maint.diagnosis_text or ''
        for key, value in maint_data.items():
            if hasattr(maint, key):
                setattr(maint, key, value)

        # ===== 记录状态机相关事件 =====
        # 诊断内容添加事件
        if 'diagnosis_text' in maint_data and maint_data.get('diagnosis_text'):
            if len(old_diagnosis.strip()) == 0 and len(maint_data['diagnosis_text'].strip()) > 0:
                event = MaintenanceEvent(
                    maintenance_id=maint_id,
                    event_type='diagnosis_added',
                    notes='添加了诊断内容',
                    operator=_actor_username(principal)
                )
                db.add(event)

        # 验证结果提交事件
        if 'verification_result' in maint_data and maint_data.get('verification_result'):
            event = MaintenanceEvent(
                maintenance_id=maint_id,
                event_type='verification_submitted',
                notes=f"验证结果: {maint_data['verification_result']}",
                operator=_actor_username(principal)
            )
            db.add(event)

        # 验证通过事件
        if maint_data.get('verify_passed') == True:
            event = MaintenanceEvent(
                maintenance_id=maint_id,
                event_type='verification_passed',
                notes='验证通过',
                operator=_actor_username(principal)
            )
            db.add(event)

        db.commit()
        db.refresh(maint)

        return {"id": maint.id, "message": "更新成功"}
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise _internal_error("update maintenance") from exc


@router.delete("/{maint_id}")
async def delete_maintenance(
    maint_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_maintenance_delete),
):
    """删除维修记录"""
    try:
        maint = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == maint_id).first()
        if not maint:
            raise HTTPException(status_code=404, detail="维修记录不存在")

        db.delete(maint)
        db.commit()

        return {"message": "删除成功"}
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise _internal_error("delete maintenance") from exc
