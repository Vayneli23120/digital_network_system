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
        "unit_price": float(part.unit_price) if part.unit_price else 0,
        "total_instances": len(instances),
        "in_stock_count": sum(1 for i in instances if i.status == "in_stock"),
        "out_count": sum(1 for i in instances if i.status == "out"),
        "instances": [
            {
                "id": inst.id,
                "serial_number": inst.serial_number,
                "po_number": inst.po_number,
                "unit_price": float(inst.unit_price) if inst.unit_price else float(part.unit_price) if part.unit_price else 0,
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


class ManualStockIn(BaseModel):
    """手动入库"""
    serial_number: str
    po_number: Optional[str] = None
    unit_price: Optional[float] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    reason: Optional[str] = None


class ManualStockOut(BaseModel):
    """手动出库"""
    serial_number: str
    reason: str
    destination: Optional[str] = None
    notes: Optional[str] = None


@router.post("/{part_id}/manual-in")
async def api_manual_stock_in(
    part_id: int,
    data: ManualStockIn,
    db: Session = Depends(get_db)
):
    """手动入库（创建备件实例）"""
    from app.shared.models import SparePart, SparePartInstance, SparePartMovement
    from datetime import datetime

    part = db.query(SparePart).filter(SparePart.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="备件不存在")

    # 检查序列号是否已存在
    existing = db.query(SparePartInstance).filter(
        SparePartInstance.serial_number == data.serial_number
    ).first()

    if existing:
        # 如果已存在但状态不是in_stock，更新状态
        if existing.status != "in_stock":
            existing.status = "in_stock"
            existing.in_stock_at = datetime.utcnow()
            existing.out_at = None
            existing.po_number = data.po_number or existing.po_number
            existing.unit_price = data.unit_price or existing.unit_price
            existing.location = data.location or existing.location
            existing.notes = data.notes or existing.notes
        else:
            raise HTTPException(status_code=400, detail="该序列号已在库中")
    else:
        # 创建新实例
        instance = SparePartInstance(
            part_id=part_id,
            serial_number=data.serial_number,
            po_number=data.po_number,
            unit_price=data.unit_price or part.unit_price,
            status="in_stock",
            location=data.location or part.location,
            notes=data.notes,
            in_stock_at=datetime.utcnow()
        )
        db.add(instance)

    # 先flush让状态更新生效，再计算库存数量
    db.flush()

    # 更新库存数量（基于实例计数）
    actual_count = db.query(SparePartInstance).filter(
        SparePartInstance.part_id == part_id,
        SparePartInstance.status == "in_stock"
    ).count()
    part.quantity_in_stock = actual_count

    # 创建出入库记录
    movement = SparePartMovement(
        part_id=part_id,
        movement_type="in",
        quantity=1,
        reason=data.reason or "手动入库",
        operator="",
        reference=data.po_number or "",
        created_at=datetime.utcnow()
    )
    db.add(movement)

    db.commit()

    return {
        "message": f"入库成功，序列号: {data.serial_number}",
        "serial_number": data.serial_number,
        "new_stock": part.quantity_in_stock
    }


@router.post("/{part_id}/manual-out")
async def api_manual_stock_out(
    part_id: int,
    data: ManualStockOut,
    db: Session = Depends(get_db)
):
    """手动出库（通过序列号定位实例）"""
    from app.shared.models import SparePart, SparePartInstance, SparePartMovement
    from datetime import datetime

    part = db.query(SparePart).filter(SparePart.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="备件不存在")

    # 通过序列号查找实例
    instance = db.query(SparePartInstance).filter(
        SparePartInstance.serial_number == data.serial_number,
        SparePartInstance.status == "in_stock"
    ).first()

    if not instance:
        raise HTTPException(status_code=404, detail="未找到该序列号的在库实例")

    # 更新实例状态
    instance.status = "out"
    instance.out_at = datetime.utcnow()
    # 更新备注：追加出库信息
    out_note = f"出库原因: {data.reason}"
    if data.destination:
        out_note += f", 去向: {data.destination}"
    if data.notes:
        out_note += f", 备注: {data.notes}"
    if instance.notes:
        instance.notes = instance.notes + "\n" + out_note
    else:
        instance.notes = out_note

    # 先flush让状态更新生效，再计算库存数量
    db.flush()

    # 更新库存数量
    actual_count = db.query(SparePartInstance).filter(
        SparePartInstance.part_id == part_id,
        SparePartInstance.status == "in_stock"
    ).count()
    part.quantity_in_stock = actual_count

    # 创建出入库记录
    movement = SparePartMovement(
        part_id=part_id,
        movement_type="out",
        quantity=1,
        reason=data.reason,
        operator="",
        reference=data.destination or "",
        created_at=datetime.utcnow()
    )
    db.add(movement)

    db.commit()

    return {
        "message": f"出库成功，序列号: {data.serial_number}",
        "serial_number": data.serial_number,
        "new_stock": part.quantity_in_stock
    }


@router.get("/by-serial/{serial_number}")
async def api_get_part_by_serial(serial_number: str, db: Session = Depends(get_db)):
    """通过序列号查找备件实例（扫码枪接口，返回完整历史信息）"""
    from app.shared.models import SparePartInstance, SparePart, SparePartMovement

    instance = db.query(SparePartInstance).filter(
        SparePartInstance.serial_number == serial_number
    ).first()

    if not instance:
        raise HTTPException(status_code=404, detail="未找到该序列号的备件")

    part = db.query(SparePart).filter(SparePart.id == instance.part_id).first()

    # 获取该序列号的出入库历史
    movements = db.query(SparePartMovement).filter(
        SparePartMovement.serial_number == serial_number
    ).order_by(SparePartMovement.created_at).all()

    history = []
    for m in movements:
        history.append({
            "id": m.id,
            "movement_type": m.movement_type,
            "reason": m.reason,
            "reference": m.reference,
            "created_at": m.created_at.isoformat() if m.created_at else None
        })

    return {
        "id": part.id if part else None,
        "instance_id": instance.id,
        "name": part.name if part else None,
        "part_number": part.part_number if part else None,
        "serial_number": instance.serial_number,
        "po_number": instance.po_number,
        "unit_price": float(instance.unit_price) if instance.unit_price else (float(part.unit_price) if part and part.unit_price else 0),
        "status": instance.status,
        "location": instance.location,
        "quantity_in_stock": part.quantity_in_stock if part else 0,
        "in_stock_at": instance.in_stock_at.isoformat() if instance.in_stock_at else None,
        "out_at": instance.out_at.isoformat() if instance.out_at else None,
        "notes": instance.notes,
        "history": history,  # 出入库历史记录
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
