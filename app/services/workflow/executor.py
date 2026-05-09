"""工作流执行器

负责：
- 整合触发器、规则引擎、动作执行器
- 执行完整的工作流
- 记录执行结果
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from loguru import logger

from sqlalchemy.orm import Session

from app.shared.models import WorkflowRule
from .rule_engine import RuleEngine, MatchedRule
from .triggers import TriggerManager
from .actions import ActionManager


class WorkflowExecutionResult:
    """工作流执行结果"""

    def __init__(
        self,
        trigger_type: str,
        rules_matched: List[MatchedRule],
        actions_executed: List[Dict],
        success: bool = True,
        error: Optional[str] = None
    ):
        self.trigger_type = trigger_type
        self.rules_matched = rules_matched
        self.actions_executed = actions_executed
        self.success = success
        self.error = error
        self.executed_at = datetime.utcnow()

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'trigger_type': self.trigger_type,
            'rules_matched_count': len(self.rules_matched),
            'rules_matched': [
                {
                    'rule_id': m.rule.id,
                    'rule_name': m.rule.name,
                    'action_type': m.rule.action_type
                }
                for m in self.rules_matched
            ],
            'actions_executed': self.actions_executed,
            'actions_count': len(self.actions_executed),
            'success': self.success,
            'error': self.error,
            'executed_at': self.executed_at.isoformat()
        }


class WorkflowExecutor:
    """工作流执行器"""

    def __init__(self, db: Session):
        self.db = db
        self.rule_engine = RuleEngine(db)
        self.trigger_manager = TriggerManager(db)
        self.action_manager = ActionManager(db)

    async def execute(
        self,
        trigger_type: str,
        event_data: Dict[str, Any]
    ) -> WorkflowExecutionResult:
        """
        执行工作流

        流程：
        1. 触发器处理事件，构建上下文
        2. 规则引擎匹配规则
        3. 执行匹配规则的动作

        Args:
            trigger_type: 触发类型
            event_data: 事件数据

        Returns:
            WorkflowExecutionResult 执行结果
        """
        logger.info(f"Workflow triggered: {trigger_type} with data: {event_data}")

        try:
            # 1. 触发器处理事件
            context = self.trigger_manager.process_event(trigger_type, event_data)

            if not context:
                logger.info(f"Trigger {trigger_type} did not activate")
                return WorkflowExecutionResult(
                    trigger_type=trigger_type,
                    rules_matched=[],
                    actions_executed=[],
                    success=True,
                    error='Trigger not activated'
                )

            # 2. 规则引擎匹配规则
            matched_rules = self.rule_engine.match_rules(trigger_type, context)

            if not matched_rules:
                logger.info(f"No rules matched for trigger {trigger_type}")
                return WorkflowExecutionResult(
                    trigger_type=trigger_type,
                    rules_matched=[],
                    actions_executed=[],
                    success=True
                )

            # 3. 执行动作（按优先级顺序）
            actions_results = []

            for matched_rule in matched_rules:
                rule = matched_rule.rule

                # 解析动作配置
                action_config = {}
                if rule.action_config:
                    try:
                        action_config = json.loads(rule.action_config)
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid action config for rule {rule.id}")

                # 添加规则ID到配置
                action_config['rule_id'] = rule.id

                # 执行动作
                action_result = await self.action_manager.execute_action(
                    action_type=rule.action_type,
                    config=action_config,
                    context=context
                )

                actions_results.append(action_result)

                # 更新规则执行计数
                rule.execution_count = (rule.execution_count or 0) + 1
                rule.last_triggered_at = datetime.utcnow()

                logger.info(
                    f"Action executed: {rule.action_type} for rule {rule.name} "
                    f"(success: {action_result.get('success')})"
                )

            self.db.commit()

            return WorkflowExecutionResult(
                trigger_type=trigger_type,
                rules_matched=matched_rules,
                actions_executed=actions_results,
                success=True
            )

        except Exception as e:
            logger.error(f"Workflow execution error: {e}")
            return WorkflowExecutionResult(
                trigger_type=trigger_type,
                rules_matched=[],
                actions_executed=[],
                success=False,
                error=str(e)
            )

    async def trigger_fault_created(self, fault_id: int) -> WorkflowExecutionResult:
        """触发故障创建工作流"""
        return await self.execute('fault_created', {'fault_id': fault_id})

    async def trigger_health_check(self, device_id: int) -> WorkflowExecutionResult:
        """触发健康检查工作流"""
        return await self.execute('device_health_low', {'device_id': device_id})

    async def trigger_maintenance_completed(self, maintenance_id: int) -> WorkflowExecutionResult:
        """触发维修完成工作流"""
        return await self.execute('maintenance_completed', {'maintenance_id': maintenance_id})

    async def trigger_scheduled_check(self, check_type: str = 'health') -> WorkflowExecutionResult:
        """触发定时检查工作流"""
        return await self.execute('scheduled_check', {'check_type': check_type})

    def create_default_rules(self) -> List[WorkflowRule]:
        """创建默认工作流规则"""
        default_rules = [
            {
                'name': '健康评分低自动创建巡检',
                'description': '当设备健康评分低于60时，自动创建巡检任务',
                'trigger_type': 'device_health_low',
                'trigger_conditions': {'health_score': {'<': 60}},
                'action_type': 'create_pm_task',
                'action_config': {
                    'task_type': 'inspection',
                    'days_offset': 3,
                    'name_template': '健康巡检: {device_name}',
                    'reason': '健康评分低于60'
                },
                'priority': 100
            },
            {
                'name': '严重故障自动创建维修单',
                'description': '当创建严重故障时，自动创建维修单',
                'trigger_type': 'fault_created',
                'trigger_conditions': {'fault_severity': 'critical'},
                'action_type': 'create_maintenance',
                'action_config': {
                    'maint_type': 'emergency',
                    'priority': 'urgent',
                    'title_template': '紧急维修: {device_name}',
                    'description': '严重故障自动创建维修单'
                },
                'priority': 50
            },
            {
                'name': '维修完成更新健康评分',
                'description': '维修完成后，提升设备健康评分',
                'trigger_type': 'maintenance_completed',
                'trigger_conditions': {'verify_passed': True},
                'action_type': 'update_health_score',
                'action_config': {
                    'adjustment': 10,
                    'reason': '维修完成验证通过'
                },
                'priority': 100
            },
            {
                'name': '高风险设备告警',
                'description': '当设备风险等级为critical时发送告警',
                'trigger_type': 'device_health_low',
                'trigger_conditions': {'risk_level': 'critical'},
                'action_type': 'send_alert',
                'action_config': {
                    'level': 'critical',
                    'title': '设备高风险告警',
                    'message_template': '设备 {device_name} 风险等级为critical，健康评分 {health_score}'
                },
                'priority': 30
            }
        ]

        created_rules = []

        for rule_data in default_rules:
            # 检查是否已存在同名规则
            existing = self.db.query(WorkflowRule).filter(
                WorkflowRule.name == rule_data['name']
            ).first()

            if existing:
                continue

            rule = self.rule_engine.create_rule(
                name=rule_data['name'],
                trigger_type=rule_data['trigger_type'],
                trigger_conditions=rule_data['trigger_conditions'],
                action_type=rule_data['action_type'],
                action_config=rule_data['action_config'],
                description=rule_data['description'],
                priority=rule_data['priority']
            )
            created_rules.append(rule)

        return created_rules

    def get_stats(self) -> Dict:
        """获取工作流统计"""
        rule_stats = self.rule_engine.get_rule_stats()

        return {
            'rules': rule_stats,
            'triggers_available': self.trigger_manager.list_triggers(),
            'actions_available': self.action_manager.list_actions()
        }