"""
Fortinet FortiOS 驱动

支持 Fortinet FortiGate 防火墙设备。

注意：FortiOS 使用层级式配置结构，不同于 Cisco 的平面式。
"""

from typing import List, Dict, Any

from app.features.devices.drivers.base import BaseDeviceDriver


class FortinetDriver(BaseDeviceDriver):
    """Fortinet FortiOS 驱动"""

    VENDOR = "fortinet"
    OS_TYPES = ["fortinet", "fortigate", "fortios"]
    NETMIKO_DRIVER = "fortinet"
    NAPALM_DRIVER = None  # NAPALM 不原生支持

    SUPPORTS_ENABLE_MODE = False  # FortiOS 无 enable 模式
    SHOW_RUN_COMMAND = "show full-configuration"
    SAVE_CONFIG_COMMAND = "execute cfg save"
    # FortiOS 按资源路径进入配置，无通用 configure terminal
    CONFIG_MODE_COMMAND = ""
    EXIT_CONFIG_MODE = "end"

    def get_running_config(self, connection) -> str:
        """获取运行配置"""
        # FortiOS show full-configuration 可能很长，使用更长超时
        return connection.send_command(
            self.SHOW_RUN_COMMAND,
            read_timeout=120,
            max_loops=1000,
        )

    def get_device_facts(self, connection) -> Dict[str, Any]:
        """获取设备基本信息"""
        output = connection.send_command("get system status")
        return {"raw_status": output}

    def deploy_config_lines(
        self,
        connection,
        commands: List[str],
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        部署配置

        注意：FortiOS 使用层级式配置结构（config ... set ... end），
        直接发送命令列表可能无法正确进入/退出配置上下文。
        实际部署时建议使用配置脚本方式。
        """
        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "commands": commands,
                "warning": "FortiOS 配置部署需要仔细检查层级结构"
            }

        try:
            outputs = []
            for cmd in commands:
                output = connection.send_command_timing(
                    cmd,
                    delay_factor=2,
                )
                outputs.append(output)
            return {"success": True, "output": "\n".join(outputs)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def save_config(self, connection) -> bool:
        """保存配置"""
        try:
            output = connection.send_command_timing(self.SAVE_CONFIG_COMMAND)
            # FortiOS 自动保存
            return True
        except Exception:
            return False

    def get_interfaces(self, connection) -> List[Dict[str, Any]]:
        """获取接口信息"""
        output = connection.send_command("get system interface physical")
        return [{"raw": output}]