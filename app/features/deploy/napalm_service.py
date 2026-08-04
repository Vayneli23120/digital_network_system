"""
NAPALM 配置部署服务

提供安全的配置部署流程：
- load_merge_candidate / load_replace_candidate 加载候选配置
- compare_config() 预览差异
- commit_config() 提交并自动备份
- rollback() 回滚到上一版本
"""

from loguru import logger
from typing import List, Optional

try:
    from napalm import get_network_driver
    NAPALM_AVAILABLE = True
except ImportError:
    NAPALM_AVAILABLE = False
    logger.warning("napalm 未安装，NAPALM 部署功能不可用")


class NapalmDeployService:
    """NAPALM 配置部署服务"""

    def get_device_credentials(self, device: dict, credential_groups: List[dict]) -> dict:
        """根据设备的 credential_group 获取对应的凭证"""
        group_name = device.get('credential_group', 'default')

        for group in credential_groups:
            if group.get('name') == group_name:
                return {
                    'username': group.get('username'),
                    'password': group.get('password'),
                }

        # 如果未找到匹配的组，使用 default 组
        for group in credential_groups:
            if group.get('name') == 'default':
                return {
                    'username': group.get('username'),
                    'password': group.get('password'),
                }

        return {'username': '', 'password': ''}

    def connect_device(self, device: dict, credentials: dict) -> Optional[object]:
        """使用 NAPALM 连接设备"""
        if not NAPALM_AVAILABLE:
            raise RuntimeError("napalm 未安装，无法连接设备")

        # 根据 vendor 字段确定 NAPALM driver（厂商设备类型）
        # vendor: cisco, juniper, huawei, arista 等
        # device_type 是业务角色类型，不用于确定 driver
        vendor = device.get('vendor', 'cisco').lower()

        from app.features.devices.drivers.registry import DriverRegistry
        driver_class = DriverRegistry.get(vendor)
        driver_name = driver_class.NAPALM_DRIVER or 'ios'

        napalm_device = {
            'hostname': device.get('ip'),
            'username': credentials.get('username', ''),
            'password': credentials.get('password', ''),
            'optional_args': {
                'port': device.get('ssh_port', 22),
                'inline_transfer': False,  # 使用 SCP 传输（需要设备开启 ip scp server enable）
                'global_delay_factor': 3,  # 增加延迟因子
                'fast_cli': False,
                'transport': 'ssh',
                'allow_agent': False,
                'ssh_config_file': None,
                'conn_timeout': 60,
                'read_timeout': 120,
            }
        }

        try:
            logger.info(f"正在通过 NAPALM 连接设备 {device.get('name')} ({device.get('ip')})...")
            driver = get_network_driver(driver_name)
            device_conn = driver(**napalm_device)
            device_conn.open()
            logger.info(f"NAPALM 连接成功")
            return device_conn

        except Exception as e:
            logger.error(f"NAPALM 连接失败: {e}")
            raise RuntimeError(f"连接失败: {str(e)}")

    def deploy_to_device(
        self,
        device: dict,
        config: str,
        credential_groups: List[dict],
        dry_run: bool = False,
        mode: str = "merge"  # merge | replace
    ) -> dict:
        """
        NAPALM 安全部署流程

        Args:
            device: 设备信息字典
            config: 配置内容
            credential_groups: 凭证组列表
            dry_run: 是否预览模式
            mode: 配置模式 (merge 增量 / replace 完整替换)

        Returns:
            {
                'success': bool,
                'device_id': int,
                'device_name': str,
                'diff': str,              # compare_config 输出
                'rollback_available': bool,
                'message': str,
                'errors': list
            }
        """
        result = {
            'device_id': device.get('id'),
            'device_name': device.get('name'),
            'device_ip': device.get('ip'),
            'success': False,
            'diff': '',
            'rollback_available': False,
            'errors': [],
            'dry_run': dry_run,
            'mode': mode
        }

        if not NAPALM_AVAILABLE:
            result['errors'].append('napalm 未安装')
            result['message'] = 'NAPALM 服务不可用'
            return result

        # 获取凭证
        credentials = self.get_device_credentials(device, credential_groups)

        if not credentials.get('username'):
            result['errors'].append('未找到设备凭证')
            result['message'] = '未找到设备对应的凭证组'
            return result

        connection = None
        try:
            # 1. 连接设备
            connection = self.connect_device(device, credentials)

            # 2. 加载候选配置
            logger.info(f"加载候选配置 (mode={mode})...")
            if mode == 'replace':
                connection.load_replace_candidate(config=config)
            else:
                connection.load_merge_candidate(config=config)

            # 3. 对比差异
            logger.info("对比配置差异...")
            diff = connection.compare_config()
            result['diff'] = diff

            if dry_run:
                # 预览模式：放弃候选配置，返回差异
                logger.info("预览模式，放弃候选配置...")
                connection.discard_config()
                result['success'] = True
                result['message'] = '预览模式，配置未实际部署'
                result['rollback_available'] = False
                return result

            # 4. 检查是否有变更
            if not diff or diff.strip() == '':
                logger.info("配置无变更")
                connection.discard_config()
                result['success'] = True
                result['message'] = '配置无变更，跳过部署'
                return result

            # 5. 提交配置（commit_config 会自动备份）
            logger.info("提交配置变更...")
            connection.commit_config()

            result['success'] = True
            result['message'] = '配置部署成功（NAPALM 安全模式）'
            result['rollback_available'] = True
            logger.info("NAPALM 配置部署成功")

        except Exception as e:
            result['success'] = False
            result['errors'].append(str(e))
            result['message'] = f'部署失败: {str(e)}'
            logger.error(f"NAPALM 部署失败: {e}")

            # 尝试回滚
            if connection and not dry_run:
                try:
                    logger.info("尝试回滚...")
                    connection.rollback()
                    result['rollback_executed'] = True
                    result['message'] += ' (已自动回滚)'
                    logger.info("已回滚到上一版本")
                except Exception as rollback_error:
                    logger.error(f"回滚失败: {rollback_error}")
                    result['rollback_executed'] = False

        finally:
            if connection:
                try:
                    connection.close()
                except:
                    pass

        return result

    def rollback_device(
        self,
        device: dict,
        credential_groups: List[dict]
    ) -> dict:
        """
        手动回滚设备配置到上一版本

        Returns:
            {'success': bool, 'message': str, 'diff': str}
        """
        result = {
            'device_id': device.get('id'),
            'device_name': device.get('name'),
            'success': False,
            'message': '',
            'diff': '',
            'cli_output': ''
        }

        if not NAPALM_AVAILABLE:
            result['message'] = 'NAPALM 服务不可用'
            return result

        credentials = self.get_device_credentials(device, credential_groups)
        if not credentials.get('username'):
            result['message'] = '未找到设备凭证'
            return result

        connection = None
        try:
            connection = self.connect_device(device, credentials)

            # 先获取当前配置用于对比
            logger.info("获取当前配置...")
            current_config = connection.get_config()['running']

            # 执行回滚
            logger.info("执行回滚...")
            connection.rollback()

            # 获取回滚后的配置并对比
            logger.info("获取回滚后配置...")
            rollback_config = connection.get_config()['running']

            # 简单对比显示回滚结果
            import difflib
            diff = difflib.unified_diff(
                current_config.splitlines(),
                rollback_config.splitlines(),
                fromfile='回滚前',
                tofile='回滚后',
                lineterm=''
            )
            result['diff'] = '\n'.join(list(diff)[:100])  # 限制100行
            result['cli_output'] = '执行命令: configure replace flash:/rollback_config.txt force'

            result['success'] = True
            result['message'] = '配置已回滚到上一版本'
            logger.info(f"设备 {device.get('name')} 配置已回滚")

        except Exception as e:
            result['message'] = f'回滚失败: {str(e)}'
            result['cli_output'] = f'错误: {str(e)}'
            logger.error(f"回滚失败: {e}")
        finally:
            if connection:
                try:
                    connection.close()
                except:
                    pass

        return result

    def batch_deploy(
        self,
        devices: List[dict],
        config: str,
        credential_groups: List[dict],
        dry_run: bool = False,
        mode: str = "merge"
    ) -> List[dict]:
        """
        批量部署配置到多个设备

        Returns:
            每个设备的部署结果列表
        """
        results = []

        for device in devices:
            logger.info(f"开始部署到设备：{device.get('name')}")
            result = self.deploy_to_device(
                device=device,
                config=config,
                credential_groups=credential_groups,
                dry_run=dry_run,
                mode=mode
            )
            results.append(result)
            logger.info(f"设备 {device.get('name')} 部署完成：{'成功' if result['success'] else '失败'}")

        return results


def get_napalm_service():
    """获取 NAPALM 部署服务实例"""
    return NapalmDeployService()
