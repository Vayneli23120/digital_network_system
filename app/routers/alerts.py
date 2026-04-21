"""
告警通知设置 API
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session

from ..database import get_db
from ..config import get_config
from ..services.notification_service import get_notification_service

router = APIRouter(prefix="/api/alerts", tags=["告警通知"])


class AlertSettings(BaseModel):
    """告警设置"""
    enabled: bool = False
    channels: List[str] = []
    email_enabled: bool = False
    email_smtp_host: str = ""
    email_smtp_port: int = 587
    email_use_tls: bool = True
    email_username: str = ""
    email_password: str = ""
    email_from_addr: str = ""
    email_recipients: List[str] = []
    wechat_enabled: bool = False
    wechat_webhook_url: str = ""
    dingtalk_enabled: bool = False
    dingtalk_webhook_url: str = ""
    dingtalk_secret: str = ""


@router.get("/settings")
async def get_alert_settings():
    """获取告警设置"""
    config = get_config()
    alerts = config.alerts
    return {
        "enabled": alerts.enabled,
        "channels": alerts.channels,
        "email_enabled": alerts.email.enabled,
        "email_smtp_host": alerts.email.smtp_host,
        "email_smtp_port": alerts.email.smtp_port,
        "email_use_tls": alerts.email.use_tls,
        "email_username": alerts.email.username,
        "email_from_addr": alerts.email.from_addr,
        "email_recipients": alerts.email.recipients,
        "wechat_enabled": alerts.wechat_work.enabled,
        "wechat_webhook_url": alerts.wechat_work.webhook_url,
        "dingtalk_enabled": alerts.dingtalk.enabled,
        "dingtalk_webhook_url": alerts.dingtalk.webhook_url,
        "dingtalk_secret": alerts.dingtalk.secret,
    }


@router.get("/status")
async def get_alert_status():
    """获取告警渠道状态"""
    service = get_notification_service()
    return service.get_channels_status()


@router.post("/settings")
async def update_alert_settings(settings: dict):
    """更新告警设置（写入 config.yaml）"""
    import yaml
    from pathlib import Path

    config = get_config()
    config_path = Path("config.yaml")

    # 读取当前 config
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            raw_config = yaml.safe_load(f) or {}
    else:
        raw_config = {}

    if "alerts" not in raw_config:
        raw_config["alerts"] = {}

    raw_config["alerts"]["enabled"] = settings.get("enabled", False)
    raw_config["alerts"]["channels"] = settings.get("channels", [])

    # Email
    raw_config.setdefault("alerts", {}).setdefault("email", {})
    raw_config["alerts"]["email"]["enabled"] = settings.get("email_enabled", False)
    raw_config["alerts"]["email"]["smtp_host"] = settings.get("email_smtp_host", "")
    raw_config["alerts"]["email"]["smtp_port"] = settings.get("email_smtp_port", 587)
    raw_config["alerts"]["email"]["use_tls"] = settings.get("email_use_tls", True)
    raw_config["alerts"]["email"]["username"] = settings.get("email_username", "")
    raw_config["alerts"]["email"]["password"] = settings.get("email_password", "")
    raw_config["alerts"]["email"]["from_addr"] = settings.get("email_from_addr", "")
    raw_config["alerts"]["email"]["recipients"] = settings.get("email_recipients", [])

    # WeChat Work
    raw_config.setdefault("alerts", {}).setdefault("wechat_work", {})
    raw_config["alerts"]["wechat_work"]["enabled"] = settings.get("wechat_enabled", False)
    raw_config["alerts"]["wechat_work"]["webhook_url"] = settings.get("wechat_webhook_url", "")

    # DingTalk
    raw_config.setdefault("alerts", {}).setdefault("dingtalk", {})
    raw_config["alerts"]["dingtalk"]["enabled"] = settings.get("dingtalk_enabled", False)
    raw_config["alerts"]["dingtalk"]["webhook_url"] = settings.get("dingtalk_webhook_url", "")
    raw_config["alerts"]["dingtalk"]["secret"] = settings.get("dingtalk_secret", "")

    # 写回 config.yaml
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(raw_config, f, default_flow_style=False, allow_unicode=True)

    # 重置全局 config 单例
    from ..config import _config
    import app.config as config_module
    config_module._config = None

    return {"message": "设置已保存"}


@router.post("/test")
async def test_alert_channel(channel: str = "all"):
    """测试告警渠道"""
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
