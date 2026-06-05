"""
Cisco IOS/IOS-XE 驱动

支持标准 Cisco IOS 和 IOS-XE 设备。
"""

from typing import List, Dict, Any, Optional

from app.features.devices.drivers.base import BaseDeviceDriver


class CiscoIOSDriver(BaseDeviceDriver):
    """Cisco IOS/IOS-XE 驱动"""

    VENDOR = "cisco"
    OS_TYPES = ["cisco_ios", "cisco_iosxe", "ios", "iosxe", "cisco"]
    NETMIKO_DRIVER = "cisco_ios"
    NAPALM_DRIVER = "ios"

    SUPPORTS_ENABLE_MODE = True
    SHOW_RUN_COMMAND = "show running-config"
    SAVE_CONFIG_COMMAND = "write memory"
    CONFIG_MODE_COMMAND = "configure terminal"
    EXIT_CONFIG_MODE = "end"

    def get_running_config(self, connection) -> str:
        """获取运行配置"""
        output = connection.send_command(
            self.SHOW_RUN_COMMAND,
            read_timeout=60,
            expect_string=r"#"
        )
        return output

    def get_device_facts(self, connection) -> Dict[str, Any]:
        """获取设备基本信息"""
        version_output = connection.send_command("show version")
        hostname_output = connection.send_command("show running-config | include hostname")

        # 解析基本信息
        facts = {
            "raw_version": version_output,
            "hostname": self._parse_hostname(hostname_output),
        }

        # 使用 TextFSM 解析 show version
        parsed = self.parse_output("show version", version_output)
        if parsed:
            facts.update({
                "model": parsed.get("hardware", [""])[0] if parsed.get("hardware") else "",
                "serial": parsed.get("serial", [""])[0] if parsed.get("serial") else "",
                "version": parsed.get("version", [""])[0] if parsed.get("version") else "",
            })

        return facts

    def _parse_hostname(self, output: str) -> str:
        """解析 hostname"""
        for line in output.splitlines():
            if "hostname" in line.lower():
                parts = line.split()
                if len(parts) >= 2:
                    return parts[1]
        return ""

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
            # 进入配置模式，发送命令，退出配置模式
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
            output = connection.save_config()
            return "ok" in output.lower() or "saved" in output.lower()
        except Exception:
            try:
                output = connection.send_command(self.SAVE_CONFIG_COMMAND)
                return "ok" in output.lower() or "saved" in output.lower()
            except Exception:
                return False

    def get_interfaces(self, connection) -> List[Dict[str, Any]]:
        """获取接口信息"""
        output = connection.send_command("show interfaces")
        parsed = self.parse_output("show interfaces", output)
        return parsed if parsed else [{"raw": output}]


class CiscoNXOSDriver(BaseDeviceDriver):
    """Cisco NX-OS 驱动"""

    VENDOR = "cisco_nxos"
    OS_TYPES = ["cisco_nxos", "nxos", "nexus"]
    NETMIKO_DRIVER = "cisco_nxos"
    NAPALM_DRIVER = "nxos_ssh"

    SUPPORTS_ENABLE_MODE = False  # NX-OS 无 enable 模式
    SHOW_RUN_COMMAND = "show running-config"
    SAVE_CONFIG_COMMAND = "save running-config startup-config"
    CONFIG_MODE_COMMAND = "configure terminal"
    EXIT_CONFIG_MODE = "end"

    def get_running_config(self, connection) -> str:
        """获取运行配置"""
        return connection.send_command(
            self.SHOW_RUN_COMMAND,
            read_timeout=60,
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
            output = connection.send_config_set(commands)
            return {"success": True, "output": output}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def save_config(self, connection) -> bool:
        """保存配置"""
        try:
            output = connection.send_command(self.SAVE_CONFIG_COMMAND)
            return True
        except Exception:
            return False

    def get_interfaces(self, connection) -> List[Dict[str, Any]]:
        """获取接口信息"""
        output = connection.send_command("show interface brief")
        return [{"raw": output}]