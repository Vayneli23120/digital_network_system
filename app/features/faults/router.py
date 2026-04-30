"""Fault management router"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import uuid

from app.shared.database import get_db
from app.shared.models import FaultRecord, MaintenanceRecord, Device

router = APIRouter(prefix="/api/faults", tags=["faults"])


@router.get("/{fault_id}")
async def get_fault(fault_id: int):
    """获取单个故障详情"""
    db: Session = next(get_db())

    try:
        fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()
        if not fault:
            raise HTTPException(status_code=404, detail="故障记录不存在")

        return {
            "id": fault.id,
            "fault_no": fault.fault_no,
            "device_id": fault.device_id,
            "device_name": fault.device_name,
            "severity": fault.severity,
            "status": fault.status,
            "downtime_minutes": fault.downtime_minutes,
            "impact": fault.impact,
            "description": fault.description,
            "resolution": fault.resolution,
            "reporter": fault.reporter,
            "maintenance_id": fault.maintenance_id,
            "fault_time": fault.fault_time.isoformat() if fault.fault_time else None,
            "created_at": fault.created_at.isoformat()
        }
    finally:
        db.close()


@router.get("")
async def list_faults(device_id: Optional[int] = None, status: Optional[str] = None, skip: int = 0, limit: int = 100):
    """获取故障记录列表（带分页）"""
    db: Session = next(get_db())

    try:
        query = db.query(FaultRecord)

        if device_id:
            query = query.filter(FaultRecord.device_id == device_id)
        if status:
            query = query.filter(FaultRecord.status == status)

        total = query.count()
        faults = query.order_by(FaultRecord.created_at.desc()).offset(skip).limit(limit).all()

        return {
            "total": total,
            "items": [
                {
                    "id": f.id,
                    "fault_no": f.fault_no,
                    "device_id": f.device_id,
                    "device_name": f.device_name,
                    "severity": f.severity,
                    "status": f.status,
                    "downtime_minutes": f.downtime_minutes,
                    "description": f.description,
                    "created_at": f.created_at.isoformat()
                }
                for f in faults
            ]
        }
    finally:
        db.close()


@router.post("")
async def create_fault(fault_data: dict):
    """创建故障记录"""
    db: Session = next(get_db())

    try:
        # 自动生成故障单号
        fault_no = f"FAULT-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
        fault_data["fault_no"] = fault_no

        fault = FaultRecord(**fault_data)
        db.add(fault)
        db.commit()
        db.refresh(fault)

        # 发送多渠道告警
        from app.services.notification_service import get_notification_service
        get_notification_service().notify_fault(
            fault_data.get("device_name", "Unknown"),
            fault_no,
            fault_data.get("severity", "warning"),
            fault_data.get("description", "")
        )

        # 清除 Dashboard 缓存
        from app.shared.cache import cache
        cache.invalidate_prefix("dashboard:")

        return {"id": fault.id, "fault_no": fault_no, "message": "故障记录创建成功"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.put("/{fault_id}")
async def update_fault(fault_id: int, fault_data: dict):
    """更新故障记录"""
    db: Session = next(get_db())

    try:
        fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()
        if not fault:
            raise HTTPException(status_code=404, detail="故障记录不存在")

        for key, value in fault_data.items():
            if hasattr(fault, key):
                setattr(fault, key, value)

        db.commit()
        db.refresh(fault)

        return {"id": fault.id, "message": "更新成功"}
    finally:
        db.close()


@router.delete("/{fault_id}")
async def delete_fault(fault_id: int):
    """删除故障记录"""
    db: Session = next(get_db())

    try:
        fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()
        if not fault:
            raise HTTPException(status_code=404, detail="故障记录不存在")

        db.delete(fault)
        db.commit()

        return {"message": "删除成功"}
    finally:
        db.close()


@router.post("/{fault_id}/convert-to-maintenance")
async def convert_to_maintenance(fault_id: int):
    """将故障单转换为维修单"""
    db: Session = next(get_db())

    try:
        fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()
        if not fault:
            raise HTTPException(status_code=404, detail="故障记录不存在")

        # 检查是否已关联维修单
        if fault.maintenance_id:
            raise HTTPException(status_code=400, detail="该故障已关联维修单")

        # 检查故障状态（已关闭的不能转维修）
        if fault.status == "closed":
            raise HTTPException(status_code=400, detail="已关闭的故障不能转维修")

        # 自动生成维修单号
        maint_no = f"MAINT-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

        # 创建维修单
        maintenance = MaintenanceRecord(
            maint_no=maint_no,
            device_id=fault.device_id,
            device_name=fault.device_name,
            maint_type="corrective",  # 故障驱动维修
            description=f"由故障单 {fault.fault_no} 转换\n\n故障描述：{fault.description}",
            fault_id=fault.id,
            maint_time=datetime.utcnow()
        )
        db.add(maintenance)
        db.commit()
        db.refresh(maintenance)

        # 更新故障单的维修关联
        fault.maintenance_id = maintenance.id
        db.commit()

        # 清除 Dashboard 缓存
        from app.shared.cache import cache
        cache.invalidate_prefix("dashboard:")

        return {
            "maintenance_id": maintenance.id,
            "maint_no": maint_no,
            "message": "维修单创建成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"转换失败：{str(e)}")
    finally:
        db.close()


@router.get("/{fault_id}/maintenance")
async def get_fault_maintenance(fault_id: int):
    """获取故障关联的维修单详情"""
    db: Session = next(get_db())

    try:
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
    finally:
        db.close()
