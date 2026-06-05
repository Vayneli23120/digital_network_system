"""Device management router"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional, List
from pathlib import Path
import shutil
from datetime import datetime
from io import BytesIO

try:
    import openpyxl
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

try:
    from starlette.responses import StreamingResponse
except ImportError:
    StreamingResponse = None

from pydantic import BaseModel

from app.shared.database import get_db
from app.shared.models import Device, BackupRecord, FaultRecord, MaintenanceRecord, DevicePhoto, CredentialGroup, SparePartInstance, SparePart
from app.shared.config import get_config

config = get_config()

router = APIRouter(prefix="/api/devices", tags=["devices"])


# ============ Pydantic 模型 ============

class DeviceCreate(BaseModel):
    name: str
    ip: str
    model: Optional[str] = None
    location: Optional[str] = None
    device_type: str = "other"
    role: str = "access"
    # 新字段：部署状态
    deployment_status: str = "un-used"  # in-use, un-used, maintenance, retired
    # 兼容旧字段（将被映射到 deployment_status）
    status: Optional[str] = None
    vendor: Optional[str] = None
    purchase_cost: float = 0
    credential_group: str = "default"
    modules: Optional[List[dict]] = None  # [{"type": "main", "serial_number": "SN001"}]


class DeviceUpdate(BaseModel):
    ip: Optional[str] = None
    model: Optional[str] = None
    location: Optional[str] = None
    device_type: Optional[str] = None
    role: Optional[str] = None
    # 新字段：部署状态
    deployment_status: Optional[str] = None
    # 兼容旧字段（将被映射到 deployment_status）
    status: Optional[str] = None
    vendor: Optional[str] = None
    purchase_cost: Optional[float] = None
    credential_group: Optional[str] = None
    name: Optional[str] = None
    modules: Optional[List[dict]] = None


@router.get("")
async def list_devices(status: Optional[str] = None, role: Optional[str] = None,
                        device_type: Optional[str] = None,
                        deployment_status: Optional[str] = None,
                        reachability: Optional[str] = None,
                        skip: int = 0, limit: int = 200,
                        db: Session = Depends(get_db)):
    """获取设备列表

    Args:
        status: 按旧状态过滤（兼容）
        deployment_status: 按部署状态过滤 (in-use/un-used/maintenance/retired)
        reachability: 按可达性过滤 (reachable/unreachable/unknown)
    """
    from .device_service import list_devices as svc_list_devices
    return svc_list_devices(db, status=status, role=role, device_type=device_type,
                           deployment_status=deployment_status, reachability=reachability,
                           skip=skip, limit=limit)


@router.get("/export")
async def export_devices():
    """导出设备信息为 Excel 文件"""
    if not EXCEL_AVAILABLE:
        raise HTTPException(status_code=500, detail="Excel 支持未安装，请运行 pip install openpyxl")

    db: Session = next(get_db())

    try:
        devices = db.query(Device).order_by(Device.id).limit(5000).all()

        # 创建 Excel 工作簿
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Devices"

        # 表头
        headers = ["name", "ip", "model", "serial_number", "location", "device_type", "role",
                   "deployment_status", "reachability", "credential_group", "vendor", "purchase_cost"]
        ws.append(headers)

        # 数据
        for device in devices:
            ws.append([
                device.name,
                device.ip or "",
                device.model or "",
                device.serial_number or "",
                device.location or "",
                device.device_type or "other",
                device.role or "",
                device.deployment_status or "un-used",
                device.reachability or "unknown",
                device.credential_group or "default",
                device.vendor or "",
                float(device.purchase_cost) if device.purchase_cost else 0
            ])

        # 输出为字节流
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=devices.xlsx"}
        )
    finally:
        db.close()


@router.post("/import")
async def import_devices(file: UploadFile = File(...)):
    """从 Excel 文件导入设备信息"""
    if not EXCEL_AVAILABLE:
        raise HTTPException(status_code=500, detail="Excel 支持未安装，请运行 pip install openpyxl")

    db: Session = next(get_db())

    try:
        # 读取上传的文件
        content = await file.read()
        wb = openpyxl.load_workbook(BytesIO(content))
        ws = wb.active

        # 读取表头
        headers = [cell.value for cell in ws[1]]

        success_count = 0
        failed_count = 0
        errors = []

        # 处理数据行
        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            try:
                # 跳过空行
                if not any(row):
                    continue

                # 构建设备数据字典
                device_data = {}
                for i, header in enumerate(headers):
                    if header and i < len(row):
                        device_data[header] = row[i]

                # 验证必填字段
                if not device_data.get("name") or not device_data.get("ip"):
                    errors.append(f"第{row_idx}行：缺少必填字段 (name 或 ip)")
                    failed_count += 1
                    continue

                # 检查设备名称是否已存在
                existing = db.query(Device).filter(Device.name == device_data["name"]).first()
                if existing:
                    errors.append(f"第{row_idx}行：设备名称 '{device_data['name']}' 已存在")
                    failed_count += 1
                    continue

                # 创建设备
                device = Device(
                    name=device_data.get("name"),
                    ip=device_data.get("ip"),
                    model=device_data.get("model", ""),
                    serial_number=device_data.get("serial_number", ""),
                    location=device_data.get("location", ""),
                    role=device_data.get("role", "access"),
                    # 新字段
                    deployment_status=device_data.get("deployment_status", "un-used"),
                    reachability=device_data.get("reachability", "unknown"),
                    # 兼容旧字段
                    status=device_data.get("status", "online"),
                    credential_group=device_data.get("credential_group", "default"),
                    vendor=device_data.get("vendor", ""),
                    device_type=device_data.get("device_type", "other"),
                    purchase_cost=device_data.get("purchase_cost", 0)
                )
                db.add(device)
                success_count += 1

            except Exception as e:
                errors.append(f"第{row_idx}行：{str(e)}")
                failed_count += 1

        db.commit()

        return {
            "success": success_count,
            "failed": failed_count,
            "errors": errors
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"导入失败：{str(e)}")
    finally:
        db.close()


# ============ 厂商管理 API（放在 /{device_id} 之前，避免路由匹配冲突）============

@router.get("/vendors")
async def list_vendors():
    """获取支持的厂商列表"""
    from .vendor_service import get_supported_vendors
    return get_supported_vendors()


@router.get("/vendors/{vendor}")
async def get_vendor(vendor: str):
    """获取厂商详细信息"""
    from .vendor_service import get_vendor_info
    return get_vendor_info(vendor)


# ============ 可达性监控 API ============

@router.post("/{device_id}/check-reachability")
async def manual_check_reachability(device_id: int):
    """手动触发单设备可达性检测

    立即检测设备可达性并返回结果。
    """
    from app.services.reachability_monitor import get_reachability_monitor

    db = next(get_db())
    try:
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            raise HTTPException(status_code=404, detail="设备不存在")

        monitor = get_reachability_monitor()
        result = monitor.check_device_reachability(db, device)

        return {
            "device_id": device_id,
            "device_name": device.name,
            "reachability": device.reachability,
            "latency_ms": device.reachability_latency_ms,
            "method": device.reachability_method,
            "last_check": device.last_reachability_check.isoformat() if device.last_reachability_check else None,
        }
    finally:
        db.close()


@router.get("/reachability-stats")
async def get_reachability_stats():
    """获取可达性统计

    返回已部署设备的可达性状态统计。
    """
    db = next(get_db())
    try:
        total = db.query(Device).filter(Device.deployment_status == 'in-use').count()
        reachable = db.query(Device).filter(
            Device.deployment_status == 'in-use',
            Device.reachability == 'reachable'
        ).count()
        unreachable = db.query(Device).filter(
            Device.deployment_status == 'in-use',
            Device.reachability == 'unreachable'
        ).count()
        unknown = db.query(Device).filter(
            Device.deployment_status == 'in-use',
            Device.reachability == 'unknown'
        ).count()

        # 按设备类型统计
        device_types = ['uce', 'core_switch', 'server_switch', 'office_switch', 'ap', 'wlc', 'router', 'pa', 'ftd', 'other']
        by_type = {}
        for dtype in device_types:
            type_total = db.query(Device).filter(
                Device.device_type == dtype,
                Device.deployment_status == 'in-use'
            ).count()
            by_type[dtype] = {
                'total': type_total,
                'reachable': db.query(Device).filter(
                    Device.device_type == dtype,
                    Device.deployment_status == 'in-use',
                    Device.reachability == 'reachable'
                ).count(),
                'unreachable': db.query(Device).filter(
                    Device.device_type == dtype,
                    Device.deployment_status == 'in-use',
                    Device.reachability == 'unreachable'
                ).count(),
            }

        return {
            "total_deployed": total,
            "reachable": reachable,
            "unreachable": unreachable,
            "unknown": unknown,
            "online_rate": round(reachable / total * 100, 2) if total > 0 else 0,
            "by_type": by_type,
        }
    finally:
        db.close()


@router.get("/monitor/status")
async def get_monitor_status():
    """获取可达性监控服务状态"""
    from app.services.reachability_monitor import get_reachability_monitor
    monitor = get_reachability_monitor()
    return monitor.get_stats()


@router.get("/{device_id}")
async def get_device(device_id: int, db: Session = Depends(get_db)):
    """获取设备详情"""
    from .device_service import get_device as svc_get_device
    from app.shared.exceptions import ResourceNotFoundException
    try:
        device = svc_get_device(db, device_id)
        photos = db.query(DevicePhoto).filter(DevicePhoto.device_id == device_id).all()
        backups = db.query(BackupRecord).filter(BackupRecord.device_id == device_id).order_by(BackupRecord.backup_time.desc()).limit(5).all()
        faults = db.query(FaultRecord).filter(FaultRecord.device_id == device_id).order_by(FaultRecord.created_at.desc()).limit(5).all()
        maintenances = db.query(MaintenanceRecord).filter(MaintenanceRecord.device_id == device_id).order_by(MaintenanceRecord.created_at.desc()).limit(5).all()

        return {
            **device,
            "photos": [{"id": p.id, "photo_type": p.photo_type, "photo_path": p.photo_path, "upload_date": p.upload_date.isoformat()} for p in photos],
            "recent_backups": [{"id": b.id, "backup_time": b.backup_time.isoformat(), "has_change": b.has_change} for b in backups],
            "recent_faults": [{"id": f.id, "fault_no": f.fault_no, "severity": f.severity, "status": f.status, "description": f.description, "downtime_minutes": f.downtime_minutes, "impact": f.impact, "created_at": f.created_at.isoformat()} for f in faults],
            "recent_maintenances": [{"id": m.id, "maint_no": m.maint_no, "maint_type": m.maint_type, "parts_replaced": m.parts_replaced, "parts_cost": float(m.parts_cost or 0), "labor_hours": float(m.labor_hours or 0), "labor_cost": float(m.labor_cost or 0), "vendor": m.vendor, "description": m.description, "maint_time": m.maint_time.isoformat() if m.maint_time else None, "created_at": m.created_at.isoformat()} for m in maintenances],
        }
    except ResourceNotFoundException:
        raise HTTPException(status_code=404, detail="设备不存在")


@router.post("")
async def create_device(device_data: DeviceCreate, db: Session = Depends(get_db)):
    """创建新设备"""
    from .device_service import create_device as svc_create_device
    from app.shared.exceptions import ConflictException
    try:
        result = svc_create_device(db, device_data.model_dump())
        from app.shared.cache import cache
        cache.invalidate_prefix("dashboard:")
        return {"id": result["id"], "message": "设备创建成功"}
    except ConflictException as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.put("/{device_id}")
async def update_device(device_id: int, device_data: DeviceUpdate, db: Session = Depends(get_db)):
    """更新设备信息"""
    from .device_service import update_device as svc_update_device
    from app.shared.exceptions import ResourceNotFoundException
    try:
        result = svc_update_device(db, device_id, device_data.model_dump(exclude_unset=True))
        return {"id": result["id"], "message": "更新成功"}
    except ResourceNotFoundException:
        raise HTTPException(status_code=404, detail="设备不存在")


@router.delete("/{device_id}")
async def delete_device(device_id: int, db: Session = Depends(get_db)):
    """删除设备"""
    from .device_service import delete_device as svc_delete_device
    from app.shared.exceptions import ResourceNotFoundException
    try:
        result = svc_delete_device(db, device_id)
        from app.shared.cache import cache
        cache.invalidate_prefix("dashboard:")
        return result
    except ResourceNotFoundException:
        raise HTTPException(status_code=404, detail="设备不存在")


# ============ 照片管理 API ============

@router.post("/{device_id}/photos")
async def upload_device_photo(
    device_id: int,
    photo: UploadFile = File(...),
    photo_type: str = "other",
    uploader: str = None
):
    """上传设备照片"""
    db: Session = next(get_db())

    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")

    # 确保目录存在
    photo_dir = Path(config.storage.photo_dir) / device.name / "photos"
    photo_dir.mkdir(parents=True, exist_ok=True)

    # 保存文件
    filename = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{photo.filename}"
    file_path = photo_dir / filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(photo.file, buffer)

    # 记录数据库
    photo_record = DevicePhoto(
        device_id=device_id,
        device_name=device.name,
        photo_path=str(file_path),
        photo_type=photo_type,
        uploader=uploader or "system"
    )
    db.add(photo_record)
    db.commit()
    db.refresh(photo_record)

    return {"id": photo_record.id, "path": str(file_path), "filename": filename}


@router.get("/{device_id}/photos")
async def get_device_photos(device_id: int):
    """获取设备照片列表"""
    db: Session = next(get_db())
    photos = db.query(DevicePhoto).filter(
        DevicePhoto.device_id == device_id
    ).order_by(DevicePhoto.upload_date.desc()).all()

    return {
        "items": [
            {
                "id": p.id,
                "photo_type": p.photo_type,
                "photo_path": p.photo_path,
                "upload_date": p.upload_date.isoformat(),
                "uploader": p.uploader
            }
            for p in photos
        ]
    }


@router.delete("/{device_id}/photos/{photo_id}")
async def delete_device_photo(device_id: int, photo_id: int):
    """删除设备照片"""
    db: Session = next(get_db())
    photo = db.query(DevicePhoto).filter(
        DevicePhoto.id == photo_id,
        DevicePhoto.device_id == device_id
    ).first()

    if not photo:
        raise HTTPException(status_code=404, detail="照片不存在")

    # 删除文件
    photo_path = Path(photo.photo_path)
    if photo_path.exists():
        photo_path.unlink()

    # 删除记录
    db.delete(photo)
    db.commit()

    return {"message": "删除成功"}


@router.get("/{device_id}/inventory")
async def get_device_inventory(device_id: int, db: Session = Depends(get_db)):
    """获取设备当前安装的备件列表

    Args:
        device_id: 设备 ID

    Returns:
        设备当前安装的备件列表
    """
    # 验证设备存在
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")

    # 查询当前安装在该设备上的备件（状态为 inuse）
    instances = db.query(SparePartInstance).filter(
        SparePartInstance.installed_device_id == device_id,
        SparePartInstance.status == "inuse"
    ).all()

    return {
        "device_id": device_id,
        "device_name": device.name,
        "items": [
            {
                "instance_id": i.id,
                "serial_number": i.serial_number,
                "po_number": i.po_number,  # PO号
                "part_id": i.part_id,
                "part_number": i.part.part_number if i.part else None,
                "part_name": i.part.name if i.part else None,
                "category": i.part.category if i.part else None,
                "unit_price": float(i.unit_price) if i.unit_price else 0.0,
                "installed_at": i.installed_at.isoformat() if i.installed_at else None,
                "installed_by": i.installed_by,
                "notes": i.notes,
            }
            for i in instances
        ],
        "total": len(instances)
    }
