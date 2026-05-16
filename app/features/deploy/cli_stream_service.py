"""
实时 CLI 流式传输服务 - 用于 Netmiko 模式

通过 WebSocket 实时推送 SSH 会话输出：
- 逐条发送命令
- 每条命令执行后立即推送输出
- 支持错误检测和停止后续命令
"""

import asyncio
import json
from datetime import datetime
from typing import List, Dict, Optional
from loguru import logger
from fastapi import WebSocket

try:
    from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException
    NETMIKO_AVAILABLE = True
except ImportError:
    NETMIKO_AVAILABLE = False
    logger.warning("netmiko 未安装，CLI 流式功能不可用")


class CliStreamService:
    """实时 CLI 流式传输服务 - 用于 Netmiko 模式"""

    def __init__(self):
        self.device_type_map = {
            'cisco': 'cisco_ios',
            'huawei': 'huawei',
            'h3c': 'h3c_comware',
            'juniper': 'juniper_junos',
        }
        # 存储活跃的 SSH 连接
        self._connections: Dict[int, object] = {}

    def get_device_credentials(self, device: dict, credential_groups: List[dict]) -> dict:
        """根据设备的 credential_group 获取对应的凭证"""
        group_name = device.get('credential_group', 'default')

        for group in credential_groups:
            if group.get('name') == group_name:
                return {
                    'username': group.get('username'),
                    'password': group.get('password'),
                    'enable_password': group.get('enable_password')
                }

        # 如果未找到匹配的组，使用 default 组
        for group in credential_groups:
            if group.get('name') == 'default':
                return {
                    'username': group.get('username'),
                    'password': group.get('password'),
                    'enable_password': group.get('enable_password')
                }

        return {'username': '', 'password': '', 'enable_password': ''}

    def connect_device(self, device: dict, credentials: dict) -> Optional[object]:
        """连接到网络设备"""
        if not NETMIKO_AVAILABLE:
            raise RuntimeError("netmiko 未安装，无法连接设备")

        device_type = device.get('device_type', 'cisco_ios')

        netmiko_device = {
            'device_type': device_type,
            'host': device.get('ip'),
            'port': device.get('ssh_port', 22),
            'username': credentials.get('username', ''),
            'password': credentials.get('password', ''),
            'secret': credentials.get('enable_password', ''),
            'timeout': 15,  # 减少连接超时到 15 秒
            'session_timeout': 30,  # 减少会话超时到 30 秒
        }

        try:
            logger.info(f"正在连接设备 {device.get('name')} ({device.get('ip')})...")
            connection = ConnectHandler(**netmiko_device)

            # 尝试进入特权模式
            if credentials.get('enable_password'):
                connection.enable()

            logger.info(f"设备 {device.get('name')} 连接成功")
            return connection

        except NetmikoTimeoutException as e:
            logger.error(f"连接设备 {device.get('name')} 超时：{e}")
            raise RuntimeError(f"连接超时：{device.get('ip')}")
        except NetmikoAuthenticationException as e:
            logger.error(f"设备 {device.get('name')} 认证失败：{e}")
            raise RuntimeError("认证失败，请检查凭证")
        except Exception as e:
            logger.error(f"连接设备 {device.get('name')} 失败：{e}")
            raise RuntimeError(f"连接失败：{str(e)}")

    async def push_message(self, websocket: WebSocket, message: dict):
        """推送消息到 WebSocket"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"WebSocket 推送失败: {e}")

    async def stream_netmiko_deploy(
        self,
        websocket: WebSocket,
        device: dict,
        commands: List[str],
        credential_groups: List[dict],
        dry_run: bool = False
    ):
        """
        通过 WebSocket 实时推送 SSH 会话输出（Netmiko 模式）

        流程：
        1. 推送 "正在连接设备..."
        2. 建立 SSH 连接
        3. 逐条发送命令
        4. 每条命令执行后立即推送输出
        5. 推送完成或错误消息

        推送格式：
           {
               'type': 'cli_output',
               'command': 'hostname test-switch',
               'output': '设备返回内容',
               'timestamp': '2024-05-16T10:30:00Z',
               'status': 'success' | 'error'
           }
        """
        # 获取凭证
        credentials = self.get_device_credentials(device, credential_groups)

        if not credentials.get('username'):
            await self.push_message(websocket, {
                'type': 'deploy_error',
                'message': '未找到设备凭证',
                'timestamp': datetime.utcnow().isoformat()
            })
            await self.push_message(websocket, {
                'type': 'deploy_complete',
                'success': False,
                'message': '未找到设备凭证',
                'timestamp': datetime.utcnow().isoformat()
            })
            return

        connection = None
        success = True
        executed_commands = []
        failed_command = None

        try:
            # 1. 推送连接状态
            await self.push_message(websocket, {
                'type': 'step_status',
                'step': 'connecting',
                'message': f"正在连接设备 {device.get('name')} ({device.get('ip')})...",
                'timestamp': datetime.utcnow().isoformat()
            })

            # 2. 建立 SSH 连接（在线程池中执行，带超时保护）
            try:
                connection = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, self.connect_device, device, credentials
                    ),
                    timeout=20  # 最多等待 20 秒
                )
            except asyncio.TimeoutError:
                await self.push_message(websocket, {
                    'type': 'deploy_error',
                    'message': '连接超时（20秒）',
                    'timestamp': datetime.utcnow().isoformat()
                })
                await self.push_message(websocket, {
                    'type': 'deploy_complete',
                    'success': False,
                    'message': '连接超时',
                    'timestamp': datetime.utcnow().isoformat()
                })
                return

            # 3. 推送连接成功
            await self.push_message(websocket, {
                'type': 'step_status',
                'step': 'connected',
                'message': 'SSH 连接成功，开始执行配置命令...',
                'timestamp': datetime.utcnow().isoformat()
            })

            # 4. 逐条执行命令
            for cmd in commands:
                # 推送发送命令
                await self.push_message(websocket, {
                    'type': 'cli_input',
                    'command': cmd,
                    'timestamp': datetime.utcnow().isoformat()
                })

                try:
                    # 在线程池中执行命令（Netmiko 是同步的，带超时保护）
                    if cmd.startswith('show') or cmd.startswith('display'):
                        # show 命令使用 send_command
                        output = await asyncio.wait_for(
                            asyncio.get_event_loop().run_in_executor(
                                None, connection.send_command, cmd, 15
                            ),
                            timeout=20
                        )
                    else:
                        # 配置命令使用 send_config_set（单条）
                        output = await asyncio.wait_for(
                            asyncio.get_event_loop().run_in_executor(
                                None, connection.send_config_set, [cmd]
                            ),
                            timeout=20
                        )

                    # 推送成功输出
                    await self.push_message(websocket, {
                        'type': 'cli_output',
                        'command': cmd,
                        'output': output or '(无输出)',
                        'status': 'success',
                        'timestamp': datetime.utcnow().isoformat()
                    })

                    executed_commands.append(cmd)
                    logger.info(f"命令执行成功: {cmd}")

                except asyncio.TimeoutError:
                    await self.push_message(websocket, {
                        'type': 'cli_error',
                        'command': cmd,
                        'error': '命令执行超时（20秒）',
                        'status': 'error',
                        'timestamp': datetime.utcnow().isoformat()
                    })
                    success = False
                    failed_command = cmd
                    break

                except Exception as e:
                    # 推送错误
                    await self.push_message(websocket, {
                        'type': 'cli_error',
                        'command': cmd,
                        'error': str(e),
                        'status': 'error',
                        'timestamp': datetime.utcnow().isoformat()
                    })

                    success = False
                    failed_command = cmd
                    logger.error(f"命令执行失败: {cmd} - {e}")
                    break  # 停止后续命令

            # 5. 如果是预览模式，不保存配置
            if dry_run:
                await self.push_message(websocket, {
                    'type': 'step_status',
                    'step': 'dry_run',
                    'message': '预览模式，配置未实际保存',
                    'timestamp': datetime.utcnow().isoformat()
                })
            elif success:
                # 6. 保存配置
                await self.push_message(websocket, {
                    'type': 'step_status',
                    'step': 'saving',
                    'message': '正在保存配置...',
                    'timestamp': datetime.utcnow().isoformat()
                })

                try:
                    save_output = await asyncio.get_event_loop().run_in_executor(
                        None, connection.save_config
                    )
                    await self.push_message(websocket, {
                        'type': 'cli_output',
                        'command': 'write memory / save',
                        'output': save_output or '配置已保存',
                        'status': 'success',
                        'timestamp': datetime.utcnow().isoformat()
                    })
                except Exception as e:
                    await self.push_message(websocket, {
                        'type': 'cli_error',
                        'command': 'save_config',
                        'error': str(e),
                        'status': 'error',
                        'timestamp': datetime.utcnow().isoformat()
                    })

        except Exception as e:
            success = False
            await self.push_message(websocket, {
                'type': 'deploy_error',
                'message': str(e),
                'timestamp': datetime.utcnow().isoformat()
            })

        finally:
            # 关闭连接
            if connection:
                try:
                    await asyncio.get_event_loop().run_in_executor(
                        None, connection.disconnect
                    )
                except:
                    pass

            # 推送完成消息
            await self.push_message(websocket, {
                'type': 'deploy_complete',
                'success': success,
                'device_id': device.get('id'),
                'device_name': device.get('name'),
                'executed_commands': executed_commands,
                'failed_command': failed_command,
                'message': '配置部署成功' if success else '配置部署失败',
                'timestamp': datetime.utcnow().isoformat()
            })


def get_cli_stream_service():
    """获取 CLI 流式服务实例"""
    return CliStreamService()