"""
WebSocket 端点 - 实时日志推送

前端通过 WebSocket 连接订阅工具执行日志。
支持按 tool_type / operation 过滤。
"""
import json
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.features.tool_logs.tool_executor import tool_executor

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str = "all"):
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = set()
        self.active_connections[channel].add(websocket)

    def disconnect(self, websocket: WebSocket, channel: str = "all"):
        if channel in self.active_connections:
            self.active_connections[channel].discard(websocket)
            if not self.active_connections[channel]:
                del self.active_connections[channel]

    async def broadcast(self, message: dict, channel: str = "all"):
        data = json.dumps(message, ensure_ascii=False)
        connections = set()
        if channel in self.active_connections:
            connections.update(self.active_connections[channel])
        if "all" in self.active_connections:
            connections.update(self.active_connections["all"])

        for conn in connections:
            try:
                await conn.send_text(data)
            except Exception:
                pass


manager = ConnectionManager()


@router.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket, tool_type: str = None):
    """
    WebSocket 端点 - 订阅工具执行日志

    查询参数:
        tool_type: 过滤工具类型 (napalm/netmiko/jira)，不传则接收全部
    """
    channel = tool_type or "all"
    await manager.connect(websocket, channel)

    # 注册回调
    async def push_log(data: dict):
        if tool_type is None or data.get("type") == tool_type:
            await manager.broadcast(data, channel)

    tool_executor.register_callback(push_log)

    try:
        while True:
            # 保持连接，接收前端消息（可选：用于控制）
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)
    finally:
        tool_executor.unregister_callback(push_log)


@router.websocket("/ws/logs/{operation}")
async def websocket_logs_by_op(websocket: WebSocket, operation: str):
    """
    WebSocket 端点 - 按操作订阅日志

    路径参数:
        operation: 操作标识符（如 backup_run_123）
    """
    await manager.connect(websocket, f"op:{operation}")

    async def push_log(data: dict):
        if data.get("operation", "").startswith(operation):
            await manager.broadcast(data, f"op:{operation}")

    tool_executor.register_callback(push_log)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, f"op:{operation}")
    finally:
        tool_executor.unregister_callback(push_log)
