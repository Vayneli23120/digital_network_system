"""
WebSocket 端点 - 实时日志推送 & 设备状态推送

前端通过 WebSocket 连接订阅工具执行日志或设备实时状态变化。
支持按 tool_type / operation 过滤日志；设备状态通道独立分离。
"""
import asyncio
import json
import uuid
from typing import Dict, Optional, Set
from datetime import datetime
from pathlib import Path
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

# ============ 跨线程 WebSocket 推送桥接 ============
# APScheduler 在后台线程运行，需要通过主事件循环来调用 async broadcast

_main_event_loop: Optional[asyncio.AbstractEventLoop] = None


def set_main_loop(loop: asyncio.AbstractEventLoop) -> None:
    """在 FastAPI startup 时注册主事件循环，供后台线程调用 WebSocket 推送。"""
    global _main_event_loop
    _main_event_loop = loop


def broadcast_device_status_sync(message: dict) -> None:
    """从后台线程（APScheduler）线程安全地推送设备状态变化到 WebSocket 客户端。"""
    global _main_event_loop
    if _main_event_loop and not _main_event_loop.is_closed():
        asyncio.run_coroutine_threadsafe(
            manager.broadcast(message, "device-status"),
            _main_event_loop,
        )


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


@router.websocket("/ws/device-status")
async def websocket_device_status(websocket: WebSocket):
    """
    WebSocket 端点 - 订阅设备实时可达性状态变化

    消息格式（服务端推送）：
    {
        "event": "device_status_change",
        "device_id": 123,
        "device_name": "SW-Core-01",
        "ip": "192.168.1.1",
        "location": "车间A",
        "device_type": "switch",
        "old_state": "reachable",
        "new_state": "unreachable",
        "latency_ms": null,
        "timestamp": "2026-06-05T10:30:00"
    }
    """
    await manager.connect(websocket, "device-status")
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket, "device-status")


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
                    'vendor': device_record.vendor,  # 厂商（用于确定 driver）
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


@router.websocket("/ws/deploy/{session_id}")
async def websocket_batch_deploy(websocket: WebSocket, session_id: str):
    """
    WebSocket 端点 - 批量部署实时进度推送

    前端发送：
        {
            'action': 'start_deploy',
            'mode': 'backup' | 'template' | 'snippet',
            'engine': 'netmiko' | 'napalm',
            'napalm_mode': 'merge' | 'replace',
            'target_devices': [1, 2, 3],
            'backup_file': '/path/to/config.cfg',  # backup 模式
            'template_id': 1,                       # template 模式
            'snippet': 'ntp server 10.1.1.1',       # snippet 模式
            'variables': {'hostname': 'SW-01'},
            'dry_run': false
        }

    后端推送：
        {
            'type': 'deploy_started',
            'session_id': 'xxx',
            'total_count': 3
        }
        {
            'type': 'device_progress',
            'device_id': 1,
            'device_name': 'Switch-01',
            'status': 'completed' | 'failed',
            'success': true,
            'message': '配置部署成功',
            'progress': 33,
            'completed_count': 1,
            'total_count': 3
        }
        {
            'type': 'deploy_complete',
            'success_count': 2,
            'failed_count': 1,
            'history_id': 123
        }
    """
    await websocket.accept()

    try:
        # 等待前端发送部署请求
        data = await websocket.receive_text()
        request = json.loads(data)

        action = request.get('action')

        if action == 'start_deploy':
            from app.shared.database import get_db
            from app.shared.models import Device, CredentialGroup, ConfigTemplate
            from app.features.credentials.credential_service import decrypt_password
            from app.features.deploy.deploy_stream_service import get_deploy_stream_service
            from jinja2 import Template

            engine = request.get('engine', 'netmiko')
            napalm_mode = request.get('napalm_mode', 'merge')
            target_device_ids = request.get('target_devices', [])
            dry_run = request.get('dry_run', False)
            mode = request.get('mode', 'backup')
            variables = request.get('variables', {})
            parallel_limit = request.get('parallel_limit', 1)  # 并行数量
            transfer_mode = request.get('transfer_mode', 'inline')  # scp | inline，默认 inline

            if not target_device_ids:
                await websocket.send_json({
                    'type': 'deploy_error',
                    'message': '请选择至少一台设备',
                    'timestamp': datetime.utcnow().isoformat()
                })
                await websocket.send_json({
                    'type': 'deploy_complete',
                    'success': False,
                    'timestamp': datetime.utcnow().isoformat()
                })
                return

            db = next(get_db())

            try:
                # 获取设备列表
                devices = db.query(Device).filter(Device.id.in_(target_device_ids)).all()
                if not devices:
                    await websocket.send_json({
                        'type': 'deploy_error',
                        'message': '未找到指定的设备',
                        'timestamp': datetime.utcnow().isoformat()
                    })
                    return

                # 转换设备记录为字典格式
                device_list = [
                    {
                        'id': d.id,
                        'name': d.name,
                        'ip': d.ip,
                        'vendor': d.vendor,  # 厂商（用于确定 driver）
                        'ssh_port': 22,
                        'credential_group': d.credential_group or 'default'
                    }
                    for d in devices
                ]

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

                # 获取配置内容
                config_content = None

                if mode == 'backup':
                    backup_file = request.get('backup_file')
                    if not backup_file:
                        await websocket.send_json({
                            'type': 'deploy_error',
                            'message': '请选择备份文件',
                            'timestamp': datetime.utcnow().isoformat()
                        })
                        return

                    backup_path = Path(backup_file)
                    if not backup_path.exists():
                        backup_path = Path(f"./backups/{backup_file}")

                    if not backup_path.exists():
                        await websocket.send_json({
                            'type': 'deploy_error',
                            'message': f'备份文件不存在：{backup_file}',
                            'timestamp': datetime.utcnow().isoformat()
                        })
                        return

                    with open(backup_path, 'r', encoding='utf-8') as f:
                        config_content = f.read()

                elif mode == 'template':
                    template_id = request.get('template_id')
                    if not template_id:
                        await websocket.send_json({
                            'type': 'deploy_error',
                            'message': '请选择配置模板',
                            'timestamp': datetime.utcnow().isoformat()
                        })
                        return

                    template = db.query(ConfigTemplate).filter(ConfigTemplate.id == template_id).first()
                    if not template:
                        await websocket.send_json({
                            'type': 'deploy_error',
                            'message': f'模板不存在：{template_id}',
                            'timestamp': datetime.utcnow().isoformat()
                        })
                        return

                    tmpl = Template(template.template_content)
                    context = {
                        'now': datetime.utcnow,
                        'now_str': datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    context.update(variables)
                    config_content = tmpl.render(**context)

                elif mode == 'snippet':
                    config_content = request.get('snippet', '')

                if not config_content:
                    await websocket.send_json({
                        'type': 'deploy_error',
                        'message': '配置内容为空',
                        'timestamp': datetime.utcnow().isoformat()
                    })
                    return

            finally:
                db.close()

            # 执行批量部署
            service = get_deploy_stream_service()
            await service.stream_batch_deploy(
                websocket=websocket,
                devices=device_list,
                config=config_content,
                credential_groups=credential_groups,
                engine=engine,
                napalm_mode=napalm_mode,
                transfer_mode=transfer_mode,
                dry_run=dry_run,
                session_id=session_id,
                parallel_limit=parallel_limit
            )

        elif action == 'ping':
            await websocket.send_json({'type': 'pong'})

    except WebSocketDisconnect:
        logger.info(f"WebSocket 批量部署会话断开: {session_id}")

    except Exception as e:
        logger.error(f"WebSocket 批量部署错误: {e}", exc_info=True)
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
