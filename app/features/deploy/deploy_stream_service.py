"""
批量部署流式服务
通过 WebSocket 实时推送部署进度
"""
import asyncio
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
from loguru import logger
from fastapi import WebSocket
from jinja2 import Template

try:
    from netmiko import NetmikoTimeoutException, NetmikoAuthenticationException
    NETMIKO_AVAILABLE = True
except ImportError:
    NETMIKO_AVAILABLE = False

try:
    from napalm import get_network_driver
    NAPALM_AVAILABLE = True
except ImportError:
    NAPALM_AVAILABLE = False


class DeployStreamService:
    """批量部署流式服务 - WebSocket 实时进度推送"""

    def __init__(self):
        self.active_sessions: Dict[str, dict] = {}  # session_id -> session_info

    async def push_message(self, websocket: WebSocket, message: dict):
        """推送消息到 WebSocket"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"WebSocket 推送失败: {e}")

    def _get_device_credentials(self, device: dict, credential_groups: List[dict]) -> dict:
        """根据设备的 credential_group 获取对应的凭证"""
        group_name = device.get('credential_group', 'default')
        for group in credential_groups:
            if group.get('name') == group_name:
                return {
                    'username': group.get('username'),
                    'password': group.get('password'),
                    'enable_password': group.get('enable_password')
                }
        # 默认组
        for group in credential_groups:
            if group.get('name') == 'default':
                return {
                    'username': group.get('username'),
                    'password': group.get('password'),
                    'enable_password': group.get('enable_password')
                }
        return {'username': '', 'password': '', 'enable_password': ''}

    def _deploy_single_device_netmiko(
        self,
        device: dict,
        config: str,
        credentials: dict,
        dry_run: bool = False
    ) -> dict:
        """使用 Netmiko 部署单个设备"""
        import time
        start_time = time.time()

        result = {
            'device_id': device.get('id'),
            'device_name': device.get('name'),
            'device_ip': device.get('ip'),
            'success': False,
            'message': '',
            'cli_output': '',
            'log_content': '',  # 详细日志内容
            'errors': []
        }

        # 构建日志内容
        log_lines = []
        log_lines.append(f"[INFO] 开始部署设备配置: {device.get('name')} ({device.get('ip')})")
        log_lines.append(f"[INFO] 使用引擎: Netmiko")
        cred_group = device.get('credential_group', 'default')
        log_lines.append(f"[INFO] 使用凭证组: {cred_group}")
        log_lines.append(f"[INFO] 用户名: {credentials.get('username', 'N/A')}")

        if not NETMIKO_AVAILABLE:
            log_lines.append("[ERROR] Netmiko 未安装")
            result['message'] = 'Netmiko 未安装'
            result['log_content'] = '\n'.join(log_lines)
            return result

        from netmiko import ConnectHandler

        # 根据 vendor 字段确定 Netmiko device_type（使用统一驱动注册表）
        vendor = device.get('vendor', 'cisco').lower()

        from app.features.devices.drivers.registry import DriverRegistry
        driver_class = DriverRegistry.get(vendor)
        netmiko_device_type = driver_class.NETMIKO_DRIVER

        log_lines.append(f"[INFO] 设备类型: {netmiko_device_type} (vendor: {vendor})")

        # 解析配置为命令列表
        commands = self._parse_config_to_commands(config)
        log_lines.append(f"[INFO] 配置命令数量: {len(commands)} 行")
        if dry_run:
            log_lines.append("[INFO] 预览模式: 配置不会实际执行")

        netmiko_device = {
            'device_type': netmiko_device_type,
            'host': device.get('ip'),
            'port': device.get('ssh_port', 22),
            'username': credentials.get('username', ''),
            'password': credentials.get('password', ''),
            'secret': credentials.get('enable_password', ''),
            'timeout': 30,
            'session_timeout': 60,
            'global_delay_factor': 2,
            'fast_cli': False,
        }

        connection = None
        try:
            log_lines.append(f"[INFO] 正在连接设备...")
            logger.info(f"正在连接设备 {device.get('name')} ({device.get('ip')})...")
            connection = ConnectHandler(**netmiko_device)
            log_lines.append(f"[INFO] SSH 连接成功")

            if credentials.get('enable_password'):
                log_lines.append(f"[INFO] 进入特权模式 (enable)")
                connection.enable()

            if dry_run:
                # 预览模式：只获取当前配置
                log_lines.append(f"[INFO] 执行命令: show running-config | section hostname")
                output = connection.send_command("show running-config | section hostname")
                result['cli_output'] = output
                result['success'] = True
                result['message'] = '预览模式，配置未实际部署'
                log_lines.append(f"[INFO] 预览完成，配置未实际部署")
            else:
                # 实际部署
                log_lines.append(f"[INFO] 开始执行配置命令...")
                output = connection.send_config_set(commands)
                result['cli_output'] = output
                result['success'] = True
                result['message'] = '配置部署成功'
                log_lines.append(f"[True] 配置部署成功")

                # 显示命令输出摘要
                if output:
                    output_lines = output.strip().split('\n')
                    log_lines.append(f"[INFO] 命令输出 ({len(output_lines)} 行)")

                # 保存配置到 startup-config
                log_lines.append(f"[INFO] 正在保存配置到 startup-config...")
                try:
                    save_output = connection.save_config()
                    log_lines.append(f"[INFO] 配置已保存 (write memory)")
                    logger.info(f"设备 {device.get('name')} 配置已保存到 startup-config")
                except Exception as save_err:
                    log_lines.append(f"[WARN] 保存配置失败: {str(save_err)}")
                    logger.warning(f"设备 {device.get('name')} 保存配置失败: {save_err}")

            logger.info(f"设备 {device.get('name')} 部署完成")

        except NetmikoTimeoutException as e:
            log_lines.append(f"[ERROR] 连接超时: {device.get('ip')}")
            log_lines.append(f"[ERROR] 错误详情: {str(e)}")
            result['message'] = f"连接超时: {device.get('ip')}"
            result['errors'].append(str(e))
            logger.error(f"设备 {device.get('name')} 连接超时: {e}")

        except NetmikoAuthenticationException as e:
            log_lines.append(f"[ERROR] 认证失败，请检查凭证")
            log_lines.append(f"[ERROR] 错误详情: {str(e)}")
            result['message'] = "认证失败，请检查凭证"
            result['errors'].append(str(e))
            logger.error(f"设备 {device.get('name')} 认证失败: {e}")

        except Exception as e:
            log_lines.append(f"[ERROR] 部署失败: {str(e)}")
            log_lines.append(f"[ERROR] 错误类型: {type(e).__name__}")
            result['message'] = f"部署失败: {str(e)}"
            result['errors'].append(str(e))
            logger.error(f"设备 {device.get('name')} 部署异常: {e}")

        finally:
            if connection:
                try:
                    connection.disconnect()
                    log_lines.append(f"[INFO] SSH 连接已关闭")
                except:
                    pass

        # 计算耗时
        duration_ms = int((time.time() - start_time) * 1000)
        log_lines.append(f"[INFO] 耗时: {duration_ms}ms")

        # 设置最终结果
        if not result['success']:
            log_lines.append(f"[False] 部署失败")

        result['log_content'] = '\n'.join(log_lines)
        result['duration_ms'] = duration_ms

        return result

    def _deploy_single_device_napalm(
        self,
        device: dict,
        config: str,
        credentials: dict,
        dry_run: bool = False,
        mode: str = 'merge',
        transfer_mode: str = 'inline'
    ) -> dict:
        """使用 NAPALM 部署单个设备

        Args:
            transfer_mode: 传输方式 (scp/inline)，scp 需要设备开启 ip scp server enable
        """
        import time
        start_time = time.time()

        result = {
            'device_id': device.get('id'),
            'device_name': device.get('name'),
            'device_ip': device.get('ip'),
            'success': False,
            'message': '',
            'diff': '',
            'rollback_available': False,
            'log_content': '',  # 详细日志内容
            'errors': []
        }

        # 构建日志内容
        log_lines = []
        log_lines.append(f"[INFO] 开始部署设备配置: {device.get('name')} ({device.get('ip')})")
        log_lines.append(f"[INFO] 使用引擎: NAPALM")
        log_lines.append(f"[INFO] 配置模式: {mode} (增量合并)")
        log_lines.append(f"[INFO] 传输方式: {transfer_mode} ({'Tcl 内联' if transfer_mode == 'inline' else 'SCP 文件传输'})")
        cred_group = device.get('credential_group', 'default')
        log_lines.append(f"[INFO] 使用凭证组: {cred_group}")
        log_lines.append(f"[INFO] 用户名: {credentials.get('username', 'N/A')}")

        if not NAPALM_AVAILABLE:
            log_lines.append("[ERROR] NAPALM 未安装")
            result['message'] = 'NAPALM 未安装'
            result['log_content'] = '\n'.join(log_lines)
            return result

        # 根据 vendor 字段确定 NAPALM driver
        vendor = device.get('vendor', 'cisco').lower()

        vendor_driver_map = {
            'cisco': 'ios',
            'juniper': 'junos',
            'huawei': 'huawei',
            'h3c': 'huawei',
            'arista': 'eos',
        }
        driver_name = vendor_driver_map.get(vendor, 'ios')
        log_lines.append(f"[INFO] NAPALM Driver: {driver_name} (vendor: {vendor})")

        # 计算配置行数
        config_lines = len(config.strip().split('\n'))
        log_lines.append(f"[INFO] 配置内容: {config_lines} 行")

        if dry_run:
            log_lines.append("[INFO] 预览模式: 配置不会实际执行")

        # 根据传输方式设置 inline_transfer
        use_inline_transfer = transfer_mode == 'inline'
        log_lines.append(f"[INFO] inline_transfer: {use_inline_transfer}")

        napalm_device = {
            'hostname': device.get('ip'),
            'username': credentials.get('username', ''),
            'password': credentials.get('password', ''),
            'optional_args': {
                'port': device.get('ssh_port', 22),
                'inline_transfer': use_inline_transfer,
                'global_delay_factor': 3,
                'fast_cli': False,
                'transport': 'ssh',
                'allow_agent': False,
                'ssh_config_file': None,
                'conn_timeout': 60,
                'read_timeout': 120,
            }
        }

        connection = None
        try:
            log_lines.append(f"[INFO] 正在连接设备...")
            logger.info(f"正在通过 NAPALM 连接设备 {device.get('name')} ({device.get('ip')})...")
            driver = get_network_driver(driver_name)
            connection = driver(**napalm_device)
            connection.open()
            log_lines.append(f"[INFO] NAPALM 连接成功")

            # 加载候选配置
            log_lines.append(f"[INFO] 加载候选配置...")
            if mode == 'replace':
                connection.load_replace_candidate(config=config)
                log_lines.append(f"[INFO] 使用 replace 模式加载配置")
            else:
                connection.load_merge_candidate(config=config)
                log_lines.append(f"[INFO] 使用 merge 模式加载配置")

            # 对比差异
            log_lines.append(f"[INFO] 对比配置差异...")
            diff = connection.compare_config()
            result['diff'] = diff

            if diff and diff.strip():
                diff_lines = len(diff.strip().split('\n'))
                log_lines.append(f"[INFO] 发现差异: {diff_lines} 行")
            else:
                log_lines.append(f"[INFO] 无配置差异")

            if dry_run:
                connection.discard_config()
                result['success'] = True
                result['message'] = '预览模式，配置未实际部署'
                log_lines.append(f"[INFO] 预览完成，配置已丢弃")
            elif not diff or diff.strip() == '':
                connection.discard_config()
                result['success'] = True
                result['message'] = '配置无变更，跳过部署'
                log_lines.append(f"[INFO] 配置无变更，跳过部署")
            else:
                log_lines.append(f"[INFO] 开始提交配置...")
                connection.commit_config()
                result['success'] = True
                result['message'] = '配置部署成功（NAPALM 安全模式）'
                result['rollback_available'] = True
                log_lines.append(f"[True] 配置部署成功")
                log_lines.append(f"[INFO] 配置已保存到 startup-config (NAPALM 自动保存)")
                log_lines.append(f"[INFO] 支持回滚（rollback_available=True）")

            logger.info(f"NAPALM 设备 {device.get('name')} 部署完成")

        except Exception as e:
            log_lines.append(f"[ERROR] 部署失败: {str(e)}")
            log_lines.append(f"[ERROR] 错误类型: {type(e).__name__}")
            result['message'] = f"部署失败: {str(e)}"
            result['errors'].append(str(e))
            logger.error(f"NAPALM 设备 {device.get('name')} 部署异常: {e}")
            if connection and not dry_run:
                try:
                    connection.rollback()
                    log_lines.append(f"[INFO] 自动回滚已执行")
                except:
                    log_lines.append(f"[WARN] 自动回滚失败")

        finally:
            if connection:
                try:
                    connection.close()
                    log_lines.append(f"[INFO] NAPALM 连接已关闭")
                except:
                    pass

        # 计算耗时
        duration_ms = int((time.time() - start_time) * 1000)
        log_lines.append(f"[INFO] 耗时: {duration_ms}ms")

        # 设置最终结果
        if not result['success']:
            log_lines.append(f"[False] 部署失败")

        result['log_content'] = '\n'.join(log_lines)
        result['duration_ms'] = duration_ms

        return result

    def _parse_config_to_commands(self, config: str) -> list:
        """解析配置文本为命令列表"""
        commands = []
        for line in config.strip().splitlines():
            line = line.strip()
            if not line or line.startswith('!') or line.startswith('#'):
                continue
            if line in ['configure terminal', 'end', 'exit']:
                continue
            commands.append(line)
        return commands

    async def stream_batch_deploy(
        self,
        websocket: WebSocket,
        devices: List[dict],
        config: str,
        credential_groups: List[dict],
        engine: str = 'netmiko',
        napalm_mode: str = 'merge',
        transfer_mode: str = 'inline',  # NAPALM 传输方式 (scp/inline)，默认 inline
        dry_run: bool = False,
        session_id: str = None,
        parallel_limit: int = 1
    ):
        """
        批量部署流式执行

        Args:
            websocket: WebSocket 连接
            devices: 设备列表
            config: 配置内容
            credential_groups: 凭证组列表
            engine: 部署引擎 (netmiko/napalm)
            napalm_mode: NAPALM 模式 (merge/replace)
            transfer_mode: NAPALM 传输方式 (scp/inline)
            dry_run: 是否预览模式
            session_id: 会话ID
            parallel_limit: 并行数量（默认1，串行）
        """
        total_count = len(devices)
        completed_count = 0
        failed_count = 0
        results = []

        # 推送开始消息
        await self.push_message(websocket, {
            'type': 'deploy_started',
            'session_id': session_id,
            'total_count': total_count,
            'engine': engine,
            'dry_run': dry_run,
            'parallel_limit': parallel_limit,
            'timestamp': datetime.utcnow().isoformat()
        })

        # 获取事件循环
        loop = asyncio.get_event_loop()

        if parallel_limit == 1:
            # ========== 串行模式：逐个执行 ==========
            for device in devices:
                device_id = device.get('id')
                device_name = device.get('name')
                device_ip = device.get('ip')

                # 推送设备开始消息
                await self.push_message(websocket, {
                    'type': 'device_started',
                    'device_id': device_id,
                    'device_name': device_name,
                    'device_ip': device_ip,
                    'timestamp': datetime.utcnow().isoformat()
                })

                # 获取凭证
                credentials = self._get_device_credentials(device, credential_groups)

                # 执行部署
                try:
                    if engine == 'napalm':
                        result = await loop.run_in_executor(
                            None,
                            lambda: self._deploy_single_device_napalm(
                                device, config, credentials, dry_run, napalm_mode, transfer_mode
                            )
                        )
                    else:
                        result = await loop.run_in_executor(
                            None,
                            self._deploy_single_device_netmiko,
                            device, config, credentials, dry_run
                        )
                except Exception as e:
                    result = {
                        'device_id': device_id,
                        'device_name': device_name,
                        'device_ip': device_ip,
                        'success': False,
                        'message': f"执行异常: {str(e)}",
                        'errors': [str(e)]
                    }

                results.append(result)

                # 更新计数
                if result.get('success'):
                    completed_count += 1
                else:
                    failed_count += 1

                # 计算进度
                progress_percent = round((completed_count + failed_count) / total_count * 100)

                # 推送设备进度消息
                await self.push_message(websocket, {
                    'type': 'device_progress',
                    'device_id': device_id,
                    'device_name': device_name,
                    'device_ip': device_ip,
                    'status': 'completed' if result.get('success') else 'failed',
                    'success': result.get('success'),
                    'message': result.get('message'),
                    'cli_output': result.get('cli_output', ''),
                    'diff': result.get('diff', ''),
                    'rollback_available': result.get('rollback_available', False),
                    'progress': progress_percent,
                    'completed_count': completed_count,
                    'failed_count': failed_count,
                    'total_count': total_count,
                    'timestamp': datetime.utcnow().isoformat()
                })

        else:
            # ========== 并行模式：使用 semaphore 控制并发数 ==========
            semaphore = asyncio.Semaphore(parallel_limit)

            async def deploy_single_with_semaphore(device: dict):
                """带并发控制的单个设备部署"""
                nonlocal completed_count, failed_count, results  # 闭包中修改外部变量

                async with semaphore:
                    device_id = device.get('id')
                    device_name = device.get('name')
                    device_ip = device.get('ip')

                    # 推送设备开始消息
                    await self.push_message(websocket, {
                        'type': 'device_started',
                        'device_id': device_id,
                        'device_name': device_name,
                        'device_ip': device_ip,
                        'timestamp': datetime.utcnow().isoformat()
                    })

                    # 获取凭证
                    credentials = self._get_device_credentials(device, credential_groups)

                    # 执行部署
                    try:
                        if engine == 'napalm':
                            result = await loop.run_in_executor(
                                None,
                                lambda: self._deploy_single_device_napalm(
                                    device, config, credentials, dry_run, napalm_mode, transfer_mode
                                )
                            )
                        else:
                            result = await loop.run_in_executor(
                                None,
                                self._deploy_single_device_netmiko,
                                device, config, credentials, dry_run
                            )
                    except Exception as e:
                        result = {
                            'device_id': device_id,
                            'device_name': device_name,
                            'device_ip': device_ip,
                            'success': False,
                            'message': f"执行异常: {str(e)}",
                            'errors': [str(e)]
                        }

                    results.append(result)

                    # 更新计数
                    if result.get('success'):
                        completed_count += 1
                    else:
                        failed_count += 1

                    # 计算进度
                    progress_percent = round((completed_count + failed_count) / total_count * 100)

                    # 推送设备进度消息
                    await self.push_message(websocket, {
                        'type': 'device_progress',
                        'device_id': device_id,
                        'device_name': device_name,
                        'device_ip': device_ip,
                        'status': 'completed' if result.get('success') else 'failed',
                        'success': result.get('success'),
                        'message': result.get('message'),
                        'cli_output': result.get('cli_output', ''),
                        'diff': result.get('diff', ''),
                        'rollback_available': result.get('rollback_available', False),
                        'progress': progress_percent,
                        'completed_count': completed_count,
                        'failed_count': failed_count,
                        'total_count': total_count,
                        'timestamp': datetime.utcnow().isoformat()
                    })

            # 并行执行所有设备
            await asyncio.gather(*[deploy_single_with_semaphore(d) for d in devices])

        # 创建部署历史记录
        history_id = None
        try:
            from app.shared.database import get_db
            from app.shared.models import DeployHistory, DeployDeviceResult, LogEntry

            db = next(get_db())
            try:
                # 判断是否全部成功
                all_success = failed_count == 0

                # 设备数据列表
                device_data_list = [
                    {'id': d.get('id'), 'name': d.get('name'), 'ip': d.get('ip')}
                    for d in devices
                ]

                # 创建历史主记录
                history = DeployHistory(
                    user_id=None,
                    username="Web",
                    operation_type='deploy',
                    engine=engine,
                    mode=napalm_mode if engine == 'napalm' else 'config',
                    target_devices=json.dumps(device_data_list),
                    success=all_success,
                    total_devices=total_count,
                    success_count=completed_count,
                    failed_count=failed_count,
                    parent_id=None,
                    created_at=datetime.utcnow()
                )
                db.add(history)
                db.flush()

                history_id = history.id

                # 创建设备执行结果和工具执行日志
                for result in results:
                    device_result = DeployDeviceResult(
                        deploy_id=history_id,
                        device_id=result.get('device_id'),
                        device_name=result.get('device_name'),
                        status='completed' if result.get('success') else 'failed',
                        rollback_available=result.get('rollback_available', False),
                        rollback_status='pending',
                        cli_output=result.get('cli_output'),
                        diff_output=result.get('diff'),
                        error_message=result.get('message') if not result.get('success') else None,
                        created_at=datetime.utcnow()
                    )
                    db.add(device_result)

                    # 创建工具执行日志 (LogEntry) - 详细日志
                    log_entry = LogEntry(
                        tool_type=engine,  # netmiko 或 napalm
                        operation=f"deploy - {result.get('device_name')}",
                        target=f"{result.get('device_name')} ({result.get('device_ip')})",
                        status='success' if result.get('success') else 'failed',
                        log_content=result.get('log_content', result.get('message', '')),
                        duration_ms=result.get('duration_ms'),
                        created_by="Web"
                    )
                    db.add(log_entry)

                db.commit()
                logger.info(f"创建部署历史记录: id={history_id}")

            except Exception as db_error:
                logger.error(f"创建部署历史记录失败: {db_error}")
                db.rollback()
            finally:
                db.close()
        except Exception as e:
            logger.error(f"数据库操作失败: {e}")

        # 推送完成消息
        await self.push_message(websocket, {
            'type': 'deploy_complete',
            'session_id': session_id,
            'success_count': completed_count,
            'failed_count': failed_count,
            'total_count': total_count,
            'history_id': history_id,
            'timestamp': datetime.utcnow().isoformat()
        })


# 全局实例
_deploy_stream_service = None


def get_deploy_stream_service():
    """获取部署流式服务实例"""
    global _deploy_stream_service
    if _deploy_stream_service is None:
        _deploy_stream_service = DeployStreamService()
    return _deploy_stream_service