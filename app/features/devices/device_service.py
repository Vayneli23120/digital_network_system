"""
设备管理服务层

封装设备 CRUD 操作的业务逻辑，供路由和测试使用。
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.shared.models import Device
from app.shared.exceptions import ResourceNotFoundException, ConflictException


def list_devices(db: Session, status: Optional[str] = None, role: Optional[str] = None,
                 device_type: Optional[str] = None, deployment_status: Optional[str] = None,
                 reachability: Optional[str] = None, skip: int = 0, limit: int = 200) -> Dict[str, Any]:
    """获取设备列表

    Args:
        db: 数据库会话
        status: 按旧状态过滤（兼容）
        role: 按角色过滤
        device_type: 按设备类型过滤
        deployment_status: 按部署状态过滤
        reachability: 按可达性状态过滤
        skip: 偏移量
        limit: 最大返回数量

    Returns:
        包含 total 和 items 的字典
    """
    query = db.query(Device)

    # 新字段过滤
    if deployment_status:
        query = query.filter(Device.deployment_status == deployment_status)
    if reachability:
        query = query.filter(Device.reachability == reachability)

    # 兼容旧字段过滤
    if status:
        query = query.filter(Device.status == status)
    if role:
        query = query.filter(Device.role == role)
    if device_type:
        query = query.filter(Device.device_type == device_type)

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
                # 新字段
                "deployment_status": d.deployment_status,
                "reachability": d.reachability,
                "last_reachability_check": d.last_reachability_check.isoformat() if d.last_reachability_check else None,
                "reachability_latency_ms": d.reachability_latency_ms,
                "reachability_method": d.reachability_method,
                # 兼容旧字段
                "status": d.status,
                "device_type": d.device_type,
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

    # 处理 modules 字段 - 转换为 JSON
    modules_data = device_data.pop("modules", None)
    if modules_data:
        import json
        device_data["modules"] = json.dumps(modules_data)

    # 设置默认值 - 新字段
    if "deployment_status" not in device_data:
        device_data["deployment_status"] = "un-used"
    if "reachability" not in device_data:
        device_data["reachability"] = "unknown"

    # 兼容旧字段：如果传入 status，映射到 deployment_status
    if "status" in device_data and "deployment_status" not in device_data:
        status_map = {
            "online": "in-use",
            "offline": "un-used",
            "maintenance": "maintenance",
            "retired": "retired"
        }
        device_data["deployment_status"] = status_map.get(device_data["status"], "un-used")

    device = Device(**device_data)
    db.add(device)
    db.commit()
    db.refresh(device)

    return {
        "id": device.id,
        "name": device.name,
        "ip": device.ip,
        "model": device.model,
        "location": device.location,
        "device_type": device.device_type,
        "role": device.role,
        # 新字段
        "deployment_status": device.deployment_status,
        "reachability": device.reachability,
        # 兼容旧字段
        "status": device.status,
        "credential_group": device.credential_group,
        "vendor": device.vendor,
        "purchase_date": device.purchase_date.isoformat() if device.purchase_date else None,
        "purchase_cost": float(device.purchase_cost) if device.purchase_cost else 0,
        "modules": device.get_modules_list(),
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
        "location": device.location,
        "device_type": device.device_type,
        "role": device.role,
        # 新字段
        "deployment_status": device.deployment_status,
        "reachability": device.reachability,
        "last_reachability_check": device.last_reachability_check.isoformat() if device.last_reachability_check else None,
        "reachability_latency_ms": device.reachability_latency_ms,
        "reachability_method": device.reachability_method,
        # 兼容旧字段
        "status": device.status,
        "credential_group": device.credential_group,
        "vendor": device.vendor,
        "purchase_date": device.purchase_date.isoformat() if device.purchase_date else None,
        "purchase_cost": float(device.purchase_cost) if device.purchase_cost else 0,
        "modules": device.get_modules_list(),
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

    # 新字段允许更新
    allowed_fields = [
        "ip", "model", "location",
        "device_type", "role", "purchase_date", "vendor", "purchase_cost",
        "photo_dir", "credential_group", "name",
        # 新字段
        "deployment_status",
        # 兼容旧字段（status 将被映射到 deployment_status）
        "status",
    ]

    for key, value in update_data.items():
        if key in allowed_fields and hasattr(device, key):
            # 兼容映射：status → deployment_status
            if key == "status":
                status_map = {
                    "online": "in-use",
                    "offline": "un-used",
                    "maintenance": "maintenance",
                    "retired": "retired"
                }
                device.deployment_status = status_map.get(value, "un-used")
                device.status = value  # 兼容保留旧字段
            else:
                setattr(device, key, value)

    # 处理 modules 字段
    if "modules" in update_data:
        import json
        if update_data["modules"]:
            device.modules = json.dumps(update_data["modules"])
        else:
            device.modules = None

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
        # 新字段
        "deployment_status": device.deployment_status,
        "reachability": device.reachability,
        # 兼容旧字段
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

    # 先断开 FaultRecord 和 MaintenanceRecord 之间的循环依赖
    # 将 FaultRecord 的 maintenance_id 设置为 NULL
    from app.shared.models import FaultRecord, MaintenanceRecord
    db.query(FaultRecord).filter(
        FaultRecord.device_id == device_id,
        FaultRecord.maintenance_id.isnot(None)
    ).update({"maintenance_id": None}, synchronize_session="fetch")

    # 删除设备关联的 MaintenanceRecord（它们可能引用 FaultRecord）
    db.query(MaintenanceRecord).filter(
        MaintenanceRecord.device_id == device_id
    ).delete(synchronize_session="fetch")

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
