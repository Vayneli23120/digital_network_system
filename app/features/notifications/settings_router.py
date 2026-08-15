"""通知设置 API（二期）：渠道管理 / 模板 / 策略 / 发送日志

- 渠道配置加密入库（Fernet），敏感字段脱敏返回、留空即保留
- 策略：级别×事件×目标×渠道×模板×频控
- 发送日志查询（notification_log）
"""

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.shared.crypto import encrypt_text
from app.shared.database import get_db
from app.shared.dependencies import require_permission
from app.shared.models import (
    NotificationChannel,
    NotificationLog,
    NotificationPolicy,
    NotificationTemplate,
    Role,
    User,
    UserGroup,
)

router = APIRouter(prefix="/api/notification-settings", tags=["通知设置"])

require_notification_manage = require_permission("notification:manage")

CHANNEL_TYPES = ("email", "wechat_work", "dingtalk", "webhook")


# ==================== 请求模型 ====================

class ChannelCreate(BaseModel):
    type: str = Field(pattern="^(email|wechat_work|dingtalk|webhook)$")
    name: str = Field(min_length=1, max_length=100)
    enabled: bool = True
    config: dict = Field(default_factory=dict)


class ChannelUpdate(BaseModel):
    name: Optional[str] = None
    enabled: Optional[bool] = None
    config: dict = Field(default_factory=dict)  # 敏感字段留空/省略表示保留现值
    clear_keys: list[str] = Field(default_factory=list)  # 显式置空的敏感键


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    channel_type: str = "email"
    subject_tpl: str = "{{ title }}"
    body_tpl: str = "{{ content }}"


class PolicyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    enabled: bool = True
    priority: int = 100
    severities: Optional[list[str]] = None
    event_types: Optional[list[str]] = None
    target_type: str = Field(default="all", pattern="^(all|group|role|user)$")
    target_id: Optional[int] = None
    channels: list[str] = Field(default_factory=lambda: ["inapp", "email", "wechat_work", "dingtalk"])
    template_id: Optional[int] = None
    rate_limit_window_s: int = 0
    rate_limit_max: int = 0


# ==================== 渠道 ====================

def _channel_dict(row: NotificationChannel) -> dict:
    from app.services.notification_channels import _decrypt_config
    cfg = _decrypt_config(row)
    masked = dict(cfg)
    has_secret = {k: bool(masked.get(k)) for k in ("password", "webhook_url", "secret", "username") if k in masked}
    for k in has_secret:
        masked.pop(k, None)
    return {
        "id": row.id,
        "type": row.type,
        "name": row.name,
        "enabled": row.enabled,
        "config": masked,
        "has_secret": has_secret,
    }


@router.get("/channels")
async def list_channels(db: Session = Depends(get_db),
                        _: None = Depends(require_notification_manage)):
    rows = db.query(NotificationChannel).order_by(NotificationChannel.id.asc()).all()
    return {"items": [_channel_dict(r) for r in rows]}


@router.post("/channels")
async def create_channel(payload: ChannelCreate, db: Session = Depends(get_db),
                         _: None = Depends(require_notification_manage)):
    if payload.type not in CHANNEL_TYPES:
        raise HTTPException(status_code=400, detail="不支持的渠道类型")
    if db.query(NotificationChannel).filter(NotificationChannel.type == payload.type).first():
        raise HTTPException(status_code=409, detail="该类型渠道已存在（每种类型一个，直接编辑即可）")
    row = NotificationChannel(
        type=payload.type, name=payload.name, enabled=payload.enabled,
        config_encrypted=encrypt_text(json.dumps(payload.config, ensure_ascii=False)),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _channel_dict(row)


@router.put("/channels/{channel_id}")
async def update_channel(channel_id: int, payload: ChannelUpdate, db: Session = Depends(get_db),
                         _: None = Depends(require_notification_manage)):
    row = db.query(NotificationChannel).filter(NotificationChannel.id == channel_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="渠道不存在")
    from app.services.notification_channels import _decrypt_config
    merged = _decrypt_config(row)
    if payload.name:
        row.name = payload.name
    if payload.enabled is not None:
        row.enabled = payload.enabled
    for key, value in payload.config.items():
        if value:
            merged[key] = value
    for key in payload.clear_keys:
        merged.pop(key, None)
    row.config_encrypted = encrypt_text(json.dumps(merged, ensure_ascii=False))
    db.commit()
    db.refresh(row)
    return _channel_dict(row)


@router.delete("/channels/{channel_id}")
async def delete_channel(channel_id: int, db: Session = Depends(get_db),
                         _: None = Depends(require_notification_manage)):
    row = db.query(NotificationChannel).filter(NotificationChannel.id == channel_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="渠道不存在")
    db.delete(row)
    db.commit()
    return {"message": "渠道已删除"}


@router.post("/channels/{channel_id}/test")
async def test_channel(channel_id: int, db: Session = Depends(get_db),
                       _: None = Depends(require_notification_manage)):
    """向渠道发送测试消息。"""
    row = db.query(NotificationChannel).filter(NotificationChannel.id == channel_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="渠道不存在")
    from app.services.notification_channels import _decrypt_config
    from app.services.notification_service import get_notification_service
    cfg = _decrypt_config(row)
    svc = get_notification_service()
    if row.type == "email":
        if not cfg.get("smtp_host"):
            return {"ok": False, "detail": "邮件渠道未配置 SMTP 主机"}
        from app.services.notification_channels import send_with_retry
        ok = send_with_retry("email", lambda: svc._send_email(
            subject="[NAS 测试] 渠道测试", body="这是一封渠道测试邮件。",
            to_addresses=cfg.get("recipients") or None))
        return {"ok": bool(ok)}
    if row.type == "wechat_work":
        ok = svc._send_wechat("send_text", content="🔔 [NAS 测试] 企业微信渠道测试",
                              webhook_url=cfg.get("webhook_url") or None)
        return {"ok": bool(ok)}
    if row.type == "dingtalk":
        ok = svc._send_dingtalk("send_text", content="🔔 [NAS 测试] 钉钉渠道测试",
                                webhook_url=cfg.get("webhook_url") or None,
                                secret=cfg.get("secret") or None)
        return {"ok": bool(ok)}
    return {"ok": False, "detail": f"渠道类型 {row.type} 暂不支持测试"}


# ==================== 全局总开关（合并自旧"告警通知设置"） ====================

class GlobalSwitchUpdate(BaseModel):
    enabled: bool


@router.get("/global")
async def get_global_switch(_: None = Depends(require_notification_manage)):
    """读取告警总开关（config.yaml alerts.enabled，渠道明细已在 DB）。"""
    from app.shared.config import get_config
    return {"alerts_enabled": bool(get_config().alerts.enabled)}


@router.put("/global")
async def update_global_switch(payload: GlobalSwitchUpdate,
                               _: None = Depends(require_notification_manage)):
    """更新告警总开关（只写 config.yaml 的 alerts.enabled，原子替换）。"""
    import os as _os
    import yaml as _yaml
    from pathlib import Path as _Path

    config_path = _Path("config.yaml")
    raw = {}
    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as f:
            raw = _yaml.safe_load(f) or {}
    raw.setdefault("alerts", {})["enabled"] = payload.enabled
    config_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = config_path.with_suffix(config_path.suffix + ".tmp")
    try:
        with tmp_path.open("w", encoding="utf-8") as f:
            _yaml.safe_dump(raw, f, default_flow_style=False, allow_unicode=True)
            f.flush()
            _os.fsync(f.fileno())
        _os.replace(tmp_path, config_path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    import app.shared.config as config_module
    config_module._config = None
    from app.services.notification_service import reset_notification_service
    reset_notification_service()
    return {"alerts_enabled": payload.enabled}


# ==================== 模板 ====================

def _template_dict(row: NotificationTemplate) -> dict:
    return {
        "id": row.id, "name": row.name, "channel_type": row.channel_type,
        "subject_tpl": row.subject_tpl, "body_tpl": row.body_tpl,
    }


@router.get("/templates")
async def list_templates(db: Session = Depends(get_db),
                         _: None = Depends(require_notification_manage)):
    rows = db.query(NotificationTemplate).order_by(NotificationTemplate.id.asc()).all()
    return {"items": [_template_dict(r) for r in rows]}


@router.post("/templates")
async def create_template(payload: TemplateCreate, db: Session = Depends(get_db),
                          _: None = Depends(require_notification_manage)):
    row = NotificationTemplate(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return _template_dict(row)


@router.put("/templates/{template_id}")
async def update_template(template_id: int, payload: TemplateCreate, db: Session = Depends(get_db),
                          _: None = Depends(require_notification_manage)):
    row = db.query(NotificationTemplate).filter(NotificationTemplate.id == template_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="模板不存在")
    row.name = payload.name
    row.channel_type = payload.channel_type
    row.subject_tpl = payload.subject_tpl
    row.body_tpl = payload.body_tpl
    db.commit()
    db.refresh(row)
    return _template_dict(row)


@router.delete("/templates/{template_id}")
async def delete_template(template_id: int, db: Session = Depends(get_db),
                          _: None = Depends(require_notification_manage)):
    row = db.query(NotificationTemplate).filter(NotificationTemplate.id == template_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="模板不存在")
    db.delete(row)
    db.commit()
    return {"message": "模板已删除"}


# ==================== 策略 ====================

def _policy_dict(row: NotificationPolicy) -> dict:
    return {
        "id": row.id, "name": row.name, "enabled": row.enabled, "priority": row.priority,
        "severities": json.loads(row.severities) if row.severities else [],
        "event_types": json.loads(row.event_types) if row.event_types else [],
        "target_type": row.target_type, "target_id": row.target_id,
        "channels": json.loads(row.channels) if row.channels else [],
        "template_id": row.template_id,
        "rate_limit_window_s": row.rate_limit_window_s,
        "rate_limit_max": row.rate_limit_max,
    }


@router.get("/policies")
async def list_policies(db: Session = Depends(get_db),
                        _: None = Depends(require_notification_manage)):
    rows = db.query(NotificationPolicy).order_by(NotificationPolicy.priority.asc(), NotificationPolicy.id.asc()).all()
    return {"items": [_policy_dict(r) for r in rows]}


@router.post("/policies")
async def create_policy(payload: PolicyCreate, db: Session = Depends(get_db),
                        _: None = Depends(require_notification_manage)):
    row = NotificationPolicy(
        name=payload.name, enabled=payload.enabled, priority=payload.priority,
        severities=json.dumps(payload.severities, ensure_ascii=False) if payload.severities else None,
        event_types=json.dumps(payload.event_types, ensure_ascii=False) if payload.event_types else None,
        target_type=payload.target_type, target_id=payload.target_id,
        channels=json.dumps(payload.channels, ensure_ascii=False),
        template_id=payload.template_id,
        rate_limit_window_s=payload.rate_limit_window_s,
        rate_limit_max=payload.rate_limit_max,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _policy_dict(row)


@router.put("/policies/{policy_id}")
async def update_policy(policy_id: int, payload: PolicyCreate, db: Session = Depends(get_db),
                        _: None = Depends(require_notification_manage)):
    row = db.query(NotificationPolicy).filter(NotificationPolicy.id == policy_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="策略不存在")
    row.name = payload.name
    row.enabled = payload.enabled
    row.priority = payload.priority
    row.severities = json.dumps(payload.severities, ensure_ascii=False) if payload.severities else None
    row.event_types = json.dumps(payload.event_types, ensure_ascii=False) if payload.event_types else None
    row.target_type = payload.target_type
    row.target_id = payload.target_id
    row.channels = json.dumps(payload.channels, ensure_ascii=False)
    row.template_id = payload.template_id
    row.rate_limit_window_s = payload.rate_limit_window_s
    row.rate_limit_max = payload.rate_limit_max
    db.commit()
    db.refresh(row)
    return _policy_dict(row)


@router.delete("/policies/{policy_id}")
async def delete_policy(policy_id: int, db: Session = Depends(get_db),
                        _: None = Depends(require_notification_manage)):
    row = db.query(NotificationPolicy).filter(NotificationPolicy.id == policy_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="策略不存在")
    db.delete(row)
    db.commit()
    return {"message": "策略已删除"}


@router.get("/targets")
async def list_targets(db: Session = Depends(get_db),
                       _: None = Depends(require_notification_manage)):
    """策略目标选择器数据：用户/角色/分组。"""
    return {
        "users": [{"id": u.id, "username": u.username} for u in db.query(User).all()],
        "roles": [{"id": r.id, "name": r.name} for r in db.query(Role).all()],
        "groups": [{"id": g.id, "name": g.name} for g in db.query(UserGroup).all()],
    }


# ==================== 统计（三期） ====================

@router.get("/stats")
async def get_governance_stats(db: Session = Depends(get_db),
                               _: None = Depends(require_notification_manage)):
    """告警治理统计：渠道成功率、升级触发、组 MTTA/MTTR、静默/抑制现状。"""
    from datetime import datetime, timedelta
    from app.shared.models import FaultRecord, MaintenanceTask

    now = datetime.utcnow()
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)

    # ---- 渠道成功率（24h / 7d）----
    def channel_stats(since):
        rows = (db.query(NotificationLog.channel, NotificationLog.status)
                .filter(NotificationLog.created_at >= since)
                .all())
        stats = {}
        for channel, status in rows:
            item = stats.setdefault(channel, {"sent": 0, "failed": 0, "suppressed": 0})
            item[status if status in item else "sent"] += 1
        result = []
        for channel, item in stats.items():
            total = item["sent"] + item["failed"]
            result.append({
                "channel": channel,
                "sent": item["sent"],
                "failed": item["failed"],
                "suppressed": item["suppressed"],
                "success_rate": round(item["sent"] / total * 100, 1) if total else None,
            })
        return result

    # ---- 升级触发（7d，按层级）----
    escalated = (db.query(FaultRecord.escalation_level)
                 .filter(FaultRecord.escalated_at >= week_ago)
                 .all())
    by_level = {}
    for (level,) in escalated:
        key = f"L{level or 0}"
        by_level[key] = by_level.get(key, 0) + 1

    # ---- 组 MTTA/MTTR（7d 内解决；MTTA 用 assigned_at）----
    week_faults = db.query(FaultRecord).filter(FaultRecord.created_at >= week_ago).all()
    group_stats = {}
    for fault in week_faults:
        gid = fault.group_id
        item = group_stats.setdefault(gid, {
            "group_id": gid, "group_name": None, "total": 0, "open": 0,
            "mtta_sum_s": 0.0, "mtta_n": 0, "mttr_sum_s": 0.0, "mttr_n": 0,
        })
        item["total"] += 1
        if fault.status not in ("resolved", "closed"):
            item["open"] += 1
        if fault.assigned_at and fault.created_at:
            item["mtta_sum_s"] += (fault.assigned_at - fault.created_at).total_seconds()
            item["mtta_n"] += 1
        if fault.resolved_at and fault.created_at:
            item["mttr_sum_s"] += (fault.resolved_at - fault.created_at).total_seconds()
            item["mttr_n"] += 1
    group_rows = []
    for gid, item in group_stats.items():
        group = db.query(UserGroup).filter(UserGroup.id == gid).first() if gid else None
        item["group_name"] = group.name if group else ("未分组" if gid is None else f"组#{gid}")
        item["mtta_min"] = round(item["mtta_sum_s"] / 60 / item["mtta_n"], 1) if item["mtta_n"] else None
        item["mttr_hours"] = round(item["mttr_sum_s"] / 3600 / item["mttr_n"], 2) if item["mttr_n"] else None
        item.pop("mtta_sum_s", None)
        item.pop("mttr_sum_s", None)
        item.pop("mtta_n", None)
        item.pop("mttr_n", None)
        group_rows.append(item)
    group_rows.sort(key=lambda x: x["total"], reverse=True)

    # ---- 静默/抑制现状 + 维护窗口 ----
    open_faults = db.query(FaultRecord).filter(
        FaultRecord.status.notin_(["resolved", "closed"])).all()
    silenced_open = sum(1 for f in open_faults if f.silenced)
    suppressed_open = sum(1 for f in open_faults if f.suppressed_by)
    active_windows = 0
    for task in db.query(MaintenanceTask).filter(MaintenanceTask.scheduled_date.isnot(None)).all():
        end = task.scheduled_end or (task.scheduled_date + timedelta(
            hours=float(task.estimated_hours or 4)))
        if task.scheduled_date <= now < end:
            active_windows += 1

    return {
        "channels_24h": channel_stats(day_ago),
        "channels_7d": channel_stats(week_ago),
        "escalations_7d": {"total": sum(by_level.values()), "by_level": by_level},
        "groups": group_rows,
        "open_faults": len(open_faults),
        "silenced_open": silenced_open,
        "suppressed_open": suppressed_open,
        "active_maintenance_windows": active_windows,
    }


# ==================== 发送日志 ====================

@router.get("/logs")
async def list_logs(
    event_type: Optional[str] = None,
    channel: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: None = Depends(require_notification_manage),
):
    query = db.query(NotificationLog)
    if event_type:
        query = query.filter(NotificationLog.event_type == event_type)
    if channel:
        query = query.filter(NotificationLog.channel == channel)
    if status:
        query = query.filter(NotificationLog.status == status)
    rows = query.order_by(NotificationLog.id.desc()).limit(limit).all()
    return {"items": [{
        "id": r.id,
        "event_type": r.event_type,
        "fault_id": r.fault_id,
        "maintenance_id": r.maintenance_id,
        "channel": r.channel,
        "recipient": r.recipient,
        "title": r.title,
        "status": r.status,
        "retry_count": r.retry_count,
        "error": r.error,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in rows]}
