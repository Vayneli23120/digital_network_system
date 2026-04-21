"""
钉钉 Webhook 告警服务

通过钉钉自定义机器人 Webhook 发送告警通知。
文档：https://open.dingtalk.com/document/orgapp/custom-robots-send-group-messages
"""

import json
import hmac
import hashlib
import base64
import urllib.parse
from typing import Optional
from urllib import request as urllib_request
from urllib.error import URLError

from loguru import logger

from ..config import get_config


class DingTalkAlertService:
    """钉钉 Webhook 告警服务"""

    def __init__(self):
        self.config = get_config()
        self.webhook_url = self.config.alerts.dingtalk.webhook_url
        self.secret = self.config.alerts.dingtalk.secret

    def _get_signed_url(self) -> str:
        """获取带签名的 Webhook URL"""
        if not self.secret:
            return self.webhook_url

        timestamp = str(int(__import__("time").time() * 1000))
        string_to_sign = f"{timestamp}\n{self.secret}"
        hmac_code = hmac.new(
            self.secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return f"{self.webhook_url}&timestamp={timestamp}&sign={sign}"

    def send_text(self, content: str, at_mobiles: Optional[list] = None,
                  is_at_all: bool = False) -> bool:
        """发送文本消息"""
        if not self.config.alerts.enabled or not self.webhook_url:
            logger.warning("钉钉 Webhook 告警未启用")
            return False

        data = {
            "msgtype": "text",
            "text": {"content": content},
            "at": {
                "atMobiles": at_mobiles or [],
                "isAtAll": is_at_all,
            }
        }
        return self._send(data)

    def send_markdown(self, title: str, text: str,
                      at_mobiles: Optional[list] = None) -> bool:
        """发送 Markdown 消息"""
        if not self.config.alerts.enabled or not self.webhook_url:
            logger.warning("钉钉 Webhook 告警未启用")
            return False

        data = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": text,
            },
            "at": {
                "atMobiles": at_mobiles or [],
                "isAtAll": False,
            }
        }
        return self._send(data)

    def _send(self, data: dict) -> bool:
        """发送 HTTP POST 请求到 Webhook"""
        try:
            url = self._get_signed_url()
            payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
            req = urllib_request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib_request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                if result.get("errcode") == 0:
                    logger.info("钉钉 Webhook 发送成功")
                    return True
                else:
                    logger.error(f"钉钉 Webhook 发送失败：{result}")
                    return False
        except URLError as e:
            logger.error(f"钉钉 Webhook 网络错误：{e}")
            return False
        except Exception as e:
            logger.error(f"钉钉 Webhook 发送异常：{e}")
            return False

    def send_backup_failure_alert(self, device_name: str, error: str,
                                   operator: Optional[str] = None) -> bool:
        """发送备份失败告警"""
        title = "设备备份失败"
        text = (
            f"## 🔴 {title}\n\n"
            f"- **设备名称**：{device_name}\n"
            f"- **操作人员**：{operator or '系统'}\n"
            f"- **错误信息**：{error}\n\n"
            f"> 请及时检查设备状态和网络连接"
        )
        return self.send_markdown(title, text)

    def send_device_unreachable_alert(self, device_name: str, ip: str,
                                       operator: Optional[str] = None) -> bool:
        """发送设备不可达告警"""
        title = "设备不可达"
        text = (
            f"## 🔴 {title}\n\n"
            f"- **设备名称**：{device_name}\n"
            f"- **设备 IP**：{ip}\n"
            f"- **操作人员**：{operator or '系统'}\n\n"
            f"> 请检查设备网络状态和 SSH 服务"
        )
        return self.send_markdown(title, text)

    def send_fault_alert(self, device_name: str, fault_no: str,
                          severity: str, description: str) -> bool:
        """发送故障告警"""
        severity_map = {"critical": "🚨 严重", "major": "🔶 主要", "minor": "⚠️ 次要", "warning": "📢 警告"}
        title = f"故障告警 - {severity_map.get(severity, '❓ 未知')}"
        text = (
            f"## {title}\n\n"
            f"- **故障单号**：{fault_no}\n"
            f"- **设备名称**：{device_name}\n"
            f"- **故障级别**：{severity_map.get(severity, severity)}\n"
            f"- **故障描述**：{description}\n\n"
            f"> 请及时处理"
        )
        return self.send_markdown(title, text)

    def send_low_stock_alert(self, part_name: str, part_number: str,
                              quantity: int, min_quantity: int) -> bool:
        """发送库存不足预警"""
        title = "备件库存不足"
        text = (
            f"## ⚠️ {title}\n\n"
            f"- **备件名称**：{part_name}\n"
            f"- **备件型号**：{part_number}\n"
            f"- **当前库存**：{quantity}\n"
            f"- **最低库存**：{min_quantity}\n\n"
            f"> 请及时采购"
        )
        return self.send_markdown(title, text)


# 全局服务实例
_dingtalk_service: Optional[DingTalkAlertService] = None


def get_dingtalk_service() -> DingTalkAlertService:
    """获取钉钉告警服务实例"""
    global _dingtalk_service
    if _dingtalk_service is None:
        _dingtalk_service = DingTalkAlertService()
    return _dingtalk_service
