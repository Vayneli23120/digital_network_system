"""
WebSocket 端点 - 实时日志推送

前端通过 WebSocket 连接订阅工具执行日志。
支持按 tool_type / operation 过滤。
"""
import asyncio
import json
import uuid
from typing import Dict, Set
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from loguru import logger

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


@router.websocket("/ws/cli/{session_id}")
async def websocket_cli_stream(websocket: WebSocket, session_id: str):
    """
    WebSocket 端点 - 实时 CLI 会话（支持 Netmiko 和 NAPALM）

    前端发送：
        {
            'action': 'deploy',
            'engine': 'netmiko' | 'napalm',
            'device_id': 123,
            'commands': [...],       # Netmiko 模式
            'config': '...',         # NAPALM 模式
            'napalm_mode': 'merge',  # NAPALM 模式
            'dry_run': false
        }

    后端推送（Netmiko）：
        {
            'type': 'cli_output',
            'command': 'hostname test',
            'output': 'test\n',
            'status': 'success'
        }

    后端推送（NAPALM）：
        {
            'type': 'step_status',
            'step': 'compare_config',
            'message': '正在对比配置差异...'
        }
        {
            'type': 'config_diff',
            'diff': '+ hostname new-name\n- hostname old-name'
        }
    """
    await websocket.accept()

    try:
        # 等待前端发送部署请求
        data = await websocket.receive_text()
        request = json.loads(data)

        action = request.get('action')

        if action == 'deploy':
            engine = request.get('engine', 'netmiko')
            device_id = request.get('device_id')

            # 获取设备和凭证信息
            from app.shared.database import get_db
            from app.shared.models import Device, CredentialGroup
            from app.features.credentials.credential_service import decrypt_password

            db = next(get_db())

            try:
                # 获取设备信息
                device_record = db.query(Device).filter(Device.id == device_id).first()
                if not device_record:
                    await websocket.send_json({
                        'type': 'deploy_error',
                        'message': '设备不存在',
                        'timestamp': datetime.utcnow().isoformat()
                    })
                    await websocket.send_json({
                        'type': 'deploy_complete',
                        'success': False,
                        'timestamp': datetime.utcnow().isoformat()
                    })
                    return

                # 转换设备记录为字典格式
                device = {
                    'id': device_record.id,
                    'name': device_record.name,
                    'ip': device_record.ip,
                    'device_type': device_record.device_type,
                    'ssh_port': 22,
                    'credential_group': device_record.credential_group or 'default'
                }

                # 获取凭证组
                credential_records = db.query(CredentialGroup).all()
                credential_groups = []

                for cred in credential_records:
                    try:
                        password = decrypt_password(cred.password_encrypted) if cred.password_encrypted else ''
                        enable_password = decrypt_password(cred.enable_password_encrypted) if cred.enable_password_encrypted else None
                    except Exception:
                        password = ''
                        enable_password = None

                    credential_groups.append({
                        'name': cred.name,
                        'username': cred.username or '',
                        'password': password,
                        'enable_password': enable_password
                    })

            finally:
                db.close()

            if engine == 'napalm':
                # NAPALM 模式
                from app.features.deploy.napalm_service import get_napalm_stream_service

                config = request.get('config', '')
                napalm_mode = request.get('napalm_mode', 'merge')
                dry_run = request.get('dry_run', False)

                service = get_napalm_stream_service()
                await service.stream_napalm_deploy(
                    websocket=websocket,
                    device=device,
                    config=config,
                    credential_groups=credential_groups,
                    dry_run=dry_run,
                    mode=napalm_mode
                )

            else:
                # Netmiko 模式
                from app.features.deploy.cli_stream_service import get_cli_stream_service

                commands = request.get('commands', [])
                dry_run = request.get('dry_run', False)

                # 解析配置命令
                if not commands and request.get('config'):
                    # 如果没有 commands 但有 config，解析为命令列表
                    config_text = request.get('config', '')
                    commands = parse_config_to_commands(config_text)

                service = get_cli_stream_service()
                await service.stream_netmiko_deploy(
                    websocket=websocket,
                    device=device,
                    commands=commands,
                    credential_groups=credential_groups,
                    dry_run=dry_run
                )

        elif action == 'ping':
            await websocket.send_json({'type': 'pong'})

    except WebSocketDisconnect:
        logger.info(f"WebSocket CLI 会话断开: {session_id}")

    except Exception as e:
        logger.error(f"WebSocket CLI 错误: {e}", exc_info=True)
        try:
            await websocket.send_json({
                'type': 'deploy_error',
                'message': str(e),
                'timestamp': datetime.utcnow().isoformat()
            })
            await websocket.send_json({
                'type': 'deploy_complete',
                'success': False,
                'timestamp': datetime.utcnow().isoformat()
            })
        except:
            pass


def parse_config_to_commands(config: str) -> list:
    """解析配置文本为命令列表"""
    commands = []
    for line in config.strip().splitlines():
        line = line.strip()
        # 跳过空行和注释
        if not line or line.startswith('!') or line.startswith('#'):
            continue
        # 跳过已经包含的命令头
        if line in ['configure terminal', 'end', 'exit']:
            continue
        commands.append(line)
    return commands
