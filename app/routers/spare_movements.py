"""
备件出入库操作 API

提供备件的入库/出库操作和记录查询。
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel

from app.database import get_db
from app.models import SparePart, SparePartMovement

router = APIRouter(prefix="/spare-movements", tags=["备件出入库"])


class MovementCreate(BaseModel):
    part_id: int
    movement_type: str  # "in" or "out"
    quantity: int
    reason: Optional[str] = None
    operator: Optional[str] = None
    reference: Optional[str] = None


class MovementResponse(BaseModel):
    id: int
    part_id: int
    movement_type: str
    quantity: int
    reason: Optional[str]
    operator: Optional[str]
    reference: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/", response_model=MovementResponse)
async def create_movement(movement: MovementCreate, db: Session = Depends(get_db)):
    """
    备件出入库操作

    - movement_type="in": 入库，增加库存
    - movement_type="out": 出库，减少库存（库存不足时拒绝）
    """
    part = db.query(SparePart).filter(SparePart.id == movement.part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="备件不存在")

    if movement.quantity <= 0:
        raise HTTPException(status_code=400, detail="数量必须大于 0")

    if movement.movement_type == "out":
        if part.quantity_in_stock < movement.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"库存不足：当前 {part.quantity_in_stock}，需要 {movement.quantity}"
            )
        part.quantity_in_stock -= movement.quantity
    elif movement.movement_type == "in":
        part.quantity_in_stock += movement.quantity
    else:
        raise HTTPException(status_code=400, detail="movement_type 必须为 'in' 或 'out'")

    # 更新状态
    if part.quantity_in_stock == 0:
        part.status = "depleted"
    elif part.quantity_in_stock < part.min_quantity:
        part.status = "active"  # 库存不足但仍然活跃
    else:
        part.status = "active"

    db_movement = SparePartMovement(**movement.model_dump())
    db.add(db_movement)
    db.commit()
    db.refresh(db_movement)

    return db_movement


@router.get("/", response_model=List[MovementResponse])
async def list_movements(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    part_id: Optional[int] = Query(None),
    movement_type: Optional[str] = Query(None),
    operator: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """出入库记录列表"""
    query = db.query(SparePartMovement)

    if part_id:
        query = query.filter(SparePartMovement.part_id == part_id)
    if movement_type:
        query = query.filter(SparePartMovement.movement_type == movement_type)
    if operator:
        query = query.filter(SparePartMovement.operator == operator)

    movements = query.order_by(desc(SparePartMovement.created_at)).offset(skip).limit(limit).all()
    return movements


@router.get("/{movement_id}", response_model=MovementResponse)
async def get_movement(movement_id: int, db: Session = Depends(get_db)):
    """出入库记录详情"""
    movement = db.query(SparePartMovement).filter(SparePartMovement.id == movement_id).first()
    if not movement:
        raise HTTPException(status_code=404, detail="记录不存在")
    return movement
