"""工作流规则引擎

负责：
- 规则加载与管理
- 触发条件解析与判断
- 规则匹配逻辑

支持的条件表达式：
- 字段比较：{"health_score": {"<": 60}}
- 多条件组合：{"and": [{"health_score": {"<": 60}}, {"status": "online"}]}
- 或条件：{"or": [{"risk_level": "critical"}, {"risk_level": "high"}]}
"""

import json
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime
from loguru import logger

from sqlalchemy.orm import Session

from app.shared.models import WorkflowRule


@dataclass
class MatchedRule:
    """匹配到的规则"""
    rule: WorkflowRule
    context: Dict[str, Any]
    matched_at: datetime = datetime.utcnow()


class RuleEngine:
    """规则引擎"""

    # 支持的比较操作符
    COMPARISON_OPERATORS = {
        '<': lambda a, b: a < b,
        '<=': lambda a, b: a <= b,
        '>': lambda a, b: a > b,
        '>=': lambda a, b: a >= b,
        '=': lambda a, b: a == b,
        '!=': lambda a, b: a != b,
        'in': lambda a, b: a in b if isinstance(b, (list, tuple)) else False,
        'not_in': lambda a, b: a not in b if isinstance(b, (list, tuple)) else True,
        'contains': lambda a, b: b in a if isinstance(a, str) else False,
        'not_contains': lambda a, b: b not in a if isinstance(a, str) else True,
    }

    # 支持的逻辑操作符
    LOGICAL_OPERATORS = ['and', 'or', 'not']

    def __init__(self, db: Session):
        self.db = db

    def load_active_rules(self, trigger_type: Optional[str] = None) -> List[WorkflowRule]:
        """加载活跃规则"""
        query = self.db.query(WorkflowRule).filter(WorkflowRule.is_active == True)

        if trigger_type:
            query = query.filter(WorkflowRule.trigger_type == trigger_type)

        return query.order_by(WorkflowRule.priority.asc()).all()

    def match_rules(
        self,
        trigger_type: str,
        context: Dict[str, Any]
    ) -> List[MatchedRule]:
        """
        匹配规则

        Args:
            trigger_type: 触发类型
            context: 上下文数据（包含设备信息、故障信息等）

        Returns:
            匹配到的规则列表（按优先级排序）
        """
        rules = self.load_active_rules(trigger_type)
        matched = []

        for rule in rules:
            try:
                conditions = self._parse_conditions(rule.trigger_conditions)

                if self._evaluate_conditions(conditions, context):
                    matched.append(MatchedRule(rule=rule, context=context))
                    logger.info(f"Rule matched: {rule.name} (ID: {rule.id})")

            except Exception as e:
                logger.error(f"Rule evaluation error for rule {rule.id}: {e}")
                continue

        return matched

    def _parse_conditions(self, conditions_json: Optional[str]) -> Dict:
        """解析条件JSON"""
        if not conditions_json:
            return {}

        try:
            return json.loads(conditions_json)
        except json.JSONDecodeError:
            logger.warning(f"Invalid conditions JSON: {conditions_json}")
            return {}

    def _evaluate_conditions(
        self,
        conditions: Dict,
        context: Dict[str, Any]
    ) -> bool:
        """
        评估条件表达式

        Args:
            conditions: 条件字典
            context: 上下文数据

        Returns:
            是否满足条件
        """
        if not conditions:
            # 无条件则默认满足
            return True

        # 处理逻辑操作符
        for op in self.LOGICAL_OPERATORS:
            if op in conditions:
                return self._evaluate_logical(op, conditions[op], context)

        # 处理字段比较
        for field, comparison in conditions.items():
            if isinstance(comparison, dict):
                # 字段比较表达式
                if not self._evaluate_field_comparison(field, comparison, context):
                    return False
            else:
                # 直接值比较
                field_value = context.get(field)
                if field_value != comparison:
                    return False

        return True

    def _evaluate_logical(
        self,
        operator: str,
        operands: Any,
        context: Dict[str, Any]
    ) -> bool:
        """评估逻辑操作符"""
        if operator == 'and':
            if not isinstance(operands, list):
                return False
            return all(self._evaluate_conditions(op, context) for op in operands)

        elif operator == 'or':
            if not isinstance(operands, list):
                return False
            return any(self._evaluate_conditions(op, context) for op in operands)

        elif operator == 'not':
            return not self._evaluate_conditions(operands, context)

        return False

    def _evaluate_field_comparison(
        self,
        field: str,
        comparison: Dict,
        context: Dict[str, Any]
    ) -> bool:
        """评估字段比较"""
        field_value = context.get(field)

        for op, threshold in comparison.items():
            if op not in self.COMPARISON_OPERATORS:
                logger.warning(f"Unknown operator: {op}")
                continue

            try:
                if not self.COMPARISON_OPERATORS[op](field_value, threshold):
                    return False
            except Exception as e:
                logger.warning(f"Comparison error: {field} {op} {threshold}: {e}")
                return False

        return True

    def create_rule(
        self,
        name: str,
        trigger_type: str,
        trigger_conditions: Dict,
        action_type: str,
        action_config: Dict,
        description: Optional[str] = None,
        priority: int = 100,
        is_active: bool = True
    ) -> WorkflowRule:
        """创建新规则"""
        rule = WorkflowRule(
            name=name,
            description=description,
            trigger_type=trigger_type,
            trigger_conditions=json.dumps(trigger_conditions),
            action_type=action_type,
            action_config=json.dumps(action_config),
            priority=priority,
            is_active=is_active,
            execution_count=0
        )

        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)

        logger.info(f"Created workflow rule: {name} (ID: {rule.id})")
        return rule

    def update_rule(self, rule_id: int, updates: Dict) -> Optional[WorkflowRule]:
        """更新规则"""
        rule = self.db.query(WorkflowRule).filter(WorkflowRule.id == rule_id).first()

        if not rule:
            return None

        for key, value in updates.items():
            if hasattr(rule, key):
                if key in ['trigger_conditions', 'action_config']:
                    value = json.dumps(value)
                setattr(rule, key, value)

        self.db.commit()
        self.db.refresh(rule)
        return rule

    def delete_rule(self, rule_id: int) -> bool:
        """删除规则"""
        rule = self.db.query(WorkflowRule).filter(WorkflowRule.id == rule_id).first()

        if not rule:
            return False

        self.db.delete(rule)
        self.db.commit()
        return True

    def get_rule(self, rule_id: int) -> Optional[WorkflowRule]:
        """获取单个规则"""
        return self.db.query(WorkflowRule).filter(WorkflowRule.id == rule_id).first()

    def list_rules(
        self,
        trigger_type: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> List[WorkflowRule]:
        """列出规则"""
        query = self.db.query(WorkflowRule)

        if trigger_type:
            query = query.filter(WorkflowRule.trigger_type == trigger_type)

        if is_active is not None:
            query = query.filter(WorkflowRule.is_active == is_active)

        return query.order_by(WorkflowRule.priority.asc()).all()

    def get_rule_stats(self) -> Dict:
        """获取规则统计"""
        rules = self.db.query(WorkflowRule).all()

        total = len(rules)
        active = len([r for r in rules if r.is_active])
        by_trigger_type = {}
        by_action_type = {}

        for rule in rules:
            if rule.trigger_type not in by_trigger_type:
                by_trigger_type[rule.trigger_type] = 0
            by_trigger_type[rule.trigger_type] += 1

            if rule.action_type not in by_action_type:
                by_action_type[rule.action_type] = 0
            by_action_type[rule.action_type] += 1

        return {
            'total_rules': total,
            'active_rules': active,
            'inactive_rules': total - active,
            'by_trigger_type': by_trigger_type,
            'by_action_type': by_action_type,
            'total_executions': sum(r.execution_count or 0 for r in rules)
        }