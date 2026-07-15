"""工作流动作执行器

负责：
- 执行各种自动化动作
- 动作结果记录

动作类型：
- create_maintenance: 创建维修单
- create_pm_task: 创建计划性维护任务
- send_alert: 发送告警通知
- update_health_score: 更新设备健康评分
- log_event: 记录事件日志
"""

import json
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from loguru import logger

from sqlalchemy.orm import Session

from app.shared.models import (
    Device, MaintenanceRecord, FaultRecord,
    MaintenanceTask
)
from app.services.fault_maintenance import (
    FaultMaintenanceConflictError,
    create_fault_maintenance_once,
)


class BaseAction(ABC):
    """动作执行器抽象基类"""

    action_type: str = None

    @abstractmethod
    async def execute(
        self,
        config: Dict[str, Any],
        context: Dict[str, Any],
        db: Session
    ) -> Dict[str, Any]:
        """
        执行动作

        Args:
            config: 动作配置
            context: 触发上下文
            db: 数据库会话

        Returns:
            执行结果
        """
        pass


class CreateMaintenanceAction(BaseAction):
    """创建维修单动作"""

    action_type = 'create_maintenance'

    async def execute(
        self,
        config: Dict[str, Any],
        context: Dict[str, Any],
        db: Session
    ) -> Dict[str, Any]:
        """创建维修单"""
        import uuid

        device_id = context.get('device_id')

        if not device_id:
            return {'success': False, 'error': 'No device_id in context'}

        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            return {'success': False, 'error': 'Device not found'}

        # 确定维修类型
        maint_type = config.get('maint_type', 'corrective')
        priority = config.get('priority', 'normal')

        # 构建维修单标题
        title_template = config.get('title_template', '自动创建维修单: {device_name}')
        title = title_template.replace('{device_name}', device.name)

        # 如果是故障触发的，关联故障记录
        fault_id = context.get('fault_id')

        if fault_id:
            fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()
            if not fault:
                return {'success': False, 'error': 'Fault not found'}

        # 生成维修单号
        maint_no = f"WF-MAINT-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

        # 创建维修单
        maintenance = MaintenanceRecord(
            maint_no=maint_no,
            device_id=device.id,
            device_name=device.name,
            title=title,
            problem_description=config.get('description', f"健康评分触发: {context.get('health_score', 'N/A')}"),
            maint_type=maint_type,
            status='pending',
            priority=priority,
            fault_id=fault_id,
            auto_created=True
        )

        created = True
        if fault_id:
            try:
                maintenance, created = create_fault_maintenance_once(
                    db,
                    fault,
                    maintenance,
                    fault_updates={
                        FaultRecord.auto_created_maintenance: True,
                    },
                )
            except FaultMaintenanceConflictError as exc:
                return {'success': False, 'error': str(exc)}
        else:
            db.add(maintenance)
            db.commit()
            db.refresh(maintenance)

        logger.info(
            f"{'Created' if created else 'Reused'} maintenance record "
            f"{maintenance.id} for device {device_id}"
        )

        return {
            'success': True,
            'action': 'create_maintenance',
            'maintenance_id': maintenance.id,
            'device_id': device_id,
            'title': maintenance.title,
            'created_at': maintenance.created_at.isoformat(),
            'reused': not created
        }


class CreatePMTaskAction(BaseAction):
    """创建计划性维护任务动作"""

    action_type = 'create_pm_task'

    async def execute(
        self,
        config: Dict[str, Any],
        context: Dict[str, Any],
        db: Session
    ) -> Dict[str, Any]:
        """创建巡检/维护任务"""
        import uuid

        device_id = context.get('device_id')

        if not device_id:
            return {'success': False, 'error': 'No device_id in context'}

        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            return {'success': False, 'error': 'Device not found'}

        # 确定任务类型和日期
        task_type = config.get('task_type', 'inspection')
        days_offset = config.get('days_offset', 7)
        scheduled_date = datetime.utcnow() + timedelta(days=days_offset)

        # 构建任务名称
        name_template = config.get('name_template', '自动巡检: {device_name}')
        task_name = name_template.replace('{device_name}', device.name)

        # 生成任务编号
        task_no = f"WF-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"

        # 创建任务
        pm_task = MaintenanceTask(
            device_id=device.id,
            device_name=device.name,
            task_no=task_no,
            scheduled_date=scheduled_date,
            status='pending',
            notes=json.dumps({
                'task_name': task_name,
                'task_type': task_type,
                'trigger_context': context,
                'reason': config.get('reason', '健康评分低于阈值'),
                'workflow_rule_id': config.get('rule_id'),
                'ai_generated': True
            })
        )

        db.add(pm_task)
        db.commit()
        db.refresh(pm_task)

        logger.info(f"Created PM task {pm_task.id} for device {device_id}")

        return {
            'success': True,
            'action': 'create_pm_task',
            'pm_task_id': pm_task.id,
            'device_id': device_id,
            'task_name': task_name,
            'scheduled_date': scheduled_date.isoformat()
        }


class SendAlertAction(BaseAction):
    """发送告警动作"""

    action_type = 'send_alert'

    async def execute(
        self,
        config: Dict[str, Any],
        context: Dict[str, Any],
        db: Session
    ) -> Dict[str, Any]:
        """发送告警通知"""
        # 确定告警级别
        alert_level = config.get('level', 'warning')

        # 构建告警消息
        message_template = config.get('message_template', '设备 {device_name} 需要关注')
        message = message_template

        # 替换模板变量
        for key, value in context.items():
            message = message.replace(f'{{{key}}}', str(value))

        # 记录告警日志（暂不创建数据库记录，后续可集成通知服务）
        alert_id = f"alert-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{context.get('device_id', 0)}"

        logger.warning(
            f"Workflow Alert [{alert_level}]: {config.get('title', '自动化告警')} - {message}"
        )

        # TODO: 集成邮件/钉钉/企业微信通知服务

        return {
            'success': True,
            'action': 'send_alert',
            'alert_id': alert_id,
            'message': message,
            'level': alert_level,
            'logged_at': datetime.utcnow().isoformat()
        }


class UpdateHealthScoreAction(BaseAction):
    """更新健康评分动作"""

    action_type = 'update_health_score'

    async def execute(
        self,
        config: Dict[str, Any],
        context: Dict[str, Any],
        db: Session
    ) -> Dict[str, Any]:
        """更新设备健康评分"""
        device_id = context.get('device_id')

        if not device_id:
            return {'success': False, 'error': 'No device_id in context'}

        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            return {'success': False, 'error': 'Device not found'}

        # 计算新健康评分
        # 可以基于维修结果调整评分
        score_adjustment = config.get('adjustment', 0)

        current_score = device.health_score or 100
        new_score = max(0, min(100, current_score + score_adjustment))

        # 更新设备健康评分
        device.health_score = new_score
        device.last_health_check = datetime.utcnow()

        # 确定风险等级
        if new_score >= 80:
            device.risk_level = 'low'
        elif new_score >= 60:
            device.risk_level = 'medium'
        elif new_score >= 40:
            device.risk_level = 'high'
        else:
            device.risk_level = 'critical'

        db.commit()

        logger.info(f"Updated health score for device {device_id}: {current_score} -> {new_score}")

        return {
            'success': True,
            'action': 'update_health_score',
            'device_id': device_id,
            'previous_score': current_score,
            'new_score': new_score,
            'adjustment': score_adjustment
        }


class LogEventAction(BaseAction):
    """记录事件日志动作"""

    action_type = 'log_event'

    async def execute(
        self,
        config: Dict[str, Any],
        context: Dict[str, Any],
        db: Session
    ) -> Dict[str, Any]:
        """记录事件到日志"""
        event_type = config.get('event_type', 'workflow_triggered')
        message = config.get('message', 'Workflow triggered')

        # 构建完整日志
        log_entry = {
            'event_type': event_type,
            'message': message,
            'context': context,
            'config': config,
            'timestamp': datetime.utcnow().isoformat()
        }

        logger.info(f"Workflow event: {json.dumps(log_entry)}")

        return {
            'success': True,
            'action': 'log_event',
            'event_type': event_type,
            'message': message,
            'logged_at': log_entry['timestamp']
        }


class ActionManager:
    """动作管理器"""

    ACTION_CLASSES = {
        'create_maintenance': CreateMaintenanceAction,
        'create_pm_task': CreatePMTaskAction,
        'send_alert': SendAlertAction,
        'update_health_score': UpdateHealthScoreAction,
        'log_event': LogEventAction,
    }

    def __init__(self, db: Session):
        self.db = db
        self.actions: Dict[str, BaseAction] = {}

        # 初始化动作实例
        for action_type, action_class in self.ACTION_CLASSES.items():
            self.actions[action_type] = action_class()

    def get_action(self, action_type: str) -> Optional[BaseAction]:
        """获取动作执行器"""
        return self.actions.get(action_type)

    async def execute_action(
        self,
        action_type: str,
        config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行动作

        Args:
            action_type: 动作类型
            config: 动作配置
            context: 触发上下文

        Returns:
            执行结果
        """
        action = self.get_action(action_type)
        if not action:
            logger.warning(f"Unknown action type: {action_type}")
            return {'success': False, 'error': f"Unknown action type: {action_type}"}

        try:
            result = await action.execute(config, context, self.db)
            return result
        except Exception as e:
            logger.error(f"Action execution error: {action_type} - {e}")
            return {'success': False, 'error': str(e)}

    def list_actions(self) -> List[str]:
        """列出所有动作类型"""
        return list(self.ACTION_CLASSES.keys())

    def get_action_info(self, action_type: str) -> Optional[Dict]:
        """获取动作信息"""
        if action_type not in self.ACTION_CLASSES:
            return None

        return {
            'type': action_type,
            'class': self.ACTION_CLASSES[action_type].__name__,
            'description': self.ACTION_CLASSES[action_type].__doc__
        }