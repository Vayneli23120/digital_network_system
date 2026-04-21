"""Backup management router"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from pathlib import Path
import difflib
from datetime import datetime

from app.shared.database import get_db
from app.shared.models import BackupRecord, Device, CredentialGroup
from .netmiko_service import backup_device_config
from .credential_service import decrypt_password

router = APIRouter(prefix="/api/backups", tags=["backups"])


@router.post("/backup/{device_id}")
async def backup_device(device_id: int, operator: Optional[str] = None):
    """备份单个设备配置"""
    db: Session = next(get_db())

    try:
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            raise HTTPException(status_code=404, detail="设备不存在")

        # 从凭证组获取 SSH 凭证
        cred_group_name = device.credential_group or "default"
        cred_group = db.query(CredentialGroup).filter(
            CredentialGroup.name == cred_group_name
        ).first()

        if not cred_group:
            # 如果指定的凭证组不存在，尝试使用 default
            cred_group = db.query(CredentialGroup).filter(
                CredentialGroup.name == "default"
            ).first()

        if not cred_group:
            raise HTTPException(
                status_code=500,
                detail="未配置 SSH 凭证，请先在凭证管理页面添加凭证组"
            )

        credentials = {
            "username": cred_group.username,
            "password": decrypt_password(cred_group.password_encrypted),
            "secret": decrypt_password(cred_group.enable_password_encrypted) if cred_group.enable_password_encrypted else ""
        }

        # 执行备份
        from app.shared.config import get_config
        config = get_config()
        result = backup_device_config(device, credentials, config.storage.backup_dir)

        if result["success"]:
            # 记录备份记录
            backup_record = BackupRecord(
                device_id=device.id,
                device_name=device.name,
                backup_file=result["file_path"],
                file_size=result["file_size"],
                md5_hash=result["md5_hash"],
                has_change=result["has_change"],
                operator=operator
            )
            db.add(backup_record)

            # 更新设备最后备份时间
            device.last_backup_time = datetime.utcnow()

            db.commit()

            return {"success": True, "message": result["message"], "backup_id": backup_record.id}
        else:
            # 发送多渠道告警
            from app.services.notification_service import get_notification_service
            get_notification_service().notify_backup_failure(device.name, result["message"], operator)

            # 清除 Dashboard 缓存
            from ..services.cache import cache
            cache.invalidate_prefix("dashboard:")

            raise HTTPException(status_code=500, detail=result["message"])

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("")
async def list_backups(device_id: Optional[int] = None, skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """获取备份记录列表"""
    from .backup_service import list_backups as svc_list_backups
    return svc_list_backups(db, device_id=device_id, skip=skip, limit=limit)


@router.get("/{backup_id}/content")
async def get_backup_content(backup_id: int):
    """获取备份配置内容"""
    db: Session = next(get_db())
    backup = db.query(BackupRecord).filter(BackupRecord.id == backup_id).first()

    if not backup:
        raise HTTPException(status_code=404, detail="备份记录不存在")

    backup_path = Path(backup.backup_file)
    if not backup_path.exists():
        raise HTTPException(status_code=404, detail="备份文件不存在")

    with open(backup_path, "r", encoding="utf-8") as f:
        content = f.read()

    return {
        "backup_id": backup_id,
        "device_name": backup.device_name,
        "backup_time": backup.backup_time.isoformat(),
        "content": content
    }


@router.get("/{backup_id}/diff")
async def get_backup_diff(backup_id: int):
    """获取配置差异对比"""
    db: Session = next(get_db())
    backup = db.query(BackupRecord).filter(BackupRecord.id == backup_id).first()

    if not backup:
        raise HTTPException(status_code=404, detail="备份记录不存在")

    prev_backup = db.query(BackupRecord).filter(
        BackupRecord.device_id == backup.device_id,
        BackupRecord.backup_time < backup.backup_time
    ).order_by(BackupRecord.backup_time.desc()).first()

    if not prev_backup:
        return {"diff": "这是第一个备份，没有可对比的配置"}

    with open(backup.backup_file, "r", encoding="utf-8") as f:
        new_lines = f.readlines()
    with open(prev_backup.backup_file, "r", encoding="utf-8") as f:
        old_lines = f.readlines()

    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=prev_backup.backup_file,
        tofile=backup.backup_file,
        lineterm=""
    )

    return {
        "backup_id": backup_id,
        "prev_backup_id": prev_backup.id,
        "diff": "".join(diff)
    }


@router.post("/batch")
async def batch_backup(device_ids: List[int], operator: Optional[str] = None):
    """批量备份设备配置"""
    db: Session = next(get_db())
    devices = db.query(Device).filter(Device.id.in_(device_ids)).all()

    results = []

    for device in devices:
        # 从凭证组获取 SSH 凭证
        cred_group_name = device.credential_group or "default"
        cred_group = db.query(CredentialGroup).filter(
            CredentialGroup.name == cred_group_name
        ).first()

        if not cred_group:
            cred_group = db.query(CredentialGroup).filter(
                CredentialGroup.name == "default"
            ).first()

        if cred_group:
            credentials = {
                "username": cred_group.username,
                "password": decrypt_password(cred_group.password_encrypted),
                "secret": decrypt_password(cred_group.enable_password_encrypted) if cred_group.enable_password_encrypted else ""
            }
        else:
            credentials = {"username": "admin", "password": "", "secret": ""}

        from app.shared.config import get_config
        config = get_config()
        result = backup_device_config(device, credentials, config.storage.backup_dir)

        if result["success"]:
            backup_record = BackupRecord(
                device_id=device.id,
                device_name=device.name,
                backup_file=result["file_path"],
                file_size=result["file_size"],
                md5_hash=result["md5_hash"],
                has_change=result["has_change"],
                operator=operator
            )
            db.add(backup_record)
            device.last_backup_time = datetime.utcnow()
            db.commit()

        results.append({
            "device_name": device.name,
            "success": result["success"],
            "message": result["message"]
        })

    return {"results": results}
