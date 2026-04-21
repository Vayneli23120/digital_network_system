"""
统一告警通知服务

统一管理多种告警渠道（邮件、企业微信、钉钉），提供统一的告警发送接口。
"""

from typing import Optional, List
from loguru import logger

from ..config import get_config


class NotificationService:
    """统一告警通知服务"""

    def __init__(self):
        self.config = get_config()

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
        channels = self.config.alerts.channels

        if "email" in channels:
            self._send_email(
                subject=f"[NAS 告警] 设备备份失败：{device_name}",
                body=f"设备：{device_name}\n操作人：{operator or '系统'}\n错误：{error}",
            )

        if "wechat_work" in channels:
            self._send_wechat("send_backup_failure_alert", device_name=device_name, error=error, operator=operator)

        if "dingtalk" in channels:
            self._send_dingtalk("send_backup_failure_alert", device_name=device_name, error=error, operator=operator)

    def notify_device_unreachable(self, device_name: str, ip: str,
                                   operator: Optional[str] = None):
        """设备不可达告警 — 多渠道发送"""
        channels = self.config.alerts.channels

        if "email" in channels:
            self._send_email(
                subject=f"[NAS 告警] 设备不可达：{device_name}",
                body=f"设备：{device_name}\nIP：{ip}\n操作人：{operator or '系统'}",
            )

        if "wechat_work" in channels:
            self._send_wechat("send_device_unreachable_alert", device_name=device_name, ip=ip, operator=operator)

        if "dingtalk" in channels:
            self._send_dingtalk("send_device_unreachable_alert", device_name=device_name, ip=ip, operator=operator)

    def notify_fault(self, device_name: str, fault_no: str,
                      severity: str, description: str):
        """故障告警 — 多渠道发送（仅 critical/major）"""
        if severity not in ("critical", "major"):
            return

        channels = self.config.alerts.channels

        if "email" in channels:
            from .email_service import get_email_service
            get_email_service().send_fault_alert(
                device_name=device_name, fault_no=fault_no,
                severity=severity, description=description,
            )

        if "wechat_work" in channels:
            self._send_wechat("send_fault_alert", device_name=device_name, fault_no=fault_no,
                              severity=severity, description=description)

        if "dingtalk" in channels:
            self._send_dingtalk("send_fault_alert", device_name=device_name, fault_no=fault_no,
                                severity=severity, description=description)

    def notify_low_stock(self, part_name: str, part_number: str,
                          quantity: int, min_quantity: int):
        """库存不足预警 — 多渠道发送"""
        channels = self.config.alerts.channels

        if "wechat_work" in channels:
            self._send_wechat("send_low_stock_alert", part_name=part_name, part_number=part_number,
                              quantity=quantity, min_quantity=min_quantity)

        if "dingtalk" in channels:
            self._send_dingtalk("send_low_stock_alert", part_name=part_name, part_number=part_number,
                                quantity=quantity, min_quantity=min_quantity)

    def get_channels_status(self) -> dict:
        """获取各渠道状态"""
        channels = self.config.alerts.channels
        return {
            "enabled": self.config.alerts.enabled,
            "channels": channels,
            "email": "email" in channels,
            "wechat_work": "wechat_work" in channels,
            "dingtalk": "dingtalk" in channels,
        }


# 全局服务实例
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """获取统一告警通知服务实例"""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service
