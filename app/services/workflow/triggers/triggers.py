"""工作流触发器

负责：
- 事件监听与检测
- 上下文数据构建
- 触发工作流执行

触发类型：
- fault_created: 故障创建时触发
- fault_status_changed: 故障状态变更时触发
- device_health_low: 设备健康评分低于阈值时触发
- maintenance_completed: 维修完成时触发
- scheduled_check: 定时检查触发
"""

import json
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from loguru import logger

from sqlalchemy.orm import Session

from app.shared.models import Device, FaultRecord, MaintenanceRecord


class BaseTrigger(ABC):
    """触发器抽象基类"""

    trigger_type: str = None

    @abstractmethod
    def get_context(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        构建触发上下文

        Args:
            event_data: 事件数据

        Returns:
            上下文字典（用于规则匹配）
        """
        pass

    @abstractmethod
    def should_trigger(self, event_data: Dict[str, Any]) -> bool:
        """
        是否应该触发

        Args:
            event_data: 事件数据

        Returns:
            是否触发
        """
        pass


class FaultCreatedTrigger(BaseTrigger):
    """故障创建触发器"""

    trigger_type = 'fault_created'

    def __init__(self, db: Session):
        self.db = db

    def get_context(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """构建上下文"""
        fault_id = event_data.get('fault_id')

        fault = self.db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()
        if not fault:
            return {}

        device = self.db.query(Device).filter(Device.id == fault.device_id).first()

        return {
            'fault_id': fault.id,
            'fault_title': fault.title,
            'fault_severity': fault.severity,
            'fault_status': fault.status,
            'device_id': fault.device_id,
            'device_name': device.name if device else 'Unknown',
            'device_status': device.status if device else 'Unknown',
            'device_health_score': device.health_score if device else 100,
            'device_risk_level': device.risk_level if device else 'low',
            'created_at': fault.created_at.isoformat()
        }

    def should_trigger(self, event_data: Dict[str, Any]) -> bool:
        """始终触发（故障创建事件）"""
        return event_data.get('fault_id') is not None


class DeviceHealthLowTrigger(BaseTrigger):
    """设备健康评分低触发器"""

    trigger_type = 'device_health_low'

    def __init__(self, db: Session, threshold: int = 60):
        self.db = db
        self.threshold = threshold

    def get_context(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """构建上下文"""
        device_id = event_data.get('device_id')

        device = self.db.query(Device).filter(Device.id == device_id).first()
        if not device:
            return {}

        # 获取最近的故障和维修
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_faults = self.db.query(FaultRecord).filter(
            FaultRecord.device_id == device.id,
            FaultRecord.created_at >= thirty_days_ago
        ).count()

        ninety_days_ago = datetime.utcnow() - timedelta(days=90)
        recent_repairs = self.db.query(MaintenanceRecord).filter(
            MaintenanceRecord.device_id == device.id,
            MaintenanceRecord.created_at >= ninety_days_ago
        ).count()

        return {
            'device_id': device.id,
            'device_name': device.name,
            'device_status': device.status,
            'health_score': device.health_score or 100,
            'risk_level': device.risk_level or 'low',
            'lifecycle_stage': device.lifecycle_stage or 'new',
            'uptime_days': device.uptime_days or 0,
            'recent_fault_count': recent_faults,
            'recent_repair_count': recent_repairs,
            'last_health_check': device.last_health_check.isoformat() if device.last_health_check else None
        }

    def should_trigger(self, event_data: Dict[str, Any]) -> bool:
        """健康评分低于阈值时触发"""
        device_id = event_data.get('device_id')

        device = self.db.query(Device).filter(Device.id == device_id).first()
        if not device:
            return False

        health_score = device.health_score or 100
        return health_score < self.threshold


class MaintenanceCompletedTrigger(BaseTrigger):
    """维修完成触发器"""

    trigger_type = 'maintenance_completed'

    def __init__(self, db: Session):
        self.db = db

    def get_context(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """构建上下文"""
        maintenance_id = event_data.get('maintenance_id')

        maintenance = self.db.query(MaintenanceRecord).filter(
            MaintenanceRecord.id == maintenance_id
        ).first()
        if not maintenance:
            return {}

        device = self.db.query(Device).filter(Device.id == maintenance.device_id).first()

        # 计算维修耗时
        duration_hours = 0
        if maintenance.created_at and maintenance.updated_at:
            duration_hours = (maintenance.updated_at - maintenance.created_at).total_seconds() / 3600

        return {
            'maintenance_id': maintenance.id,
            'maintenance_type': maintenance.maint_type,
            'maintenance_status': maintenance.status,
            'device_id': maintenance.device_id,
            'device_name': device.name if device else 'Unknown',
            'device_status': device.status if device else 'Unknown',
            'device_health_score': device.health_score if device else 100,
            'technician': maintenance.technician,
            'duration_hours': round(duration_hours, 1),
            'parts_cost': float(maintenance.parts_cost) if maintenance.parts_cost else 0,
            'labor_cost': float(maintenance.labor_cost) if maintenance.labor_cost else 0,
            'completed_at': maintenance.updated_at.isoformat() if maintenance.updated_at else None,
            'verify_passed': maintenance.status == 'completed'
        }

    def should_trigger(self, event_data: Dict[str, Any]) -> bool:
        """维修状态为completed时触发"""
        maintenance_id = event_data.get('maintenance_id')

        maintenance = self.db.query(MaintenanceRecord).filter(
            MaintenanceRecord.id == maintenance_id
        ).first()
        if not maintenance:
            return False

        return maintenance.status == 'completed'


class ScheduledCheckTrigger(BaseTrigger):
    """定时检查触发器"""

    trigger_type = 'scheduled_check'

    def __init__(self, db: Session):
        self.db = db

    def get_context(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """构建上下文（扫描所有设备）"""
        check_type = event_data.get('check_type', 'health')

        # 获取所有活跃设备
        devices = self.db.query(Device).filter(
            Device.status.in_(['online', 'offline', 'maintenance'])
        ).all()

        # 统计数据
        health_below_60 = [d for d in devices if (d.health_score or 100) < 60]
        risk_critical = [d for d in devices if d.risk_level == 'critical']
        risk_high = [d for d in devices if d.risk_level == 'high']

        return {
            'check_type': check_type,
            'total_devices': len(devices),
            'devices_health_below_60': len(health_below_60),
            'devices_critical': len(risk_critical),
            'devices_high_risk': len(risk_high),
            'check_time': datetime.utcnow().isoformat(),
            'device_ids': [d.id for d in devices]
        }

    def should_trigger(self, event_data: Dict[str, Any]) -> bool:
        """始终触发（定时任务）"""
        return True


class TriggerManager:
    """触发器管理器"""

    TRIGGER_CLASSES = {
        'fault_created': FaultCreatedTrigger,
        'device_health_low': DeviceHealthLowTrigger,
        'maintenance_completed': MaintenanceCompletedTrigger,
        'scheduled_check': ScheduledCheckTrigger,
    }

    def __init__(self, db: Session):
        self.db = db
        self.triggers: Dict[str, BaseTrigger] = {}

        # 初始化触发器实例
        for trigger_type, trigger_class in self.TRIGGER_CLASSES.items():
            self.triggers[trigger_type] = trigger_class(db)

    def get_trigger(self, trigger_type: str) -> Optional[BaseTrigger]:
        """获取触发器"""
        return self.triggers.get(trigger_type)

    def process_event(
        self,
        trigger_type: str,
        event_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        处理事件

        Args:
            trigger_type: 触发类型
            event_data: 事件数据

        Returns:
            触发上下文（如果触发成功）
        """
        trigger = self.get_trigger(trigger_type)
        if not trigger:
            logger.warning(f"Unknown trigger type: {trigger_type}")
            return None

        if trigger.should_trigger(event_data):
            context = trigger.get_context(event_data)
            logger.info(f"Trigger activated: {trigger_type}")
            return context

        return None

    def list_triggers(self) -> List[str]:
        """列出所有触发类型"""
        return list(self.TRIGGER_CLASSES.keys())


# 工厂函数
def create_trigger(trigger_type: str, db: Session) -> Optional[BaseTrigger]:
    """创建触发器实例"""
    trigger_class = TriggerManager.TRIGGER_CLASSES.get(trigger_type)
    if trigger_class:
        return trigger_class(db)
    return None