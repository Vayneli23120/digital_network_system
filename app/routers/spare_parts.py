"""
备件资产管理 API

提供备件的 CRUD 和统计功能。
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from pydantic import BaseModel

from app.database import get_db
from app.models import SparePart

router = APIRouter(prefix="/spare-parts", tags=["备件管理"])


class SparePartCreate(BaseModel):
    name: str
    part_number: str
    category: Optional[str] = None
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


class SparePartResponse(BaseModel):
    id: int
    name: str
    part_number: str
    category: Optional[str]
    manufacturer: Optional[str]
    description: Optional[str]
    quantity_in_stock: int
    min_quantity: int
    unit_price: float
    location: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SparePartStats(BaseModel):
    total_parts: int
    total_quantity: int
    low_stock_count: int  # quantity < min_quantity
    total_value: float
    by_category: dict


@router.get("/", response_model=List[SparePartResponse])
async def list_parts(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    low_stock: bool = Query(False, description="只显示库存不足"),
    search: Optional[str] = Query(None, description="搜索名称/型号"),
    db: Session = Depends(get_db)
):
    """备件列表"""
    query = db.query(SparePart)

    if category:
        query = query.filter(SparePart.category == category)
    if status:
        query = query.filter(SparePart.status == status)
    if low_stock:
        query = query.filter(SparePart.quantity_in_stock < SparePart.min_quantity)
    if search:
        query = query.filter(
            SparePart.name.contains(search) | SparePart.part_number.contains(search)
        )

    parts = query.order_by(desc(SparePart.updated_at)).offset(skip).limit(limit).all()
    return parts


@router.post("/", response_model=SparePartResponse)
async def create_part(part: SparePartCreate, db: Session = Depends(get_db)):
    """新增备件"""
    existing = db.query(SparePart).filter(SparePart.part_number == part.part_number).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"备件编号 {part.part_number} 已存在")

    db_part = SparePart(**part.model_dump())
    db.add(db_part)
    db.commit()
    db.refresh(db_part)
    return db_part


@router.get("/{part_id}", response_model=SparePartResponse)
async def get_part(part_id: int, db: Session = Depends(get_db)):
    """备件详情"""
    part = db.query(SparePart).filter(SparePart.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="备件不存在")
    return part


@router.put("/{part_id}", response_model=SparePartResponse)
async def update_part(part_id: int, part: SparePartUpdate, db: Session = Depends(get_db)):
    """更新备件"""
    db_part = db.query(SparePart).filter(SparePart.id == part_id).first()
    if not db_part:
        raise HTTPException(status_code=404, detail="备件不存在")

    update_data = part.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_part, key, value)

    db.commit()
    db.refresh(db_part)
    return db_part


@router.delete("/{part_id}")
async def delete_part(part_id: int, db: Session = Depends(get_db)):
    """删除备件"""
    db_part = db.query(SparePart).filter(SparePart.id == part_id).first()
    if not db_part:
        raise HTTPException(status_code=404, detail="备件不存在")

    db.delete(db_part)
    db.commit()
    return {"message": "备件已删除"}


@router.get("/stats/summary", response_model=SparePartStats)
async def get_stats(db: Session = Depends(get_db)):
    """备件统计"""
    total_parts = db.query(SparePart).count()
    total_qty = db.query(func.sum(SparePart.quantity_in_stock)).scalar() or 0
    low_stock = db.query(SparePart).filter(
        SparePart.quantity_in_stock < SparePart.min_quantity
    ).count()
    total_value = db.query(func.sum(SparePart.quantity_in_stock * SparePart.unit_price)).scalar() or 0

    by_category = {}
    rows = db.query(SparePart.category, func.sum(SparePart.quantity_in_stock)).group_by(SparePart.category).all()
    for cat, qty in rows:
        by_category[cat or "未分类"] = qty

    return SparePartStats(
        total_parts=total_parts,
        total_quantity=total_qty,
        low_stock_count=low_stock,
        total_value=float(total_value),
        by_category=by_category
    )
