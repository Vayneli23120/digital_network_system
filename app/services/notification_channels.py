"""通知渠道服务（二期）——渠道配置 DB 化 + 发送重试 + 熔断

- 渠道配置加密入库（复用 app.shared.crypto：Fernet，密钥 ENCRYPTION_KEY/JWT_SECRET 派生）
- 发送失败指数退避重试（×2，进程内同步），连续失败 N 次熔断该渠道 5 分钟
- DB 无对应渠道记录时回退 config.yaml 现有行为（平滑过渡）
"""

import json
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.shared.crypto import decrypt_or_passthrough, encrypt_text
from app.shared.models import NotificationChannel

logger = logging.getLogger(__name__)

CHANNEL_TYPES = ("email", "wechat_work", "dingtalk", "webhook")

# 熔断阈值：连续失败 N 次 → 暂停 BREAK_SECONDS 秒
CIRCUIT_FAIL_THRESHOLD = 3
CIRCUIT_BREAK_SECONDS = 300

# 重试：指数退避（秒），共 2 次重试
RETRY_BACKOFF_SECONDS = (1, 4)

_lock = threading.Lock()
_fail_counts: Dict[str, int] = {}
_blocked_until: Dict[str, datetime] = {}


def _channel_key(channel_type: str) -> str:
    return channel_type


def is_circuit_open(channel_type: str) -> bool:
    with _lock:
        blocked = _blocked_until.get(_channel_key(channel_type))
        if blocked and blocked > datetime.utcnow():
            return True
        if blocked:
            _blocked_until.pop(_channel_key(channel_type), None)
            _fail_counts.pop(_channel_key(channel_type), None)
        return False


def record_success(channel_type: str) -> None:
    with _lock:
        _fail_counts.pop(_channel_key(channel_type), None)
        _blocked_until.pop(_channel_key(channel_type), None)


def record_failure(channel_type: str) -> bool:
    """记录失败；返回 True 表示本次触发熔断。"""
    key = _channel_key(channel_type)
    with _lock:
        count = _fail_counts.get(key, 0) + 1
        _fail_counts[key] = count
        if count >= CIRCUIT_FAIL_THRESHOLD:
            _blocked_until[key] = datetime.utcnow() + timedelta(seconds=CIRCUIT_BREAK_SECONDS)
            _fail_counts.pop(key, None)
            return True
        return False


def send_with_retry(channel_type: str, send_fn) -> bool:
    """带熔断与指数退避重试的渠道发送；返回是否成功。"""
    if is_circuit_open(channel_type):
        logger.warning("渠道 %s 已熔断，跳过本次发送", channel_type)
        return False
    for attempt in range(1 + len(RETRY_BACKOFF_SECONDS)):
        try:
            ok = bool(send_fn())
            if ok:
                record_success(channel_type)
                return True
        except Exception:
            ok = False
        if attempt < len(RETRY_BACKOFF_SECONDS):
            time.sleep(RETRY_BACKOFF_SECONDS[attempt])
    if record_failure(channel_type):
        logger.error("渠道 %s 连续失败，熔断 %s 秒", channel_type, CIRCUIT_BREAK_SECONDS)
    return False


def _decrypt_config(row: NotificationChannel) -> dict:
    if not row.config_encrypted:
        return {}
    try:
        raw = decrypt_or_passthrough(row.config_encrypted)
        value = json.loads(raw)
        return value if isinstance(value, dict) else {}
    except Exception:
        logger.exception("渠道配置解密失败 channel=%s", row.type)
        return {}


def seed_channels_from_config(db: Session, alerts_config) -> None:
    """幂等：config.yaml 现有渠道配置 seed 进 DB（仅当 DB 尚无该类型渠道时）。"""
    try:
        existing_types = {c.type for c in db.query(NotificationChannel).all()}

        if "email" not in existing_types and alerts_config.email.enabled:
            payload = {
                "smtp_host": alerts_config.email.smtp_host,
                "smtp_port": alerts_config.email.smtp_port,
                "use_tls": alerts_config.email.use_tls,
                "username": alerts_config.email.username or "",
                "password": alerts_config.email.password or "",
                "from_addr": alerts_config.email.from_addr,
                "recipients": list(alerts_config.email.recipients or []),
            }
            db.add(NotificationChannel(type="email", name="邮件渠道",
                                       enabled=alerts_config.email.enabled,
                                       config_encrypted=encrypt_text(json.dumps(payload, ensure_ascii=False))))
            logger.info("[channels] 已从 config.yaml seed 邮件渠道")

        if "wechat_work" not in existing_types and alerts_config.wechat_work.enabled:
            payload = {"webhook_url": alerts_config.wechat_work.webhook_url or ""}
            db.add(NotificationChannel(type="wechat_work", name="企业微信渠道",
                                       enabled=alerts_config.wechat_work.enabled,
                                       config_encrypted=encrypt_text(json.dumps(payload, ensure_ascii=False))))
            logger.info("[channels] 已从 config.yaml seed 企业微信渠道")

        if "dingtalk" not in existing_types and alerts_config.dingtalk.enabled:
            payload = {"webhook_url": alerts_config.dingtalk.webhook_url or "",
                       "secret": alerts_config.dingtalk.secret or ""}
            db.add(NotificationChannel(type="dingtalk", name="钉钉渠道",
                                       enabled=alerts_config.dingtalk.enabled,
                                       config_encrypted=encrypt_text(json.dumps(payload, ensure_ascii=False))))
            logger.info("[channels] 已从 config.yaml seed 钉钉渠道")

        db.commit()
    except Exception:
        db.rollback()
        logger.exception("渠道 seed 失败")


def get_db_channel(db: Session, channel_type: str) -> Optional[dict]:
    """读取 DB 渠道（解密配置）。返回 {enabled, config} 或 None。"""
    row = db.query(NotificationChannel).filter(
        NotificationChannel.type == channel_type,
        NotificationChannel.enabled == True,  # noqa: E712
    ).first()
    if not row:
        return None
    return {"enabled": bool(row.enabled), "config": _decrypt_config(row)}
