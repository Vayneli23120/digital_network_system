"""设备信息查询工具 - 供 AI Agent 调用"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta

from app.shared.database import get_db
from app.shared.models import Device


def get_device_info(device_id: int) -> Dict:
    """获取设备详细信息

    Args:
        device_id: 设备ID

    Returns:
        设备信息字典（名称、类型、IP、状态等）
    """
    db = next(get_db())
    try:
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            return {"error": "设备不存在"}
        return {
            "id": device.id,
            "name": device.name,
            "device_type": device.device_type,
            "ip": device.ip,
            "status": device.status,
            "vendor": device.vendor,
            "model": device.model or "",
            "location": device.location or "",
            "uptime_days": device.uptime_days or 0,
            "health_score": device.health_score or 100,
            "last_seen": device.last_seen.isoformat() if device.last_seen else None,
            "created_at": device.created_at.isoformat() if device.created_at else None,
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()


def get_device_metrics(device_id: int, hours: int = 24) -> Dict:
    """获取设备运行指标（从设备基础信息获取）

    Args:
        device_id: 设备ID
        hours: 获取最近多少小时的数据（预留参数）

    Returns:
        设备指标数据（健康评分等）
    """
    db = next(get_db())
    try:
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            return {"error": "设备不存在"}

        # 返回设备基础指标（DeviceMetric 表不存在）
        return {
            "device_name": device.name,
            "health_score": device.health_score or 100,
            "uptime_days": device.uptime_days or 0,
            "status": device.status,
            "message": "详细指标数据需配置监控采集"
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()


def search_devices(keyword: str) -> List[Dict]:
    """按关键词搜索设备
    
    Args:
        keyword: 搜索关键词（名称、IP等）
    
    Returns:
        匹配的设备列表
    """
    db = next(get_db())
    try:
        devices = db.query(Device).filter(
            Device.name.ilike(f"%{keyword}%") |
            Device.ip.ilike(f"%{keyword}%") |
            Device.location.ilike(f"%{keyword}%")
        ).limit(10).all()
        return [
            {
                "id": d.id,
                "name": d.name,
                "ip": d.ip,
                "status": d.status,
                "device_type": d.device_type,
                "location": d.location or ""
            }
            for d in devices
        ]
    except Exception as e:
        return [{"error": str(e)}]
    finally:
        db.close()
