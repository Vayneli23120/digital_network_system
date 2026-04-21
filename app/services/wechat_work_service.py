"""
企业微信 Webhook 告警服务

通过企业微信群机器人 Webhook 发送告警通知。
文档：https://developer.work.weixin.qq.com/document/path/91770
"""

import json
from typing import Optional, List
from urllib import request as urllib_request
from urllib.error import URLError

from loguru import logger

from ..config import get_config


class WeChatWorkAlertService:
    """企业微信 Webhook 告警服务"""

    def __init__(self):
        self.config = get_config()
        self.webhook_url = self.config.alerts.wechat_work.webhook_url

    def send_text(self, content: str, mentioned_list: Optional[List[str]] = None,
                  mentioned_mobile_list: Optional[List[str]] = None) -> bool:
        """发送文本消息

        Args:
            content: 文本内容（最长 4096 字节）
            mentioned_list: 需要 @ 的用户 ID 列表
            mentioned_mobile_list: 需要 @ 的手机号列表
        """
        if not self.config.alerts.enabled or not self.webhook_url:
            logger.warning("企业微信 Webhook 告警未启用")
            return False

        data = {
            "msgtype": "text",
            "text": {
                "content": content,
            }
        }
        if mentioned_list:
            data["text"]["mentioned_list"] = mentioned_list
        if mentioned_mobile_list:
            data["text"]["mentioned_mobile_list"] = mentioned_mobile_list

        return self._send(data)

    def send_markdown(self, content: str) -> bool:
        """发送 Markdown 消息"""
        if not self.config.alerts.enabled or not self.webhook_url:
            logger.warning("企业微信 Webhook 告警未启用")
            return False

        data = {
            "msgtype": "markdown",
            "markdown": {
                "content": content,
            }
        }
        return self._send(data)

    def _send(self, data: dict) -> bool:
        """发送 HTTP POST 请求到 Webhook"""
        try:
            payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
            req = urllib_request.Request(
                self.webhook_url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib_request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                if result.get("errcode") == 0:
                    logger.info("企业微信 Webhook 发送成功")
                    return True
                else:
                    logger.error(f"企业微信 Webhook 发送失败：{result}")
                    return False
        except URLError as e:
            logger.error(f"企业微信 Webhook 网络错误：{e}")
            return False
        except Exception as e:
            logger.error(f"企业微信 Webhook 发送异常：{e}")
            return False

    def send_backup_failure_alert(self, device_name: str, error: str,
                                   operator: Optional[str] = None) -> bool:
        """发送备份失败告警"""
        content = (
            f"## 🔴 设备备份失败\n"
            f"> 设备名称：{device_name}\n"
            f"> 操作人员：{operator or '系统'}\n"
            f"> 错误信息：{error}\n"
            f"> 请及时检查设备状态和网络连接"
        )
        return self.send_markdown(content)

    def send_device_unreachable_alert(self, device_name: str, ip: str,
                                       operator: Optional[str] = None) -> bool:
        """发送设备不可达告警"""
        content = (
            f"## 🔴 设备不可达\n"
            f"> 设备名称：{device_name}\n"
            f"> 设备 IP：{ip}\n"
            f"> 操作人员：{operator or '系统'}\n"
            f"> 请检查设备网络状态和 SSH 服务"
        )
        return self.send_markdown(content)

    def send_fault_alert(self, device_name: str, fault_no: str,
                          severity: str, description: str) -> bool:
        """发送故障告警"""
        severity_emoji = {"critical": "🚨", "major": "🔶", "minor": "⚠️", "warning": "📢"}
        emoji = severity_emoji.get(severity, "❓")
        severity_map = {"critical": "严重", "major": "主要", "minor": "次要", "warning": "警告"}

        content = (
            f"## {emoji} 故障告警 - {severity_map.get(severity, severity)}\n"
            f"> 故障单号：{fault_no}\n"
            f"> 设备名称：{device_name}\n"
            f"> 故障级别：{severity_map.get(severity, severity)}\n"
            f"> 故障描述：{description}\n"
            f"> 请及时处理"
        )
        return self.send_markdown(content)

    def send_low_stock_alert(self, part_name: str, part_number: str,
                              quantity: int, min_quantity: int) -> bool:
        """发送库存不足预警"""
        content = (
            f"## ⚠️ 备件库存不足\n"
            f"> 备件名称：{part_name}\n"
            f"> 备件型号：{part_number}\n"
            f"> 当前库存：{quantity}\n"
            f"> 最低库存：{min_quantity}\n"
            f"> 请及时采购"
        )
        return self.send_markdown(content)


# 全局服务实例
_wechat_service: Optional[WeChatWorkAlertService] = None


def get_wechat_work_service() -> WeChatWorkAlertService:
    """获取企业微信告警服务实例"""
    global _wechat_service
    if _wechat_service is None:
        _wechat_service = WeChatWorkAlertService()
    return _wechat_service
