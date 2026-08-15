"""通知分组/排班/分发规则/升级策略 API —— 通知模块一期（v1.1）"""

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.shared.database import get_db
from app.shared.models import (
    DispatchRule,
    EscalationPolicy,
    OncallSchedule,
    User,
    UserGroup,
    UserGroupMember,
)
from app.shared.dependencies import require_permission
from app.features.groups.service import ensure_default_notification_setup

router = APIRouter(prefix="/api/groups", tags=["通知分组"])

require_notification_manage = require_permission("notification:manage")


# ===== 请求模型 =====

class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None
    is_oncall: bool = True


class GroupUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None
    is_oncall: Optional[bool] = None


class MemberAdd(BaseModel):
    user_id: int
    is_leader: bool = False


class ScheduleCreate(BaseModel):
    user_id: int
    start_at: str
    end_at: Optional[str] = None
    repeat_rule: str = "none"  # none/daily/weekly


class RuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    enabled: bool = True
    priority: int = 100
    source_types: Optional[list[str]] = None
    device_types: Optional[list[str]] = None
    severities: Optional[list[str]] = None
    target_group_id: Optional[int] = None


class PolicyUpdate(BaseModel):
    enabled: Optional[bool] = None
    levels: list[dict] = Field(default_factory=list)


def _group_dict(group: UserGroup) -> dict:
    members = [{
        "id": m.id,
        "user_id": m.user_id,
        "username": m.username,
        "is_leader": m.is_leader,
    } for m in group.members]
    return {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "is_oncall": group.is_oncall,
        "members": members,
    }


def _get_group(db: Session, group_id: int) -> UserGroup:
    group = db.query(UserGroup).filter(UserGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="分组不存在")
    return group


# ===== 分组 CRUD =====

@router.get("")
async def list_groups(db: Session = Depends(get_db),
                      _: None = Depends(require_notification_manage)):
    """分组列表（含成员/组长）。"""
    groups = db.query(UserGroup).order_by(UserGroup.id.asc()).all()
    return {"items": [_group_dict(g) for g in groups]}


@router.post("")
async def create_group(payload: GroupCreate, db: Session = Depends(get_db),
                       _: None = Depends(require_notification_manage)):
    if db.query(UserGroup).filter(UserGroup.name == payload.name).first():
        raise HTTPException(status_code=409, detail="同名分组已存在")
    group = UserGroup(name=payload.name, description=payload.description, is_oncall=payload.is_oncall)
    db.add(group)
    db.commit()
    db.refresh(group)
    return _group_dict(group)


@router.put("/{group_id}")
async def update_group(group_id: int, payload: GroupUpdate, db: Session = Depends(get_db),
                       _: None = Depends(require_notification_manage)):
    group = _get_group(db, group_id)
    if payload.name and payload.name != group.name:
        if db.query(UserGroup).filter(UserGroup.name == payload.name).first():
            raise HTTPException(status_code=409, detail="同名分组已存在")
        group.name = payload.name
    if payload.description is not None:
        group.description = payload.description
    if payload.is_oncall is not None:
        group.is_oncall = payload.is_oncall
    db.commit()
    db.refresh(group)
    return _group_dict(group)


@router.delete("/{group_id}")
async def delete_group(group_id: int, db: Session = Depends(get_db),
                       _: None = Depends(require_notification_manage)):
    group = _get_group(db, group_id)
    db.delete(group)
    db.commit()
    return {"message": f"分组 {group.name} 已删除"}


# ===== 成员管理 =====

@router.post("/{group_id}/members")
async def add_member(group_id: int, payload: MemberAdd, db: Session = Depends(get_db),
                     _: None = Depends(require_notification_manage)):
    group = _get_group(db, group_id)
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    member = db.query(UserGroupMember).filter(
        UserGroupMember.group_id == group.id,
        UserGroupMember.user_id == user.id,
    ).first()
    if member:
        member.is_leader = payload.is_leader
    else:
        member = UserGroupMember(group_id=group.id, user_id=user.id,
                                 username=user.username, is_leader=payload.is_leader)
        db.add(member)
    db.commit()
    db.refresh(group)
    return _group_dict(group)


@router.delete("/{group_id}/members/{user_id}")
async def remove_member(group_id: int, user_id: int, db: Session = Depends(get_db),
                        _: None = Depends(require_notification_manage)):
    _get_group(db, group_id)
    member = db.query(UserGroupMember).filter(
        UserGroupMember.group_id == group_id,
        UserGroupMember.user_id == user_id,
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="成员不存在")
    db.delete(member)
    db.commit()
    return {"message": "成员已移除"}


# ===== 排班 =====

@router.get("/{group_id}/schedules")
async def list_schedules(group_id: int, db: Session = Depends(get_db),
                         _: None = Depends(require_notification_manage)):
    _get_group(db, group_id)
    schedules = (db.query(OncallSchedule)
                 .filter(OncallSchedule.group_id == group_id)
                 .order_by(OncallSchedule.start_at.desc())
                 .all())
    return {"items": [{
        "id": s.id, "user_id": s.user_id, "username": s.username,
        "start_at": s.start_at.isoformat() if s.start_at else None,
        "end_at": s.end_at.isoformat() if s.end_at else None,
        "repeat_rule": s.repeat_rule,
    } for s in schedules]}


@router.post("/{group_id}/schedules")
async def create_schedule(group_id: int, payload: ScheduleCreate, db: Session = Depends(get_db),
                          _: None = Depends(require_notification_manage)):
    _get_group(db, group_id)
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    from datetime import datetime as _dt
    start_at = _dt.fromisoformat(payload.start_at)
    end_at = _dt.fromisoformat(payload.end_at) if payload.end_at else None
    if end_at and end_at <= start_at:
        raise HTTPException(status_code=400, detail="结束时间必须晚于开始时间")
    schedule = OncallSchedule(group_id=group_id, user_id=user.id, username=user.username,
                              start_at=start_at, end_at=end_at,
                              repeat_rule=payload.repeat_rule or "none")
    db.add(schedule)
    db.commit()
    return {"message": "排班已添加", "id": schedule.id}


@router.delete("/{group_id}/schedules/{schedule_id}")
async def delete_schedule(group_id: int, schedule_id: int, db: Session = Depends(get_db),
                          _: None = Depends(require_notification_manage)):
    schedule = db.query(OncallSchedule).filter(
        OncallSchedule.id == schedule_id,
        OncallSchedule.group_id == group_id,
    ).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="排班不存在")
    db.delete(schedule)
    db.commit()
    return {"message": "排班已删除"}


# ===== 分发规则 =====

def _rule_dict(rule: DispatchRule) -> dict:
    return {
        "id": rule.id,
        "name": rule.name,
        "enabled": rule.enabled,
        "priority": rule.priority,
        "source_types": json.loads(rule.source_types) if rule.source_types else [],
        "device_types": json.loads(rule.device_types) if rule.device_types else [],
        "severities": json.loads(rule.severities) if rule.severities else [],
        "target_group_id": rule.target_group_id,
    }


@router.get("/dispatch-rules")
async def list_dispatch_rules(db: Session = Depends(get_db),
                              _: None = Depends(require_notification_manage)):
    rules = db.query(DispatchRule).order_by(DispatchRule.priority.asc(), DispatchRule.id.asc()).all()
    return {"items": [_rule_dict(r) for r in rules]}


@router.post("/dispatch-rules")
async def create_dispatch_rule(payload: RuleCreate, db: Session = Depends(get_db),
                               _: None = Depends(require_notification_manage)):
    rule = DispatchRule(
        name=payload.name, enabled=payload.enabled, priority=payload.priority,
        source_types=json.dumps(payload.source_types, ensure_ascii=False) if payload.source_types else None,
        device_types=json.dumps(payload.device_types, ensure_ascii=False) if payload.device_types else None,
        severities=json.dumps(payload.severities, ensure_ascii=False) if payload.severities else None,
        target_group_id=payload.target_group_id,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return _rule_dict(rule)


@router.put("/dispatch-rules/{rule_id}")
async def update_dispatch_rule(rule_id: int, payload: RuleCreate, db: Session = Depends(get_db),
                               _: None = Depends(require_notification_manage)):
    rule = db.query(DispatchRule).filter(DispatchRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    rule.name = payload.name
    rule.enabled = payload.enabled
    rule.priority = payload.priority
    rule.source_types = json.dumps(payload.source_types, ensure_ascii=False) if payload.source_types else None
    rule.device_types = json.dumps(payload.device_types, ensure_ascii=False) if payload.device_types else None
    rule.severities = json.dumps(payload.severities, ensure_ascii=False) if payload.severities else None
    rule.target_group_id = payload.target_group_id
    db.commit()
    db.refresh(rule)
    return _rule_dict(rule)


@router.delete("/dispatch-rules/{rule_id}")
async def delete_dispatch_rule(rule_id: int, db: Session = Depends(get_db),
                               _: None = Depends(require_notification_manage)):
    rule = db.query(DispatchRule).filter(DispatchRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    db.delete(rule)
    db.commit()
    return {"message": "规则已删除"}


# ===== 升级策略（默认策略） =====

@router.get("/escalation-policy")
async def get_escalation_policy(db: Session = Depends(get_db),
                                _: None = Depends(require_notification_manage)):
    policy = db.query(EscalationPolicy).filter(EscalationPolicy.name == "默认升级策略").first()
    if not policy:
        raise HTTPException(status_code=404, detail="升级策略不存在")
    levels = json.loads(policy.levels_json) if policy.levels_json else []
    return {"id": policy.id, "name": policy.name, "enabled": policy.enabled, "levels": levels}


@router.put("/escalation-policy")
async def update_escalation_policy(payload: PolicyUpdate, db: Session = Depends(get_db),
                                   _: None = Depends(require_notification_manage)):
    policy = db.query(EscalationPolicy).filter(EscalationPolicy.name == "默认升级策略").first()
    if not policy:
        policy = EscalationPolicy(name="默认升级策略", enabled=True, levels_json="[]")
        db.add(policy)
    if payload.enabled is not None:
        policy.enabled = payload.enabled
    if payload.levels:
        policy.levels_json = json.dumps(payload.levels, ensure_ascii=False)
    db.commit()
    db.refresh(policy)
    levels = json.loads(policy.levels_json) if policy.levels_json else []
    return {"id": policy.id, "name": policy.name, "enabled": policy.enabled, "levels": levels}
