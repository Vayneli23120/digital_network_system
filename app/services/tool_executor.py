"""
统一工具执行器 - 封装 napalm/netmiko/jira 等运维工具的调用

功能：
- 统一接口调用不同运维工具
- 实时日志记录（通过 WebSocket 推送）
- 持久化存储（SQLite log_entries 表）
- 执行耗时统计
"""
import time
import asyncio
import logging
from typing import Dict, List, Optional, Callable, AsyncGenerator
from datetime import datetime
from contextlib import asynccontextmanager

from app.database import get_db
from app.models import LogEntry

logger = logging.getLogger(__name__)


class ToolExecutor:
    """统一工具执行器"""

    def __init__(self):
        self._callbacks: List[Callable] = []

    def register_callback(self, callback: Callable):
        """注册日志回调（用于 WebSocket 实时推送）"""
        self._callbacks.append(callback)

    async def _log(self, log_entry: LogEntry, message: str, db=None):
        """记录日志并推送"""
        log_entry.log_content = (log_entry.log_content or "") + message + "\n"
        if db:
            db.add(log_entry)
            db.commit()

        # 推送给所有 WebSocket 订阅者
        for cb in self._callbacks:
            try:
                await cb({
                    "type": log_entry.tool_type,
                    "operation": log_entry.operation,
                    "target": log_entry.target,
                    "status": log_entry.status,
                    "message": message,
                    "timestamp": log_entry.timestamp.isoformat()
                })
            except Exception:
                pass

    async def execute_netmiko(
        self,
        device: dict,
        commands: List[str],
        operation: str = "execute_commands",
        created_by: str = None
    ) -> Dict:
        """
        通过 Netmiko SSH 执行命令

        Args:
            device: 设备信息 {"ip": "...", "username": "...", "password": "...", "device_type": "..."}
            commands: 要执行的命令列表
            operation: 操作描述
            created_by: 操作用户

        Returns:
            {"success": bool, "output": str, "duration_ms": int}
        """
        from netmiko import ConnectHandler
        from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException

        start_time = time.time()
        log_entry = LogEntry(
            tool_type="netmiko",
            operation=operation,
            target=device.get("ip", "unknown"),
            status="running",
            created_by=created_by
        )

        db = next(get_db())
        db.add(log_entry)
        db.commit()

        try:
            await self._log(log_entry, f"[{datetime.utcnow().isoformat()}] Connecting to {device['ip']}...", db)

            conn = ConnectHandler(**device)
            await self._log(log_entry, f"Connected successfully.", db)

            outputs = []
            for cmd in commands:
                await self._log(log_entry, f"Executing: {cmd}", db)
                output = conn.send_command(cmd)
                outputs.append(output)
                await self._log(log_entry, f"Output ({len(output)} chars): {output[:200]}...", db)

            conn.disconnect()

            duration_ms = int((time.time() - start_time) * 1000)
            log_entry.status = "success"
            log_entry.duration_ms = duration_ms
            db.commit()

            await self._log(log_entry, f"Completed in {duration_ms}ms.", db)

            return {
                "success": True,
                "output": "\n".join(outputs),
                "duration_ms": duration_ms
            }

        except (NetmikoTimeoutException, NetmikoAuthenticationException) as e:
            duration_ms = int((time.time() - start_time) * 1000)
            log_entry.status = "failed"
            log_entry.duration_ms = duration_ms
            log_entry.log_content = (log_entry.log_content or "") + f"Error: {str(e)}\n"
            db.commit()
            return {"success": False, "error": str(e), "duration_ms": duration_ms}

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            log_entry.status = "failed"
            log_entry.duration_ms = duration_ms
            log_entry.log_content = (log_entry.log_content or "") + f"Error: {str(e)}\n"
            db.commit()
            return {"success": False, "error": str(e), "duration_ms": duration_ms}

    async def execute_napalm(
        self,
        device: dict,
        method: str,
        args: dict = None,
        operation: str = "napalm_call",
        created_by: str = None
    ) -> Dict:
        """
        通过 NAPALM 执行网络设备操作

        Args:
            device: 设备信息 {"hostname": "...", "username": "...", "password": "...", "optional_args": {...}}
            method: NAPALM 方法名 (get_facts, get_interfaces, load_merge_candidate 等)
            args: 方法参数
            operation: 操作描述

        Returns:
            {"success": bool, "result": any, "duration_ms": int}
        """
        try:
            from napalm import get_network_driver
        except ImportError:
            return {"success": False, "error": "napalm not installed. pip install napalm"}

        start_time = time.time()
        log_entry = LogEntry(
            tool_type="napalm",
            operation=operation,
            target=device.get("hostname", "unknown"),
            status="running",
            created_by=created_by
        )

        db = next(get_db())
        db.add(log_entry)
        db.commit()

        try:
            await self._log(log_entry, f"Initializing NAPALM driver for {device['hostname']}...", db)

            driver = get_network_driver("ios")  # 默认 IOS，可扩展
            driver_instance = driver(**device)
            driver_instance.open()
            await self._log(log_entry, "NAPALM connection established.", db)

            method_fn = getattr(driver_instance, method, None)
            if method_fn is None:
                raise AttributeError(f"NAPALM method '{method}' not found")

            result = method_fn(**(args or {}))
            await self._log(log_entry, f"Method '{method}' executed successfully.", db)

            driver_instance.close()

            duration_ms = int((time.time() - start_time) * 1000)
            log_entry.status = "success"
            log_entry.duration_ms = duration_ms
            log_entry.log_content = (log_entry.log_content or "") + f"Result: {str(result)[:500]}...\n"
            db.commit()

            return {"success": True, "result": result, "duration_ms": duration_ms}

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            log_entry.status = "failed"
            log_entry.duration_ms = duration_ms
            log_entry.log_content = (log_entry.log_content or "") + f"Error: {str(e)}\n"
            db.commit()
            return {"success": False, "error": str(e), "duration_ms": duration_ms}

    async def execute_jira(
        self,
        action: str,
        issue_data: dict = None,
        operation: str = "jira_action",
        created_by: str = None
    ) -> Dict:
        """
        通过 JIRA API 创建/更新工单

        Args:
            action: create / update / transition / comment
            issue_data: 工单数据
            operation: 操作描述

        Returns:
            {"success": bool, "issue_key": str, "duration_ms": int}
        """
        try:
            from jira import JIRA
        except ImportError:
            return {"success": False, "error": "jira not installed. pip install jira"}

        from app.config import settings

        start_time = time.time()
        log_entry = LogEntry(
            tool_type="jira",
            operation=operation,
            target="JIRA",
            status="running",
            created_by=created_by
        )

        db = next(get_db())
        db.add(log_entry)
        db.commit()

        try:
            await self._log(log_entry, f"Connecting to JIRA ({settings.jira_server})...", db)

            jira = JIRA(
                server=settings.jira_server,
                basic_auth=(settings.jira_username, settings.jira_password)
            )
            await self._log(log_entry, "JIRA connected.", db)

            if action == "create":
                issue = jira.create_issue(**issue_data)
                await self._log(log_entry, f"Issue created: {issue.key}", db)
                result = {"issue_key": issue.key}
            elif action == "update":
                issue = jira.issue(issue_data["key"])
                issue.update(**issue_data.get("fields", {}))
                await self._log(log_entry, f"Issue {issue_data['key']} updated.", db)
                result = {"issue_key": issue_data["key"]}
            else:
                raise ValueError(f"Unknown JIRA action: {action}")

            jira.close()

            duration_ms = int((time.time() - start_time) * 1000)
            log_entry.status = "success"
            log_entry.duration_ms = duration_ms
            db.commit()

            return {"success": True, **result, "duration_ms": duration_ms}

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            log_entry.status = "failed"
            log_entry.duration_ms = duration_ms
            log_entry.log_content = (log_entry.log_content or "") + f"Error: {str(e)}\n"
            db.commit()
            return {"success": False, "error": str(e), "duration_ms": duration_ms}


# 全局实例
tool_executor = ToolExecutor()
