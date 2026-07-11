"""
设备探测服务

提供设备预检功能：IP可达性测试、SSH连接测试、设备信息获取
"""

import re
import subprocess
import platform
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from loguru import logger

from app.shared.models import Device, CredentialGroup
from app.features.backups.netmiko_service import NetmikoService
from app.features.credentials.credential_service import decrypt_password
from app.features.devices.vendor_adapter import get_vendor_profile


class DeviceProbeService:
    """设备探测服务"""

    # 不支持SSH的设备类型
    SSH_UNSUPPORTED_TYPES = ['ap']
    # 需要特殊权限的设备类型
    SSH_SPECIAL_PERMISSION_TYPES = ['pa', 'ftd']

    def test_ip_reachability(self, ip: str) -> Dict[str, Any]:
        """测试IP可达性（ping测试）

        Args:
            ip: 设备IP地址

        Returns:
            {
                "reachable": bool,
                "latency_ms": int or None,
                "message": str
            }
        """
        result = {
            "reachable": False,
            "latency_ms": None,
            "message": ""
        }

        try:
            # 根据操作系统选择ping参数
            param = '-n' if platform.system().lower() == 'windows' else '-c'

            # 执行ping命令，只发送1个包
            command = ['ping', param, '1', '-W', '3', ip] if platform.system().lower() != 'windows' else ['ping', param, '1', '-w', '3000', ip]

            # Windows下参数不同
            if platform.system().lower() == 'windows':
                command = ['ping', '-n', '1', '-w', '3000', ip]

            output = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=5
            )

            # 解析ping输出
            if output.returncode == 0:
                result["reachable"] = True
                # 尝试解析延迟
                latency_match = re.search(r'time[=<>](\d+)', output.stdout, re.IGNORECASE)
                if latency_match:
                    result["latency_ms"] = int(latency_match.group(1))
                else:
                    # Windows格式
                    latency_match = re.search(r'平均[=](\d+)', output.stdout)
                    if latency_match:
                        result["latency_ms"] = int(latency_match.group(1))
                result["message"] = f"可达，延迟 {result['latency_ms']}ms" if result['latency_ms'] else "可达"
            else:
                result["message"] = "不可达：设备未响应ping请求"

        except subprocess.TimeoutExpired:
            result["message"] = "不可达：ping超时"
        except Exception as e:
            result["message"] = f"测试失败：{str(e)}"
            logger.error(f"Ping测试失败: {e}")

        return result

    def get_ssh_capability(self, device_type: str) -> Dict[str, Any]:
        """获取设备类型的SSH能力状态

        Args:
            device_type: 设备类型

        Returns:
            {
                "supported": bool,
                "special_permission": bool,
                "message": str
            }
        """
        if device_type in self.SSH_UNSUPPORTED_TYPES:
            return {
                "supported": False,
                "special_permission": False,
                "message": "公司策略AP未开启SSH，不支持远程连接测试"
            }

        if device_type in self.SSH_SPECIAL_PERMISSION_TYPES:
            return {
                "supported": True,
                "special_permission": True,
                "message": "防火墙需要GoVault权限才能SSH连接"
            }

        return {
            "supported": True,
            "special_permission": False,
            "message": ""
        }

    def test_ssh_connection(self, db: Session, ip: str, credential_group_name: str,
                            vendor: str = "cisco", device_type: str = None) -> Dict[str, Any]:
        """测试SSH连接

        Args:
            db: 数据库会话
            ip: 设备IP地址
            credential_group_name: 凭证组名称
            vendor: 设备厂商
            device_type: 设备类型（用于校验SSH能力）

        Returns:
            {
                "connected": bool,
                "message": str
            }
        """
        result = {
            "connected": False,
            "message": ""
        }

        # 校验设备类型SSH能力
        if device_type:
            ssh_cap = self.get_ssh_capability(device_type)
            if not ssh_cap["supported"]:
                return {
                    "connected": False,
                    "message": ssh_cap["message"]
                }
            if ssh_cap["special_permission"]:
                result["message"] = ssh_cap["message"] + " - "

        # 获取凭证组
        credential = db.query(CredentialGroup).filter(
            CredentialGroup.name == credential_group_name
        ).first()

        if not credential:
            return {
                "connected": False,
                "message": "凭证组不存在"
            }

        try:
            # 解密密码
            password = decrypt_password(credential.password_encrypted)
            secret = decrypt_password(credential.enable_password_encrypted) if credential.enable_password_encrypted else ""

            credentials = {
                "username": credential.username,
                "password": password,
                "secret": secret
            }

            # 创建临时设备对象用于连接
            temp_device = type('TempDevice', (), {
                'ip': ip,
                'name': f'temp_{ip}',
                'vendor': vendor
            })()

            # 尝试连接
            service = NetmikoService()
            service.connect(temp_device, credentials)
            service.disconnect()

            result["connected"] = True
            result["message"] = (result["message"] if result["message"] else "") + "SSH连接成功"

        except Exception as e:
            error_msg = str(e)
            result["message"] = (result["message"] if result["message"] else "") + f"SSH连接失败: {error_msg}"
            logger.error(f"SSH连接测试失败: {e}")

        return result

    def fetch_device_info(self, db: Session, ip: str, credential_group_name: str,
                          vendor: str = "cisco", device_type: str = None) -> Dict[str, Any]:
        """获取设备信息（通过SSH连接执行命令）

        Args:
            db: 数据库会话
            ip: 设备IP地址
            credential_group_name: 凭证组名称
            vendor: 设备厂商
            device_type: 设备类型

        Returns:
            {
                "success": bool,
                "model": str,
                "serial_number": str,
                "modules": list,
                "location": str,
                "message": str
            }
        """
        result = {
            "success": False,
            "model": "",
            "serial_number": "",
            "modules": [],
            "location": "",
            "message": ""
        }

        # 校验设备类型SSH能力
        if device_type:
            ssh_cap = self.get_ssh_capability(device_type)
            if not ssh_cap["supported"]:
                return {
                    "success": False,
                    "message": ssh_cap["message"]
                }

        # 获取凭证组
        credential = db.query(CredentialGroup).filter(
            CredentialGroup.name == credential_group_name
        ).first()

        if not credential:
            return {
                "success": False,
                "message": "凭证组不存在"
            }

        try:
            # 解密密码
            password = decrypt_password(credential.password_encrypted)
            secret = decrypt_password(credential.enable_password_encrypted) if credential.enable_password_encrypted else ""

            credentials = {
                "username": credential.username,
                "password": password,
                "secret": secret
            }

            # 创建临时设备对象
            temp_device = type('TempDevice', (), {
                'ip': ip,
                'name': f'temp_{ip}',
                'vendor': vendor
            })()

            # 连接设备
            service = NetmikoService()
            service.connect(temp_device, credentials)

            # 执行 show inventory
            inventory_output = service.connection.send_command("show inventory", read_timeout=30)
            inventory_info = self._parse_inventory(inventory_output, vendor)

            # 执行 show snmp location
            snmp_output = service.connection.send_command("show snmp location", read_timeout=10)
            location = self._parse_snmp_location(snmp_output, vendor)

            service.disconnect()

            result["success"] = True
            result["model"] = inventory_info.get("model", "")
            result["serial_number"] = inventory_info.get("serial_number", "")
            result["modules"] = inventory_info.get("modules", [])
            result["location"] = location
            result["message"] = "设备信息获取成功"

        except Exception as e:
            result["message"] = f"获取设备信息失败: {str(e)}"
            logger.error(f"获取设备信息失败: {e}")

        return result

    def _parse_inventory(self, output: str, vendor: str) -> Dict[str, Any]:
        """解析 show inventory 输出

        Args:
            output: 命令输出
            vendor: 设备厂商

        Returns:
            {
                "model": str,
                "serial_number": str,
                "modules": list
            }
        """
        result = {
            "model": "",
            "serial_number": "",
            "modules": []
        }

        if vendor.lower() == 'cisco':
            # Cisco IOS 格式解析
            # NAME: "c9300-24p", DESCR: "Catalyst 9300 24-port PoE+ Switch"
            # PID: C9300-24P, VID: V02, SN: FCX2345ABCDE

            lines = output.split('\n')
            modules = []
            first_module = True

            for line in lines:
                # 解析 NAME 和 DESCR 行
                name_match = re.search(r'NAME:\s*"([^"]+)"', line)
                descr_match = re.search(r'DESCR:\s*"([^"]+)"', line)

                # 解析 PID、VID、SN 行
                pid_match = re.search(r'PID:\s*(\S+)', line)
                vid_match = re.search(r'VID:\s*(\S+)', line)
                sn_match = re.search(r'SN:\s*(\S+)', line)

                if pid_match and sn_match:
                    pid = pid_match.group(1).rstrip(',')
                    sn = sn_match.group(1)

                    # 判断模块类型
                    module_type = "other"
                    name = name_match.group(1) if name_match else ""

                    if name:
                        if 'Power' in name or 'PWR' in pid:
                            module_type = "power"
                        elif 'Fan' in name or 'FAN' in pid:
                            module_type = "fan"
                        elif 'SFP' in name or 'Transceiver' in descr_match.group(1) if descr_match else False:
                            module_type = "sfp"
                        elif first_module:
                            module_type = "main"

                    module_info = {
                        "type": module_type,
                        "name": name,
                        "pid": pid,
                        "serial_number": sn
                    }
                    modules.append(module_info)

                    # 第一个模块作为主设备信息
                    if first_module:
                        result["model"] = pid
                        result["serial_number"] = sn
                        first_module = False

            # 转换为前端需要的格式（包含 pid 型号信息）
            result["modules"] = [
                {"type": m["type"], "pid": m.get("pid", ""), "serial_number": m["serial_number"]}
                for m in modules
            ]

        elif vendor.lower() == 'huawei' or vendor.lower() == 'h3c':
            # 华为/H3C 格式解析
            # 使用 display device 命令格式
            for line in output.split('\n'):
                sn_match = re.search(r'Serial\s*Number[:\s]+(\S+)', line, re.IGNORECASE)
                if sn_match and not result["serial_number"]:
                    result["serial_number"] = sn_match.group(1)

                model_match = re.search(r'Device\s*Type[:\s]+(\S+)', line, re.IGNORECASE)
                if model_match and not result["model"]:
                    result["model"] = model_match.group(1)

        return result

    def _parse_snmp_location(self, output: str, vendor: str) -> str:
        """解析 show snmp location 输出

        Args:
            output: 命令输出
            vendor: 设备厂商

        Returns:
            location 字符串
        """
        location = ""

        # Cisco 格式: SNMP location: 机房A-机架01
        match = re.search(r'SNMP\s*location[:\s]+(.+)$', output, re.IGNORECASE)
        if match:
            location = match.group(1).strip()

        # 华为/H3C 格式可能不同
        if not location and vendor.lower() in ['huawei', 'h3c']:
            match = re.search(r'Location[:\s]+(.+)$', output, re.IGNORECASE)
            if match:
                location = match.group(1).strip()

        return location


# 单例实例
_probe_service = None

def get_probe_service() -> DeviceProbeService:
    """获取探测服务实例"""
    global _probe_service
    if _probe_service is None:
        _probe_service = DeviceProbeService()
    return _probe_service