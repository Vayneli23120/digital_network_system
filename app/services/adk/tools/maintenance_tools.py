"""维修信息工具 - 供 AI Agent 调用"""

from typing import Dict, List
from datetime import datetime, timedelta

from app.shared.database import get_db
from app.shared.models import MaintenanceRecord, SparePart


def get_maintenance_detail(maintenance_id: int) -> Dict:
    """获取维修详情
    
    Args:
        maintenance_id: 维修记录ID
    
    Returns:
        维修详情
    """
    db = next(get_db())
    try:
        record = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == maintenance_id).first()
        if not record:
            return {"error": "维修记录不存在"}
        
        device_info = {}
        if record.device:
            device_info = {
                "id": record.device.id,
                "name": record.device.name,
                "ip": record.device.ip,
                "device_type": record.device.device_type,
            }
        
        return {
            "id": record.id,
            "device": device_info,
            "maintenance_type": record.maintenance_type,
            "status": record.status,
            "description": record.description or "",
            "start_time": record.start_time.isoformat() if record.start_time else None,
            "end_time": record.end_time.isoformat() if record.end_time else None,
            "technician": record.technician or "",
            "notes": record.notes or "",
            "cost": float(record.cost) if record.cost else 0,
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()


def get_maintenance_history(device_id: int, days: int = 365) -> List[Dict]:
    """获取设备维修历史
    
    Args:
        device_id: 设备ID
        days: 查询最近多少天的历史
    
    Returns:
        维修历史列表
    """
    db = next(get_db())
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        records = db.query(MaintenanceRecord).filter(
            MaintenanceRecord.device_id == device_id,
            MaintenanceRecord.start_time >= cutoff
        ).order_by(MaintenanceRecord.start_time.desc()).limit(50).all()
        
        if not records:
            return []
        
        return [
            {
                "id": r.id,
                "maintenance_type": r.maintenance_type,
                "status": r.status,
                "description": r.description[:100] if r.description else "",
                "start_time": r.start_time.isoformat() if r.start_time else None,
                "end_time": r.end_time.isoformat() if r.end_time else None,
                "technician": r.technician or "",
                "cost": float(r.cost) if r.cost else 0,
            }
            for r in records
        ]
    except Exception as e:
        return [{"error": str(e)}]
    finally:
        db.close()


def get_repair_parts(maintenance_id: int) -> List[Dict]:
    """获取维修使用的备件
    
    Args:
        maintenance_id: 维修记录ID
    
    Returns:
        使用的备件列表
    """
    db = next(get_db())
    try:
        # 通过 maintenance_id 关联查找备件使用记录
        # 这里假设有 spare_part_usage 关联表
        parts = db.query(SparePart).filter(
            SparePart.maintenance_id == maintenance_id
        ).all()
        
        if not parts:
            return []
        
        return [
            {
                "id": p.id,
                "name": p.name,
                "part_number": p.part_number or "",
                "quantity": p.quantity or 1,
                "unit_price": float(p.unit_price) if p.unit_price else 0,
                "total_price": float(p.unit_price or 0) * (p.quantity or 1),
            }
            for p in parts
        ]
    except Exception as e:
        return [{"error": str(e)}]
    finally:
        db.close()
