"""AI服务管理器入口

提供便捷的AI分析函数，供各模块调用。
"""

from typing import Dict, Optional
from sqlalchemy.orm import Session

from app.services.ai.manager.ai_manager import ai_manager


async def analyze_fault(fault_id: int, db: Session) -> Dict:
    """
    分析故障记录

    Args:
        fault_id: 故障ID
        db: 数据库会话

    Returns:
        分析结果
    """
    return await ai_manager.analyze_fault(fault_id, db)


async def analyze_device_health(device_id: int, db: Session) -> Dict:
    """
    AI辅助健康评分分析

    Args:
        device_id: 设备ID
        db: 数据库会话

    Returns:
        分析结果
    """
    return await ai_manager.analyze_device_health(device_id, db)


async def generate_maintenance_summary(maintenance_id: int, db: Session) -> Dict:
    """
    生成维修总结报告

    Args:
        maintenance_id: 维修ID
        db: 数据库会话

    Returns:
        分析结果
    """
    return await ai_manager.generate_maintenance_summary(maintenance_id, db)


async def predictive_maintenance_analysis(device_id: int, db: Session) -> Dict:
    """
    预测性维护分析

    Args:
        device_id: 设备ID
        db: 数据库会话

    Returns:
        分析结果
    """
    from app.shared.models import Device

    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        return {'success': False, 'error': 'Device not found'}

    return await ai_manager.analyze(
        analysis_type='pm_recommend',
        target_type='device',
        target_id=device_id,
        variables={
            'device_name': device.name,
            'device_model': device.device_type,
            'uptime_days': device.uptime_days or 0,
            'health_score': device.health_score or 100
        },
        db=db
    )


def get_ai_manager():
    """获取AI管理器实例"""
    return ai_manager