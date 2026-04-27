"""
Netmiko SSH 服务 - 用于连接 Cisco IOS 设备
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import hashlib
import os

from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException
from netmiko.exceptions import SSHException
from loguru import logger

from app.shared.config import get_config
from app.shared.models import Device
from app.features.devices.vendor_adapter import get_vendor_profile


class NetmikoService:
    """Netmiko SSH 服务"""

    def __init__(self):
        self.config = get_config()
        self.connection: Optional[ConnectHandler] = None

    def get_device_params(self, device: Device, credentials: Dict[str, str]) -> Dict[str, Any]:
        """构建设备连接参数（支持多厂商）"""
        vendor_profile = get_vendor_profile(getattr(device, 'vendor', 'cisco'))
        return {
            "device_type": vendor_profile.netmiko_device_type,
            "host": device.ip,
            "port": 22,
            "username": credentials.get("username", "admin"),
            "password": credentials.get("password", ""),
            "secret": credentials.get("secret", ""),
            "timeout": 30,
            "session_timeout": 60,
        }

    def connect(self, device: Device, credentials: Dict[str, str]) -> ConnectHandler:
        """连接到设备（支持多厂商）"""
        params = self.get_device_params(device, credentials)
        vendor_profile = get_vendor_profile(getattr(device, 'vendor', 'cisco'))

        logger.info(f"正在连接设备 {device.name} ({device.ip}) [厂商: {vendor_profile.display_name}]")

        try:
            self.connection = ConnectHandler(**params)
            # 只有 Cisco/Arista 等需要 enable 模式
            if vendor_profile.enter_enable_mode:
                self.connection.enable()
            logger.info(f"成功连接到设备 {device.name}")
            return self.connection
        except NetmikoTimeoutException as e:
            logger.error(f"连接设备 {device.name} 超时：{e}")
            raise
        except NetmikoAuthenticationException as e:
            logger.error(f"设备 {device.name} 认证失败：{e}")
            raise
        except SSHException as e:
            logger.error(f"设备 {device.name} SSH 错误：{e}")
            raise

    def disconnect(self):
        """断开连接"""
        if self.connection:
            self.connection.disconnect()
            self.connection = None

    def get_running_config(self) -> str:
        """获取 running-config"""
        if not self.connection:
            raise RuntimeError("未连接到设备")

        logger.debug("执行 show running-config")
        config = self.connection.send_command("show running-config")
        return config

    def save_config(self) -> str:
        """保存配置到 startup-config"""
        if not self.connection:
            raise RuntimeError("未连接到设备")

        logger.debug("执行 write memory")
        result = self.connection.save_config()
        return result if result else "[OK]"

    def send_commands(self, commands: List[str], verify: bool = False) -> str:
        """发送配置命令"""
        if not self.connection:
            raise RuntimeError("未连接到设备")

        logger.debug(f"发送配置命令，共 {len(commands)} 条")

        if verify:
            # 逐条发送并验证
            results = []
            for cmd in commands:
                result = self.connection.send_config_set([cmd])
                results.append(result)
            return "\n".join(results)
        else:
            return self.connection.send_config_set(commands)

    @staticmethod
    def calculate_md5(content: str) -> str:
        """计算配置内容的 MD5 哈希值"""
        return hashlib.md5(content.encode()).hexdigest()

    @staticmethod
    def compare_configs(old_config: str, new_config: str) -> bool:
        """比较两个配置是否相同"""
        # 移除时间戳等动态内容后比较
        old_lines = [line.strip() for line in old_config.splitlines()
                     if not line.strip().startswith("!")]
        new_lines = [line.strip() for line in new_config.splitlines()
                     if not line.strip().startswith("!")]

        return old_lines == new_lines


def backup_device_config(device: Device, credentials: Dict[str, str],
                          backup_dir: str = "./backups") -> Dict[str, Any]:
    """
    备份设备配置

    Returns:
        dict: {
            "success": bool,
            "file_path": str,
            "file_size": int,
            "md5_hash": str,
            "has_change": bool,
            "message": str
        }
    """
    result = {
        "success": False,
        "file_path": "",
        "file_size": 0,
        "md5_hash": "",
        "has_change": False,
        "message": ""
    }

    service = NetmikoService()

    try:
        # 连接设备
        service.connect(device, credentials)

        # 获取配置
        config = service.get_running_config()

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{device.name}_{timestamp}.cfg"

        # 确保目录存在
        device_backup_dir = os.path.join(backup_dir, device.name)
        os.makedirs(device_backup_dir, exist_ok=True)

        file_path = os.path.join(device_backup_dir, filename)

        # 保存配置
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(config)

        # 计算 MD5
        md5_hash = service.calculate_md5(config)

        # 检查是否有变更（与 latest.cfg 比较）
        latest_path = os.path.join(device_backup_dir, "latest.cfg")
        has_change = True

        if os.path.exists(latest_path):
            with open(latest_path, "r", encoding="utf-8") as f:
                old_config = f.read()
            has_change = not service.compare_configs(old_config, config)

        # 更新 latest.cfg（Windows 上使用复制代替 symlink）
        import shutil
        if os.path.exists(latest_path):
            os.remove(latest_path)
        shutil.copy2(file_path, latest_path)

        result["success"] = True
        result["file_path"] = file_path
        result["file_size"] = len(config)
        result["md5_hash"] = md5_hash
        result["has_change"] = has_change
        result["message"] = "备份成功"

        logger.info(f"设备 {device.name} 备份成功：{file_path}")

    except Exception as e:
        result["message"] = str(e)
        logger.error(f"设备 {device.name} 备份失败：{e}")

    finally:
        service.disconnect()

    return result
