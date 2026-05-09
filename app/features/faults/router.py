"""Incident Center - 故障管理路由

企业级Incident Center风格：
- AI辅助故障分析
- 根因分析支持
- 自动创建维修单决策
- 故障生命周期管理
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel
import uuid
import json

from app.shared.database import get_db
from app.shared.models import FaultRecord, MaintenanceRecord, Device, AIAnalysisRecord
from app.services.ai_manager import analyze_fault as ai_analyze_fault
from app.services.workflow.executor import WorkflowExecutor

router = APIRouter(prefix="/api/faults", tags=["faults"])


# ===== Request Models =====

class CreateFaultRequest(BaseModel):
    """创建故障请求"""
    device_id: int
    severity: str = "minor"  # minor/warning/major/critical
    description: str
    impact: Optional[str] = None
    reporter: Optional[str] = None
    fault_time: Optional[datetime] = None


class UpdateFaultRequest(BaseModel):
    """更新故障请求"""
    severity: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    resolution: Optional[str] = None
    impact: Optional[str] = None


class AnalyzeFaultRequest(BaseModel):
    """AI分析故障请求"""
    auto_create_maintenance: bool = False  # 是否根据AI建议自动创建维修单


# ===== Basic CRUD =====

@router.get("")
async def list_faults(
    device_id: Optional[int] = None,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    has_ai_analysis: Optional[bool] = None,
    need_repair: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
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
    faults = query.order_by(
        # 严重程度排序：critical > major > warning > minor
        FaultRecord.severity.desc()
    ).order_by(
        FaultRecord.created_at.desc()
    ).offset(skip).limit(limit).all()

    items = []
    for f in faults:
        device = db.query(Device).filter(Device.id == f.device_id).first()

        items.append({
            "id": f.id,
            "fault_no": f.fault_no,
            "device_id": f.device_id,
            "device_name": f.device_name or (device.name if device else "Unknown"),
            "device_ip": device.ip if device else None,
            "device_health_score": device.health_score if device else None,
            "severity": f.severity,
            "status": f.status,
            "downtime_minutes": f.downtime_minutes,
            "description": f.description,
            "impact": f.impact,
            "reporter": f.reporter,
            "maintenance_id": f.maintenance_id,
            "auto_created_maintenance": f.auto_created_maintenance or False,
            "has_ai_analysis": f.ai_analysis_result is not None,
            "ai_recommendation": f.ai_recommendation,
            "ai_confidence": float(f.ai_confidence) if f.ai_confidence else None,
            "fault_time": f.fault_time.isoformat() if f.fault_time else None,
            "created_at": f.created_at.isoformat(),
            "updated_at": f.updated_at.isoformat() if f.updated_at else None
        })

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": items
    }


@router.get("/{fault_id}")
async def get_fault(fault_id: int, db: Session = Depends(get_db)):
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

    # 获取关联维修单
    maintenance = None
    if fault.maintenance_id:
        m = db.query(MaintenanceRecord).filter(
            MaintenanceRecord.id == fault.maintenance_id
        ).first()
        if m:
            maintenance = {
                "id": m.id,
                "maint_no": m.maint_no,
                "maint_type": m.maint_type,
                "status": m.status,
                "created_at": m.created_at.isoformat()
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
        "maintenance_id": fault.maintenance_id,
        "maintenance": maintenance,
        "auto_created_maintenance": fault.auto_created_maintenance if hasattr(fault, 'auto_created_maintenance') else False,
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
    db: Session = Depends(get_db)
):
    """
    创建故障记录（Incident）

    创建后自动触发：
    - 工作流检查（是否需要自动创建维修单）
    - AI分析（如果配置了自动分析）
    """
    # 获取设备信息
    device = db.query(Device).filter(Device.id == request.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")

    # 自动生成故障单号
    fault_no = f"FAULT-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

    # 确定故障时间
    fault_time = request.fault_time or datetime.utcnow()

    # 创建故障记录
    fault = FaultRecord(
        fault_no=fault_no,
        device_id=request.device_id,
        device_name=device.name,
        severity=request.severity,
        status="open",
        description=request.description,
        impact=request.impact,
        reporter=request.reporter,
        fault_time=fault_time
    )

    db.add(fault)
    db.commit()
    db.refresh(fault)

    # 触发工作流（后台执行）
    background_tasks.add_task(
        trigger_fault_workflow,
        fault.id,
        request.severity
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
    db: Session = Depends(get_db)
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
async def delete_fault(fault_id: int, db: Session = Depends(get_db)):
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
    db: Session = Depends(get_db)
):
    """
    AI分析故障

    返回：
    - 故障类型判断
    - 根因分析
    - 是否需要维修建议
    - 处理建议
    """
    fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()
    if not fault:
        raise HTTPException(status_code=404, detail="故障记录不存在")

    # 执行AI分析
    result = await ai_analyze_fault(fault_id, db)

    if not result.get('success'):
        return {
            "success": False,
            "error": result.get('error'),
            "message": "AI分析失败"
        }

    analysis_result = result.get('result', {})

    # 根据AI建议自动创建维修单
    if request.auto_create_maintenance:
        need_repair = analysis_result.get('need_repair')

        if need_repair == True or need_repair == 'repair':
            # 检查是否已有维修单
            if not fault.maintenance_id:
                # 创建维修单
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

                db.add(maintenance)
                fault.maintenance_id = maintenance.id
                fault.auto_created_maintenance = True

                db.commit()
                db.refresh(maintenance)

                result['created_maintenance_id'] = maintenance.id
                result['created_maintenance_no'] = maintenance.maint_no

    return result


@router.get("/{fault_id}/root-cause")
async def get_root_cause(fault_id: int, db: Session = Depends(get_db)):
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


@router.post("/{fault_id}/auto-create-maintenance")
async def auto_create_maintenance(
    fault_id: int,
    maint_type: str = "corrective",
    priority: str = "normal",
    db: Session = Depends(get_db)
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

    # 检查是否已有维修单
    if fault.maintenance_id:
        raise HTTPException(
            status_code=400,
            detail="该故障已关联维修单"
        )

    # 检查故障状态
    if fault.status == "closed":
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

    db.add(maintenance)
    fault.maintenance_id = maintenance.id

    db.commit()
    db.refresh(maintenance)

    return {
        "success": True,
        "maintenance_id": maintenance.id,
        "maint_no": maint_no,
        "fault_id": fault_id,
        "message": "维修单创建成功"
    }


# ===== Status Management =====

@router.patch("/{fault_id}/status")
async def update_fault_status(
    fault_id: int,
    status: str,
    resolution: Optional[str] = None,
    db: Session = Depends(get_db)
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
    db: Session = Depends(get_db)
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
    executor = WorkflowExecutor(db)
    await executor.trigger_fault_created(fault_id)

    return {
        "id": fault_id,
        "previous_severity": fault.severity,
        "new_severity": new_severity,
        "message": "故障已升级"
    }


# ===== Convert to Maintenance =====

@router.post("/{fault_id}/convert-to-maintenance")
async def convert_to_maintenance(fault_id: int, db: Session = Depends(get_db)):
    """手动将故障转换为维修单"""
    fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()

    if not fault:
        raise HTTPException(status_code=404, detail="故障记录不存在")

    if fault.maintenance_id:
        raise HTTPException(status_code=400, detail="该故障已关联维修单")

    if fault.status == "closed":
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

    db.add(maintenance)
    fault.maintenance_id = maintenance.id

    db.commit()
    db.refresh(maintenance)

    return {
        "maintenance_id": maintenance.id,
        "maint_no": maint_no,
        "message": "维修单创建成功"
    }


@router.get("/{fault_id}/maintenance")
async def get_fault_maintenance(fault_id: int, db: Session = Depends(get_db)):
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
async def get_incidents_dashboard(db: Session = Depends(get_db)):
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
        FaultRecord.status.in_(['open', 'investigating', 'resolved'])
    ).count()

    # 各状态统计
    status_counts = {}
    for status in ['open', 'investigating', 'resolved', 'closed']:
        count = db.query(FaultRecord).filter(FaultRecord.status == status).count()
        status_counts[status] = count

    # 各严重程度统计（活跃故障）
    severity_counts = {}
    for severity in ['critical', 'major', 'warning', 'minor']:
        count = db.query(FaultRecord).filter(
            FaultRecord.severity == severity,
            FaultRecord.status.in_(['open', 'investigating'])
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
        FaultRecord.status.in_(['open', 'investigating'])
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

async def trigger_fault_workflow(fault_id: int, severity: str):
    """后台触发故障工作流"""
    from app.shared.database import get_db_manager

    db_manager = get_db_manager()
    db = db_manager.get_session()

    try:
        executor = WorkflowExecutor(db)
        await executor.trigger_fault_created(fault_id)
    except Exception as e:
        print(f"Workflow trigger error: {e}")
    finally:
        db.close()