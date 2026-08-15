"""
统一告警通知服务

统一管理多种告警渠道（邮件、企业微信、钉钉），提供统一的告警发送接口。
一期（v1.1）新增 dispatch() 统一通知出口：站内 + 邮件 + IM 三渠道，全量落 notification_log 审计。
二期（v1.2）dispatch() 挂接通知策略表：级别×事件×目标×渠道×模板多维路由 + 频控 + 重试熔断；
未命中策略时回退一期默认行为（recipients 直用 + config.yaml 渠道）。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from loguru import logger

from app.shared.config import get_config


def record_notification_log(db, *, event_type: str, channel: str, recipient: str,
                            title: str, status: str, fault_id: Optional[int] = None,
                            maintenance_id: Optional[int] = None,
                            retry_count: int = 0, error: Optional[str] = None) -> None:
    """写通知发送日志（不 commit，由调用方统一提交）。"""
    try:
        from app.shared.models import NotificationLog
        db.add(NotificationLog(
            event_type=event_type,
            fault_id=fault_id,
            maintenance_id=maintenance_id,
            channel=channel,
            recipient=recipient,
            title=title[:300],
            status=status,
            retry_count=retry_count,
            error=(error or "")[:2000] if error else None,
        ))
    except Exception:
        logger.exception("写通知日志失败 event={} channel={}", event_type, channel)


class NotificationService:
    """统一告警通知服务"""

    # ---- 频控（进程内滑动窗口；key = 策略:事件:对象）----
    _rate_limits: Dict[str, List[float]] = {}

    def __init__(self):
        self.config = get_config()

    # ==================== 一期兼容方法（保留） ====================

    def _send_email(self, subject: str, body: str, **kwargs):
        """发送邮件告警"""
        try:
            from .email_service import get_email_service
            service = get_email_service()
            return service.send_email(subject, body, **kwargs)
        except Exception as e:
            logger.error(f"邮件告警失败：{e}")
            return False

    def _send_wechat(self, method: str, **kwargs):
        """发送企业微信告警"""
        try:
            if not self.config.alerts.wechat_work.enabled or not self.config.alerts.wechat_work.webhook_url:
                return False
            from .wechat_work_service import get_wechat_work_service
            service = get_wechat_work_service()
            fn = getattr(service, method, None)
            if fn:
                return fn(**kwargs)
            return False
        except Exception as e:
            logger.error(f"企业微信告警失败：{e}")
            return False

    def _send_dingtalk(self, method: str, **kwargs):
        """发送钉钉告警"""
        try:
            if not self.config.alerts.dingtalk.enabled or not self.config.alerts.dingtalk.webhook_url:
                return False
            from .dingtalk_service import get_dingtalk_service
            service = get_dingtalk_service()
            fn = getattr(service, method, None)
            if fn:
                return fn(**kwargs)
            return False
        except Exception as e:
            logger.error(f"钉钉告警失败：{e}")
            return False

    def notify_backup_failure(self, device_name: str, error: str,
                               operator: Optional[str] = None):
        """备份失败告警 — 多渠道发送"""
        if not self.config.alerts.enabled:
            return
        self._send_email(
            subject=f"[NAS 告警] 设备备份失败：{device_name}",
            body=f"设备：{device_name}\n操作人：{operator or '系统'}\n错误：{error}",
        )
        self._send_wechat("send_backup_failure_alert", device_name=device_name, error=error, operator=operator)
        self._send_dingtalk("send_backup_failure_alert", device_name=device_name, error=error, operator=operator)

    def notify_device_unreachable(self, device_name: str, ip: str,
                                   operator: Optional[str] = None):
        """设备不可达告警 — 多渠道发送"""
        if not self.config.alerts.enabled:
            return
        self._send_email(
            subject=f"[NAS 告警] 设备不可达：{device_name}",
            body=f"设备：{device_name}\nIP：{ip}\n操作人：{operator or '系统'}",
        )
        self._send_wechat("send_device_unreachable_alert", device_name=device_name, ip=ip, operator=operator)
        self._send_dingtalk("send_device_unreachable_alert", device_name=device_name, ip=ip, operator=operator)

    def notify_device_recovered(self, device_name: str, ip: str,
                                  downtime: Optional[int] = None):
        """设备恢复通知 — 多渠道发送"""
        if not self.config.alerts.enabled:
            return
        downtime_text = f"\n离线时间：约 {downtime} 分钟" if downtime else ""
        self._send_email(
            subject=f"[NAS 通知] 设备恢复：{device_name}",
            body=f"设备：{device_name}\nIP：{ip}\n状态：已恢复在线{downtime_text}\n时间：{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}",
        )
        self._send_wechat("send_device_recovered_alert", device_name=device_name, ip=ip, downtime=downtime)
        self._send_dingtalk("send_device_recovered_alert", device_name=device_name, ip=ip, downtime=downtime)

    def notify_fault(self, device_name: str, fault_no: str,
                      severity: str, description: str):
        """故障告警 — 多渠道发送（仅 critical/major）"""
        if severity not in ("critical", "major"):
            return
        if not self.config.alerts.enabled:
            return
        from .email_service import get_email_service
        get_email_service().send_fault_alert(
            device_name=device_name, fault_no=fault_no,
            severity=severity, description=description,
        )
        self._send_wechat("send_fault_alert", device_name=device_name, fault_no=fault_no,
                          severity=severity, description=description)
        self._send_dingtalk("send_fault_alert", device_name=device_name, fault_no=fault_no,
                            severity=severity, description=description)

    def notify_low_stock(self, part_name: str, part_number: str,
                          quantity: int, min_quantity: int):
        """库存不足预警 — 多渠道发送"""
        if not self.config.alerts.enabled:
            return
        self._send_wechat("send_low_stock_alert", part_name=part_name, part_number=part_number,
                          quantity=quantity, min_quantity=min_quantity)
        self._send_dingtalk("send_low_stock_alert", part_name=part_name, part_number=part_number,
                            quantity=quantity, min_quantity=min_quantity)

    # ==================== 二期：策略引擎 ====================

    @classmethod
    def _rate_limited(cls, key: str, window_s: int, max_count: int) -> bool:
        """内存滑动窗口频控；返回 True 表示超限（应抑制）。"""
        import time as _time
        now = _time.time()
        stamps = cls._rate_limits.setdefault(key, [])
        stamps[:] = [t for t in stamps if now - t < window_s]
        if max_count > 0 and len(stamps) >= max_count:
            return True
        stamps.append(now)
        return False

    def _match_policy(self, db, event_type: str, severity: Optional[str]):
        """按优先级匹配通知策略；无命中返回 None。"""
        import json as _json
        from app.shared.models import NotificationPolicy
        policies = (db.query(NotificationPolicy)
                    .filter(NotificationPolicy.enabled == True)  # noqa: E712
                    .order_by(NotificationPolicy.priority.asc(), NotificationPolicy.id.asc())
                    .all())
        for policy in policies:
            severities = _json.loads(policy.severities) if policy.severities else []
            event_types = _json.loads(policy.event_types) if policy.event_types else []
            if severities and (severity is None or severity not in severities):
                continue
            if event_types and event_type not in event_types:
                continue
            return policy
        return None

    def _resolve_policy_targets(self, db, policy) -> tuple:
        """按策略目标解析真实账号收件人与邮箱。"""
        from app.shared.models import User
        usernames: List[str] = []
        target_type = (policy.target_type or "all").lower()

        if target_type == "user":
            if policy.target_id:
                user = db.query(User).filter(User.id == policy.target_id).first()
                if user:
                    usernames.append(user.username)
        elif target_type == "role":
            from app.shared.models import Role
            if policy.target_id:
                role = db.query(Role).filter(Role.id == policy.target_id).first()
                if role:
                    usernames += [u.username for u in role.users]
        elif target_type == "group":
            from app.features.groups.service import group_members
            if policy.target_id:
                usernames += [m.username for m in group_members(db, policy.target_id)]
            usernames.append("admin")
        else:  # all：默认组 + admin
            from app.features.groups.service import resolve_fault_targets
            _assigned, usernames, emails, _group = resolve_fault_targets(db)
            return usernames, emails

        usernames = list(dict.fromkeys([u for u in usernames if u]))
        emails = [u.email for u in db.query(User).filter(User.username.in_(usernames)).all() if u.email]
        return usernames, emails

    def _render_template(self, db, policy, *, title: str, content: str, event_type: str,
                         severity: Optional[str], fault_id: Optional[int],
                         maintenance_id: Optional[int], reference_type: Optional[str],
                         reference_id: Optional[int],
                         extra_context: Optional[dict] = None) -> tuple:
        """按策略模板渲染标题/正文；无模板或渲染失败回退原文。"""
        if not policy or not policy.template_id:
            return title, content
        from app.shared.models import NotificationTemplate
        tpl = db.query(NotificationTemplate).filter(NotificationTemplate.id == policy.template_id).first()
        if not tpl:
            return title, content
        context = {
            "title": title,
            "content": content,
            "event_type": event_type,
            "severity": severity or "",
            "fault_id": fault_id or "",
            "maintenance_id": maintenance_id or "",
            "reference_type": reference_type or "",
            "reference_id": reference_id or "",
        }
        if extra_context:
            context.update(extra_context)
        try:
            from jinja2.sandbox import SandboxedEnvironment
            env = SandboxedEnvironment()
            subject = env.from_string(tpl.subject_tpl or "{{ title }}").render(**context)
            body = env.from_string(tpl.body_tpl or "{{ content }}").render(**context)
            return subject, body
        except Exception as e:
            logger.warning(f"通知模板渲染失败，回退原文: {e}")
            return title, content

    def _channel_db(self, db, channel_type: str) -> Optional[dict]:
        """读取 DB 渠道（解密配置）；无记录返回 None（回退 config.yaml）。"""
        from app.services.notification_channels import get_db_channel
        return get_db_channel(db, channel_type)

    def _send_inapp(self, db, *, event_type, title, content, recipients,
                    reference_type=None, reference_id=None, fault_id=None,
                    maintenance_id=None) -> int:
        from app.services.system_notification import SystemNotificationService
        inapp_service = SystemNotificationService(db)
        count = 0
        seen = set()
        for user in recipients or []:
            if not user or user in seen:
                continue
            seen.add(user)
            try:
                inapp_service.send_notification(
                    user=user, type=event_type, title=title,
                    content=(content or "")[:2000],
                    reference_type=reference_type, reference_id=reference_id,
                )
                record_notification_log(db, event_type=event_type, channel="inapp",
                                        recipient=user, title=title, status="sent",
                                        fault_id=fault_id, maintenance_id=maintenance_id)
                count += 1
            except Exception as e:
                logger.warning(f"站内通知失败 user={user}: {e}")
                record_notification_log(db, event_type=event_type, channel="inapp",
                                        recipient=user, title=title, status="failed",
                                        fault_id=fault_id, maintenance_id=maintenance_id, error=str(e))
        return count

    def _any_db_channel_enabled(self, db) -> bool:
        for ctype in ("email", "wechat_work", "dingtalk", "webhook"):
            dbc = self._channel_db(db, ctype)
            if dbc and dbc["enabled"]:
                return True
        return False

    def _send_email_robust(self, db, subject: str, body: str,
                           to_addresses: Optional[List[str]] = None) -> bool:
        """邮件发送（DB 渠道覆盖 recipients + 重试熔断）。

        渠道开关以 DB 为准；仅当 DB 无该渠道时才回退 config.yaml 开关（兜底）。
        """
        from app.services.notification_channels import send_with_retry
        dbc = self._channel_db(db, "email")
        if dbc is not None and not dbc["enabled"]:
            return False
        if dbc is not None and dbc["config"].get("recipients"):
            to_addresses = list(dbc["config"]["recipients"])
        if dbc is None and not self.config.alerts.email.enabled:
            return False
        return send_with_retry(
            "email",
            lambda: self._send_email(subject=subject, body=body, to_addresses=to_addresses),
        )

    def _send_wechat_robust(self, db, content: str) -> bool:
        """企业微信发送（DB 渠道覆盖 webhook + 重试熔断）。"""
        from app.services.notification_channels import send_with_retry
        dbc = self._channel_db(db, "wechat_work")
        if dbc is not None and not dbc["enabled"]:
            return False
        url = (dbc["config"].get("webhook_url") or None) if dbc else None
        if not self.config.alerts.wechat_work.enabled and not url:
            return False
        return send_with_retry(
            "wechat_work",
            lambda: self._send_wechat("send_text", content=content, webhook_url=url),
        )

    def _send_dingtalk_robust(self, db, content: str) -> bool:
        """钉钉发送（DB 渠道覆盖 webhook/secret + 重试熔断）。"""
        from app.services.notification_channels import send_with_retry
        dbc = self._channel_db(db, "dingtalk")
        if dbc is not None and not dbc["enabled"]:
            return False
        url, secret = None, None
        if dbc:
            url = dbc["config"].get("webhook_url") or None
            secret = dbc["config"].get("secret") or None
        if not self.config.alerts.dingtalk.enabled and not url:
            return False
        return send_with_retry(
            "dingtalk",
            lambda: self._send_dingtalk("send_text", content=content, webhook_url=url, secret=secret),
        )

    def dispatch(
        self,
        db,
        *,
        event_type: str,
        title: str,
        content: str,
        recipients: List[str],
        emails: Optional[List[str]] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[int] = None,
        fault_id: Optional[int] = None,
        maintenance_id: Optional[int] = None,
        use_email: bool = True,
        use_im: bool = True,
        severity: Optional[str] = None,
        group_id: Optional[int] = None,
        extra_context: Optional[dict] = None,
    ) -> Dict[str, Any]:
        """统一通知出口（二期）：策略路由 + 模板 + 频控 + 重试熔断，全量落 notification_log。

        命中 notification_policy 时按策略目标/渠道/模板/频控发送；
        未命中时回退一期默认行为（recipients 直用 + config.yaml 渠道）。
        """
        policy = self._match_policy(db, event_type, severity)
        if policy is not None:
            return self._dispatch_via_policy(
                db, policy, event_type=event_type, title=title, content=content,
                severity=severity, reference_type=reference_type,
                reference_id=reference_id, fault_id=fault_id,
                maintenance_id=maintenance_id, extra_context=extra_context,
            )
        return self._dispatch_default(
            db, event_type=event_type, title=title, content=content,
            recipients=recipients, emails=emails,
            reference_type=reference_type, reference_id=reference_id,
            fault_id=fault_id, maintenance_id=maintenance_id,
            use_email=use_email, use_im=use_im,
        )

    def _dispatch_via_policy(self, db, policy, *, event_type, title, content,
                             severity=None, reference_type=None, reference_id=None,
                             fault_id=None, maintenance_id=None, extra_context=None) -> Dict[str, Any]:
        """按策略路由发送。"""
        import json as _json
        channels = _json.loads(policy.channels) if policy.channels else ["inapp", "email", "wechat_work", "dingtalk"]
        results: Dict[str, Any] = {
            "policy": policy.name, "inapp": 0, "email": False,
            "wechat_work": False, "dingtalk": False, "rate_limited": False,
        }

        # 频控：超限只落一条 suppressed 日志
        if policy.rate_limit_window_s and policy.rate_limit_max:
            rl_key = f"{policy.id}:{event_type}:{fault_id or reference_id or 'global'}"
            if self._rate_limited(rl_key, int(policy.rate_limit_window_s), int(policy.rate_limit_max)):
                results["rate_limited"] = True
                record_notification_log(db, event_type=event_type, channel="all",
                                        recipient="policy", title=title, status="suppressed",
                                        fault_id=fault_id, maintenance_id=maintenance_id)
                try:
                    db.commit()
                except Exception:
                    logger.exception("通知日志提交失败（频控）")
                return results

        usernames, emails = self._resolve_policy_targets(db, policy)
        subject, body = self._render_template(
            db, policy, title=title, content=content, event_type=event_type,
            severity=severity, fault_id=fault_id, maintenance_id=maintenance_id,
            reference_type=reference_type, reference_id=reference_id,
            extra_context=extra_context,
        )

        if "inapp" in channels:
            results["inapp"] = self._send_inapp(
                db, event_type=event_type, title=subject, content=body,
                recipients=usernames, reference_type=reference_type,
                reference_id=reference_id, fault_id=fault_id, maintenance_id=maintenance_id,
            )
        if "email" in channels:
            ok = self._send_email_robust(db, subject=subject, body=body, to_addresses=emails or None)
            results["email"] = bool(ok)
            record_notification_log(db, event_type=event_type, channel="email",
                                    recipient=",".join(emails) if emails else "config-recipients",
                                    title=subject, status="sent" if ok else "failed",
                                    fault_id=fault_id, maintenance_id=maintenance_id)
        if "wechat_work" in channels:
            ok = self._send_wechat_robust(db, f"{subject}\n{body}"[:1800])
            results["wechat_work"] = bool(ok)
            record_notification_log(db, event_type=event_type, channel="wechat_work",
                                    recipient="webhook", title=subject,
                                    status="sent" if ok else "failed",
                                    fault_id=fault_id, maintenance_id=maintenance_id)
        if "dingtalk" in channels:
            ok = self._send_dingtalk_robust(db, f"{subject}\n{body}"[:1800])
            results["dingtalk"] = bool(ok)
            record_notification_log(db, event_type=event_type, channel="dingtalk",
                                    recipient="webhook", title=subject,
                                    status="sent" if ok else "failed",
                                    fault_id=fault_id, maintenance_id=maintenance_id)

        try:
            db.commit()
        except Exception:
            logger.exception("通知日志提交失败（策略）")
        return results

    def _dispatch_default(self, db, *, event_type, title, content, recipients, emails=None,
                          reference_type=None, reference_id=None, fault_id=None,
                          maintenance_id=None, use_email=True, use_im=True) -> Dict[str, Any]:
        """一期默认行为（未命中策略时）：站内 + config.yaml 渠道，带重试熔断。"""
        results: Dict[str, Any] = {"inapp": 0, "email": False, "wechat_work": False, "dingtalk": False}
        # 主开关：config.yaml 总开关 或 任一 DB 渠道启用（渠道已 DB 化，二者皆可放行）
        alerts_enabled = bool(self.config.alerts.enabled) or self._any_db_channel_enabled(db)

        results["inapp"] = self._send_inapp(
            db, event_type=event_type, title=title, content=content,
            recipients=recipients, reference_type=reference_type,
            reference_id=reference_id, fault_id=fault_id, maintenance_id=maintenance_id,
        )
        try:
            db.commit()
        except Exception:
            logger.exception("通知日志提交失败")

        if not alerts_enabled:
            return results

        if use_email:
            to_addresses = emails or list(self.config.alerts.email.recipients or [])
            ok = self._send_email_robust(db, subject=title, body=content, to_addresses=to_addresses)
            results["email"] = bool(ok)
            record_notification_log(db, event_type=event_type, channel="email",
                                    recipient=",".join(to_addresses), title=title,
                                    status="sent" if ok else "failed",
                                    fault_id=fault_id, maintenance_id=maintenance_id)
        if use_im:
            im_body = f"{title}\n{content}"[:1800]
            ok_wechat = self._send_wechat_robust(db, im_body)
            results["wechat_work"] = bool(ok_wechat)
            record_notification_log(db, event_type=event_type, channel="wechat_work",
                                    recipient=self.config.alerts.wechat_work.webhook_url or "webhook",
                                    title=title, status="sent" if ok_wechat else "failed",
                                    fault_id=fault_id, maintenance_id=maintenance_id)

            ok_dingtalk = self._send_dingtalk_robust(db, im_body)
            results["dingtalk"] = bool(ok_dingtalk)
            record_notification_log(db, event_type=event_type, channel="dingtalk",
                                    recipient=self.config.alerts.dingtalk.webhook_url or "webhook",
                                    title=title, status="sent" if ok_dingtalk else "failed",
                                    fault_id=fault_id, maintenance_id=maintenance_id)

        try:
            db.commit()
        except Exception:
            logger.exception("通知日志提交失败（渠道）")
        return results

    def get_channels_status(self) -> dict:
        """获取各渠道状态"""
        alerts = self.config.alerts
        return {
            "enabled": alerts.enabled,
            "channels": alerts.channels,
            "email": alerts.email.enabled,
            "wechat_work": alerts.wechat_work.enabled,
            "dingtalk": alerts.dingtalk.enabled,
        }


# 全局服务实例
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """获取统一告警通知服务实例"""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service


def reset_notification_service() -> None:
    """配置更新后丢弃缓存实例，使下一次调用读取最新配置。"""
    global _notification_service
    _notification_service = None
