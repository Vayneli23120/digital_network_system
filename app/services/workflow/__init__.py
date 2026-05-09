"""自动化工作流引擎

负责：
- 规则定义与管理
- 触发条件判断
- 动作执行器
- 事件驱动的自动化流程

核心流程：
事件发生 → 规则匹配 → 条件判断 → 执行动作 → 记录结果
"""

from .rule_engine import RuleEngine, WorkflowRule
from .triggers import TriggerManager, BaseTrigger
from .actions import ActionManager, BaseAction
from .executor import WorkflowExecutor

__all__ = [
    'RuleEngine',
    'WorkflowRule',
    'TriggerManager',
    'BaseTrigger',
    'ActionManager',
    'BaseAction',
    'WorkflowExecutor',
]