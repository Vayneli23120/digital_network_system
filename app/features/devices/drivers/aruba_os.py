"""
Aruba ArubaOS-Switch 驱动

支持 Aruba (原 HP ProCurve) ArubaOS-Switch 设备。
"""

from typing import List, Dict, Any

from app.features.devices.drivers.base import BaseDeviceDriver


class ArubaOSDriver(BaseDeviceDriver):
    """Aruba ArubaOS-Switch 驱动"""

    VENDOR = "aruba"
    OS_TYPES = ["aruba", "aruba_os", "aruba-os", "aruba_procurve", "procurve"]
    NETMIKO_DRIVER = "aruba_os"
    NAPALM_DRIVER = None  # NAPALM 不原生支持

    SUPPORTS_ENABLE_MODE = True
    SHOW_RUN_COMMAND = "show running-config"
    SAVE_CONFIG_COMMAND = "write memory"
    CONFIG_MODE_COMMAND = "configure terminal"
    EXIT_CONFIG_MODE = "end"

    def get_running_config(self, connection) -> str:
        """获取运行配置"""
        return connection.send_command(
            self.SHOW_RUN_COMMAND,
            read_timeout=60,
            expect_string=r"#"
        )

    def get_device_facts(self, connection) -> Dict[str, Any]:
        """获取设备基本信息"""
        output = connection.send_command("show version")
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
            output = connection.send_config_set(
                commands,
                enter_config_mode=True,
                exit_config_mode=True,
                delay_factor=2,
            )
            return {"success": True, "output": output}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def save_config(self, connection) -> bool:
        """保存配置"""
        try:
            output = connection.send_command(
                self.SAVE_CONFIG_COMMAND,
                expect_string=r"#"
            )
            return "error" not in output.lower()
        except Exception:
            return False

    def get_interfaces(self, connection) -> List[Dict[str, Any]]:
        """获取接口信息"""
        output = connection.send_command("show interfaces brief")
        return [{"raw": output}]