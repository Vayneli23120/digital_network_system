"""Maintenance management router"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta
import uuid

from app.shared.database import get_db
from app.shared.models import MaintenanceRecord, MaintenanceEvent, FaultRecord

router = APIRouter(prefix="/api/maintenance", tags=["maintenance"])

# 状态流转规则
VALID_TRANSITIONS = {
    'created': ['diagnosing', 'cancelled'],
    'diagnosing': ['repairing', 'cancelled'],
    'repairing': ['verifying', 'cancelled'],
    'verifying': ['completed', 'cancelled'],
    'completed': [],
    'cancelled': []
}

STATUS_LABELS = {
    'created': '创建',
    'diagnosing': '诊断',
    'repairing': '维修',
    'verifying': '验证',
    'completed': '完成',
    'cancelled': '取消'
}

STATUS_PERCENT = {
    'created': 20,
    'diagnosing': 40,
    'repairing': 60,
    'verifying': 80,
    'completed': 100,
    'cancelled': 0
}


def build_events_from_record(maintenance):
    """从维修记录构建事件时间线"""
    events = []

    # 创建事件
    events.append({
        "event_type": "created",
        "event_time": maintenance.created_at.isoformat() if maintenance.created_at else None,
        "operator": maintenance.operator or "System",
        "notes": f"创建维修单 {maintenance.maint_no}"
    })

    # 各阶段事件
    if maintenance.diagnosing_at:
        events.append({
            "event_type": "diagnosing",
            "event_time": maintenance.diagnosing_at.isoformat(),
            "operator": maintenance.current_owner or maintenance.operator,
            "notes": "开始故障诊断"
        })

    if maintenance.repairing_at:
        events.append({
            "event_type": "repairing",
            "event_time": maintenance.repairing_at.isoformat(),
            "operator": maintenance.current_owner or maintenance.operator,
            "notes": "开始维修作业"
        })

    if maintenance.verifying_at:
        events.append({
            "event_type": "verifying",
            "event_time": maintenance.verifying_at.isoformat(),
            "operator": maintenance.current_owner or maintenance.operator,
            "notes": "提交验证"
        })

    if maintenance.completed_at:
        events.append({
            "event_type": "completed",
            "event_time": maintenance.completed_at.isoformat(),
            "operator": maintenance.current_owner or maintenance.operator,
            "notes": "维修完成"
        })

    if maintenance.cancelled_at:
        events.append({
            "event_type": "cancelled",
            "event_time": maintenance.cancelled_at.isoformat(),
            "operator": maintenance.current_owner or maintenance.operator,
            "notes": "维修取消"
        })

    return events


@router.get("/{maint_id}")
async def get_maintenance(maint_id: int):
    """获取单个维修详情"""
    db: Session = next(get_db())

    try:
        maintenance = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == maint_id).first()
        if not maintenance:
            raise HTTPException(status_code=404, detail="维修记录不存在")

        # 获取关联的故障信息
        fault_info = None
        if maintenance.fault_id:
            fault = db.query(FaultRecord).filter(FaultRecord.id == maintenance.fault_id).first()
            if fault:
                fault_info = {
                    "id": fault.id,
                    "fault_no": fault.fault_no,
                    "severity": fault.severity,
                    "status": fault.status,
                    "description": fault.description
                }

        # 构建事件时间线
        events = build_events_from_record(maintenance)

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
            "maint_time": maintenance.maint_time.isoformat() if maintenance.maint_time else None,
            "created_at": maintenance.created_at.isoformat(),
            # 新增状态系统字段
            "status": maintenance.status or "created",
            "status_label": STATUS_LABELS.get(maintenance.status, "创建"),
            "progress_percent": STATUS_PERCENT.get(maintenance.status, 20),
            "priority": maintenance.priority or "P3",
            "current_owner": maintenance.current_owner,
            "sla_deadline": maintenance.sla_deadline.isoformat() if maintenance.sla_deadline else None,
            "sla_remaining": sla_remaining,
            "diagnosing_at": maintenance.diagnosing_at.isoformat() if maintenance.diagnosing_at else None,
            "repairing_at": maintenance.repairing_at.isoformat() if maintenance.repairing_at else None,
            "verifying_at": maintenance.verifying_at.isoformat() if maintenance.verifying_at else None,
            "completed_at": maintenance.completed_at.isoformat() if maintenance.completed_at else None,
            "cancelled_at": maintenance.cancelled_at.isoformat() if maintenance.cancelled_at else None,
            "events": events
        }
    finally:
        db.close()


@router.get("/{maint_id}/events")
async def get_maintenance_events(maint_id: int):
    """获取维修事件时间线"""
    db: Session = next(get_db())

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
    finally:
        db.close()


@router.post("/{maint_id}/transition")
async def transition_maintenance_status(maint_id: int, data: dict):
    """状态流转"""
    db: Session = next(get_db())

    try:
        maintenance = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == maint_id).first()
        if not maintenance:
            raise HTTPException(status_code=404, detail="维修记录不存在")

        new_status = data.get("status")
        operator = data.get("operator", "System")
        notes = data.get("notes")

        if not new_status:
            raise HTTPException(status_code=400, detail="缺少目标状态")

        # 验证状态流转是否合法
        current_status = maintenance.status or "created"
        if new_status not in VALID_TRANSITIONS.get(current_status, []):
            raise HTTPException(status_code=400, detail=f"不能从 {current_status} 转换到 {new_status}")

        # 更新状态和时间戳
        maintenance.status = new_status

        if new_status == "diagnosing":
            maintenance.diagnosing_at = datetime.utcnow()
        elif new_status == "repairing":
            maintenance.repairing_at = datetime.utcnow()
        elif new_status == "verifying":
            maintenance.verifying_at = datetime.utcnow()
        elif new_status == "completed":
            maintenance.completed_at = datetime.utcnow()
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
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.put("/{maint_id}/assign")
async def assign_maintenance(maint_id: int, data: dict):
    """分配负责人"""
    db: Session = next(get_db())

    try:
        maintenance = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == maint_id).first()
        if not maintenance:
            raise HTTPException(status_code=404, detail="维修记录不存在")

        owner = data.get("owner")
        if not owner:
            raise HTTPException(status_code=400, detail="缺少负责人")

        maintenance.current_owner = owner

        # 创建事件记录
        event = MaintenanceEvent(
            maintenance_id=maint_id,
            event_type="assigned",
            event_time=datetime.utcnow(),
            operator=owner,
            notes=f"分配给 {owner}"
        )
        db.add(event)

        db.commit()

        return {"id": maint_id, "owner": owner, "message": f"已分配给 {owner}"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("")
@router.get("/")
async def list_maintenances(
    device_id: Optional[int] = None,
    fault_id: Optional[int] = None,
    maint_type: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    has_fault: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100
):
    """获取维修记录列表（带分页和状态筛选）"""
    db: Session = next(get_db())

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
                    "current_owner": m.current_owner
                }
                for m in maintenances
            ]
        }
    finally:
        db.close()


@router.post("")
@router.post("/")
async def create_maintenance(maint_data: dict):
    """创建维修记录"""
    db: Session = next(get_db())

    try:
        maint_no = f"MAINT-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

        # 过滤掉不属于模型的字段
        valid_fields = {
            'device_id', 'device_name', 'maint_type', 'maint_time',
            'parts_replaced', 'parts_cost', 'labor_hours', 'labor_cost',
            'vendor', 'description', 'post_status', 'operator',
            'status', 'priority', 'current_owner', 'sla_deadline'
        }
        filtered_data = {k: v for k, v in maint_data.items() if k in valid_fields}
        filtered_data["maint_no"] = maint_no
        filtered_data["status"] = "created"

        # 设置维修时间为当前时间（如果未提供）
        if "maint_time" not in filtered_data or not filtered_data["maint_time"]:
            filtered_data["maint_time"] = datetime.utcnow()

        # 设置 SLA 截止时间（默认24小时）
        if "sla_deadline" not in filtered_data:
            filtered_data["sla_deadline"] = datetime.utcnow() + timedelta(hours=24)

        maint = MaintenanceRecord(**filtered_data)
        db.add(maint)

        # 创建事件记录
        event = MaintenanceEvent(
            maintenance_id=maint.id,
            event_type="created",
            event_time=datetime.utcnow(),
            operator=maint_data.get("operator", "System"),
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
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.put("/{maint_id}")
async def update_maintenance(maint_id: int, maint_data: dict):
    """更新维修记录"""
    db: Session = next(get_db())

    try:
        maint = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == maint_id).first()
        if not maint:
            raise HTTPException(status_code=404, detail="维修记录不存在")

        # 过滤掉不属于模型的字段
        valid_fields = {
            'device_id', 'device_name', 'maint_type', 'maint_time',
            'parts_replaced', 'parts_cost', 'labor_hours', 'labor_cost',
            'vendor', 'description', 'post_status', 'operator',
            'status', 'priority', 'current_owner', 'sla_deadline'
        }

        for key, value in maint_data.items():
            if key in valid_fields and hasattr(maint, key):
                setattr(maint, key, value)

        db.commit()
        db.refresh(maint)

        return {"id": maint.id, "message": "更新成功"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.delete("/{maint_id}")
async def delete_maintenance(maint_id: int):
    """删除维修记录"""
    db: Session = next(get_db())

    try:
        maint = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == maint_id).first()
        if not maint:
            raise HTTPException(status_code=404, detail="维修记录不存在")

        db.delete(maint)
        db.commit()

        return {"message": "删除成功"}
    finally:
        db.close()
