"""
Huawei VRP 驱动

支持华为 VRP (Versatile Routing Platform) 设备。
"""

from typing import List, Dict, Any

from app.features.devices.drivers.base import BaseDeviceDriver


class HuaweiVRPDriver(BaseDeviceDriver):
    """Huawei VRP 驱动"""

    VENDOR = "huawei"
    OS_TYPES = ["huawei", "huawei_vrp", "vrp", "huawei_vrpv8", "huawei_vrpv5"]
    NETMIKO_DRIVER = "huawei"
    NAPALM_DRIVER = "huawei"  # 社区版支持

    SUPPORTS_ENABLE_MODE = False  # Huawei 无 enable 模式
    SHOW_RUN_COMMAND = "display current-configuration"
    SAVE_CONFIG_COMMAND = "save"
    CONFIG_MODE_COMMAND = "system-view"
    EXIT_CONFIG_MODE = "return"

    def get_running_config(self, connection) -> str:
        """获取运行配置"""
        return connection.send_command(
            self.SHOW_RUN_COMMAND,
            read_timeout=90,  # Huawei 配置可能较长
        )

    def get_device_facts(self, connection) -> Dict[str, Any]:
        """获取设备基本信息"""
        output = connection.send_command("display version")
        return {"raw_version": output}

    def deploy_config_lines(
        self,
        connection,
        commands: List[str],
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """部署配置"""
        if dry_run:
            return {"success": True, "dry_run": True, "commands": commands}

        try:
            # Huawei 需要先进入 system-view
            output = connection.send_config_set(
                commands,
                enter_config_mode=True,
                exit_config_mode=True,
            )
            return {"success": True, "output": output}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def save_config(self, connection) -> bool:
        """保存配置"""
        try:
            # Huawei save 命令可能需要确认
            output = connection.send_command_timing(
                self.SAVE_CONFIG_COMMAND,
                delay_factor=2,
            )
            # 可能需要回答 "y" 确认
            if "confirm" in output.lower() or "yes" in output.lower():
                output += connection.send_command_timing("y")
            return "success" in output.lower() or "saved" in output.lower()
        except Exception:
            return False

    def get_interfaces(self, connection) -> List[Dict[str, Any]]:
        """获取接口信息"""
        output = connection.send_command("display interface brief")
        return [{"raw": output}]