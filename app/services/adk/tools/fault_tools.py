"""故障信息查询工具 - 供 AI Agent 调用"""

from typing import Dict, List
from datetime import datetime, timedelta

from app.shared.database import get_db
from app.shared.models import FaultRecord


def get_fault_detail(fault_id: int) -> Dict:
    """获取故障详细信息

    Args:
        fault_id: 故障ID

    Returns:
        故障详情（设备、类型、描述、状态等）
    """
    db = next(get_db())
    try:
        fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()
        if not fault:
            return {"error": "故障不存在"}
        
        device_info = {}
        if fault.device:
            device_info = {
                "id": fault.device.id,
                "name": fault.device.name,
                "ip": fault.device.ip,
                "device_type": fault.device.device_type,
                "vendor": fault.device.vendor,
            }
        
        return {
            "id": fault.id,
            "fault_type": fault.fault_type,
            "severity": fault.severity,
            "description": fault.description,
            "status": fault.status,
            "device": device_info,
            "detected_at": fault.detected_at.isoformat() if fault.detected_at else None,
            "resolved_at": fault.resolved_at.isoformat() if fault.resolved_at else None,
            "root_cause": fault.root_cause or "",
            "resolution": fault.resolution or "",
            "assigned_to": fault.assigned_to or "",
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()


def get_fault_history(device_id: int, days: int = 30) -> List[Dict]:
    """获取设备故障历史
    
    Args:
        device_id: 设备ID
        days: 查询最近多少天的历史
    
    Returns:
        故障历史列表
    """
    db = next(get_db())
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        faults = db.query(FaultRecord).filter(
            FaultRecord.device_id == device_id,
            FaultRecord.detected_at >= cutoff
        ).order_by(FaultRecord.detected_at.desc()).limit(50).all()
        
        if not faults:
            return []
        
        return [
            {
                "id": f.id,
                "fault_type": f.fault_type,
                "severity": f.severity,
                "description": f.description[:200] if f.description else "",
                "status": f.status,
                "detected_at": f.detected_at.isoformat() if f.detected_at else None,
                "resolved_at": f.resolved_at.isoformat() if f.resolved_at else None,
                "root_cause": f.root_cause or "",
            }
            for f in faults
        ]
    except Exception as e:
        return [{"error": str(e)}]
    finally:
        db.close()


def get_recent_faults(limit: int = 20) -> List[Dict]:
    """获取最近发生的故障
    
    Args:
        limit: 返回数量限制
    
    Returns:
        最近故障列表
    """
    db = next(get_db())
    try:
        faults = db.query(FaultRecord).order_by(FaultRecord.detected_at.desc()).limit(limit).all()
        return [
            {
                "id": f.id,
                "device_name": f.device.name if f.device else "Unknown",
                "fault_type": f.fault_type,
                "severity": f.severity,
                "description": f.description[:100] if f.description else "",
                "status": f.status,
                "detected_at": f.detected_at.isoformat() if f.detected_at else None,
            }
            for f in faults
        ]
    except Exception as e:
        return [{"error": str(e)}]
    finally:
        db.close()
