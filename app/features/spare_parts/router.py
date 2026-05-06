"""
备件资产管理 API

提供备件的 CRUD 和统计功能。
"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.shared.database import get_db
from .spare_part_service import (
    list_parts as svc_list_parts,
    get_part as svc_get_part,
    create_part as svc_create_part,
    update_part as svc_update_part,
    delete_part as svc_delete_part,
    get_stats as svc_get_stats,
)
from app.shared.exceptions import ResourceNotFoundException, ConflictException

router = APIRouter(prefix="/api/spare-parts", tags=["备件管理"])


class SparePartCreate(BaseModel):
    name: str
    part_number: str  # 型号（唯一）
    category: Optional[str] = None  # 模块/电源/线缆/其他
    manufacturer: Optional[str] = None
    description: Optional[str] = None
    quantity_in_stock: int = 0
    min_quantity: int = 0
    unit_price: float = 0
    location: Optional[str] = None


class SparePartUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    manufacturer: Optional[str] = None
    description: Optional[str] = None
    min_quantity: Optional[int] = None
    unit_price: Optional[float] = None
    location: Optional[str] = None
    status: Optional[str] = None


class SparePartStats(BaseModel):
    total_parts: int
    total_quantity: int
    low_stock_count: int
    total_value: float
    by_category: dict


@router.get("/")
async def api_list_parts(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    low_stock: bool = Query(False, description="只显示库存不足"),
    search: Optional[str] = Query(None, description="搜索名称/型号"),
    db: Session = Depends(get_db),
):
    """备件列表"""
    return svc_list_parts(db, skip=skip, limit=limit, category=category, status=status, low_stock=low_stock, search=search)


@router.post("/")
async def api_create_part(part: SparePartCreate, db: Session = Depends(get_db)):
    """新增备件"""
    try:
        result = svc_create_part(db, part.model_dump())
        return {"id": result["id"], "message": result["message"]}
    except ConflictException as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{part_id}")
async def api_get_part(part_id: int, db: Session = Depends(get_db)):
    """备件详情"""
    try:
        return svc_get_part(db, part_id)
    except ResourceNotFoundException:
        raise HTTPException(status_code=404, detail="备件不存在")


@router.get("/{part_id}/instances")
async def api_get_part_instances(
    part_id: int,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取备件的所有实例列表（每个个体的SN号、PO号等）"""
    from app.shared.models import SparePartInstance, SparePart

    # 先检查备件是否存在
    part = db.query(SparePart).filter(SparePart.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="备件不存在")

    # 查询实例列表
    query = db.query(SparePartInstance).filter(SparePartInstance.part_id == part_id)
    if status:
        query = query.filter(SparePartInstance.status == status)

    instances = query.order_by(SparePartInstance.created_at.desc()).all()

    return {
        "part_id": part_id,
        "part_name": part.name,
        "part_number": part.part_number,
        "total_instances": len(instances),
        "in_stock_count": sum(1 for i in instances if i.status == "in_stock"),
        "out_count": sum(1 for i in instances if i.status == "out"),
        "instances": [
            {
                "id": inst.id,
                "serial_number": inst.serial_number,
                "po_number": inst.po_number,
                "status": inst.status,
                "location": inst.location,
                "in_stock_at": inst.in_stock_at.isoformat() if inst.in_stock_at else None,
                "out_at": inst.out_at.isoformat() if inst.out_at else None,
                "notes": inst.notes,
                "created_at": inst.created_at.isoformat() if inst.created_at else None,
            }
            for inst in instances
        ]
    }


@router.get("/by-serial/{serial_number}")
async def api_get_part_by_serial(serial_number: str, db: Session = Depends(get_db)):
    """通过序列号查找备件实例（扫码枪接口）"""
    from app.shared.models import SparePartInstance, SparePart

    instance = db.query(SparePartInstance).filter(
        SparePartInstance.serial_number == serial_number
    ).first()

    if not instance:
        raise HTTPException(status_code=404, detail="未找到该序列号的备件")

    part = db.query(SparePart).filter(SparePart.id == instance.part_id).first()

    return {
        "id": part.id if part else None,
        "instance_id": instance.id,
        "name": part.name if part else None,
        "part_number": part.part_number if part else None,
        "serial_number": instance.serial_number,
        "po_number": instance.po_number,
        "status": instance.status,
        "location": instance.location,
        "quantity_in_stock": part.quantity_in_stock if part else 0,
    }


@router.put("/{part_id}")
async def api_update_part(part_id: int, part: SparePartUpdate, db: Session = Depends(get_db)):
    """更新备件"""
    try:
        result = svc_update_part(db, part_id, part.model_dump(exclude_unset=True))
        return {"id": result["id"], "message": result["message"]}
    except ResourceNotFoundException:
        raise HTTPException(status_code=404, detail="备件不存在")


@router.delete("/{part_id}")
async def api_delete_part(part_id: int, db: Session = Depends(get_db)):
    """删除备件"""
    try:
        return svc_delete_part(db, part_id)
    except ResourceNotFoundException:
        raise HTTPException(status_code=404, detail="备件不存在")


@router.get("/stats/summary")
async def api_get_stats(db: Session = Depends(get_db)):
    """备件统计"""
    return svc_get_stats(db)
