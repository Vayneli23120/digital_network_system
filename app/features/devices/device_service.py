"""
设备管理服务层

封装设备 CRUD 操作的业务逻辑，供路由和测试使用。
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.shared.models import Device
from app.shared.exceptions import ResourceNotFoundException, ConflictException


def list_devices(db: Session, status: Optional[str] = None, role: Optional[str] = None, skip: int = 0, limit: int = 200) -> Dict[str, Any]:
    """获取设备列表

    Args:
        db: 数据库会话
        status: 按状态过滤
        role: 按角色过滤
        skip: 偏移量
        limit: 最大返回数量

    Returns:
        包含 total 和 items 的字典
    """
    query = db.query(Device)

    if status:
        query = query.filter(Device.status == status)
    if role:
        query = query.filter(Device.role == role)

    total = query.count()
    devices = query.offset(skip).limit(limit).all()

    return {
        "total": total,
        "items": [
            {
                "id": d.id,
                "name": d.name,
                "ip": d.ip,
                "model": d.model,
                "serial_number": d.serial_number,
                "location": d.location,
                "role": d.role,
                "status": d.status,
                "credential_group": d.credential_group,
                "last_backup_time": d.last_backup_time.isoformat() if d.last_backup_time else None,
            }
            for d in devices
        ]
    }


def create_device(db: Session, device_data: Dict[str, Any]) -> Dict[str, Any]:
    """创建新设备

    Args:
        db: 数据库会话
        device_data: 设备数据字典

    Returns:
        创建的设备信息字典

    Raises:
        ConflictException: 设备名称已存在
    """
    # 检查名称是否重复
    existing = db.query(Device).filter(Device.name == device_data.get("name")).first()
    if existing:
        raise ConflictException(f"设备名称 '{device_data.get('name')}' already exists")

    device = Device(**device_data)
    db.add(device)
    db.commit()
    db.refresh(device)

    return {
        "id": device.id,
        "name": device.name,
        "ip": device.ip,
        "model": device.model,
        "serial_number": device.serial_number,
        "location": device.location,
        "role": device.role,
        "status": device.status,
        "credential_group": device.credential_group,
        "vendor": device.vendor,
        "purchase_date": device.purchase_date.isoformat() if device.purchase_date else None,
        "purchase_cost": float(device.purchase_cost) if device.purchase_cost else 0,
    }


def get_device(db: Session, device_id: int) -> Dict[str, Any]:
    """获取设备详情

    Args:
        db: 数据库会话
        device_id: 设备 ID

    Returns:
        设备信息字典

    Raises:
        ResourceNotFoundException: 设备不存在
    """
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise ResourceNotFoundException("Device")

    return {
        "id": device.id,
        "name": device.name,
        "ip": device.ip,
        "model": device.model,
        "serial_number": device.serial_number,
        "location": device.location,
        "role": device.role,
        "status": device.status,
        "credential_group": device.credential_group,
        "vendor": device.vendor,
        "purchase_date": device.purchase_date.isoformat() if device.purchase_date else None,
        "purchase_cost": float(device.purchase_cost) if device.purchase_cost else 0,
    }


def update_device(db: Session, device_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
    """更新设备信息

    Args:
        db: 数据库会话
        device_id: 设备 ID
        update_data: 要更新的字段

    Returns:
        更新后的设备信息字典

    Raises:
        ResourceNotFoundException: 设备不存在
    """
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise ResourceNotFoundException("Device")

    allowed_fields = [
        "ip", "model", "serial_number", "location",
        "role", "status", "purchase_date", "vendor", "purchase_cost",
        "photo_dir", "credential_group", "name"
    ]

    for key, value in update_data.items():
        if key in allowed_fields and hasattr(device, key):
            setattr(device, key, value)

    db.commit()
    db.refresh(device)

    return {
        "id": device.id,
        "name": device.name,
        "ip": device.ip,
        "model": device.model,
        "serial_number": device.serial_number,
        "location": device.location,
        "role": device.role,
        "status": device.status,
        "credential_group": device.credential_group,
        "message": "更新成功",
    }


def delete_device(db: Session, device_id: int) -> Dict[str, Any]:
    """删除设备

    Args:
        db: 数据库会话
        device_id: 设备 ID

    Returns:
        操作结果字典

    Raises:
        ResourceNotFoundException: 设备不存在
    """
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise ResourceNotFoundException("Device")

    db.delete(device)
    db.commit()

    return {"success": True, "message": "删除成功"}


def batch_update_devices(db: Session, device_ids: List[int], update_data: Dict[str, Any]) -> Dict[str, Any]:
    """批量更新设备状态

    Args:
        db: 数据库会话
        device_ids: 设备 ID 列表
        update_data: 要更新的字段

    Returns:
        包含更新数量的字典
    """
    updated = db.query(Device).filter(Device.id.in_(device_ids)).update(
        update_data, synchronize_session="fetch"
    )
    db.commit()

    return {"updated": updated}
