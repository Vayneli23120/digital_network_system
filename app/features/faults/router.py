"""Incident Center - 故障管理路由

企业级Incident Center风格：
- AI辅助故障分析（使用 ADK Agent）
- 根因分析支持
- 自动创建维修单决策
- 故障生命周期管理
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy import case
from sqlalchemy.orm import Session, selectinload
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, ConfigDict, Field, field_validator
from loguru import logger
import uuid
import json

from app.features.auth.identity import Principal, get_current_principal
from app.features.maintenance.schemas import MaintenancePriority, MaintenanceType
from app.shared.database import get_db
from app.shared.time_utils import utc_iso
from app.shared.dependencies import require_permission
from app.shared.models import FaultRecord, MaintenanceRecord, Device, AIAnalysisRecord
from app.services.fault_maintenance import (
    FaultMaintenanceConflictError,
    create_fault_maintenance_once,
    find_fault_maintenance,
)
from app.services.workflow.executor import WorkflowExecutor

# ADK 导入（可选：AI 依赖未安装时降级）
try:
    from app.services.adk.runner import adk_runner
    from app.services.adk.agents import fault_analysis_agent
    ADK_AVAILABLE = True
except Exception:
    adk_runner = None
    fault_analysis_agent = None
    ADK_AVAILABLE = False

router = APIRouter(prefix="/api/faults", tags=["faults"])
require_fault_read = require_permission("fault:read")
require_fault_write = require_permission("fault:write")
require_fault_delete = require_permission("fault:delete")
require_fault_analyze = require_permission("fault:analyze")


# ===== 状态流转规则 =====
# 新流程：创建 → 指派 → 开始诊断 → 技术处理/转维修 → 解决 → 关闭
# 去掉"接收"步骤，指派后直接进入诊断
FAULT_VALID_TRANSITIONS = {
    'open': ['assigned', 'closed'],
    'assigned': ['diagnosing', 'reassigned', 'closed'],  # 直接开始诊断
    'accepted': ['diagnosing', 'reassigned', 'closed'],  # 兼容接收确认后的下一步
    'diagnosing': ['resolving', 'transferred', 'resolved', 'reassigned'],  # 支持转单，禁止直接关闭
    'resolving': ['resolved', 'closed'],
    'transferred': ['resolved', 'closed'],  # 维修完成需人工确认
    'resolved': ['closed'],
    'closed': []
}

FAULT_STATUS_LABELS = {
    'open': '待处理',
    'assigned': '已指派',
    'accepted': '已确认',
    'diagnosing': '诊断中',
    'resolving': '技术处理',
    'transferred': '已转维修',
    'resolved': '已解决',
    'closed': '已关闭',
    'reassigned': '已转单',
    'investigating': '调查中',  # 兼容旧状态
}

FAULT_STATUS_COLORS = {
    'open': 'warning',
    'assigned': 'info',
    'accepted': 'primary',
    'diagnosing': 'warning',
    'resolving': 'primary',
    'transferred': 'success',
    'resolved': 'success',
    'closed': 'info',
    'investigating': 'warning',
}

FAULT_ACTIVE_STATUSES = tuple(
    status for status in FAULT_STATUS_LABELS if status != "closed"
)

FAULT_DIAGNOSIS_RESULTS = {
    'config_issue': '配置问题',
    'software_issue': '软件问题',
    'need_replace': '需更换配件',
    'need_upgrade': '需升级',
    'field_check': '需现场排查',
    'no_fault': '未发现故障',
}


# ===== Request Models =====

class CreateFaultRequest(BaseModel):
    """创建故障请求"""
    device_id: int
    severity: str = "minor"  # minor/warning/major/critical
    description: str
    impact: Optional[str] = None
    fault_time: Optional[datetime] = None
    fault_type: Optional[str] = None  # hardware/software/config/network/other
    assigned_to: Optional[str] = None  # 指派负责人


class AssignFaultRequest(BaseModel):
    """指派故障请求"""
    assigned_to: str  # 负责人


class AcceptFaultRequest(BaseModel):
    """接收故障请求"""
    accepted: bool = True


class DiagnoseFaultRequest(BaseModel):
    """诊断故障请求"""
    fault_type: Optional[str] = None
    diagnosis_text: Optional[str] = None
    diagnosis_result: Optional[str] = None  # config_issue/need_replace/need_upgrade/field_check


class TransferToMaintenanceRequest(BaseModel):
    """转维修请求"""
    maintenance_type: MaintenanceType = "corrective"
    description: Optional[str] = Field(default=None, max_length=100_000)
    diagnosis_text: Optional[str] = Field(default=None, max_length=10_000)
    priority: MaintenancePriority = "P3"
    maintenance_owner: Optional[str] = Field(default=None, max_length=100)
    estimated_parts: Optional[str] = Field(default=None, max_length=10_000)


class ResolveFaultRequest(BaseModel):
    """解决故障请求"""
    resolution: str
    resolution_type: Optional[str] = None  # config_fix/software_fix/other


class UpdateFaultRequest(BaseModel):
    """更新故障请求"""
    severity: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    resolution: Optional[str] = None
    impact: Optional[str] = None
    assigned_to: Optional[str] = None
    fault_type: Optional[str] = None
    diagnosis_text: Optional[str] = None
    diagnosis_result: Optional[str] = None


class AnalyzeFaultRequest(BaseModel):
    """AI分析故障请求"""
    auto_create_maintenance: bool = False  # 是否根据AI建议自动创建维修单


class ReviewFaultRequest(BaseModel):
    """管理员复核监控自动创建的故障"""
    false_positive: bool = False
    notes: Optional[str] = None


class WorkNoteRequest(BaseModel):
    """故障工作日志请求。"""

    model_config = ConfigDict(extra="forbid")

    note: str = Field(min_length=1, max_length=10_000)

    @field_validator("note")
    @classmethod
    def normalize_note(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("日志内容不能为空")
        return normalized


def _actor_username(principal: Any) -> str:
    return principal.username if isinstance(principal, Principal) else "system"


# ===== Basic CRUD =====

@router.get("")
async def list_faults(
    device_id: Optional[int] = None,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    has_ai_analysis: Optional[bool] = None,
    need_repair: Optional[str] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: None = Depends(require_fault_read)
):
    """
    获取故障记录列表

    Args:
        device_id: 设备ID筛选
        status: 状态筛选（open/investigating/resolved/closed）
        severity: 严重程度筛选
        has_ai_analysis: 是否有AI分析
        need_repair: AI建议是否需要维修（repair/watch/ignore）
        skip: 跳过数量
        limit: 返回数量
    """
    query = db.query(FaultRecord)

    if device_id:
        query = query.filter(FaultRecord.device_id == device_id)

    # 支持多状态筛选（逗号分隔）
    if status:
        statuses = [s.strip() for s in status.split(',')]
        query = query.filter(FaultRecord.status.in_(statuses))

    if severity:
        query = query.filter(FaultRecord.severity == severity)

    if has_ai_analysis is not None:
        if has_ai_analysis:
            query = query.filter(FaultRecord.ai_analysis_result.isnot(None))
        else:
            query = query.filter(FaultRecord.ai_analysis_result.is_(None))

    if need_repair:
        query = query.filter(FaultRecord.ai_recommendation == need_repair)

    total = query.count()
    severity_rank = case(
        (FaultRecord.severity == "critical", 4),
        (FaultRecord.severity == "major", 3),
        (FaultRecord.severity == "warning", 2),
        (FaultRecord.severity == "minor", 1),
        else_=0,
    )
    faults = query.options(
        selectinload(FaultRecord.device),
        selectinload(FaultRecord.maintenance),
    ).order_by(
        severity_rank.desc(),
        FaultRecord.created_at.desc(),
    ).offset(skip).limit(limit).all()

    items = []
    for f in faults:
        # 关联已由 selectinload 批量预加载，避免逐条查询 Device/MaintenanceRecord
        device = f.device

        # 获取关联维修单成本
        maintenance_cost = 0
        if f.maintenance_id and f.maintenance:
            maintenance = f.maintenance
            maintenance_cost = float(maintenance.parts_cost or 0) + float(maintenance.labor_cost or 0)

        # 计算SLA剩余时间（根据严重程度设置不同SLA时长）
        sla_hours = {"critical": 4, "major": 24, "minor": 72, "warning": 168}
        sla_deadline_hours = sla_hours.get(f.severity, 72)
        if f.created_at:
            elapsed_hours = (datetime.utcnow() - f.created_at).total_seconds() / 3600
            remaining_hours = sla_deadline_hours - elapsed_hours
            if remaining_hours > 0:
                if remaining_hours >= 24:
                    sla_remaining = f"{int(remaining_hours / 24)}d {int(remaining_hours % 24)}h"
                else:
                    sla_remaining = f"{int(remaining_hours)}h"
            else:
                sla_remaining = "已超期"
        else:
            sla_remaining = "--"

        items.append({
            "id": f.id,
            "fault_no": f.fault_no,
            "device_id": f.device_id,
            "device_name": f.device_name or (device.name if device else "Unknown"),
            "device_ip": device.ip if device else None,
            "device_health_score": device.health_score if device else None,
            "severity": f.severity,
            "status": f.status,
            "assigned_to": f.assigned_to,
            "fault_type": f.fault_type,
            "downtime_minutes": f.downtime_minutes,
            "description": f.description,
            "impact": f.impact,
            "reporter": f.reporter,
            "maintenance_id": f.maintenance_id,
            "maintenance_cost": maintenance_cost,
            "sla_remaining": sla_remaining,
            "auto_created_maintenance": f.auto_created_maintenance or False,
            "source_type": f.source_type,
            "source_key": f.source_key,
            "source_event": f.source_event,
            "if_index": f.if_index,
            "if_name": f.if_name,
            "peer_device_id": f.peer_device_id,
            "peer_if_name": f.peer_if_name,
            "event_count": f.event_count or 1,
            "last_event_at": utc_iso(f.last_event_at),
            "recommendation": f.recommendation,
            "assigned_email": f.assigned_email,
            "review_required": bool(f.review_required) if f.review_required is not None else False,
            "reviewed_at": utc_iso(f.reviewed_at),
            "reviewed_by": f.reviewed_by,
            "false_positive": bool(f.false_positive) if f.false_positive is not None else False,
            "has_ai_analysis": f.ai_analysis_result is not None,
            "ai_recommendation": f.ai_recommendation,
            "ai_root_cause": f.ai_root_cause,
            "ai_confidence": float(f.ai_confidence) if f.ai_confidence else None,
            "fault_time": utc_iso(f.fault_time),
            "created_at": utc_iso(f.created_at),
            "updated_at": utc_iso(f.updated_at)
        })

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": items
    }


@router.get("/{fault_id}")
async def get_fault(
    fault_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_fault_read),
):
    """获取单个故障详情"""
    fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()

    if not fault:
        raise HTTPException(status_code=404, detail="故障记录不存在")

    device = db.query(Device).filter(Device.id == fault.device_id).first()

    # 获取AI分析记录
    ai_records = db.query(AIAnalysisRecord).filter(
        AIAnalysisRecord.target_type == 'fault',
        AIAnalysisRecord.target_id == fault_id
    ).order_by(AIAnalysisRecord.created_at.desc()).limit(5).all()

    ai_history = [
        {
            "id": r.id,
            "analysis_type": r.analysis_type,
            "provider": r.ai_provider,
            "model": r.model_name,
            "confidence": float(r.confidence_score) if r.confidence_score else None,
            "processing_time_ms": r.processing_time_ms,
            "status": r.status,
            "created_at": r.created_at.isoformat()
        }
        for r in ai_records
    ]

    # 获取关联维修单（增强显示）
    maintenance = None
    if fault.maintenance_id:
        m = db.query(MaintenanceRecord).filter(
            MaintenanceRecord.id == fault.maintenance_id
        ).first()
        if m:
            # 获取维修单关联的备件更换记录
            spare_parts_used = []
            if hasattr(m, 'spare_parts_used') and m.spare_parts_used:
                try:
                    spare_parts_used = json.loads(m.spare_parts_used)
                except Exception as e:
                    logger.warning(f"解析维修单备件更换记录 JSON 失败: {e}")
                    spare_parts_used = []

            maintenance = {
                "id": m.id,
                "maint_no": m.maint_no,
                "maint_type": m.maint_type,
                "status": m.status,
                "status_label": {
                    "created": "已创建",
                    "in_progress": "进行中",
                    "completed": "已完成",
                    "verified": "已验证"
                }.get(m.status, m.status),
                "current_owner": m.current_owner if hasattr(m, 'current_owner') else None,
                "priority": m.priority if hasattr(m, 'priority') else None,
                "estimated_completion": m.estimated_completion.isoformat() if hasattr(m, 'estimated_completion') and m.estimated_completion else None,
                "spare_parts_used": spare_parts_used,
                "parts_cost": float(m.parts_cost) if hasattr(m, 'parts_cost') and m.parts_cost else 0,
                "labor_cost": float(m.labor_cost) if hasattr(m, 'labor_cost') and m.labor_cost else 0,
                "description": m.description,
                "created_at": m.created_at.isoformat(),
                "updated_at": m.updated_at.isoformat() if hasattr(m, 'updated_at') and m.updated_at else None
            }

    return {
        "id": fault.id,
        "fault_no": fault.fault_no,
        "device_id": fault.device_id,
        "device_name": fault.device_name or (device.name if device else "Unknown"),
        "device_ip": device.ip if device else None,
        "device_health_score": device.health_score if device else None,
        "device_risk_level": device.risk_level if device else None,
        "severity": fault.severity,
        "status": fault.status,
        "downtime_minutes": fault.downtime_minutes,
        "impact": fault.impact,
        "description": fault.description,
        "resolution": fault.resolution,
        "reporter": fault.reporter,
        "fault_type": fault.fault_type if hasattr(fault, 'fault_type') else None,
        "assigned_to": fault.assigned_to if hasattr(fault, 'assigned_to') else None,
        "assigned_at": fault.assigned_at.isoformat() if hasattr(fault, 'assigned_at') and fault.assigned_at else None,
        "accepted_at": fault.accepted_at.isoformat() if hasattr(fault, 'accepted_at') and fault.accepted_at else None,
        "diagnosing_at": fault.diagnosing_at.isoformat() if hasattr(fault, 'diagnosing_at') and fault.diagnosing_at else None,
        "transferred_at": fault.transferred_at.isoformat() if hasattr(fault, 'transferred_at') and fault.transferred_at else None,
        "resolved_at": fault.resolved_at.isoformat() if hasattr(fault, 'resolved_at') and fault.resolved_at else None,
        "closed_at": fault.closed_at.isoformat() if hasattr(fault, 'closed_at') and fault.closed_at else None,
        "diagnosis_text": fault.diagnosis_text if hasattr(fault, 'diagnosis_text') else None,
        "diagnosis_result": fault.diagnosis_result if hasattr(fault, 'diagnosis_result') else None,
        "maintenance_id": fault.maintenance_id,
        "maintenance": maintenance,
        "auto_created_maintenance": fault.auto_created_maintenance if hasattr(fault, 'auto_created_maintenance') else False,
        "source_type": fault.source_type,
        "source_key": fault.source_key,
        "source_event": fault.source_event,
        "if_index": fault.if_index,
        "if_name": fault.if_name,
        "peer_device_id": fault.peer_device_id,
        "peer_if_name": fault.peer_if_name,
        "event_count": fault.event_count or 1,
        "last_event_at": fault.last_event_at.isoformat() if fault.last_event_at else None,
        "recommendation": fault.recommendation,
        "assigned_email": fault.assigned_email,
        "review_required": bool(fault.review_required) if fault.review_required is not None else False,
        "reviewed_at": fault.reviewed_at.isoformat() if fault.reviewed_at else None,
        "reviewed_by": fault.reviewed_by,
        "false_positive": bool(fault.false_positive) if fault.false_positive is not None else False,
        "ai_analysis_result": json.loads(fault.ai_analysis_result) if fault.ai_analysis_result else None,
        "ai_root_cause": fault.ai_root_cause,
        "ai_recommendation": fault.ai_recommendation,
        "ai_confidence": float(fault.ai_confidence) if fault.ai_confidence else None,
        "incident_type": fault.incident_type if hasattr(fault, 'incident_type') else None,
        "ai_history": ai_history,
        "fault_time": fault.fault_time.isoformat() if fault.fault_time else None,
        "created_at": fault.created_at.isoformat(),
        "updated_at": fault.updated_at.isoformat() if fault.updated_at else None
    }


@router.post("")
async def create_fault(
    request: CreateFaultRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: None = Depends(require_fault_write),
    principal: Principal = Depends(get_current_principal),
):
    """
    创建故障记录（Incident）

    创建后自动触发：
    - 工作流检查（是否需要自动创建维修单）
    - AI分析（如果配置了自动分析）
    - 如果指定了负责人，自动进入assigned状态
    """
    # 获取设备信息
    device = db.query(Device).filter(Device.id == request.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")

    # 自动生成故障单号
    fault_no = f"INC-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

    # 确定故障时间
    fault_time = request.fault_time or datetime.utcnow()

    # 确定初始状态
    initial_status = "open"
    assigned_at = None
    if request.assigned_to:
        initial_status = "assigned"
        assigned_at = datetime.utcnow()

    # 创建故障记录
    fault = FaultRecord(
        fault_no=fault_no,
        device_id=request.device_id,
        device_name=device.name,
        severity=request.severity,
        status=initial_status,
        description=request.description,
        impact=request.impact,
        reporter=_actor_username(principal),
        fault_time=fault_time,
        fault_type=request.fault_type,
        assigned_to=request.assigned_to,
        assigned_at=assigned_at
    )

    db.add(fault)
    db.commit()
    db.refresh(fault)

    # 触发工作流（后台执行）
    background_tasks.add_task(
        trigger_fault_workflow,
        fault.id,
        request.severity,
        principal.username,
        principal.user_id,
    )

    # 严重/重要故障：后台触发 AI 预判（仅在已配置 AI 时生效）
    if request.severity in ("critical", "major"):
        background_tasks.add_task(trigger_fault_ai_prediagnosis, fault.id)

    # 如果有负责人，触发通知（后台执行）
    if request.assigned_to:
        background_tasks.add_task(
            send_fault_assigned_notification,
            fault.id,
            request.assigned_to
        )

    # 清除Dashboard缓存
    from app.shared.cache import cache
    cache.invalidate_prefix("dashboard:")

    return {
        "id": fault.id,
        "fault_no": fault_no,
        "device_name": device.name,
        "severity": request.severity,
        "message": "故障记录创建成功，已触发自动化流程"
    }


@router.put("/{fault_id}")
async def update_fault(
    fault_id: int,
    request: UpdateFaultRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_fault_write)
):
    """更新故障记录"""
    fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()

    if not fault:
        raise HTTPException(status_code=404, detail="故障记录不存在")

    updates = request.dict(exclude_none=True)
    for key, value in updates.items():
        if hasattr(fault, key):
            setattr(fault, key, value)

    db.commit()
    db.refresh(fault)

    return {
        "id": fault.id,
        "fault_no": fault.fault_no,
        "message": "更新成功"
    }


@router.delete("/{fault_id}")
async def delete_fault(
    fault_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_fault_delete),
):
    """删除故障记录"""
    fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()

    if not fault:
        raise HTTPException(status_code=404, detail="故障记录不存在")

    # 检查是否已关联维修单
    if fault.maintenance_id:
        raise HTTPException(
            status_code=400,
            detail="该故障已关联维修单，不能删除"
        )

    db.delete(fault)
    db.commit()

    return {"message": "删除成功"}


# ===== AI Analysis =====

@router.post("/{fault_id}/analyze")
async def analyze_fault(
    fault_id: int,
    request: AnalyzeFaultRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_fault_analyze)
):
    """
    AI分析故障（使用 ADK Agent）

    返回：
    - 故障类型判断
    - 根因分析
    - 是否需要维修建议
    - 处理建议
    """
    fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()
    if not fault:
        raise HTTPException(status_code=404, detail="故障记录不存在")

    device_name = fault.device.name if fault.device else fault.device_name or "Unknown"

    if not ADK_AVAILABLE:
        raise HTTPException(status_code=503, detail="AI 分析服务未启用，请先安装 AI 依赖（pip install -r requirements-ai.txt）")

    # 使用 ADK Agent 执行分析
    result = await adk_runner.run_agent(
        agent=fault_analysis_agent,
        user_id="faults_api",
        message=f"请分析故障 ID={fault_id}，设备名称={device_name}，故障描述={fault.description}",
        analysis_type="fault",
        target_type="fault",
        target_id=fault_id,
        db=db
    )

    if not result.get('success'):
        return {
            "success": False,
            "error": result.get('error'),
            "message": "AI分析失败"
        }

    # 解析结果
    analysis_result = adk_runner.parse_json_response(result.get('response', '')) or {}

    # 根据AI建议自动创建维修单
    if request.auto_create_maintenance:
        need_repair = analysis_result.get('need_repair')

        if need_repair == True or need_repair == 'repair':
            maintenance = MaintenanceRecord(
                maint_no=f"MAINT-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}",
                device_id=fault.device_id,
                device_name=fault.device_name,
                maint_type='corrective',
                title=f"AI推荐维修: {fault.description[:50]}",
                problem_description=fault.description,
                status='pending',
                fault_id=fault.id,
                auto_created=True,
                ai_recommended=True
            )
            try:
                maintenance, created = create_fault_maintenance_once(
                    db,
                    fault,
                    maintenance,
                    fault_updates={
                        FaultRecord.auto_created_maintenance: True,
                    },
                )
            except FaultMaintenanceConflictError as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc

            result['created_maintenance_id'] = maintenance.id
            result['created_maintenance_no'] = maintenance.maint_no
            result['maintenance_reused'] = not created

    return result


@router.get("/{fault_id}/root-cause")
async def get_root_cause(
    fault_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_fault_read),
):
    """获取故障根因分析"""
    fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()

    if not fault:
        raise HTTPException(status_code=404, detail="故障记录不存在")

    if fault.ai_root_cause:
        return {
            "fault_id": fault_id,
            "has_analysis": True,
            "root_cause": fault.ai_root_cause,
            "confidence": float(fault.ai_confidence) if fault.ai_confidence else None,
            "full_analysis": json.loads(fault.ai_analysis_result) if fault.ai_analysis_result else None
        }

    # 如果没有AI分析，可以触发一次分析
    return {
        "fault_id": fault_id,
        "has_analysis": False,
        "message": "该故障尚未进行根因分析，请先执行AI分析"
    }


@router.post("/{fault_id}/ai-pre-diagnose")
async def ai_pre_diagnose(
    fault_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_fault_analyze),
):
    """一键 AI 预判故障原因（轻量、可降级）。

    把设备、故障、近期温度与故障历史一键投喂给已配置的模型，返回预判根因和
    处理建议。未配置 AI 或调用失败时返回 available=false，不影响故障流程。
    """
    from app.services.ai_triage import pre_diagnose_fault

    fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()
    if not fault:
        raise HTTPException(status_code=404, detail="故障记录不存在")

    diagnosis = await pre_diagnose_fault(db, fault)
    if diagnosis.get("available") and diagnosis.get("probable_cause"):
        fault.ai_root_cause = diagnosis["probable_cause"]
        db.commit()

    return {"fault_id": fault_id, **diagnosis}


@router.post("/{fault_id}/auto-create-maintenance")
async def auto_create_maintenance(
    fault_id: int,
    maint_type: str = "corrective",
    priority: str = "normal",
    db: Session = Depends(get_db),
    _: None = Depends(require_fault_analyze)
):
    """
    根据AI建议自动创建维修单

    Args:
        fault_id: 故障ID
        maint_type: 维修类型（corrective/emergency）
        priority: 优先级（urgent/high/normal/low）
    """
    fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()

    if not fault:
        raise HTTPException(status_code=404, detail="故障记录不存在")

    existing_maintenance = find_fault_maintenance(db, fault)

    # 检查故障状态
    if not existing_maintenance and fault.status == "closed":
        raise HTTPException(
            status_code=400,
            detail="已关闭的故障不能创建维修单"
        )

    # 创建维修单
    maint_no = f"MAINT-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

    maintenance = MaintenanceRecord(
        maint_no=maint_no,
        device_id=fault.device_id,
        device_name=fault.device_name,
        maint_type=maint_type,
        title=f"故障维修: {fault.description[:50]}",
        problem_description=f"关联故障: {fault.fault_no}\n\n{fault.description}",
        status='pending',
        priority=priority,
        fault_id=fault.id,
        auto_created=True
    )

    try:
        maintenance, created = create_fault_maintenance_once(
            db,
            fault,
            maintenance,
            fault_updates={
                FaultRecord.auto_created_maintenance: True,
            },
        )
    except FaultMaintenanceConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    # v1.1：自动建单补指派（dispatch_rule → 运维组值班人/组名）+ 通知 admin + 运维组
    if created:
        from app.features.groups.service import resolve_fault_targets
        device = db.query(Device).filter(Device.id == fault.device_id).first()
        assigned_to, usernames, emails, group = resolve_fault_targets(
            db,
            source_type=fault.source_type,
            device_type=(device.device_type if device else None),
            severity=fault.severity,
        )
        maintenance.current_owner = assigned_to
        maintenance.group_id = group.id if group else None
        db.commit()
        from app.services.notification_service import get_notification_service
        get_notification_service().dispatch(
            db,
            event_type="maintenance_auto_created",
            title=f"新维修单: {maintenance.maint_no}",
            content=f"设备 {maintenance.device_name} 已自动创建维修单（来源故障 {fault.fault_no}），请安排处理。",
            recipients=usernames,
            emails=emails,
            reference_type="maintenance",
            reference_id=maintenance.id,
            maintenance_id=maintenance.id,
        )

    return {
        "success": True,
        "maintenance_id": maintenance.id,
        "maint_no": maintenance.maint_no,
        "fault_id": fault_id,
        "message": "维修单创建成功" if created else "维修单已存在"
    }


# ===== Status Management =====

@router.patch("/{fault_id}/status")
async def update_fault_status(
    fault_id: int,
    status: str,
    resolution: Optional[str] = None,
    db: Session = Depends(get_db),
    _: None = Depends(require_fault_write)
):
    """
    更新故障状态

    状态流转：open → investigating → resolved → closed
    """
    valid_statuses = ['open', 'investigating', 'resolved', 'closed']

    if status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"无效状态，有效状态: {valid_statuses}"
        )

    fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()

    if not fault:
        raise HTTPException(status_code=404, detail="故障记录不存在")

    fault.status = status

    if resolution:
        fault.resolution = resolution

    # 如果关闭，记录关闭时间
    if status == 'closed':
        # 计算故障持续时间
        if fault.fault_time:
            downtime = (datetime.utcnow() - fault.fault_time).total_seconds() / 60
            fault.downtime_minutes = int(downtime)

    db.commit()

    return {
        "id": fault_id,
        "status": status,
        "message": "状态更新成功"
    }


@router.post("/{fault_id}/escalate")
async def escalate_fault(
    fault_id: int,
    new_severity: str,
    reason: str,
    db: Session = Depends(get_db),
    _: None = Depends(require_fault_write),
    principal: Principal = Depends(get_current_principal),
):
    """
    升级故障严重程度

    Args:
        fault_id: 故障ID
        new_severity: 新严重程度（需比当前更高）
        reason: 升级原因
    """
    severity_levels = ['minor', 'warning', 'major', 'critical']
    severity_order = {s: i for i, s in enumerate(severity_levels)}

    fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()

    if not fault:
        raise HTTPException(status_code=404, detail="故障记录不存在")

    # 检查是否升级
    current_level = severity_order.get(fault.severity, 0)
    new_level = severity_order.get(new_severity, 0)

    if new_level <= current_level:
        raise HTTPException(
            status_code=400,
            detail="只能升级到更高严重程度"
        )

    # 更新严重程度
    fault.severity = new_severity

    # 添加升级记录到描述
    escalation_note = f"\n\n[升级记录 {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}] {fault.severity} → {new_severity}, 原因: {reason}"
    fault.description = fault.description + escalation_note

    db.commit()

    # 触发工作流（可能需要创建紧急维修单）
    await _run_fault_workflow(
        db,
        fault_id,
        principal.username,
        principal.user_id,
    )

    return {
        "id": fault_id,
        "previous_severity": fault.severity,
        "new_severity": new_severity,
        "message": "故障已升级"
    }


# ===== Convert to Maintenance =====

@router.post("/{fault_id}/convert-to-maintenance")
async def convert_to_maintenance(
    fault_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_fault_write),
):
    """手动将故障转换为维修单"""
    fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()

    if not fault:
        raise HTTPException(status_code=404, detail="故障记录不存在")

    existing_maintenance = find_fault_maintenance(db, fault)

    if not existing_maintenance and fault.status == "closed":
        raise HTTPException(status_code=400, detail="已关闭的故障不能转维修")

    maint_no = f"MAINT-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

    maintenance = MaintenanceRecord(
        maint_no=maint_no,
        device_id=fault.device_id,
        device_name=fault.device_name,
        maint_type="corrective",
        title=f"故障维修: {fault.description[:50]}",
        problem_description=f"由故障单 {fault.fault_no} 转换\n\n故障描述：{fault.description}",
        fault_id=fault.id,
        status='pending'
    )

    try:
        maintenance, created = create_fault_maintenance_once(
            db,
            fault,
            maintenance,
        )
    except FaultMaintenanceConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return {
        "maintenance_id": maintenance.id,
        "maint_no": maintenance.maint_no,
        "message": "维修单创建成功" if created else "维修单已存在"
    }


@router.get("/{fault_id}/maintenance")
async def get_fault_maintenance(
    fault_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_fault_read),
):
    """获取故障关联的维修单详情"""
    fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()

    if not fault:
        raise HTTPException(status_code=404, detail="故障记录不存在")

    if not fault.maintenance_id:
        return {"maintenance": None}

    maintenance = db.query(MaintenanceRecord).filter(
        MaintenanceRecord.id == fault.maintenance_id
    ).first()

    if not maintenance:
        return {"maintenance": None}

    return {
        "maintenance": {
            "id": maintenance.id,
            "maint_no": maintenance.maint_no,
            "maint_type": maintenance.maint_type,
            "status": maintenance.status,
            "parts_replaced": maintenance.parts_replaced,
            "parts_cost": float(maintenance.parts_cost) if maintenance.parts_cost else 0,
            "labor_hours": float(maintenance.labor_hours) if maintenance.labor_hours else 0,
            "labor_cost": float(maintenance.labor_cost) if maintenance.labor_cost else 0,
            "vendor": maintenance.vendor,
            "description": maintenance.description,
            "maint_time": maintenance.maint_time.isoformat() if maintenance.maint_time else None,
            "created_at": maintenance.created_at.isoformat()
        }
    }


# ===== Dashboard =====

@router.get("/incidents/dashboard")
async def get_incidents_dashboard(
    db: Session = Depends(get_db),
    _: None = Depends(require_fault_read),
):
    """
    Incident Center Dashboard统计

    Returns:
        - 各状态故障数量
        - 各严重程度故障数量
        - AI分析覆盖率
        - 自动创建维修单统计
        - 平均响应时间
    """
    # 总故障数
    total_faults = db.query(FaultRecord).count()

    # 活跃故障（未关闭）
    active_faults = db.query(FaultRecord).filter(
        FaultRecord.status.in_(FAULT_ACTIVE_STATUSES)
    ).count()

    # 各状态统计
    status_counts = {}
    for status in FAULT_STATUS_LABELS:
        count = db.query(FaultRecord).filter(FaultRecord.status == status).count()
        status_counts[status] = count

    # 各严重程度统计（活跃故障）
    severity_counts = {}
    for severity in ['critical', 'major', 'warning', 'minor']:
        count = db.query(FaultRecord).filter(
            FaultRecord.severity == severity,
            FaultRecord.status.in_(FAULT_ACTIVE_STATUSES)
        ).count()
        severity_counts[severity] = count

    # AI分析覆盖率
    faults_with_ai = db.query(FaultRecord).filter(
        FaultRecord.ai_analysis_result.isnot(None)
    ).count()
    ai_coverage = round(faults_with_ai / total_faults * 100 if total_faults > 0 else 0, 1)

    # 自动创建维修单统计
    auto_maintenance_count = db.query(FaultRecord).filter(
        FaultRecord.maintenance_id.isnot(None)
    ).count()

    # 最近的活跃故障
    recent_faults = db.query(FaultRecord).filter(
        FaultRecord.status.in_(FAULT_ACTIVE_STATUSES)
    ).order_by(FaultRecord.created_at.desc()).limit(10).all()

    recent_incidents = [
        {
            "id": f.id,
            "fault_no": f.fault_no,
            "device_name": f.device_name,
            "severity": f.severity,
            "status": f.status,
            "description": f.description[:50] + "..." if f.description and len(f.description) > 50 else f.description,
            "created_at": f.created_at.isoformat(),
            "has_ai": f.ai_analysis_result is not None
        }
        for f in recent_faults
    ]

    return {
        "total_faults": total_faults,
        "active_faults": active_faults,
        "status_distribution": status_counts,
        "severity_distribution": severity_counts,
        "ai_analysis_coverage": ai_coverage,
        "auto_maintenance_count": auto_maintenance_count,
        "recent_incidents": recent_incidents,
        "last_updated": datetime.utcnow().isoformat()
    }


# ===== Background Tasks =====

async def trigger_fault_workflow(
    fault_id: int,
    severity: str,
    actor: str = "system",
    actor_user_id: Optional[int] = None,
):
    """后台触发故障工作流"""
    from app.shared.database import get_db_manager

    db_manager = get_db_manager()
    db = db_manager.get_session()

    try:
        await _run_fault_workflow(db, fault_id, actor, actor_user_id)
    except Exception:
        logger.exception("Workflow trigger failed for fault {}", fault_id)
    finally:
        db.close()


async def _run_fault_workflow(
    db: Session,
    fault_id: int,
    actor: str,
    actor_user_id: Optional[int],
):
    from app.services.workflow import (
        ACTION_REQUIRED_PERMISSIONS,
        WorkflowPermissionError,
    )
    from app.shared.dependencies import get_user_all_permissions

    action_authorizer = None
    if actor_user_id is not None:
        permissions = set(get_user_all_permissions(actor_user_id, db))

        def action_authorizer(action_type: str) -> bool:
            required = ACTION_REQUIRED_PERMISSIONS.get(action_type)
            return required is None or "admin:all" in permissions or required in permissions

    executor = WorkflowExecutor(db)
    try:
        return await executor.trigger_fault_created(
            fault_id,
            actor=actor,
            action_authorizer=action_authorizer,
        )
    except WorkflowPermissionError as exc:
        logger.warning(
            "Skipped fault workflow actions for user {} missing permissions: {}",
            actor,
            ", ".join(exc.missing_permissions),
        )
        return None


async def trigger_fault_ai_prediagnosis(fault_id: int):
    """后台 AI 故障预判：把设备/故障/温度/历史投给已配置的模型，写入 ai_root_cause。

    仅在配置了 AI 时执行；任何失败都不影响故障流程。
    """
    from app.shared.database import get_db_manager
    from app.services.ai_triage import ai_available, pre_diagnose_fault

    if not ai_available():
        return

    db_manager = get_db_manager()
    db = db_manager.get_session()
    try:
        fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()
        if not fault:
            return
        result = await pre_diagnose_fault(db, fault)
        if result.get("available") and result.get("probable_cause"):
            fault.ai_root_cause = result["probable_cause"]
            db.commit()
    except Exception:
        logger.exception("AI pre-diagnosis failed for fault {}", fault_id)
    finally:
        db.close()


async def send_fault_assigned_notification(fault_id: int, assigned_to: str):
    """后台发送故障指派通知（站内 + 邮件 + IM，经 dispatch 统一出口，落通知日志）"""
    from app.shared.database import get_db_manager
    from app.services.notification_service import get_notification_service

    db_manager = get_db_manager()
    db = db_manager.get_session()

    try:
        fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()
        if fault and assigned_to:
            # 只发给被指派的人（真实账号）
            get_notification_service().dispatch(
                db,
                event_type="fault_assigned",
                title=f"新故障指派: {fault.fault_no}",
                content=f"设备 {fault.device_name} 的故障已指派给您，请尽快处理。",
                recipients=[assigned_to],
                reference_type="fault",
                reference_id=fault_id,
                fault_id=fault_id,
            )
    except Exception:
        logger.exception("Assignment notification failed for fault {}", fault_id)
    finally:
        db.close()


async def send_maintenance_assigned_notification(maintenance_id: int, assigned_to: str):
    """后台发送维修单指派通知（站内 + 邮件 + IM，经 dispatch 统一出口，落通知日志）"""
    from app.shared.database import get_db_manager
    from app.services.notification_service import get_notification_service

    db_manager = get_db_manager()
    db = db_manager.get_session()

    try:
        maintenance = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == maintenance_id).first()
        if maintenance and assigned_to:
            # 只发给被指派的人（真实账号）
            get_notification_service().dispatch(
                db,
                event_type="maintenance_assigned",
                title=f"新维修单指派: {maintenance.maint_no}",
                content=f"设备 {maintenance.device_name} 的维修任务已指派给您，故障来源: {maintenance.fault_id}。",
                recipients=[assigned_to],
                reference_type="maintenance",
                reference_id=maintenance_id,
                maintenance_id=maintenance_id,
            )
    except Exception:
        logger.exception(
            "Assignment notification failed for maintenance {}",
            maintenance_id,
        )
    finally:
        db.close()


async def send_maintenance_completed_notification(fault_id: int, maintenance_id: int):
    """后台发送维修完成通知（通知故障负责人确认解决，经 dispatch 统一出口）"""
    from app.shared.database import get_db_manager
    from app.services.notification_service import get_notification_service

    db_manager = get_db_manager()
    db = db_manager.get_session()

    try:
        fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()
        maintenance = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == maintenance_id).first()
        if fault and maintenance:
            recipients = [fault.assigned_to] if fault.assigned_to else ["admin"]
            get_notification_service().dispatch(
                db,
                event_type="maintenance_completed",
                title=f"维修完成待确认: {maintenance.maint_no}",
                content=f"设备 {maintenance.device_name} 的维修已完成，请确认故障是否解决。",
                recipients=recipients,
                reference_type="fault",
                reference_id=fault_id,
                fault_id=fault_id,
                maintenance_id=maintenance_id,
            )
    except Exception:
        logger.exception(
            "Completion notification failed for maintenance {}",
            maintenance_id,
        )
    finally:
        db.close()


# ===== 状态流转API =====

@router.post("/{fault_id}/assign")
async def assign_fault(
    fault_id: int,
    request: AssignFaultRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: None = Depends(require_fault_write)
):
    """指派故障给负责人"""
    fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()
    if not fault:
        raise HTTPException(status_code=404, detail="故障记录不存在")

    # 验证状态流转
    if fault.status not in FAULT_VALID_TRANSITIONS:
        raise HTTPException(status_code=400, detail=f"当前状态 {fault.status} 不允许指派")

    if 'assigned' not in FAULT_VALID_TRANSITIONS.get(fault.status, []):
        raise HTTPException(status_code=400, detail=f"不能从 {fault.status} 转换到 assigned")

    # 更新故障
    fault.assigned_to = request.assigned_to
    fault.assigned_at = datetime.utcnow()
    fault.status = "assigned"
    fault.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(fault)

    # 发送通知
    background_tasks.add_task(
        send_fault_assigned_notification,
        fault_id,
        request.assigned_to
    )

    return {
        "id": fault_id,
        "status": fault.status,
        "status_label": FAULT_STATUS_LABELS.get(fault.status),
        "assigned_to": fault.assigned_to,
        "assigned_at": fault.assigned_at.isoformat(),
        "message": f"故障已指派给 {request.assigned_to}"
    }


@router.post("/{fault_id}/accept")
async def accept_fault(
    fault_id: int,
    request: AcceptFaultRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_fault_write)
):
    """接收故障（负责人确认）"""
    fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()
    if not fault:
        raise HTTPException(status_code=404, detail="故障记录不存在")

    if fault.status != 'assigned':
        raise HTTPException(status_code=400, detail="只有已指派的故障才能接收")

    fault.status = "accepted"
    fault.accepted_at = datetime.utcnow()
    fault.updated_at = datetime.utcnow()

    db.commit()

    return {
        "id": fault_id,
        "status": fault.status,
        "status_label": FAULT_STATUS_LABELS.get(fault.status),
        "accepted_at": fault.accepted_at.isoformat(),
        "message": "故障已接收"
    }


@router.post("/{fault_id}/review")
async def review_fault(
    fault_id: int,
    request: ReviewFaultRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_fault_write),
    principal: Principal = Depends(get_current_principal),
):
    """管理员复核监控自动创建的故障（大屏/邮件复核入口）"""
    fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()
    if not fault:
        raise HTTPException(status_code=404, detail="故障记录不存在")

    fault.review_required = False
    fault.reviewed_at = datetime.utcnow()
    reviewer = _actor_username(principal)
    fault.reviewed_by = reviewer
    fault.false_positive = request.false_positive
    fault.updated_at = datetime.utcnow()

    note = request.notes or ("标记为误报" if request.false_positive else "管理员已复核确认")
    if fault.diagnosis_text:
        fault.diagnosis_text += f"\n\n--- {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} ---\n{note}"
    else:
        fault.diagnosis_text = note

    if request.false_positive:
        fault.status = "closed"
        fault.closed_at = datetime.utcnow()
        fault.resolution = note
    elif fault.status == "open":
        fault.status = "assigned"
        fault.assigned_to = fault.assigned_to or reviewer
        fault.assigned_at = fault.assigned_at or datetime.utcnow()

    db.commit()

    return {
        "id": fault_id,
        "fault_no": fault.fault_no,
        "status": fault.status,
        "status_label": FAULT_STATUS_LABELS.get(fault.status, fault.status),
        "review_required": bool(fault.review_required),
        "reviewed_by": fault.reviewed_by,
        "reviewed_at": fault.reviewed_at.isoformat() if fault.reviewed_at else None,
        "false_positive": bool(fault.false_positive),
        "message": "故障已标记为误报并关闭" if request.false_positive else "故障已复核确认",
    }


@router.post("/{fault_id}/diagnose")
async def diagnose_fault(
    fault_id: int,
    request: DiagnoseFaultRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_fault_write)
):
    """开始诊断并填写诊断信息

    新流程：assigned 状态可直接开始诊断，无需先接收
    """
    fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()
    if not fault:
        raise HTTPException(status_code=404, detail="故障记录不存在")

    # 新流程：允许 assigned 或 diagnosing 状态直接诊断
    if fault.status not in ['assigned', 'diagnosing']:
        raise HTTPException(status_code=400, detail="只有已指派或诊断中的故障才能进行诊断")

    # 如果是第一次诊断（从 assigned 开始），更新状态为 diagnosing
    if fault.status == 'assigned':
        fault.status = "diagnosing"
        fault.diagnosing_at = datetime.utcnow()

    # 更新诊断信息
    if request.fault_type:
        fault.fault_type = request.fault_type
    if request.diagnosis_text:
        fault.diagnosis_text = request.diagnosis_text
    if request.diagnosis_result:
        fault.diagnosis_result = request.diagnosis_result

    fault.updated_at = datetime.utcnow()

    db.commit()

    return {
        "id": fault_id,
        "status": fault.status,
        "status_label": FAULT_STATUS_LABELS.get(fault.status),
        "fault_type": fault.fault_type,
        "diagnosis_text": fault.diagnosis_text,
        "diagnosis_result": fault.diagnosis_result,
        "diagnosis_result_label": FAULT_DIAGNOSIS_RESULTS.get(fault.diagnosis_result),
        "message": "诊断信息已保存"
    }


@router.post("/{fault_id}/work-note")
async def add_fault_work_note(
    fault_id: int,
    request: WorkNoteRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_fault_write)
):
    """添加工作日志（在故障未关闭前都可以添加）

    用于记录故障诊断/处理过程中的工作进展
    """
    fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()
    if not fault:
        raise HTTPException(status_code=404, detail="故障记录不存在")

    # 不允许在已关闭状态添加日志
    if fault.status == 'closed':
        raise HTTPException(status_code=400, detail="已关闭的故障不能添加日志")

    note_text = request.note

    # 追加到诊断内容（用换行分隔多条日志）
    if fault.diagnosis_text:
        fault.diagnosis_text = f"{fault.diagnosis_text}\n\n--- {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} ---\n{note_text}"
    else:
        fault.diagnosis_text = note_text

    fault.updated_at = datetime.utcnow()
    db.commit()

    return {
        "id": fault_id,
        "diagnosis_text": fault.diagnosis_text,
        "message": "工作日志已添加"
    }


@router.post("/{fault_id}/transfer-to-maintenance")
async def transfer_to_maintenance(
    fault_id: int,
    request: TransferToMaintenanceRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: None = Depends(require_fault_write),
    principal: Principal = Depends(get_current_principal),
):
    """转维修（创建维修单）

    维修负责人默认继承诊断负责人，可通过 maintenance_owner 参数指定其他负责人
    """
    fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()
    if not fault:
        raise HTTPException(status_code=404, detail="故障记录不存在")

    existing_maintenance = find_fault_maintenance(db, fault)
    if existing_maintenance:
        if fault.maintenance_id != existing_maintenance.id:
            fault.maintenance_id = existing_maintenance.id
            db.commit()
        return {
            "id": fault_id,
            "status": fault.status,
            "status_label": FAULT_STATUS_LABELS.get(fault.status),
            "maintenance_id": existing_maintenance.id,
            "maint_no": existing_maintenance.maint_no,
            "maintenance_owner": existing_maintenance.current_owner,
            "message": f"维修单 {existing_maintenance.maint_no} 已存在"
        }

    if fault.status not in ['assigned', 'accepted', 'diagnosing']:
        raise HTTPException(status_code=400, detail="只有已指派/已确认/诊断中的故障才能转维修")

    # 确定维修负责人：默认继承诊断负责人，如果指定了 maintenance_owner 则覆盖
    maintenance_owner = request.maintenance_owner or fault.assigned_to

    # 创建维修单 - 状态直接设为 repairing（跳过诊断，故障已诊断过）
    maint_no = f"MAINT-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
    maintenance_description = request.description or fault.description
    if request.estimated_parts:
        maintenance_description = (
            f"{maintenance_description}\n\n预估备件: {request.estimated_parts}"
        )

    maintenance = MaintenanceRecord(
        maint_no=maint_no,
        device_id=fault.device_id,
        device_name=fault.device_name,
        fault_id=fault_id,
        maint_type=request.maintenance_type,
        description=maintenance_description,
        status="repairing",  # 直接进入维修状态（故障已诊断）
        priority=request.priority,
        current_owner=maintenance_owner,
        operator=_actor_username(principal),
        repairing_at=datetime.utcnow()  # 设置维修开始时间
    )

    # 复制故障的诊断内容到维修单，方便维修参考
    if request.diagnosis_text or fault.diagnosis_text:
        maintenance.diagnosis_text = request.diagnosis_text or fault.diagnosis_text
    if fault.diagnosis_result:
        maintenance.diagnosis_result = fault.diagnosis_result

    transferred_at = datetime.utcnow()
    try:
        maintenance, created = create_fault_maintenance_once(
            db,
            fault,
            maintenance,
            fault_updates={
                FaultRecord.status: "transferred",
                FaultRecord.transferred_at: transferred_at,
                FaultRecord.updated_at: transferred_at,
            },
            claim_filters=(
                FaultRecord.status.in_(['assigned', 'accepted', 'diagnosing']),
            ),
        )
    except FaultMaintenanceConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail="故障状态已变化，请刷新后重试",
        ) from exc

    # 发送通知给维修负责人
    if created and maintenance_owner:
        background_tasks.add_task(
            send_maintenance_assigned_notification,
            maintenance.id,
            maintenance_owner
        )

    return {
        "id": fault_id,
        "status": fault.status,
        "status_label": FAULT_STATUS_LABELS.get(fault.status),
        "maintenance_id": maintenance.id,
        "maint_no": maintenance.maint_no,
        "maintenance_owner": maintenance.current_owner,
        "message": (
            f"已创建维修单 {maintenance.maint_no}，负责人: {maintenance.current_owner}"
            if created
            else f"维修单 {maintenance.maint_no} 已存在"
        )
    }


@router.post("/{fault_id}/resolve")
async def resolve_fault(
    fault_id: int,
    request: ResolveFaultRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_fault_write)
):
    """直接解决故障（技术问题，无需备件）"""
    fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()
    if not fault:
        raise HTTPException(status_code=404, detail="故障记录不存在")

    if fault.status not in ['diagnosing', 'resolving']:
        raise HTTPException(status_code=400, detail="只有诊断中或技术处理中的故障才能解决")

    fault.status = "resolved"
    fault.resolved_at = datetime.utcnow()
    fault.resolution = request.resolution
    fault.updated_at = datetime.utcnow()

    db.commit()

    return {
        "id": fault_id,
        "status": fault.status,
        "status_label": FAULT_STATUS_LABELS.get(fault.status),
        "resolution": fault.resolution,
        "resolved_at": fault.resolved_at.isoformat(),
        "message": "故障已解决"
    }


@router.post("/{fault_id}/close")
async def close_fault(
    fault_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_fault_write),
):
    """关闭故障"""
    fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()
    if not fault:
        raise HTTPException(status_code=404, detail="故障记录不存在")

    if fault.status not in ['resolved', 'transferred']:
        raise HTTPException(status_code=400, detail="只有已解决或已转维修的故障才能关闭")

    # 如果是转维修状态，检查维修是否完成
    if fault.status == 'transferred' and fault.maintenance_id:
        maintenance = db.query(MaintenanceRecord).filter(
            MaintenanceRecord.id == fault.maintenance_id
        ).first()
        if maintenance and maintenance.status != 'completed':
            raise HTTPException(status_code=400, detail="关联的维修单尚未完成")

    fault.status = "closed"
    fault.closed_at = datetime.utcnow()
    fault.updated_at = datetime.utcnow()

    db.commit()

    return {
        "id": fault_id,
        "status": fault.status,
        "status_label": FAULT_STATUS_LABELS.get(fault.status),
        "closed_at": fault.closed_at.isoformat(),
        "message": "故障已关闭"
    }


@router.get("/{fault_id}/transitions")
async def get_fault_transitions(
    fault_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_fault_read),
):
    """获取故障可用的状态流转选项"""
    fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()
    if not fault:
        raise HTTPException(status_code=404, detail="故障记录不存在")

    valid_transitions = FAULT_VALID_TRANSITIONS.get(fault.status, [])
    transition_options = []

    for status in valid_transitions:
        transition_options.append({
            "status": status,
            "label": FAULT_STATUS_LABELS.get(status),
            "color": FAULT_STATUS_COLORS.get(status)
        })

    return {
        "current_status": fault.status,
        "current_status_label": FAULT_STATUS_LABELS.get(fault.status),
        "valid_transitions": transition_options
    }