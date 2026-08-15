"""通知分组/排班/升级策略 特性模块（通知模块一期 v1.1）"""

from app.features.groups.service import (
    DEFAULT_OPS_GROUP,
    DEFAULT_ESCALATION_LEVELS,
    ensure_default_notification_setup,
    group_leader_usernames,
    group_members,
    match_dispatch_rule,
    resolve_fault_targets,
    resolve_oncall,
)

__all__ = [
    "DEFAULT_OPS_GROUP",
    "DEFAULT_ESCALATION_LEVELS",
    "ensure_default_notification_setup",
    "group_leader_usernames",
    "group_members",
    "match_dispatch_rule",
    "resolve_fault_targets",
    "resolve_oncall",
]
