"""
设备管理服务层

封装设备 CRUD 操作的业务逻辑，供路由和测试使用。
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime

from app.shared.models import Device, SparePart, SparePartInstance
from app.shared.exceptions import ResourceNotFoundException, ConflictException


def _sync_modules_to_inventory(db: Session, device_id: int, modules: List[Dict[str, Any]]) -> None:
    """同步设备模块到资产库存

    将模块信息同步到 SparePartInstance 表，状态为 inuse（安装在设备上）。
    这些模块不会出现在备件库存（in_stock）中。

    Args:
        db: 数据库会话
        device_id: 设备 ID
        modules: 模块列表，格式 [{"type": "main", "pid": "C9300-24P", "serial_number": "ABC123"}]
    """
    if not modules:
        return

    for module in modules:
        pid = module.get("pid", "")
        serial_number = module.get("serial_number", "")
        module_type = module.get("type", "other")

        if not pid or not serial_number:
            continue

        # 检查序列号是否已存在
        existing_instance = db.query(SparePartInstance).filter(
            SparePartInstance.serial_number == serial_number
        ).first()

        if existing_instance:
            # 如果已存在，更新设备关联和分类信息
            if existing_instance.installed_device_id != device_id:
                # 如果之前安装在其他设备上，记录拆卸信息
                if existing_instance.installed_device_id:
                    existing_instance.removed_from_device_id = existing_instance.installed_device_id
                    existing_instance.removed_at = datetime.utcnow()
                # 更新为当前设备
                existing_instance.installed_device_id = device_id
                existing_instance.installed_at = datetime.utcnow()
                existing_instance.status = "inuse"

            # 更新 SparePart 的分类（根据模块类型）
            if existing_instance.part:
                category_map = {
                    "main": "主机模块",
                    "expansion": "扩展模块",
                    "power": "电源模块",
                    "sfp": "光模块",
                    "fan": "风扇模块",
                    "other": "其他"
                }
                new_category = category_map.get(module_type, "其他")
                if existing_instance.part.category != new_category:
                    existing_instance.part.category = new_category

            # 更新备注中的模块类型
            existing_instance.notes = f"设备自带模块，类型: {module_type}"
            continue

        # 查找或创建 SparePart（型号基础信息）
        spare_part = db.query(SparePart).filter(
            SparePart.part_number == pid
        ).first()

        if not spare_part:
            # 根据模块类型确定分类
            category_map = {
                "main": "主机模块",
                "expansion": "扩展模块",
                "power": "电源模块",
                "sfp": "光模块",
                "fan": "风扇模块",
                "other": "其他"
            }
            category = category_map.get(module_type, "其他")

            # 创建新的 SparePart
            spare_part = SparePart(
                name=pid,  # 使用型号作为名称
                part_number=pid,
                category=category,
                manufacturer="",  # 可以后续补充
                description=f"设备自带模块，通过SSH自动获取",
                quantity_in_stock=0,  # 不计入库存
                min_quantity=0
            )
            db.add(spare_part)
            db.flush()  # 获取 part_id

        # 创建 SparePartInstance
        instance = SparePartInstance(
            part_id=spare_part.id,
            serial_number=serial_number,
            status="inuse",  # 直接标记为在设备上使用
            installed_device_id=device_id,
            installed_at=datetime.utcnow(),
            installed_by="system",  # 系统自动创建
            notes=f"设备自带模块，类型: {module_type}"
        )
        db.add(instance)

    db.commit()


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

    # 一次性批量查询活跃故障计数，避免 n+1 查询
    device_ids = [d.id for d in devices]
    fault_counts: dict = {}
    if device_ids:
        from sqlalchemy import func
        from app.shared.models import FaultRecord
        rows = (
            db.query(FaultRecord.device_id, func.count(FaultRecord.id))
            .filter(
                FaultRecord.device_id.in_(device_ids),
                FaultRecord.status.in_(["open", "in_progress"]),
            )
            .group_by(FaultRecord.device_id)
            .all()
        )
        fault_counts = {row[0]: row[1] for row in rows}

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
                "active_fault_count": fault_counts.get(d.id, 0),
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

    # 同步模块到设备资产
    if modules_data:
        _sync_modules_to_inventory(db, device.id, modules_data)

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
    modules_data = None
    if "modules" in update_data:
        import json
        modules_data = update_data["modules"]
        if modules_data:
            device.modules = json.dumps(modules_data)
        else:
            device.modules = None

    db.commit()
    db.refresh(device)

    # 同步模块到设备资产
    if modules_data:
        _sync_modules_to_inventory(db, device.id, modules_data)

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
