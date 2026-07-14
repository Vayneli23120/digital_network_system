"""
设备可达性监控服务 - 异步并发版本

企业级设备可达性监控，参考 Cisco DNA Center 设计：
- 分级探测：critical(15s) / normal(60s) / low(300s)
- 异步并发网络检测（ICMP/SSH）
- 串行化数据库写入（SQLite 兼容）
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
import asyncio
from loguru import logger
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.shared.database import get_db
from app.shared.models import Device
from app.shared.cache import cache


class ReachabilityMonitor:
    """企业级设备可达性监控服务 - 异步并发版本"""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self._running = False

        # 分级探测配置（间隔越短告警越快）
        self.tier_intervals = {
            "critical": 10,   # 核心设备 10 秒探测
            "normal": 30,     # 普通设备 30 秒探测
            "low": 120,       # 低优先级 120 秒探测
        }

        # 分级阈值（连续多少周期失败才判离线）
        # 单次探测内已有快速重试抑制误判，故可降低阈值加快告警
        self.tier_thresholds = {
            "critical": 3,    # 核心设备 3 个周期失败即告警（约 30s，抗瞬时抖动）
            "normal": 2,      # 普通设备 2 个周期（约 60s）
            "low": 2,         # 低优先级 2 个周期（约 240s）
        }

        # 单次探测内的 ICMP 快速重试次数（抑制单包丢失误判）
        self.icmp_retries = 5

        # 并发控制（网络检测）
        self.max_concurrency = 50

        # 数据库写入锁（使用线程锁，兼容 APScheduler 后台线程 + asyncio.run）
        import threading
        self._db_lock = threading.Lock()

        # 检测历史缓存（Redis 内存缓存）
        self._history_cache_prefix = "reachability_history:"

    def start(self):
        """启动监控服务 - 分级调度"""
        if self._running:
            logger.warning("Reachability monitor is already running")
            return

        try:
            # 分级注册探测任务
            for tier, interval in self.tier_intervals.items():
                self.scheduler.add_job(
                    lambda t=tier: asyncio.run(self._check_tier(t)),
                    trigger=IntervalTrigger(seconds=interval),
                    id=f'reachability_check_{tier}',
                    name=f'设备可达性检查-{tier}',
                    replace_existing=True
                )

            self.scheduler.start()
            self._running = True
            logger.info(f"Reachability monitor started with tiered intervals: {self.tier_intervals}")
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

    async def _check_tier(self, tier: str):
        """分级并发探测

        Args:
            tier: 监控分级 (critical/normal/low)
        """
        # 加载该分级的设备列表
        devices = self._load_devices_by_tier(tier)

        if not devices:
            logger.debug(f"No devices in tier {tier}")
            return

        logger.debug(f"Checking {len(devices)} devices in tier {tier}")

        # 并发网络检测
        sem = asyncio.Semaphore(self.max_concurrency)

        async def _detect_one(device_dict):
            async with sem:
                # 网络检测（并发）
                result = await asyncio.to_thread(self._detect_reachability, device_dict['ip'])
                return {
                    'id': device_dict['id'],
                    'name': device_dict['name'],
                    'tier': tier,
                    'result': result
                }

        # 并发执行网络检测
        detect_results = await asyncio.gather(*[_detect_one(d) for d in devices], return_exceptions=True)

        # 串行化数据库写入（SQLite 兼容）
        for detect_result in detect_results:
            if isinstance(detect_result, Exception):
                logger.error(f"Detection failed: {detect_result}")
                continue

            # 使用线程锁确保串行写入（兼容 APScheduler 后台线程）
            with self._db_lock:
                await asyncio.to_thread(self._update_device_status, detect_result)

        # 清除 Dashboard 缓存
        cache.invalidate_prefix("dashboard:")
        logger.info(f"Completed tier {tier} check for {len(devices)} devices")

    def _detect_reachability(self, ip: str) -> Dict[str, any]:
        """网络检测（ICMP + SSH），不涉及数据库

        Args:
            ip: 设备 IP

        Returns:
            检测结果字典
        """
        results = []

        # Layer 1: ICMP Ping（单次探测内快速重试，抑制单包丢失误判）
        ping_result = {'reachable': False, 'latency_ms': None}
        for attempt in range(max(1, self.icmp_retries)):
            ping_result = self._icmp_check(ip)
            if ping_result['reachable']:
                break
        results.append(('icmp', ping_result['reachable'], ping_result['latency_ms']))

        # Layer 2: SSH Port Check (如果 ICMP 失败)
        if not ping_result['reachable']:
            ssh_result = self._ssh_port_check(ip)
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

        return {
            'reachable': is_reachable,
            'latency_ms': best_latency,
            'method': best_method
        }

    def _update_device_status(self, detect_result: Dict):
        """更新设备状态（串行化，SQLite 兼容）

        Args:
            detect_result: 检测结果 {id, name, tier, result}
        """
        db = next(get_db())
        try:
            device = db.query(Device).filter(Device.id == detect_result['id']).first()
            if not device:
                logger.warning(f"Device {detect_result['id']} not found")
                return

            result = detect_result['result']
            tier = detect_result['tier']

            # 获取历史记录
            history = self._get_check_history(device.id)
            history.append(result['reachable'])

            # 保留最近10次记录
            if len(history) > 10:
                history = history[-10:]

            # 更新历史缓存
            self._update_check_history(device.id, history)

            # 使用分级阈值判定状态
            old_reachability = device.reachability
            new_reachability = self._determine_state(history, old_reachability, tier)

            # 更新设备状态
            device.reachability = new_reachability
            device.last_reachability_check = datetime.utcnow()
            device.reachability_latency_ms = result['latency_ms']
            device.reachability_method = result['method']

            db.commit()

            # 状态变化触发告警
            if old_reachability != new_reachability:
                self._trigger_state_change_alert(device, old_reachability, new_reachability)
                logger.info(
                    f"Device {device.name} reachability changed: {old_reachability} -> {new_reachability}"
                )
        except Exception as e:
            logger.error(f"Failed to update device {detect_result['name']}: {e}")
            db.rollback()
        finally:
            db.close()

    def _load_devices_by_tier(self, tier: str) -> List[Dict]:
        """加载指定分级的设备列表

        Args:
            tier: 监控分级

        Returns:
            设备信息列表 [{id, name, ip, monitor_tier}]
        """
        db = next(get_db())
        try:
            devices = db.query(Device).filter(
                Device.deployment_status == 'in-use',
                Device.ip.isnot(None),
                Device.monitor_tier == tier,
                Device.device_type != 'ap',   # AP 在线状态由所连交换机端口(CDP)判定，不做 ping/ssh 探测
            ).all()

            return [
                {
                    'id': d.id,
                    'name': d.name,
                    'ip': d.ip,
                    'monitor_tier': d.monitor_tier
                }
                for d in devices
            ]
        finally:
            db.close()

    def _icmp_check(self, ip: str, timeout: int = 2) -> Dict[str, any]:
        """ICMP Ping 检测"""
        try:
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
        """SSH TCP Port 检测"""
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
        """解析 Ping 输出的延迟"""
        try:
            if is_windows:
                match = re.search(r'time[=<](\d+)ms', output)
            else:
                match = re.search(r'time=(\d+\.?\d*)\s*ms', output)

            if match:
                latency = float(match.group(1))
                return int(latency)
            return None
        except Exception:
            return None

    def _get_check_history(self, device_id: int) -> List[bool]:
        """获取设备检测历史（从缓存）"""
        key = f"{self._history_cache_prefix}{device_id}"
        cached = cache.get(key)
        if cached:
            try:
                return cached if isinstance(cached, list) else []
            except Exception:
                return []
        return []

    def _update_check_history(self, device_id: int, history: List[bool]):
        """更新设备检测历史（缓存）"""
        key = f"{self._history_cache_prefix}{device_id}"
        # 缓存 1 小时
        cache.set(key, history, ttl=3600)

    def _determine_state(self, history: List[bool], current_state: str, tier: str = "normal") -> str:
        """基于历史记录和分级阈值判定最终状态

        Args:
            history: 历史检测结果列表
            current_state: 当前状态
            tier: 监控分级

        Returns:
            新状态: reachable / unreachable / unknown
        """
        if len(history) == 0:
            return current_state or 'unknown'

        # 使用分级阈值
        threshold = self.tier_thresholds.get(tier, 3)

        # 最近的结果
        recent = history[-threshold:] if len(history) >= threshold else history

        # 检查是否全部失败（判定 unreachable）
        if len(recent) >= threshold and all(not r for r in recent):
            return 'unreachable'

        # 检查是否有成功（判定 reachable）
        if recent[-1]:  # 最新一次成功
            return 'reachable'

        # 其他情况保持当前状态（避免误判）
        return current_state

    def _trigger_state_change_alert(self, device: Device, old_state: str, new_state: str):
        """状态变化触发告警"""
        self._upsert_incident_from_reachability(device, old_state, new_state)

        try:
            from app.services.notification_service import get_notification_service
            notification_service = get_notification_service()

            if new_state == 'unreachable':
                notification_service.notify_device_unreachable(
                    device_name=device.name,
                    ip=device.ip or 'N/A',
                    operator='自动监控'
                )
            elif new_state == 'reachable' and old_state == 'unreachable':
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
                "monitor_tier": device.monitor_tier or "normal",
                "old_state": old_state,
                "new_state": new_state,
                "latency_ms": device.reachability_latency_ms,
                "timestamp": datetime.utcnow().isoformat(),
            })
        except Exception as e:
            logger.error(f"Failed to push device status to WebSocket: {e}")

    def _upsert_incident_from_reachability(self, device: Device, old_state: str, new_state: str):
        """把设备可达性变化写入故障工单闭环"""
        if new_state not in ("unreachable", "reachable"):
            return
        if new_state == "reachable" and old_state != "unreachable":
            return

        db = next(get_db())
        try:
            from app.services.incident_automation import MonitorEvent, upsert_fault_from_monitor_event
            upsert_fault_from_monitor_event(db, MonitorEvent(
                source_type="reachability",
                event_type="device_recovered" if new_state == "reachable" else "device_unreachable",
                device_id=device.id,
                device_name=device.name,
                ip=device.ip,
                raw={
                    "old_state": old_state,
                    "new_state": new_state,
                    "latency_ms": device.reachability_latency_ms,
                    "monitor_tier": device.monitor_tier,
                },
            ))
        except Exception as e:
            logger.warning(f"设备可达性自动故障工单处理失败: {e}")
        finally:
            db.close()

    def _estimate_downtime(self, device: Device) -> Optional[int]:
        """估算设备离线时间（分钟）"""
        if device.last_reachability_check:
            delta = datetime.utcnow() - device.last_reachability_check
            return int(delta.total_seconds() / 60)
        return None

    def get_stats(self) -> Dict[str, any]:
        """获取监控服务统计信息"""
        return {
            "running": self._running,
            "tier_intervals": self.tier_intervals,
            "tier_thresholds": self.tier_thresholds,
            "max_concurrency": self.max_concurrency,
        }

    def check_now(self, tier: Optional[str] = None) -> Dict[str, any]:
        """立即触发一次检测（同步阻塞，用于测试/手动刷新）

        注意：内部使用 asyncio.run，必须在没有运行中事件循环的线程里调用
        （FastAPI 端点中请用 await asyncio.to_thread(monitor.check_now)）。

        Args:
            tier: 指定分级，None 表示全部分级

        Returns:
            各分级检测结果摘要
        """
        tiers = [tier] if tier else list(self.tier_intervals.keys())
        summary = {}
        for t in tiers:
            try:
                asyncio.run(self._check_tier(t))
                summary[t] = "ok"
            except Exception as e:
                summary[t] = f"error: {e}"
        return summary

    def diagnostics(self) -> Dict[str, any]:
        """监控诊断：列出被监控/被跳过的设备及当前状态，定位为何无告警。"""
        db = next(get_db())
        try:
            all_devices = db.query(Device).all()
            in_use = [d for d in all_devices if d.deployment_status == 'in-use' and d.ip]
            not_monitored = [d for d in all_devices if d.deployment_status != 'in-use' or not d.ip]

            tier_counts = {t: 0 for t in self.tier_intervals}
            invalid_tier = []
            for d in in_use:
                t = d.monitor_tier or 'normal'
                if t in tier_counts:
                    tier_counts[t] += 1
                else:
                    # 分级不在 critical/normal/low 之内 → 不会被任何定时任务检测
                    invalid_tier.append({"id": d.id, "name": d.name, "monitor_tier": d.monitor_tier})

            monitored = [
                {
                    "id": d.id,
                    "name": d.name,
                    "ip": d.ip,
                    "monitor_tier": d.monitor_tier or 'normal',
                    "reachability": d.reachability,
                    "last_check": d.last_reachability_check.isoformat() if d.last_reachability_check else None,
                    "check_history": self._get_check_history(d.id),
                }
                for d in in_use
            ]

            return {
                "running": self._running,
                "total_devices": len(all_devices),
                "monitored_count": len(in_use),
                "tier_counts": tier_counts,
                "invalid_tier_devices": invalid_tier,
                "not_monitored_count": len(not_monitored),
                "not_monitored_sample": [
                    {
                        "id": d.id,
                        "name": d.name,
                        "ip": d.ip,
                        "deployment_status": d.deployment_status,
                        "reason": "deployment_status 非 in-use" if d.deployment_status != 'in-use' else "缺少 IP",
                    }
                    for d in not_monitored[:30]
                ],
                "monitored_devices": monitored,
            }
        finally:
            db.close()


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