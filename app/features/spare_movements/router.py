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
    movement_type: str  # "in", "out", or "scrap_in"
    quantity: int
    serial_number: Optional[str] = None  # 序列号
    reason: Optional[str] = None
    operator: Optional[str] = None
    reference: Optional[str] = None


@router.post("/")
async def api_create_movement(movement: MovementCreate, db: Session = Depends(get_db)):
    """
    备件出入库操作

    - movement_type="in": 入库，增加库存
    - movement_type="out": 出库，减少库存（库存不足时拒绝）
    - movement_type="scrap_in": 报废入库，增加库存（用于返回件）
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
    db: Session = Depends(get_db),
):
    """出入库记录列表"""
    return svc_list_movements(
        db, skip=skip, limit=limit, part_id=part_id, movement_type=movement_type, operator=operator,
    )


@router.get("/{movement_id}")
async def api_get_movement(movement_id: int, db: Session = Depends(get_db)):
    """出入库记录详情"""
    try:
        return svc_get_movement(db, movement_id)
    except ResourceNotFoundException:
        raise HTTPException(status_code=404, detail="记录不存在")
