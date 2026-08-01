"""告警通知设置 API。"""

import os
from pathlib import Path
from typing import Literal, Optional

import yaml
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field

import app.shared.config as config_module
from app.services.notification_service import (
    get_notification_service,
    reset_notification_service,
)
from app.shared.config import AlertsConfig, get_config
from app.shared.dependencies import require_permission

router = APIRouter(prefix="/api/alerts", tags=["告警通知"])

AlertChannel = Literal["email", "wechat_work", "dingtalk"]
TestChannel = Literal["all", "email", "wechat_work", "dingtalk"]
require_alert_manage = require_permission("alert:manage")


class AlertSettingsUpdate(BaseModel):
    """告警设置更新；敏感字段省略或留空表示保留现值。"""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    channels: list[AlertChannel] = Field(default_factory=list)
    email_enabled: bool = False
    email_smtp_host: str = Field(default="", max_length=255)
    email_smtp_port: int = Field(default=587, ge=1, le=65535)
    email_use_tls: bool = True
    email_username: Optional[str] = Field(default=None, max_length=255)
    email_password: Optional[str] = Field(default=None, max_length=4096)
    email_from_addr: str = Field(default="", max_length=320)
    email_recipients: list[str] = Field(default_factory=list)
    wechat_enabled: bool = False
    wechat_webhook_url: Optional[str] = Field(default=None, max_length=4096)
    dingtalk_enabled: bool = False
    dingtalk_webhook_url: Optional[str] = Field(default=None, max_length=4096)
    dingtalk_secret: Optional[str] = Field(default=None, max_length=4096)
    clear_email_username: bool = False
    clear_email_password: bool = False
    clear_wechat_webhook_url: bool = False
    clear_dingtalk_webhook_url: bool = False
    clear_dingtalk_secret: bool = False


def _settings_response(alerts: AlertsConfig) -> dict:
    """返回可编辑设置，但绝不回传凭据或完整 Webhook。"""
    return {
        "enabled": alerts.enabled,
        "channels": alerts.channels,
        "email_enabled": alerts.email.enabled,
        "email_smtp_host": alerts.email.smtp_host,
        "email_smtp_port": alerts.email.smtp_port,
        "email_use_tls": alerts.email.use_tls,
        "email_from_addr": alerts.email.from_addr,
        "email_recipients": alerts.email.recipients,
        "wechat_enabled": alerts.wechat_work.enabled,
        "dingtalk_enabled": alerts.dingtalk.enabled,
        "has_email_username": bool(alerts.email.username),
        "has_email_password": bool(alerts.email.password),
        "has_wechat_webhook_url": bool(alerts.wechat_work.webhook_url),
        "has_dingtalk_webhook_url": bool(alerts.dingtalk.webhook_url),
        "has_dingtalk_secret": bool(alerts.dingtalk.secret),
    }


def _set_sensitive(section: dict, key: str, value: Optional[str], clear: bool) -> None:
    if clear:
        section[key] = ""
    elif value:
        section[key] = value


def persist_alert_settings(
    settings: AlertSettingsUpdate,
    config_path: Path = Path("config.yaml"),
) -> None:
    """合并并原子写入告警配置，避免空输入误清除已保存的秘密。"""
    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as config_file:
            raw_config = yaml.safe_load(config_file) or {}
    else:
        raw_config = {}

    alerts = raw_config.setdefault("alerts", {})
    alerts["enabled"] = settings.enabled
    alerts["channels"] = list(settings.channels)

    email = alerts.setdefault("email", {})
    email.update({
        "enabled": settings.email_enabled,
        "smtp_host": settings.email_smtp_host,
        "smtp_port": settings.email_smtp_port,
        "use_tls": settings.email_use_tls,
        "from_addr": settings.email_from_addr,
        "recipients": settings.email_recipients,
    })
    _set_sensitive(email, "username", settings.email_username, settings.clear_email_username)
    _set_sensitive(email, "password", settings.email_password, settings.clear_email_password)

    wechat = alerts.setdefault("wechat_work", {})
    wechat["enabled"] = settings.wechat_enabled
    _set_sensitive(
        wechat,
        "webhook_url",
        settings.wechat_webhook_url,
        settings.clear_wechat_webhook_url,
    )

    dingtalk = alerts.setdefault("dingtalk", {})
    dingtalk["enabled"] = settings.dingtalk_enabled
    _set_sensitive(
        dingtalk,
        "webhook_url",
        settings.dingtalk_webhook_url,
        settings.clear_dingtalk_webhook_url,
    )
    _set_sensitive(
        dingtalk,
        "secret",
        settings.dingtalk_secret,
        settings.clear_dingtalk_secret,
    )

    config_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = config_path.with_suffix(f"{config_path.suffix}.tmp")
    try:
        with temporary_path.open("w", encoding="utf-8") as config_file:
            yaml.safe_dump(raw_config, config_file, default_flow_style=False, allow_unicode=True)
            config_file.flush()
            os.fsync(config_file.fileno())
        os.replace(temporary_path, config_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()

    config_module._config = None
    reset_notification_service()


@router.get("/settings")
async def get_alert_settings(
    _: None = Depends(require_alert_manage),
):
    """获取脱敏后的告警设置。"""
    return _settings_response(get_config().alerts)


@router.get("/status")
async def get_alert_status():
    """获取告警渠道运行状态；不包含任何配置秘密。"""
    service = get_notification_service()
    return service.get_channels_status()


@router.post("/settings")
async def update_alert_settings(
    settings: AlertSettingsUpdate,
    _: None = Depends(require_alert_manage),
):
    """更新告警设置。"""
    persist_alert_settings(settings)
    return {"message": "设置已保存"}


@router.post("/test")
async def test_alert_channel(
    channel: TestChannel = Query(default="all"),
    _: None = Depends(require_alert_manage),
):
    """向已配置渠道发送测试告警。"""
    service = get_notification_service()
    config = get_config()
    results = {}

    if channel in ("all", "email"):
        if config.alerts.email.enabled:
            results["email"] = service._send_email(
                subject="[NAS 测试] 邮件告警测试",
                body="这是一封测试邮件，确认邮件告警渠道配置正确。",
            )
        else:
            results["email"] = "未启用"

    if channel in ("all", "wechat_work"):
        if config.alerts.wechat_work.enabled:
            results["wechat_work"] = service._send_wechat(
                "send_text", content="🔔 [NAS 测试] 企业微信告警测试\n这是一条测试消息。",
            )
        else:
            results["wechat_work"] = "未启用"

    if channel in ("all", "dingtalk"):
        if config.alerts.dingtalk.enabled:
            results["dingtalk"] = service._send_dingtalk(
                "send_text", content="🔔 [NAS 测试] 钉钉告警测试\n这是一条测试消息。",
            )
        else:
            results["dingtalk"] = "未启用"

    return {"results": results}
