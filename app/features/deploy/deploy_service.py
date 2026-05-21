"""
配置部署服务
支持通过 SSH/Netmiko 将配置部署到网络设备
"""

from loguru import logger
from typing import List, Dict, Optional
from datetime import datetime
import re

try:
    from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException
    NETMIKO_AVAILABLE = True
except ImportError:
    NETMIKO_AVAILABLE = False
    logger.warning("netmiko 未安装，配置部署功能将不可用。请运行：pip install netmiko")


class DeployService:
    """配置部署服务"""

    def __init__(self):
        self.device_type_map = {
            'cisco': 'cisco_ios',
            'huawei': 'huawei',
            'h3c': 'h3c_comware',
            'juniper': 'juniper_junos',
        }

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

        # 根据 vendor 字段确定 Netmiko device_type（厂商设备类型）
        # vendor: cisco, juniper, huawei, arista 等
        # device_type 是业务角色类型，不用于确定 device_type
        vendor = device.get('vendor', 'cisco').lower()

        vendor_device_type_map = {
            'cisco': 'cisco_ios',       # Cisco IOS/IOS-XE 设备
            'juniper': 'juniper_junos', # Juniper 设备
            'huawei': 'huawei',         # 华为设备
            'h3c': 'hp_comware',        # H3C 设备
            'arista': 'arista_eos',     # Arista 设备
        }
        netmiko_device_type = vendor_device_type_map.get(vendor, 'cisco_ios')

        netmiko_device = {
            'device_type': netmiko_device_type,
            'host': device.get('ip'),
            'port': device.get('ssh_port', 22),
            'username': credentials.get('username', ''),
            'password': credentials.get('password', ''),
            'secret': credentials.get('enable_password', ''),
            'timeout': 30,
            'session_timeout': 60,
            'global_delay_factor': 2,  # 增加延迟因子，适应工业交换机等慢响应设备
            'fast_cli': False,  # 禁用快速CLI模式，提高可靠性
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

    def get_current_config(self, connection: object) -> str:
        """获取设备当前配置"""
        try:
            logger.info("正在获取设备当前配置...")
            config = connection.send_command("show running-config")
            return config if config else ""
        except Exception as e:
            logger.error(f"获取配置失败：{e}")
            raise RuntimeError(f"获取配置失败：{str(e)}")

    def deploy_config(self, connection: object, config: str, dry_run: bool = False) -> dict:
        """
        部署配置到设备

        Args:
            connection: Netmiko 连接对象
            config: 要部署的完整配置
            dry_run: 是否仅为预览，不实际执行

        Returns:
            部署结果字典
        """
        result = {
            'success': False,
            'changes': [],
            'errors': [],
            'dry_run': dry_run
        }

        try:
            # 获取当前配置
            current_config = self.get_current_config(connection)

            # 对比配置差异
            diff = self.compare_config(current_config, config)
            result['changes'] = diff

            if dry_run:
                result['success'] = True
                result['message'] = '预览模式，配置未实际部署'
                return result

            if not diff:
                result['success'] = True
                result['message'] = '配置无变更，跳过部署'
                return result

            # 进入配置模式并部署配置
            logger.info("正在部署配置...")

            # 解析配置行为单位命令
            commands = self.parse_config_commands(config)

            # 发送配置命令
            output = connection.send_config_set(commands)

            # 保存配置
            save_output = connection.save_config()

            result['success'] = True
            result['message'] = '配置部署成功'
            result['cli_output'] = output
            result['save_output'] = save_output

            logger.info("配置部署成功")

        except Exception as e:
            result['success'] = False
            result['errors'].append(str(e))
            result['message'] = f'部署失败：{str(e)}'
            logger.error(f"部署失败：{e}")

        return result

    def compare_config(self, current: str, new: str) -> List[str]:
        """
        对比当前配置和新配置的差异

        Returns:
            差异命令列表
        """
        import difflib

        current_lines = current.strip().splitlines()
        new_lines = new.strip().splitlines()

        diff = difflib.unified_diff(
            current_lines,
            new_lines,
            fromfile='current',
            tofile='new',
            lineterm=''
        )

        changes = []
        for line in diff:
            if line.startswith('+') and not line.startswith('+++'):
                changes.append({
                    'type': 'add',
                    'content': line[1:].strip()
                })
            elif line.startswith('-') and not line.startswith('---'):
                changes.append({
                    'type': 'remove',
                    'content': line[1:].strip()
                })

        return changes

    def parse_config_commands(self, config: str) -> List[str]:
        """
        解析配置文件为命令列表

        注意：实际部署时，通常只需要增量配置命令，
        而不是完整的 running-config
        """
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

    def deploy_from_backup(
        self,
        device: dict,
        backup_file: str,
        credential_groups: List[dict],
        dry_run: bool = False
    ) -> dict:
        """
        从备份文件部署配置到设备

        Args:
            device: 设备信息字典
            backup_file: 备份文件路径
            credential_groups: 凭证组列表
            dry_run: 是否预览模式

        Returns:
            部署结果
        """
        # 读取备份文件
        try:
            from pathlib import Path
            backup_path = Path(backup_file)
            if not backup_path.exists():
                # 尝试相对路径
                backup_path = Path(f"./backups/{backup_file}")

            with open(backup_path, 'r', encoding='utf-8') as f:
                config_content = f.read()
        except Exception as e:
            return {
                'success': False,
                'message': f'读取备份文件失败：{str(e)}',
                'device_name': device.get('name')
            }

        return self.deploy_to_device(device, config_content, credential_groups, dry_run)

    def deploy_from_template(
        self,
        device: dict,
        template_content: str,
        variables: Dict[str, str],
        credential_groups: List[dict],
        dry_run: bool = False
    ) -> dict:
        """
        从模板渲染并部署配置

        Args:
            device: 设备信息
            template_content: 模板内容
            variables: 变量替换字典
            credential_groups: 凭证组列表
            dry_run: 是否预览模式

        Returns:
            部署结果
        """
        from jinja2 import Template

        try:
            # 渲染模板
            tmpl = Template(template_content)
            context = {
                'now': datetime.utcnow,
                'now_str': datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                'device': device
            }
            context.update(variables)
            rendered_config = tmpl.render(**context)
        except Exception as e:
            return {
                'success': False,
                'message': f'模板渲染失败：{str(e)}',
                'device_name': device.get('name')
            }

        return self.deploy_to_device(device, rendered_config, credential_groups, dry_run)

    def deploy_to_device(
        self,
        device: dict,
        config: str,
        credential_groups: List[dict],
        dry_run: bool = False
    ) -> dict:
        """
        部署配置到单个设备

        Args:
            device: 设备信息
            config: 配置内容
            credential_groups: 凭证组列表
            dry_run: 是否预览模式

        Returns:
            部署结果
        """
        result = {
            'device_id': device.get('id'),
            'device_name': device.get('name'),
            'device_ip': device.get('ip'),
            'success': False,
            'changes': [],
            'errors': []
        }

        # 获取凭证
        credentials = self.get_device_credentials(device, credential_groups)

        if not credentials.get('username'):
            result['errors'].append('未找到设备凭证')
            result['message'] = '未找到设备对应的凭证组，请检查设备配置'
            return result

        # 连接设备并部署
        connection = None
        try:
            connection = self.connect_device(device, credentials)
            deploy_result = self.deploy_config(connection, config, dry_run)
            result.update(deploy_result)
        except Exception as e:
            result['success'] = False
            result['errors'].append(str(e))
            result['message'] = f'部署失败：{str(e)}'
        finally:
            if connection:
                try:
                    connection.disconnect()
                except:
                    pass

        return result

    def batch_deploy(
        self,
        devices: List[dict],
        config: str,
        credential_groups: List[dict],
        dry_run: bool = False
    ) -> List[dict]:
        """
        批量部署配置到多个设备

        Returns:
            每个设备的部署结果列表
        """
        results = []

        for device in devices:
            logger.info(f"开始部署到设备：{device.get('name')}")
            result = self.deploy_to_device(device, config, credential_groups, dry_run)
            results.append(result)
            logger.info(f"设备 {device.get('name')} 部署完成：{'成功' if result['success'] else '失败'}")

        return results


def get_deploy_service():
    """获取部署服务实例"""
    return DeployService()
