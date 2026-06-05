"""
设备可达性监控服务

企业级设备可达性监控，参考 Cisco DNA Center 设计：
- ICMP Ping 检测（Layer 3）
- SSH TCP Port 检测（Layer 4）
- 状态判定逻辑（避免瞬时故障误判）
- 状态变化触发告警

部署状态 (deployment_status) 由用户手动管理
可达性状态 (reachability) 由本服务自动监控
"""

from datetime import datetime
from typing import Dict, Optional, List
import subprocess
import socket
import re
import platform
from loguru import logger
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.shared.database import get_db
from app.shared.models import Device
from app.shared.cache import cache


class ReachabilityMonitor:
    """企业级设备可达性监控服务"""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.check_interval = 300  # 5分钟
        self.failure_threshold = 3  # 连续3次失败判定离线
        self.success_threshold = 1  # 连续1次成功判定在线
        self._running = False

        # 检测历史缓存（Redis 内存缓存）
        # key: device_id, value: list of bool results
        self._history_cache_prefix = "reachability_history:"

    def start(self):
        """启动监控服务"""
        if self._running:
            logger.warning("Reachability monitor is already running")
            return

        try:
            self.scheduler.add_job(
                self.check_all_devices,
                trigger=IntervalTrigger(seconds=self.check_interval),
                id='reachability_check',
                name='设备可达性检查',
                replace_existing=True
            )
            self.scheduler.start()
            self._running = True
            logger.info(f"Reachability monitor started (interval: {self.check_interval}s)")
        except Exception as e:
            logger.error(f"Failed to start reachability monitor: {e}")

    def stop(self):
        """停止监控服务"""
        if not self._running:
            return

        try:
            self.scheduler.shutdown(wait=False)
            self._running = False
            logger.info("Reachability monitor stopped")
        except Exception as e:
            logger.error(f"Failed to stop reachability monitor: {e}")

    def check_all_devices(self):
        """批量检查所有 in-use 设备"""
        db = next(get_db())

        try:
            # 只检查已部署的设备
            devices = db.query(Device).filter(
                Device.deployment_status == 'in-use',
                Device.ip.isnot(None)
            ).all()

            logger.debug(f"Checking reachability for {len(devices)} devices")

            for device in devices:
                try:
                    self.check_device_reachability(db, device)
                except Exception as e:
                    logger.error(f"Check failed for {device.name}: {e}")

            # 清除 Dashboard 缓存
            cache.invalidate_prefix("dashboard:")

        except Exception as e:
            logger.error(f"Reachability check batch failed: {e}")
        finally:
            db.close()

    def check_device_reachability(self, db, device: Device) -> Dict[str, any]:
        """检查单个设备可达性

        Args:
            db: 数据库会话
            device: 设备对象

        Returns:
            检测结果字典
        """
        if not device.ip:
            logger.warning(f"Device {device.name} has no IP address")
            return {"reachable": False, "reason": "no_ip"}

        # 多层次检测
        results = []

        # Layer 1: ICMP Ping
        ping_result = self._icmp_check(device.ip)
        results.append(('icmp', ping_result['reachable'], ping_result['latency_ms']))

        # Layer 2: SSH Port Check (如果 ICMP 失败)
        if not ping_result['reachable']:
            ssh_result = self._ssh_port_check(device.ip)
            results.append(('ssh', ssh_result['reachable'], ssh_result['latency_ms']))

        # 综合判定
        is_reachable = any(r[1] for r in results)
        best_latency = min(
            (r[2] for r in results if r[1] and r[2] is not None),
            default=None
        )
        best_method = next(
            (r[0] for r in results if r[1]),
            None
        )

        # 获取历史记录
        history = self._get_check_history(device.id)

        # 添加当前结果到历史
        history.append(is_reachable)

        # 保留最近10次记录
        if len(history) > 10:
            history = history[-10:]

        # 更新历史缓存
        self._update_check_history(device.id, history)

        # 状态判定
        old_reachability = device.reachability
        new_reachability = self._determine_state(history, old_reachability)

        # 更新设备状态
        device.reachability = new_reachability
        device.last_reachability_check = datetime.utcnow()
        device.reachability_latency_ms = best_latency
        device.reachability_method = best_method

        db.commit()

        # 状态变化触发告警
        if old_reachability != new_reachability:
            self._trigger_state_change_alert(device, old_reachability, new_reachability)
            logger.info(
                f"Device {device.name} reachability changed: {old_reachability} -> {new_reachability}"
            )

        return {
            "device_id": device.id,
            "device_name": device.name,
            "ip": device.ip,
            "reachable": is_reachable,
            "reachability": new_reachability,
            "latency_ms": best_latency,
            "method": best_method,
            "history_length": len(history)
        }

    def _icmp_check(self, ip: str, timeout: int = 2) -> Dict[str, any]:
        """ICMP Ping 检测

        Args:
            ip: 设备 IP 地址
            timeout: 超时时间（秒）

        Returns:
            {"reachable": bool, "latency_ms": int or None}
        """
        try:
            # Windows 使用 -n, Linux/Mac 使用 -c
            is_windows = platform.system().lower() == 'windows'

            if is_windows:
                cmd = ['ping', '-n', '1', '-w', str(timeout * 1000), ip]
            else:
                cmd = ['ping', '-c', '1', '-W', str(timeout), ip]

            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=timeout + 2,
                text=True
            )

            if result.returncode == 0:
                # 解析延迟
                latency = self._parse_ping_latency(result.stdout, is_windows)
                return {'reachable': True, 'latency_ms': latency}
            else:
                return {'reachable': False, 'latency_ms': None}

        except subprocess.TimeoutExpired:
            return {'reachable': False, 'latency_ms': None}
        except Exception as e:
            logger.debug(f"ICMP check failed for {ip}: {e}")
            return {'reachable': False, 'latency_ms': None}

    def _ssh_port_check(self, ip: str, port: int = 22, timeout: int = 3) -> Dict[str, any]:
        """SSH TCP Port 检测

        Args:
            ip: 设备 IP 地址
            port: SSH 端口
            timeout: 超时时间（秒）

        Returns:
            {"reachable": bool, "latency_ms": int or None}
        """
        try:
            start = datetime.utcnow()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            end = datetime.utcnow()

            latency = int((end - start).total_seconds() * 1000)
            sock.close()

            if result == 0:
                return {'reachable': True, 'latency_ms': latency}
            else:
                return {'reachable': False, 'latency_ms': None}

        except socket.timeout:
            return {'reachable': False, 'latency_ms': None}
        except socket.error as e:
            logger.debug(f"SSH port check failed for {ip}: {e}")
            return {'reachable': False, 'latency_ms': None}
        except Exception as e:
            logger.debug(f"SSH port check exception for {ip}: {e}")
            return {'reachable': False, 'latency_ms': None}

    def _parse_ping_latency(self, output: str, is_windows: bool = False) -> Optional[int]:
        """解析 Ping 输出的延迟

        Args:
            output: Ping 命令输出
            is_windows: 是否是 Windows 系统

        Returns:
            延迟毫秒数，解析失败返回 None
        """
        try:
            if is_windows:
                # Windows: "Reply from 192.168.1.1: bytes=32 time=1ms TTL=64"
                match = re.search(r'time[=<](\d+)ms', output)
            else:
                # Linux: "time=1.23 ms"
                match = re.search(r'time=(\d+\.?\d*)\s*ms', output)

            if match:
                latency = float(match.group(1))
                return int(latency)
            return None
        except Exception:
            return None

    def _get_check_history(self, device_id: int) -> List[bool]:
        """获取设备检测历史（从缓存）

        Args:
            device_id: 设备 ID

        Returns:
            历史检测结果列表 [True, False, ...]
        """
        key = f"{self._history_cache_prefix}{device_id}"
        cached = cache.get(key)
        if cached:
            try:
                return cached if isinstance(cached, list) else []
            except Exception:
                return []
        return []

    def _update_check_history(self, device_id: int, history: List[bool]):
        """更新设备检测历史（缓存）

        Args:
            device_id: 设备 ID
            history: 历史检测结果列表
        """
        key = f"{self._history_cache_prefix}{device_id}"
        # 缓存 1 小时
        cache.set(key, history, ttl=3600)

    def _determine_state(self, history: List[bool], current_state: str) -> str:
        """基于历史记录判定最终状态

        Args:
            history: 历史检测结果列表
            current_state: 当前状态

        Returns:
            新状态: reachable / unreachable / unknown
        """
        if len(history) == 0:
            return current_state or 'unknown'

        # 最近的结果
        recent = history[-self.failure_threshold:] if len(history) >= self.failure_threshold else history

        # 检查是否全部失败（判定 unreachable）
        if len(recent) >= self.failure_threshold and all(not r for r in recent):
            return 'unreachable'

        # 检查是否有成功（判定 reachable）
        if recent[-1]:  # 最新一次成功
            return 'reachable'

        # 其他情况保持当前状态（避免误判）
        return current_state

    def _trigger_state_change_alert(self, device: Device, old_state: str, new_state: str):
        """状态变化触发告警

        Args:
            device: 设备对象
            old_state: 旧状态
            new_state: 新状态
        """
        try:
            from app.services.notification_service import get_notification_service
            notification_service = get_notification_service()

            if new_state == 'unreachable':
                # 设备离线告警
                notification_service.notify_device_unreachable(
                    device_name=device.name,
                    ip=device.ip or 'N/A',
                    operator='自动监控'
                )
            elif new_state == 'reachable' and old_state == 'unreachable':
                # 设备恢复通知
                notification_service.notify_device_recovered(
                    device_name=device.name,
                    ip=device.ip or 'N/A',
                    downtime=self._estimate_downtime(device)
                )
        except Exception as e:
            logger.error(f"Failed to send reachability alert: {e}")

        # 推送实时状态变化到 WebSocket 前端（监控大屏立即感知）
        try:
            from app.features.websocket.router import broadcast_device_status_sync
            broadcast_device_status_sync({
                "event": "device_status_change",
                "device_id": device.id,
                "device_name": device.name,
                "ip": device.ip or "",
                "location": device.location or "",
                "device_type": device.device_type or "switch",
                "old_state": old_state,
                "new_state": new_state,
                "latency_ms": device.reachability_latency_ms,
                "timestamp": datetime.utcnow().isoformat(),
            })
        except Exception as e:
            logger.error(f"Failed to push device status to WebSocket: {e}")

    def _estimate_downtime(self, device: Device) -> Optional[int]:
        """估算设备离线时间（分钟）

        Args:
            device: 设备对象

        Returns:
            离线时间（分钟），无法估算返回 None
        """
        if device.last_reachability_check:
            delta = datetime.utcnow() - device.last_reachability_check
            return int(delta.total_seconds() / 60)
        return None

    def get_stats(self) -> Dict[str, any]:
        """获取监控服务统计信息

        Returns:
            统计信息字典
        """
        return {
            "running": self._running,
            "check_interval": self.check_interval,
            "failure_threshold": self.failure_threshold,
            "success_threshold": self.success_threshold,
        }


# 全局服务实例
_reachability_monitor: Optional[ReachabilityMonitor] = None


def get_reachability_monitor() -> ReachabilityMonitor:
    """获取可达性监控服务实例"""
    global _reachability_monitor
    if _reachability_monitor is None:
        _reachability_monitor = ReachabilityMonitor()
    return _reachability_monitor


def start_reachability_monitor():
    """启动可达性监控服务"""
    monitor = get_reachability_monitor()
    monitor.start()
    return monitor


def stop_reachability_monitor():
    """停止可达性监控服务"""
    if _reachability_monitor:
        _reachability_monitor.stop()