"""
备件管理服务层

封装备件 CRUD 和统计的业务逻辑，供路由和测试使用。
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.shared.models import SparePart, SparePartMovement, SparePartInstance
from app.shared.exceptions import ResourceNotFoundException, ConflictException


def list_parts(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    category: Optional[str] = None,
    status: Optional[str] = None,
    low_stock: bool = False,
    search: Optional[str] = None,
) -> Dict[str, Any]:
    """获取备件列表

    Args:
        db: 数据库会话
        skip: 偏移量
        limit: 最大返回数量
        category: 按分类过滤
        status: 按状态过滤
        low_stock: 仅显示库存不足
        search: 搜索名称或型号

    Returns:
        包含 total 和 items 的字典
    """
    query = db.query(SparePart)

    if category:
        query = query.filter(SparePart.category == category)
    if status:
        query = query.filter(SparePart.status == status)
    if low_stock:
        query = query.filter(SparePart.quantity_in_stock < SparePart.min_quantity)
    if search:
        query = query.filter(
            SparePart.name.contains(search) |
            SparePart.part_number.contains(search)
        )

    total = query.count()
    parts = query.order_by(SparePart.updated_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "items": [
            {
                "id": p.id,
                "name": p.name,
                "part_number": p.part_number,
                "category": p.category,
                "manufacturer": p.manufacturer,
                "description": p.description,
                "quantity_in_stock": p.quantity_in_stock,
                "min_quantity": p.min_quantity,
                "unit_price": float(p.unit_price),
                "location": p.location,
                "status": p.status,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            }
            for p in parts
        ]
    }


def get_part(db: Session, part_id: int) -> Dict[str, Any]:
    """获取备件详情

    Args:
        db: 数据库会话
        part_id: 备件 ID

    Returns:
        备件信息字典

    Raises:
        ResourceNotFoundException: 备件不存在
    """
    part = db.query(SparePart).filter(SparePart.id == part_id).first()
    if not part:
        raise ResourceNotFoundException("SparePart")

    return {
        "id": part.id,
        "name": part.name,
        "part_number": part.part_number,
        "category": part.category,
        "manufacturer": part.manufacturer,
        "description": part.description,
        "quantity_in_stock": part.quantity_in_stock,
        "min_quantity": part.min_quantity,
        "unit_price": float(part.unit_price),
        "location": part.location,
        "status": part.status,
        "created_at": part.created_at.isoformat() if part.created_at else None,
        "updated_at": part.updated_at.isoformat() if part.updated_at else None,
    }


def create_part(db: Session, part_data: Dict[str, Any]) -> Dict[str, Any]:
    """创建备件

    Args:
        db: 数据库会话
        part_data: 备件数据

    Returns:
        创建的备件信息

    Raises:
        ConflictException: 备件编号已存在
    """
    part_number = part_data.get("part_number")
    existing = db.query(SparePart).filter(SparePart.part_number == part_number).first()
    if existing:
        raise ConflictException(f"备件编号 '{part_number}' 已存在")

    part = SparePart(**part_data)
    db.add(part)
    db.commit()
    db.refresh(part)

    return {
        "id": part.id,
        "name": part.name,
        "part_number": part.part_number,
        "message": "备件创建成功",
    }


def update_part(db: Session, part_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
    """更新备件

    Args:
        db: 数据库会话
        part_id: 备件 ID
        update_data: 要更新的字段

    Returns:
        更新后的备件信息

    Raises:
        ResourceNotFoundException: 备件不存在
    """
    part = db.query(SparePart).filter(SparePart.id == part_id).first()
    if not part:
        raise ResourceNotFoundException("SparePart")

    for key, value in update_data.items():
        if hasattr(part, key):
            setattr(part, key, value)

    db.commit()
    db.refresh(part)

    return {
        "id": part.id,
        "name": part.name,
        "message": "更新成功",
    }


def delete_part(db: Session, part_id: int) -> Dict[str, Any]:
    """删除备件

    Args:
        db: 数据库会话
        part_id: 备件 ID

    Returns:
        操作结果

    Raises:
        ResourceNotFoundException: 备件不存在
    """
    part = db.query(SparePart).filter(SparePart.id == part_id).first()
    if not part:
        raise ResourceNotFoundException("SparePart")

    db.delete(part)
    db.commit()

    return {"success": True, "message": "删除成功"}


def get_stats(db: Session) -> Dict[str, Any]:
    """获取备件统计数据

    Args:
        db: 数据库会话

    Returns:
        统计数据字典
    """
    total_parts = db.query(SparePart).count()
    total_qty = db.query(func.sum(SparePart.quantity_in_stock)).scalar() or 0
    low_stock = db.query(SparePart).filter(
        SparePart.quantity_in_stock < SparePart.min_quantity
    ).count()
    total_value = db.query(func.sum(SparePart.quantity_in_stock * SparePart.unit_price)).scalar() or 0

    by_category = {}
    rows = db.query(
        SparePart.category, func.sum(SparePart.quantity_in_stock)
    ).group_by(SparePart.category).all()
    for cat, qty in rows:
        by_category[cat or "未分类"] = qty

    return {
        "total_parts": total_parts,
        "total_quantity": int(total_qty),
        "low_stock_count": low_stock,
        "total_value": float(total_value),
        "by_category": by_category,
    }


def create_movement(
    db: Session,
    part_id: int,
    movement_type: str,
    quantity: int,
    serial_number: Optional[str] = None,
    reason: Optional[str] = None,
    operator: Optional[str] = None,
    reference: Optional[str] = None,
    target_device_id: Optional[int] = None,
    source_device_id: Optional[int] = None,
) -> Dict[str, Any]:
    """创建备件出入库记录

    Args:
        db: 数据库会话
        part_id: 备件 ID
        movement_type: "in", "out", "scrap_in", "scrap_out"
        quantity: 数量
        serial_number: 序列号（扫码出库时记录）
        reason: 原因
        operator: 操作人
        reference: 关联单号
        target_device_id: 出库目标设备（备件安装到设备）
        source_device_id: 返回件来源设备（从哪台设备拆卸）

    Returns:
        出入库记录信息

    Raises:
        ResourceNotFoundException: 备件不存在
        ValueError: 数量或类型无效
    """
    part = db.query(SparePart).filter(SparePart.id == part_id).first()
    if not part:
        raise ResourceNotFoundException("SparePart")

    if quantity <= 0:
        raise ValueError("数量必须大于 0")

    if movement_type == "out":
        if part.quantity_in_stock < quantity:
            raise ValueError(
                f"库存不足：当前 {part.quantity_in_stock}，需要 {quantity}"
            )
        part.quantity_in_stock -= quantity

        # 如果指定了目标设备，更新备件实例状态
        if serial_number and target_device_id:
            instance = db.query(SparePartInstance).filter(
                SparePartInstance.serial_number == serial_number
            ).first()
            if instance:
                instance.status = "installed"
                instance.installed_device_id = target_device_id
                instance.installed_at = datetime.utcnow()
                instance.installed_by = operator

    elif movement_type == "in" or movement_type == "scrap_in":
        part.quantity_in_stock += quantity

        # 返回件入库，记录来源设备
        if movement_type == "scrap_in" and serial_number and source_device_id:
            instance = db.query(SparePartInstance).filter(
                SparePartInstance.serial_number == serial_number
            ).first()
            if instance:
                instance.status = "scrapped"
                instance.removed_from_device_id = source_device_id
                instance.removed_at = datetime.utcnow()
                instance.installed_device_id = None  # 清除安装设备

    elif movement_type == "scrap_out":
        # 报废出库不影响备件库存，只记录出库操作
        pass
    else:
        raise ValueError("movement_type 必须为 'in', 'out', 'scrap_in' 或 'scrap_out'")

    # 更新备件状态
    if part.quantity_in_stock == 0:
        part.status = "depleted"
    else:
        part.status = "active"

    # 库存不足预警
    if part.quantity_in_stock <= part.min_quantity:
        try:
            from .notification_service import get_notification_service
            get_notification_service().notify_low_stock(
                part_name=part.name,
                part_number=part.part_number,
                quantity=part.quantity_in_stock,
                min_quantity=part.min_quantity,
            )
        except Exception:
            pass  # 告警失败不影响主流程

    movement = SparePartMovement(
        part_id=part_id,
        movement_type=movement_type,
        quantity=quantity,
        serial_number=serial_number,
        reason=reason,
        operator=operator,
        reference=reference,
        target_device_id=target_device_id,
        source_device_id=source_device_id,
    )
    db.add(movement)
    db.commit()
    db.refresh(movement)

    return {
        "id": movement.id,
        "part_id": movement.part_id,
        "movement_type": movement.movement_type,
        "quantity": movement.quantity,
        "serial_number": movement.serial_number,
        "reason": movement.reason,
        "operator": movement.operator,
        "reference": movement.reference,
        "target_device_id": movement.target_device_id,
        "source_device_id": movement.source_device_id,
        "created_at": movement.created_at.isoformat() if movement.created_at else None,
    }


def list_movements(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    part_id: Optional[int] = None,
    movement_type: Optional[str] = None,
    operator: Optional[str] = None,
    keyword: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """获取出入库记录列表

    Args:
        db: 数据库会话
        skip: 偏移量
        limit: 最大返回数量
        part_id: 按备件 ID 过滤
        movement_type: 按类型过滤
        operator: 按操作人过滤
        keyword: 搜索关键词（名称/型号/序列号）
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        包含 total 和 items 的字典
    """
    query = db.query(SparePartMovement)

    if part_id:
        query = query.filter(SparePartMovement.part_id == part_id)
    if movement_type:
        query = query.filter(SparePartMovement.movement_type == movement_type)
    if operator:
        query = query.filter(SparePartMovement.operator == operator)

    # 关键词搜索（名称、型号、序列号）
    if keyword:
        keyword_filter = f"%{keyword}%"
        query = query.filter(
            (SparePartMovement.serial_number.ilike(keyword_filter)) |
            (SparePartMovement.part.has(SparePart.name.ilike(keyword_filter))) |
            (SparePartMovement.part.has(SparePart.part_number.ilike(keyword_filter)))
        )

    # 时间范围筛选
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(SparePartMovement.created_at >= start_dt)
        except ValueError:
            pass
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(SparePartMovement.created_at < end_dt)
        except ValueError:
            pass

    total = query.count()
    movements = query.order_by(
        SparePartMovement.created_at.desc()
    ).offset(skip).limit(limit).all()

    return {
        "total": total,
        "items": [
            {
                "id": m.id,
                "part_id": m.part_id,
                "part_number": m.part.part_number if m.part else None,
                "name": m.part.name if m.part else None,
                "movement_type": m.movement_type,
                "quantity": m.quantity,
                "serial_number": m.serial_number,
                "unit_price": float(m.part.unit_price) if m.part and m.part.unit_price else 0.0,
                "reason": m.reason,
                "operator": m.operator,
                "reference": m.reference,
                "target_device_id": m.target_device_id,
                "target_device_name": m.target_device.name if m.target_device else None,
                "source_device_id": m.source_device_id,
                "source_device_name": m.source_device.name if m.source_device else None,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in movements
        ]
    }


def get_movement(db: Session, movement_id: int) -> Dict[str, Any]:
    """获取出入库记录详情

    Args:
        db: 数据库会话
        movement_id: 记录 ID

    Returns:
        记录信息字典

    Raises:
        ResourceNotFoundException: 记录不存在
    """
    movement = db.query(SparePartMovement).filter(
        SparePartMovement.id == movement_id
    ).first()
    if not movement:
        raise ResourceNotFoundException("SparePartMovement")

    return {
        "id": movement.id,
        "part_id": movement.part_id,
        "part_number": movement.part.part_number if movement.part else None,
        "name": movement.part.name if movement.part else None,
        "movement_type": movement.movement_type,
        "quantity": movement.quantity,
        "serial_number": movement.serial_number,
        "unit_price": float(movement.part.unit_price) if movement.part and movement.part.unit_price else 0.0,
        "reason": movement.reason,
        "operator": movement.operator,
        "reference": movement.reference,
        "created_at": movement.created_at.isoformat() if movement.created_at else None,
    }
