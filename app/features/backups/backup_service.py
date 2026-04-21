"""
备份管理服务层

封装备份操作的 CRUD 业务逻辑，供路由和测试使用。
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.shared.models import BackupRecord
from app.shared.exceptions import ResourceNotFoundException


def list_backups(db: Session, device_id: Optional[int] = None, skip: int = 0, limit: int = 50) -> Dict[str, Any]:
    """获取备份记录列表

    Args:
        db: 数据库会话
        device_id: 按设备 ID 过滤
        limit: 最大返回数量

    Returns:
        包含 total 和 items 的字典
    """
    query = db.query(BackupRecord)

    if device_id:
        query = query.filter(BackupRecord.device_id == device_id)

    total = query.count()
    backups = query.order_by(BackupRecord.backup_time.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "items": [
            {
                "id": b.id,
                "device_id": b.device_id,
                "device_name": b.device_name,
                "backup_file": b.backup_file,
                "file_size": b.file_size,
                "md5_hash": b.md5_hash,
                "has_change": b.has_change,
                "backup_time": b.backup_time.isoformat() if b.backup_time else None,
                "operator": b.operator,
            }
            for b in backups
        ]
    }


def delete_backup(db: Session, backup_id: int) -> Dict[str, Any]:
    """删除备份记录

    Args:
        db: 数据库会话
        backup_id: 备份记录 ID

    Returns:
        操作结果字典

    Raises:
        ResourceNotFoundException: 备份记录不存在
    """
    backup = db.query(BackupRecord).filter(BackupRecord.id == backup_id).first()
    if not backup:
        raise ResourceNotFoundException("Backup record")

    db.delete(backup)
    db.commit()

    return {"success": True, "message": "删除成功"}
