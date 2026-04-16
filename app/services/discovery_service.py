"""
设备自动发现服务

支持两种发现方式：
1. Ping Sweep - 扫描网段内活跃 IP
2. CDP Discovery - 通过 Cisco Discovery Protocol 发现邻居设备

依赖：需要 netmiko（已安装）
可选：nmap（用于更深入的扫描）
"""

import asyncio
import ipaddress
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

try:
    import netmiko
    NETMIKO_AVAILABLE = True
except ImportError:
    NETMIKO_AVAILABLE = False
    logger.warning("netmiko 未安装，CDP 发现功能将不可用")


@dataclass
class DiscoveredDevice:
    """发现的设备"""
    ip: str
    hostname: Optional[str] = None
    model: Optional[str] = None
    vendor: str = "Unknown"
    discovery_method: str = "ping"  # ping | cdp | nmap
    port: int = 22
    is_cisco: bool = False
    cdp_neighbors: List[Dict[str, str]] = None

    def __post_init__(self):
        if self.cdp_neighbors is None:
            self.cdp_neighbors = []


class DiscoveryService:
    """设备发现服务"""

    def __init__(self, timeout: float = 2.0, workers: int = 50):
        """
        Args:
            timeout: ping/connect 超时时间（秒）
            workers: 并发扫描线程数
        """
        self.timeout = timeout
        self.workers = workers

    def ping_host(self, ip: str) -> bool:
        """Ping 单个主机"""
        try:
            # 使用 socket 检测端口 22 是否开放（更快）
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((ip, 22))
            sock.close()
            return result == 0
        except (socket.timeout, socket.error, OSError):
            return False

    def ping_sweep(self, subnet: str) -> List[DiscoveredDevice]:
        """
        Ping sweep 网段发现活跃主机

        Args:
            subnet: CIDR 格式，如 "192.168.1.0/24"

        Returns:
            发现的设备列表
        """
        logger.info(f"开始 Ping Sweep: {subnet}")
        network = ipaddress.ip_network(subnet, strict=False)
        discovered = []

        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = {
                executor.submit(self.ping_host, str(ip)): ip
                for ip in network.hosts()
            }

            for future in as_completed(futures):
                ip = futures[future]
                try:
                    if future.result():
                        device = DiscoveredDevice(
                            ip=ip,
                            discovery_method="ping",
                            is_cisco=False  # 需要进一步识别
                        )
                        discovered.append(device)
                        logger.debug(f"发现活跃主机: {ip}")
                except Exception as e:
                    logger.debug(f"Ping {ip} 失败: {e}")

        logger.info(f"Ping Sweep 完成，发现 {len(discovered)} 台活跃主机")
        return discovered

    def tcp_connect_scan(self, ip: str, ports: List[int] = None) -> Dict[int, bool]:
        """
        TCP 连接扫描 - 检测多个端口

        Args:
            ip: 目标 IP
            ports: 端口列表，默认 [22, 23, 80, 443]

        Returns:
            {端口: 是否开放}
        """
        if ports is None:
            ports = [22, 23, 80, 443]

        results = {}
        for port in ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.timeout)
                results[port] = sock.connect_ex((ip, port)) == 0
                sock.close()
            except:
                results[port] = False
        return results

    def identify_cisco_device(self, ip: str, credentials: Dict[str, str]) -> Optional[DiscoveredDevice]:
        """
        尝试连接设备并识别是否为 Cisco 设备

        Args:
            ip: 设备 IP
            credentials: SSH 凭证 {username, password, secret}

        Returns:
            DiscoveredDevice 或 None
        """
        if not NETMIKO_AVAILABLE:
            return None

        try:
            conn = netmiko.ConnectHandler(
                device_type="cisco_ios",
                host=ip,
                username=credentials.get("username", "admin"),
                password=credentials.get("password", ""),
                secret=credentials.get("secret", ""),
                timeout=self.timeout,
                session_timeout=self.timeout,
            )
            conn.enable()

            # 获取设备信息
            hostname = conn.send_command("show run | include hostname", read_timeout=5)
            hostname = hostname.replace("hostname ", "").strip()

            version_output = conn.send_command("show version", read_timeout=5)

            # 简单识别 Cisco 设备
            is_cisco = "Cisco" in version_output or "IOS" in version_output

            # 提取型号
            model = "Unknown"
            for line in version_output.split("\n"):
                if "cisco" in line.lower():
                    parts = line.split()
                    if len(parts) >= 2:
                        model = parts[1]
                        break

            conn.disconnect()

            device = DiscoveredDevice(
                ip=ip,
                hostname=hostname,
                model=model,
                vendor="Cisco",
                discovery_method="netmiko",
                is_cisco=is_cisco,
                port=22
            )
            logger.info(f"识别为 Cisco 设备: {ip} ({hostname}, {model})")
            return device

        except Exception as e:
            logger.debug(f"无法识别 {ip}: {e}")
            return None

    def cdp_discover(self, ip: str, credentials: Dict[str, str]) -> List[DiscoveredDevice]:
        """
        使用 CDP (Cisco Discovery Protocol) 发现邻居设备

        Args:
            ip: Cisco 设备 IP
            credentials: SSH 凭证

        Returns:
            邻居设备列表
        """
        if not NETMIKO_AVAILABLE:
            return []

        neighbors = []
        try:
            conn = netmiko.ConnectHandler(
                device_type="cisco_ios",
                host=ip,
                username=credentials.get("username", "admin"),
                password=credentials.get("password", ""),
                secret=credentials.get("secret", ""),
                timeout=self.timeout,
                session_timeout=self.timeout,
            )
            conn.enable()

            # 获取 CDP 邻居
            cdp_output = conn.send_command("show cdp neighbors detail", read_timeout=10)

            # 解析 CDP 输出
            current_neighbor = {}
            for line in cdp_output.split("\n"):
                line = line.strip()

                if line.startswith("Device ID:"):
                    if current_neighbor:
                        neighbors.append(current_neighbor)
                    current_neighbor = {"device_id": line.replace("Device ID:", "").strip()}
                elif ":" in line and current_neighbor:
                    key, value = line.split(":", 1)
                    current_neighbor[key.strip().lower().replace(" ", "_")] = value.strip()

            if current_neighbor:
                neighbors.append(current_neighbor)

            conn.disconnect()
            logger.info(f"CDP 发现 {len(neighbors)} 个邻居: {ip}")

        except Exception as e:
            logger.debug(f"CDP 发现失败 {ip}: {e}")

        return neighbors

    def discover_subnet(
        self,
        subnet: str,
        credentials: Dict[str, str] = None,
        use_cdp: bool = False,
        use_nmap: bool = False
    ) -> List[DiscoveredDevice]:
        """
        综合发现：先 ping sweep，再识别 Cisco 设备，可选 CDP

        Args:
            subnet: CIDR 网段
            credentials: SSH 凭证（用于设备识别）
            use_cdp: 是否执行 CDP 发现
            use_nmap: 是否使用 nmap（需要安装）

        Returns:
            发现的所有设备
        """
        logger.info(f"开始网段发现: {subnet}")

        # Phase 1: Ping Sweep
        active_hosts = self.ping_sweep(subnet)
        logger.info(f"Phase 1 完成: {len(active_hosts)} 个活跃主机")

        if not active_hosts:
            return []

        # Phase 2: 识别 Cisco 设备（如果提供凭证）
        discovered_devices = []
        cdp_enabled_devices = []

        if credentials and NETMIKO_AVAILABLE:
            for host in active_hosts:
                device = self.identify_cisco_device(host.ip, credentials)
                if device:
                    discovered_devices.append(device)
                    if use_cdp:
                        cdp_enabled_devices.append(device)

            # Phase 3: CDP 发现
            if use_cdp:
                for device in cdp_enabled_devices:
                    neighbors = self.cdp_discover(device.ip, credentials)
                    device.cdp_neighbors = neighbors

        else:
            discovered_devices = active_hosts

        logger.info(f"发现完成: {len(discovered_devices)} 台设备")
        return discovered_devices


# =============================================================================
# 便捷函数
# =============================================================================

_discovery_service: Optional[DiscoveryService] = None


def get_discovery_service(timeout: float = 2.0, workers: int = 50) -> DiscoveryService:
    """获取全局 DiscoveryService 实例"""
    global _discovery_service
    if _discovery_service is None:
        _discovery_service = DiscoveryService(timeout=timeout, workers=workers)
    return _discovery_service


def quick_discovery(subnet: str) -> List[DiscoveredDevice]:
    """
    快速发现 - 仅 Ping Sweep（不需要凭证）

    Args:
        subnet: CIDR 格式

    Returns:
        发现的设备列表
    """
    service = get_discovery_service()
    return service.ping_sweep(subnet)
