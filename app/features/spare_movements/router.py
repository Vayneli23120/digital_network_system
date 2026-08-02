"""
备件出入库操作 API

提供备件的入库/出库操作和记录查询。
"""
from typing import Literal, Optional
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict, Field, PositiveInt, condecimal

from app.features.auth.identity import Principal, get_current_principal
from app.shared.database import get_db
from app.shared.dependencies import require_permission
from app.features.spare_parts.spare_part_service import (
    create_movement as svc_create_movement,
    list_movements as svc_list_movements,
    get_movement as svc_get_movement,
)
from app.shared.exceptions import ResourceNotFoundException

router = APIRouter(prefix="/api/spare-movements", tags=["备件出入库"])
require_movement_read = require_permission("spare_movement:read")
require_movement_write = require_permission("spare_movement:write")
MovementType = Literal["in", "out", "scrap_in", "scrap_out"]
Money = condecimal(ge=0, max_digits=10, decimal_places=2)


class MovementCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    part_id: PositiveInt
    movement_type: MovementType
    quantity: int = Field(gt=0, le=100_000)
    serial_number: Optional[str] = Field(default=None, min_length=1, max_length=100)
    reason: Optional[str] = Field(default=None, max_length=500)
    reference: Optional[str] = Field(default=None, max_length=200)
    target_device_id: Optional[PositiveInt] = None
    source_device_id: Optional[PositiveInt] = None


class MovementUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: Optional[str] = Field(default=None, max_length=500)
    reference: Optional[str] = Field(default=None, max_length=200)
    unit_price: Optional[Money] = None


@router.post("/")
async def api_create_movement(
    movement: MovementCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_movement_write),
    principal: Principal = Depends(get_current_principal),
):
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
            operator=principal.username,
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
    part_id: Optional[PositiveInt] = Query(None),
    movement_type: Optional[MovementType] = Query(None),
    operator: Optional[str] = Query(None, min_length=1, max_length=100),
    keyword: Optional[str] = Query(None, min_length=1, max_length=200),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    _: None = Depends(require_movement_read),
):
    """出入库记录列表

    支持筛选：
    - part_id: 指定备件
    - movement_type: 类型（in/out/scrap_in/scrap_out）
    - operator: 操作人
    - keyword: 搜索关键词（名称/型号/序列号）
    - start_date/end_date: 时间范围
    """
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=422, detail="开始日期不能晚于结束日期")

    return svc_list_movements(
        db, skip=skip, limit=limit, part_id=part_id, movement_type=movement_type,
        operator=operator, keyword=keyword,
        start_date=start_date.isoformat() if start_date else None,
        end_date=end_date.isoformat() if end_date else None,
    )


@router.get("/{movement_id}")
async def api_get_movement(
    movement_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_movement_read),
):
    """出入库记录详情"""
    try:
        return svc_get_movement(db, movement_id)
    except ResourceNotFoundException:
        raise HTTPException(status_code=404, detail="记录不存在")


@router.put("/{movement_id}")
async def api_update_movement(
    movement_id: int,
    data: MovementUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_movement_write),
):
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
            SparePartInstance.serial_number == movement.serial_number,
            SparePartInstance.part_id == movement.part_id,
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
async def api_delete_movement(
    movement_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_movement_write),
):
    """库存审计记录不可物理删除。"""
    from app.shared.models import SparePartMovement

    movement = db.query(SparePartMovement).filter(SparePartMovement.id == movement_id).first()
    if not movement:
        raise HTTPException(status_code=404, detail="记录不存在")
    raise HTTPException(
        status_code=409,
        detail="出入库记录属于库存审计数据，不能删除；请使用反向出入库操作",
    )
