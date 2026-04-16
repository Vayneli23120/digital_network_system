"""Maintenance management router"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import uuid

from ..database import get_db
from ..models import MaintenanceRecord

router = APIRouter(prefix="/api/maintenance", tags=["maintenance"])


@router.get("/{maint_id}")
async def get_maintenance(maint_id: int):
    """获取单个维修详情"""
    db: Session = next(get_db())

    try:
        maintenance = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == maint_id).first()
        if not maintenance:
            raise HTTPException(status_code=404, detail="维修记录不存在")

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
            "maint_time": maintenance.maint_time.isoformat() if maintenance.maint_time else None,
            "created_at": maintenance.created_at.isoformat()
        }
    finally:
        db.close()


@router.get("")
async def list_maintenances(device_id: Optional[int] = None):
    """获取维修记录列表"""
    db: Session = next(get_db())

    try:
        query = db.query(MaintenanceRecord)

        if device_id:
            query = query.filter(MaintenanceRecord.device_id == device_id)

        maintenances = query.order_by(MaintenanceRecord.created_at.desc()).all()

        return {
            "items": [
                {
                    "id": m.id,
                    "maint_no": m.maint_no,
                    "device_id": m.device_id,
                    "device_name": m.device_name,
                    "maint_type": m.maint_type,
                    "parts_cost": float(m.parts_cost) if m.parts_cost else 0,
                    "labor_cost": float(m.labor_cost) if m.labor_cost else 0,
                    "total_cost": float((m.parts_cost or 0) + (m.labor_cost or 0)),
                    "maint_time": m.maint_time.isoformat() if m.maint_time else None,
                    "description": m.description,
                    "created_at": m.created_at.isoformat()
                }
                for m in maintenances
            ]
        }
    finally:
        db.close()


@router.post("")
async def create_maintenance(maint_data: dict):
    """创建维修记录"""
    db: Session = next(get_db())

    maint_no = f"MAINT-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
    maint_data["maint_no"] = maint_no

    # 设置维修时间为当前时间（如果未提供）
    if "maint_time" not in maint_data or not maint_data["maint_time"]:
        maint_data["maint_time"] = datetime.utcnow()

    maint = MaintenanceRecord(**maint_data)
    db.add(maint)
    db.commit()
    db.refresh(maint)

    return {"id": maint.id, "maint_no": maint_no, "message": "维修记录创建成功"}


@router.put("/{maint_id}")
async def update_maintenance(maint_id: int, maint_data: dict):
    """更新维修记录"""
    db: Session = next(get_db())

    maint = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == maint_id).first()
    if not maint:
        raise HTTPException(status_code=404, detail="维修记录不存在")

    for key, value in maint_data.items():
        if hasattr(maint, key):
            setattr(maint, key, value)

    db.commit()
    db.refresh(maint)

    return {"id": maint.id, "message": "更新成功"}


@router.delete("/{maint_id}")
async def delete_maintenance(maint_id: int):
    """删除维修记录"""
    db: Session = next(get_db())

    maint = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == maint_id).first()
    if not maint:
        raise HTTPException(status_code=404, detail="维修记录不存在")

    db.delete(maint)
    db.commit()

    return {"message": "删除成功"}
