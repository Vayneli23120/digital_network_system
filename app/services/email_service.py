"""
Email 告警服务
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from pathlib import Path

from loguru import logger

from ..config import get_config


class EmailAlertService:
    """Email 告警服务"""

    def __init__(self):
        self.config = get_config()
        self.email_config = self.config.alerts.email

    def send_email(self, subject: str, body: str,
                   to_addresses: Optional[List[str]] = None,
                   html: bool = False) -> bool:
        """
        发送邮件

        Args:
            subject: 邮件主题
            body: 邮件内容
            to_addresses: 收件人列表，默认使用配置中的收件人
            html: 是否使用 HTML 格式

        Returns:
            bool: 发送是否成功
        """
        if not self.config.alerts.enabled or not self.email_config.enabled:
            logger.warning("Email 告警未启用")
            return False

        recipients = to_addresses or self.email_config.recipients

        if not recipients:
            logger.error("没有指定收件人")
            return False

        try:
            # 创建邮件
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.email_config.from_addr
            msg["To"] = ", ".join(recipients)

            # 添加内容
            content_type = "html" if html else "plain"
            msg.attach(MIMEText(body, content_type, "utf-8"))

            # 连接 SMTP 服务器并发送
            logger.info(f"发送邮件到 {recipients}: {subject}")

            if self.email_config.use_tls:
                server = smtplib.SMTP(self.email_config.smtp_host, self.email_config.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP(self.email_config.smtp_host, self.email_config.smtp_port)

            server.login(self.email_config.username, self.email_config.password)
            server.sendmail(self.email_config.from_addr, recipients, msg.as_string())
            server.quit()

            logger.info(f"邮件发送成功：{subject}")
            return True

        except Exception as e:
            logger.error(f"邮件发送失败：{e}")
            return False

    def send_backup_failure_alert(self, device_name: str, error: str,
                                   operator: Optional[str] = None) -> bool:
        """发送备份失败告警"""
        subject = f"[NAS 告警] 设备备份失败：{device_name}"
        body = f"""
网络自动化系统告警

设备名称：{device_name}
操作类型：配置备份
操作人员：{operator or "系统"}
错误信息：{error}

请及时检查设备状态和网络连接。

---
Network Automation System
"""
        return self.send_email(subject, body)

    def send_device_unreachable_alert(self, device_name: str, ip: str,
                                       operator: Optional[str] = None) -> bool:
        """发送设备不可达告警"""
        subject = f"[NAS 告警] 设备不可达：{device_name} ({ip})"
        body = f"""
网络自动化系统告警

设备名称：{device_name}
设备 IP: {ip}
操作人员：{operator or "系统"}
错误信息：设备无法连接

请检查设备网络状态和 SSH 服务。

---
Network Automation System
"""
        return self.send_email(subject, body)

    def send_config_change_alert(self, device_name: str,
                                  change_summary: str,
                                  operator: Optional[str] = None) -> bool:
        """发送配置变更告警"""
        subject = f"[NAS 通知] 配置变更：{device_name}"
        body = f"""
网络自动化系统通知

设备名称：{device_name}
操作人员：{operator or "系统"}

变更摘要:
{change_summary}

---
Network Automation System
"""
        return self.send_email(subject, body)

    def send_fault_alert(self, device_name: str, fault_no: str,
                          severity: str, description: str) -> bool:
        """发送故障告警"""
        severity_map = {
            "critical": "严重",
            "major": "主要",
            "minor": "次要",
            "warning": "警告"
        }
        subject = f"[NAS 故障] {severity_map.get(severity, '未知')} - {device_name}"
        body = f"""
网络自动化系统故障通知

故障单号：{fault_no}
设备名称：{device_name}
故障级别：{severity_map.get(severity, severity)}

故障描述:
{description}

请及时处理。

---
Network Automation System
"""
        return self.send_email(subject, body)


# 全局服务实例
_email_service: Optional[EmailAlertService] = None


def get_email_service() -> EmailAlertService:
    """获取 Email 告警服务实例"""
    global _email_service
    if _email_service is None:
        _email_service = EmailAlertService()
    return _email_service


def send_alert(subject: str, body: str,
               to_addresses: Optional[List[str]] = None) -> bool:
    """快捷发送告警邮件"""
    service = get_email_service()
    return service.send_email(subject, body, to_addresses)
