"""
Device Service
"""
from sqlalchemy.orm import Session
from app.models.device import Device


class DeviceService:
    """设备服务"""

    @staticmethod
    def get_device(db: Session, device_id: int) -> Device:
        """获取单个设备"""
        return db.query(Device).filter(Device.id == device_id).first()

    @staticmethod
    def get_devices(db: Session, skip: int = 0, limit: int = 100):
        """获取设备列表"""
        return db.query(Device).offset(skip).limit(limit).all()
