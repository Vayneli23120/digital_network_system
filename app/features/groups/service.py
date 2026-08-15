"""用户组/排班/分发规则/升级策略服务 —— 通知模块一期（v1.1）

组织决策基线：
- 监控自动故障通知目标 = {admin} ∪ 运维组（废弃环境变量伪账号）
- 升级链：15min 未认领 → 运维组全员；30min 未处理 → 部门经理（组长）+ 复盘任务
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from loguru import logger
from sqlalchemy.orm import Session

from app.shared.models import (
    DispatchRule,
    EscalationPolicy,
    OncallSchedule,
    Permission,
    User,
    UserGroup,
    UserGroupMember,
)

DEFAULT_OPS_GROUP = "运维组"

# 默认升级策略（v1.1 组织决策，时长可配）
DEFAULT_ESCALATION_LEVELS = [
    {"level": 2, "timeout_minutes": 15, "targets": ["group"], "create_review": False},
    {"level": 3, "timeout_minutes": 30, "targets": ["leader", "admin"], "create_review": True},
]


def _load_json(raw: Optional[str], default: list) -> list:
    if not raw:
        return default
    try:
        value = json.loads(raw)
        return value if isinstance(value, list) else default
    except Exception:
        return default


def ensure_default_notification_setup(db: Session) -> None:
    """幂等初始化：notification:manage 权限 + 运维组（admin 组长） + 默认分发规则 + 默认升级策略。"""
    try:
        # 1) 权限（非超管角色授权用；超管天然放行）
        if not db.query(Permission).filter(Permission.name == "notification:manage").first():
            db.add(Permission(name="notification:manage", resource="notification", action="manage",
                              description="管理通知分组/排班/升级策略"))
            db.commit()
            logger.info("[groups] 已创建权限 notification:manage")

        # 2) 运维组 + admin 组长
        group = db.query(UserGroup).filter(UserGroup.name == DEFAULT_OPS_GROUP).first()
        if not group:
            group = UserGroup(name=DEFAULT_OPS_GROUP,
                              description="网络运维值班组（监控自动故障默认派发目标）",
                              is_oncall=True)
            db.add(group)
            db.commit()
            db.refresh(group)
            logger.info("[groups] 已创建默认运维组")

        admin = db.query(User).filter(User.username == "admin").first()
        if admin:
            member = db.query(UserGroupMember).filter(
                UserGroupMember.group_id == group.id,
                UserGroupMember.user_id == admin.id,
            ).first()
            if not member:
                db.add(UserGroupMember(group_id=group.id, user_id=admin.id,
                                       username=admin.username, is_leader=True))
                db.commit()
                logger.info("[groups] admin 已加入运维组并设为组长（部门经理占位，可在界面更换）")

        # 3) 默认分发规则：监控自动故障 → 运维组
        if not db.query(DispatchRule).filter(DispatchRule.name == "监控自动故障 → 运维组").first():
            db.add(DispatchRule(name="监控自动故障 → 运维组", enabled=True, priority=100,
                                source_types=None, device_types=None, severities=None,
                                target_group_id=group.id))
            db.commit()
            logger.info("[groups] 已创建默认分发规则")

        # 4) 默认升级策略
        if not db.query(EscalationPolicy).filter(EscalationPolicy.name == "默认升级策略").first():
            db.add(EscalationPolicy(name="默认升级策略", enabled=True,
                                    levels_json=json.dumps(DEFAULT_ESCALATION_LEVELS, ensure_ascii=False)))
            db.commit()
            logger.info("[groups] 已创建默认升级策略")
    except Exception:
        db.rollback()
        logger.exception("[groups] 初始化通知分组默认数据失败")


# ============================================================
# 目标解析（分发/通知共用）
# ============================================================

def _rule_matches(rule: DispatchRule, source_type: Optional[str],
                  device_type: Optional[str], severity: Optional[str]) -> bool:
    sources = _load_json(rule.source_types, [])
    devices = _load_json(rule.device_types, [])
    severities = _load_json(rule.severities, [])
    if sources and source_type and source_type not in sources:
        return False
    if devices and device_type and device_type not in devices:
        return False
    if severities and severity and severity not in severities:
        return False
    return True


def match_dispatch_rule(db: Session, source_type: Optional[str] = None,
                        device_type: Optional[str] = None,
                        severity: Optional[str] = None) -> Optional[UserGroup]:
    """按优先级匹配分发规则；无命中回退默认运维组。"""
    rules = (db.query(DispatchRule)
             .filter(DispatchRule.enabled == True)  # noqa: E712
             .order_by(DispatchRule.priority.asc(), DispatchRule.id.asc())
             .all())
    for rule in rules:
        if _rule_matches(rule, source_type, device_type, severity):
            group = db.query(UserGroup).filter(UserGroup.id == rule.target_group_id).first()
            if group:
                return group
    return db.query(UserGroup).filter(UserGroup.name == DEFAULT_OPS_GROUP).first()


def group_members(db: Session, group_id: int) -> List[UserGroupMember]:
    return db.query(UserGroupMember).filter(UserGroupMember.group_id == group_id).all()


def resolve_oncall(db: Session, group_id: int, at: Optional[datetime] = None) -> Optional[str]:
    """解析组当前值班人（真实用户名）；未排班返回 None。"""
    at = at or datetime.utcnow()
    schedules = (db.query(OncallSchedule)
                 .filter(OncallSchedule.group_id == group_id)
                 .order_by(OncallSchedule.start_at.desc())
                 .all())
    for sched in schedules:
        if sched.start_at <= at and (sched.end_at is None or at < sched.end_at):
            return sched.username
    return None


def _usernames_to_emails(db: Session, usernames: List[str]) -> List[str]:
    emails: List[str] = []
    for user in db.query(User).filter(User.username.in_(usernames)).all():
        if user.email:
            emails.append(user.email)
    return emails


def resolve_fault_targets(db: Session, source_type: Optional[str] = None,
                          device_type: Optional[str] = None,
                          severity: Optional[str] = None) -> Tuple[Optional[str], List[str], List[str], Optional[UserGroup]]:
    """监控自动故障的目标解析（v1.1 组织决策）。

    返回 (assigned_to, notify_usernames, notify_emails, group)：
    - 命中分发规则 → 目标组；值班人在岗 → assigned_to=值班人（真实账号）；
      未排班 → assigned_to=组名（由组内认领）
    - 通知目标 = {admin} ∪ 组内成员
    - 不再使用 INCIDENT_*_OWNER 环境变量伪账号
    """
    group = match_dispatch_rule(db, source_type, device_type, severity)
    assigned_to: Optional[str] = None
    if group:
        assigned_to = resolve_oncall(db, group.id) or group.name
        usernames = [m.username for m in group_members(db, group.id)]
    else:
        usernames = []
    usernames = list(dict.fromkeys(["admin"] + usernames))
    return assigned_to, usernames, _usernames_to_emails(db, usernames), group


def group_leader_usernames(db: Session, group_id: int) -> List[str]:
    """组长（部门经理）用户名列表。"""
    return [m.username for m in group_members(db, group_id) if m.is_leader]
