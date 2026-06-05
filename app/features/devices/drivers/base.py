"""
设备驱动抽象基类

所有厂商驱动必须实现此接口，可自动注册到驱动注册表。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class DeviceConnectionParams:
    """设备连接参数"""
    host: str
    username: str
    password: str
    enable_password: Optional[str] = None
    ssh_port: int = 22
    timeout: int = 30
    session_timeout: int = 60


@dataclass
class CommandResult:
    """命令执行结果"""
    command: str
    output: str
    success: bool
    error: Optional[str] = None
    parsed: Optional[Dict] = None  # TextFSM/NTC 解析结果


@dataclass
class ConfigDiff:
    """配置差异"""
    added_lines: List[str]
    removed_lines: List[str]
    raw_diff: str
    has_changes: bool


class BaseDeviceDriver(ABC):
    """
    所有厂商驱动的抽象基类

    实现此接口可自动注册到 DriverRegistry。
    """

    # 驱动元信息（子类必须定义）
    VENDOR: str = ""               # 厂商标识，如 "cisco", "huawei"
    OS_TYPES: List[str] = []       # 支持的 OS 类型列表
    NETMIKO_DRIVER: str = ""       # Netmiko device_type
    NAPALM_DRIVER: Optional[str] = None  # NAPALM driver，None 表示仅用 Netmiko

    # 设备特性（子类可覆盖）
    SUPPORTS_ENABLE_MODE: bool = True
    SHOW_RUN_COMMAND: str = "show running-config"
    SAVE_CONFIG_COMMAND: str = "write memory"
    CONFIG_MODE_COMMAND: str = "configure terminal"
    EXIT_CONFIG_MODE: str = "end"

    @abstractmethod
    def get_running_config(self, connection) -> str:
        """
        获取设备运行配置

        Args:
            connection: Netmiko 连接对象

        Returns:
            配置文本字符串
        """
        pass

    @abstractmethod
    def get_device_facts(self, connection) -> Dict[str, Any]:
        """
        获取设备基本信息

        Args:
            connection: Netmiko 连接对象

        Returns:
            包含 hostname, model, serial, version 等的字典
        """
        pass

    @abstractmethod
    def deploy_config_lines(
        self,
        connection,
        commands: List[str],
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        部署配置命令行

        Args:
            connection: Netmiko 连接对象
            commands: 配置命令列表
            dry_run: 是否为预演模式（不实际执行）

        Returns:
            {"success": bool, "output": str, "errors": list}
        """
        pass

    @abstractmethod
    def save_config(self, connection) -> bool:
        """
        保存配置到设备

        Args:
            connection: Netmiko 连接对象

        Returns:
            是否成功
        """
        pass

    @abstractmethod
    def get_interfaces(self, connection) -> List[Dict[str, Any]]:
        """
        获取接口信息

        Args:
            connection: Netmiko 连接对象

        Returns:
            接口信息列表
        """
        pass

    def parse_output(self, command: str, output: str) -> Optional[Dict]:
        """
        解析命令输出（使用 NTC-Templates）

        Args:
            command: 命令名称
            output: 原始输出

        Returns:
            解析后的结构化数据，或 None（解析失败）
        """
        try:
            from netmiko.utilities import get_structured_output
            # 使用 NTC-Templates 解析
            parsed = get_structured_output(
                output,
                command_string=command,
                platform=self.NETMIKO_DRIVER,
            )
            return parsed if parsed else None
        except Exception:
            return None

    def get_netmiko_device_type(self) -> str:
        """获取 Netmiko device_type"""
        return self.NETMIKO_DRIVER

    def supports_napalm(self) -> bool:
        """是否支持 NAPALM"""
        return self.NAPALM_DRIVER is not None

    def get_napalm_driver(self) -> Optional[str]:
        """获取 NAPALM driver 名称"""
        return self.NAPALM_DRIVER