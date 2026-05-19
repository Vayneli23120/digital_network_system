"""
备件出入库操作 API

提供备件的入库/出库操作和记录查询。
"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.shared.database import get_db
from app.features.spare_parts.spare_part_service import (
    create_movement as svc_create_movement,
    list_movements as svc_list_movements,
    get_movement as svc_get_movement,
)
from app.shared.exceptions import ResourceNotFoundException

router = APIRouter(prefix="/api/spare-movements", tags=["备件出入库"])


class MovementCreate(BaseModel):
    part_id: int
    movement_type: str  # "in", "out", "scrap_in", or "scrap_out"
    quantity: int
    serial_number: Optional[str] = None  # 序列号
    reason: Optional[str] = None
    operator: Optional[str] = None
    reference: Optional[str] = None
    target_device_id: Optional[int] = None  # 出库目标设备
    source_device_id: Optional[int] = None  # 返回件来源设备


class MovementUpdate(BaseModel):
    reason: Optional[str] = None
    reference: Optional[str] = None
    unit_price: Optional[float] = None


@router.post("/")
async def api_create_movement(movement: MovementCreate, db: Session = Depends(get_db)):
    """
    备件出入库操作

    - movement_type="in": 入库，增加库存
    - movement_type="out": 出库，减少库存（库存不足时拒绝）
        - target_device_id: 指定目标设备，备件安装到设备上
    - movement_type="scrap_in": 报废入库，增加库存（用于返回件）
        - source_device_id: 指定来源设备，记录从哪台设备拆卸
    - movement_type="scrap_out": 报废出库，不改变库存（用于报废件销毁/回收等）
    """
    try:
        return svc_create_movement(
            db,
            part_id=movement.part_id,
            movement_type=movement.movement_type,
            quantity=movement.quantity,
            serial_number=movement.serial_number,
            reason=movement.reason,
            operator=movement.operator,
            reference=movement.reference,
            target_device_id=movement.target_device_id,
            source_device_id=movement.source_device_id,
        )
    except ResourceNotFoundException:
        raise HTTPException(status_code=404, detail="备件不存在")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/")
async def api_list_movements(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    part_id: Optional[int] = Query(None),
    movement_type: Optional[str] = Query(None),
    operator: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """出入库记录列表

    支持筛选：
    - part_id: 指定备件
    - movement_type: 类型（in/out/scrap_in/scrap_out）
    - operator: 操作人
    - keyword: 搜索关键词（名称/型号/序列号）
    - start_date/end_date: 时间范围
    """
    return svc_list_movements(
        db, skip=skip, limit=limit, part_id=part_id, movement_type=movement_type,
        operator=operator, keyword=keyword, start_date=start_date, end_date=end_date,
    )


@router.get("/{movement_id}")
async def api_get_movement(movement_id: int, db: Session = Depends(get_db)):
    """出入库记录详情"""
    try:
        return svc_get_movement(db, movement_id)
    except ResourceNotFoundException:
        raise HTTPException(status_code=404, detail="记录不存在")


@router.put("/{movement_id}")
async def api_update_movement(movement_id: int, data: MovementUpdate, db: Session = Depends(get_db)):
    """更新出入库记录"""
    from app.shared.models import SparePartMovement, SparePartInstance

    movement = db.query(SparePartMovement).filter(SparePartMovement.id == movement_id).first()
    if not movement:
        raise HTTPException(status_code=404, detail="记录不存在")

    # 更新字段
    if data.reason is not None:
        movement.reason = data.reason
    if data.reference is not None:
        movement.reference = data.reference

    # 如果有序列号且指定了单价，更新实例单价
    if movement.serial_number and data.unit_price is not None:
        instance = db.query(SparePartInstance).filter(
            SparePartInstance.serial_number == movement.serial_number
        ).first()
        if instance:
            instance.unit_price = data.unit_price

    db.commit()

    return {
        "id": movement.id,
        "message": "更新成功",
        "reason": movement.reason,
        "reference": movement.reference,
    }


@router.delete("/{movement_id}")
async def api_delete_movement(movement_id: int, db: Session = Depends(get_db)):
    """删除出入库记录"""
    from app.shared.models import SparePartMovement, SparePartInstance, SparePart

    movement = db.query(SparePartMovement).filter(SparePartMovement.id == movement_id).first()
    if not movement:
        raise HTTPException(status_code=404, detail="记录不存在")

    # 如果是报废入库记录且有序列号，需要同时删除实例
    if movement.movement_type == "scrap_in" and movement.serial_number:
        instance = db.query(SparePartInstance).filter(
            SparePartInstance.serial_number == movement.serial_number,
            SparePartInstance.status == "pending_scrap"
        ).first()
        if instance:
            db.delete(instance)
            # 更新备件库存数量
            if movement.part_id:
                part = db.query(SparePart).filter(SparePart.id == movement.part_id).first()
                if part:
                    part.quantity_in_stock = db.query(SparePartInstance).filter(
                        SparePartInstance.part_id == movement.part_id,
                        SparePartInstance.status == "in_stock"
                    ).count()

    serial_number = movement.serial_number
    movement_type = movement.movement_type

    db.delete(movement)
    db.commit()

    return {
        "id": movement_id,
        "message": "删除成功",
        "serial_number": serial_number,
        "movement_type": movement_type,
    }
