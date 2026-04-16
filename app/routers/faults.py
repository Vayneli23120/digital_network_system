"""Fault management router"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import uuid

from ..database import get_db
from ..models import FaultRecord

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
            "fault_time": fault.fault_time.isoformat() if fault.fault_time else None,
            "created_at": fault.created_at.isoformat()
        }
    finally:
        db.close()


@router.get("")
async def list_faults(device_id: Optional[int] = None, status: Optional[str] = None):
    """获取故障记录列表"""
    db: Session = next(get_db())

    try:
        query = db.query(FaultRecord)

        if device_id:
            query = query.filter(FaultRecord.device_id == device_id)
        if status:
            query = query.filter(FaultRecord.status == status)

        faults = query.order_by(FaultRecord.created_at.desc()).all()

        return {
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

        # 发送告警邮件
        from ..services.email_service import get_email_service
        email_service = get_email_service()
        email_service.send_fault_alert(
            fault_data.get("device_name", "Unknown"),
            fault_no,
            fault_data.get("severity", "warning"),
            fault_data.get("description", "")
        )

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

    fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()
    if not fault:
        raise HTTPException(status_code=404, detail="故障记录不存在")

    for key, value in fault_data.items():
        if hasattr(fault, key):
            setattr(fault, key, value)

    db.commit()
    db.refresh(fault)

    return {"id": fault.id, "message": "更新成功"}


@router.delete("/{fault_id}")
async def delete_fault(fault_id: int):
    """删除故障记录"""
    db: Session = next(get_db())

    fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()
    if not fault:
        raise HTTPException(status_code=404, detail="故障记录不存在")

    db.delete(fault)
    db.commit()

    return {"message": "删除成功"}
