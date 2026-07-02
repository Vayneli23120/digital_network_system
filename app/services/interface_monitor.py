"""
接口监控服务 - SNMP 轮询接口状态与流量（阶段 A）

职责：
- 周期性轮询"已启用 SNMP 且有被监控接口"的设备
- 读取 ifOperStatus / ifHCInOctets / ifHCOutOctets / ifHighSpeed / 错误计数
- 计算入/出向 bps 与利用率，写入 device_interfaces（最近值）+ interface_traffic_samples（时序）
- 接口 oper_status 变化时通过 WebSocket 推送（复用大屏告警通道）

接口发现（discover_interfaces）由 API 触发，walk ifName/ifDescr 落库，
供用户手动标记 is_uplink / monitored。

SNMP 传输复用现有 app.features.devices.snmp_service（puresnmp，API 稳定）。
"""

import asyncio
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import func

from app.shared.database import get_db
from app.shared.models import Device, DeviceInterface, InterfaceTrafficSample
from app.features.devices.snmp_service import get_snmp_service, SNMP_AVAILABLE

# ===== 标准 IF-MIB OID（列前缀，walk 返回 {ifIndex: value}）=====
OID_IF_DESCR = "1.3.6.1.2.1.2.2.1.2"
OID_IF_ADMIN_STATUS = "1.3.6.1.2.1.2.2.1.7"
OID_IF_OPER_STATUS = "1.3.6.1.2.1.2.2.1.8"
OID_IF_IN_ERRORS = "1.3.6.1.2.1.2.2.1.14"
OID_IF_OUT_ERRORS = "1.3.6.1.2.1.2.2.1.20"
OID_IF_NAME = "1.3.6.1.2.1.31.1.1.1.1"
OID_IF_HC_IN_OCTETS = "1.3.6.1.2.1.31.1.1.1.6"
OID_IF_HC_OUT_OCTETS = "1.3.6.1.2.1.31.1.1.1.10"
OID_IF_HIGH_SPEED = "1.3.6.1.2.1.31.1.1.1.15"   # Mbps
OID_IF_SPEED = "1.3.6.1.2.1.2.2.1.5"            # bits/s（32位，ifHighSpeed 为 0 时回退）
OID_IF_IN_OCTETS = "1.3.6.1.2.1.2.2.1.10"       # 32位入向字节（无 HC 计数器时回退）
OID_IF_OUT_OCTETS = "1.3.6.1.2.1.2.2.1.16"      # 32位出向字节（无 HC 计数器时回退）

# ===== CISCO-CDP-MIB cdpCacheTable（索引 = ifIndex.deviceIndex）=====
OID_CDP_ADDRESS = "1.3.6.1.4.1.9.9.23.1.2.1.1.4"     # cdpCacheAddress（对端 IP）
OID_CDP_DEVICE_ID = "1.3.6.1.4.1.9.9.23.1.2.1.1.6"   # cdpCacheDeviceId（对端主机名）
OID_CDP_DEVICE_PORT = "1.3.6.1.4.1.9.9.23.1.2.1.1.7"  # cdpCacheDevicePort（对端端口名）
OID_CDP_PLATFORM = "1.3.6.1.4.1.9.9.23.1.2.1.1.8"    # cdpCachePlatform（对端型号）

# ===== LLDP-MIB（标准，覆盖非 Cisco）=====
# lldpRemTable 索引 = lldpRemTimeMark.lldpRemLocalPortNum.lldpRemIndex
OID_LLDP_REM_PORT_ID = "1.0.8802.1.1.2.1.4.1.1.7"     # lldpRemPortId（对端端口）
OID_LLDP_REM_PORT_DESC = "1.0.8802.1.1.2.1.4.1.1.8"   # lldpRemPortDesc
OID_LLDP_REM_SYS_NAME = "1.0.8802.1.1.2.1.4.1.1.9"    # lldpRemSysName（对端主机名）
OID_LLDP_REM_SYS_DESC = "1.0.8802.1.1.2.1.4.1.1.10"   # lldpRemSysDesc（对端描述/型号）
# lldpLocPortTable 索引 = lldpLocPortNum；lldpLocPortId 通常即本地端口名
OID_LLDP_LOC_PORT_ID = "1.0.8802.1.1.2.1.3.7.1.3"     # lldpLocPortId
OID_LLDP_LOC_PORT_DESC = "1.0.8802.1.1.2.1.3.7.1.4"   # lldpLocPortDesc

COUNTER64_MAX = 2 ** 64

# 设备层级排名：数值越大越靠核心；对端排名 >= 本端排名 → 该接口判为上行口。
# 等级相同也算上行候选，用于接入交换机下挂第三级接入交换机的场景。
DEVICE_TIER_RANK = {
    "firewall": 100,
    "router": 95,
    "core_switch": 90,
    "server_switch": 70,
    "wlc": 60,
    "office_switch": 50,
    "switch": 50,
    "uce": 30,
    "ap": 20,
}


def _tier_rank(device_type: Optional[str]) -> int:
    return DEVICE_TIER_RANK.get((device_type or "").lower(), 40)


def _decode_str(v) -> str:
    """OctetString → str（保留可读文本）"""
    if v is None:
        return ""
    if isinstance(v, (bytes, bytearray)):
        return bytes(v).decode("utf-8", "ignore").strip()
    return str(v).strip()


def _decode_ip(v) -> str:
    """cdpCacheAddress → 点分 IP（puresnmp 可能给 bytes/IPv4Address/str）"""
    if v is None:
        return ""
    if isinstance(v, (bytes, bytearray)):
        b = bytes(v)
        if len(b) == 4:
            return ".".join(str(x) for x in b)
        # 兼容十六进制字符串形式
        if len(b) == 8:
            try:
                return ".".join(str(int(b[i:i + 2], 16)) for i in range(0, 8, 2))
            except ValueError:
                return ""
        return ""
    s = str(v).strip()
    return s


def _cdp_local_ifindex(suffix: str) -> Optional[int]:
    """cdpCache 索引 'ifIndex.deviceIndex' → 本地 ifIndex"""
    if not suffix:
        return None
    head = suffix.lstrip(".").split(".")[0]
    try:
        return int(head)
    except ValueError:
        return None


def _lldp_local_portnum(suffix: str) -> Optional[int]:
    """lldpRem 索引 'timeMark.localPortNum.remIndex' → 本地 portNum"""
    if not suffix:
        return None
    parts = suffix.lstrip(".").split(".")
    if len(parts) < 2:
        return None
    try:
        return int(parts[1])
    except ValueError:
        return None



def oper_status_text(raw) -> str:
    """ifOperStatus 数值转文本：1=up 2=down 3=testing"""
    try:
        v = int(str(raw).strip())
    except (ValueError, TypeError):
        return "unknown"
    return {1: "up", 2: "down", 3: "testing"}.get(v, "unknown")


def snmp_available() -> bool:
    return SNMP_AVAILABLE


class InterfaceMonitor:
    """SNMP 接口状态/流量轮询服务"""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self._running = False
        self.tick_interval = 15          # 调度心跳（秒），每 15s 检查一次到期设备
        self.device_timeout = 25         # 单台设备采集超时（秒）
        self.retry_interval = 15         # 单台采集失败后快速重试，避免一次慢响应放大成数分钟延迟
        self.max_concurrency = 30        # 并发采集设备数
        self.snmp_timeout = 8
        self._db_lock = threading.Lock()
        # 分级采集调度表：每台设备独立周期，到期才 poll，不再一次 poll 全部
        self._schedule: Dict[int, float] = {}           # device_id → next_poll_at (time.time)
        self._inflight: Dict[int, float] = {}           # device_id → poll_started_at
        self._schedule_lock = threading.Lock()
        # 看门狗：防止 asyncio 超时因同步 IO 阻塞而失效
        # 改用计数器 + 上限，避免 FD 泄漏的同时不导致采集停滞
        self._detached_count = 0          # 当前被看门狗分离的线程数
        self._max_detached = 2            # 最多允许多少个分离线程存活
        self._stuck_since: float = 0      # 连续 stuck 开始时间戳，用于看门狗强制复位
        self._stuck_warned: bool = False  # 避免重复日志

    # ===== 生命周期 =====
    def start(self):
        if self._running:
            logger.warning("Interface monitor already running")
            return
        if not SNMP_AVAILABLE:
            logger.warning("SNMP 库不可用（puresnmp 未安装），接口监控服务未启动")
            return
        try:
            self.scheduler.add_job(
                self._tick_with_watchdog,
                trigger=IntervalTrigger(seconds=self.tick_interval),
                id="interface_poll",
                name="SNMP接口轮询",
                replace_existing=True,
                max_instances=5,  # asyncio.run() 可能挂起，允许后续 tick 覆盖
            )
            self.scheduler.start()
            self._running = True
            logger.info(f"Interface monitor started (tick={self.tick_interval}s, concurrency={self.max_concurrency})")
        except Exception as e:
            logger.error(f"Failed to start interface monitor: {e}")

    def stop(self):
        if not self._running:
            return
        try:
            self.scheduler.shutdown(wait=False)
            self._running = False
            logger.info("Interface monitor stopped")
        except Exception as e:
            logger.error(f"Failed to stop interface monitor: {e}")

    # ===== 看门狗（解决 asyncio 超时不可靠的问题）=====

    def _tick_with_watchdog(self):
        """在独立线程中运行 _tick，用 threading 超时保底。

        限制最大 detached 线程数，确保：
        - 不会因同步 IO 阻塞导致调度器卡死
        - 不会无限泄漏 FD（上限 _max_detached 个分离线程）
        - 即使线程挂死，后续 tick 仍能继续尝试采集
        """
        with self._schedule_lock:
            if self._detached_count >= self._max_detached:
                now = time.time()
                if self._stuck_since == 0:
                    self._stuck_since = now
                elif now - self._stuck_since > 120:  # 连续 stuck 超过 2 分钟则强制复位
                    logger.warning(
                        f"Interface tick stuck for {now - self._stuck_since:.0f}s, "
                        f"force resetting _detached_count ({self._detached_count} -> 0)"
                    )
                    self._detached_count = 0
                    self._stuck_since = 0
                    self._stuck_warned = False
                    # 复位后这次 tick 也跳过（让旧线程有时间彻底退出）
                    return
                if not self._stuck_warned:
                    logger.debug(
                        f"Too many detached threads ({self._detached_count}), tick skipped"
                    )
                    self._stuck_warned = True
                return
            self._stuck_since = 0
            self._stuck_warned = False
            self._detached_count += 1
        try:
            t = threading.Thread(target=self._run_tick_in_thread, daemon=True)
            t.start()
            t.join(timeout=self.tick_interval * 4)  # 最多等 60s，asyncio.run() 挂起也不阻塞
            with self._schedule_lock:
                self._detached_count = max(0, self._detached_count - 1)
            if t.is_alive():
                logger.warning(
                    f"Tick watchdog: asyncio.run() still alive after "
                    f"{self.tick_interval * 4}s (daemon thread detached)"
                )
        except Exception as e:
            logger.error(f"Tick watchdog failed: {e}")
            with self._schedule_lock:
                self._detached_count = max(0, self._detached_count - 1)

    def _run_tick_in_thread(self):
        """在独立线程中运行 _tick，完成后自动复位 _detached_count。"""
        try:
            asyncio.run(self._tick())
        except Exception as e:
            logger.error(f"Tick thread failed: {e}")

    # ===== 分级采集 =====

    def _get_device_interval(self, device_type: Optional[str]) -> int:
        """根据设备角色返回采集间隔（秒）"""
        rank = DEVICE_TIER_RANK.get((device_type or "").lower(), 40)
        if rank >= 90:
            return 30     # 核心设备：firewall / router / core_switch
        return 60         # 其他 monitored 接口：保持 60s 内刷新，避免健康面板天然 lagging

    def _claim_due_targets(self, targets: List[Dict]) -> List[Dict]:
        """认领本轮要采集的设备，避免重叠 tick 重复采同一台设备。"""
        now = time.time()
        stale_started_before = now - max(self.device_timeout * 2, 60)
        with self._schedule_lock:
            target_ids = {target["id"] for target in targets}
            for device_id in list(self._schedule.keys()):
                if device_id not in target_ids:
                    self._schedule.pop(device_id, None)
            for device_id, started_at in list(self._inflight.items()):
                if device_id not in target_ids or started_at < stale_started_before:
                    self._inflight.pop(device_id, None)

            due = []
            for target in targets:
                device_id = target["id"]
                if device_id in self._inflight:
                    continue
                if self._schedule.get(device_id, 0) <= now:
                    due.append(target)

            due.sort(key=lambda target: (self._schedule.get(target["id"], 0), target["id"]))
            selected = due[:self.max_concurrency]
            for target in selected:
                self._inflight[target["id"]] = now
            return selected

    def _finish_target_poll(self, target: Dict, success: bool, keep_inflight: bool = False):
        interval = self._get_device_interval(target.get("device_type", "")) if success else self.retry_interval
        with self._schedule_lock:
            self._schedule[target["id"]] = time.time() + interval
            if not keep_inflight:
                self._inflight.pop(target["id"], None)

    async def _tick(self):
        """分级采集调度心跳。

        不一次 poll 全部设备，而是按角色分配独立采集频率：
        - critical (90+ 分) → 30s  防火墙/路由器/核心交换机
        - other monitored → 60s  其他被监控接口

        用 asyncio.wait 替代 wait_for，避免 CancelledError 被
        内层 return_exceptions=True gather 吞掉导致无法超时。
        """
        targets = self._load_targets()
        if not targets:
            return

        due = self._claim_due_targets(targets)

        if not due:
            return

        async def poll_one(target):
            try:
                return await asyncio.wait_for(
                    self._poll_device(target),
                    timeout=self.device_timeout,
                )
            except asyncio.TimeoutError:
                logger.warning(f"Device {target['name']} ({target['ip']}) poll timed out after {self.device_timeout}s")
                return False
            except Exception as e:
                logger.error(f"Poll device {target['name']} failed: {e}")
                return False

        # 用 asyncio.wait 替代 gather，确保超时后不会因 CancelledError
        # 被内层 return_exceptions=True 吞掉而卡死。
        # 调度表更新在 wait 返回后统一执行，避免 cancelled task 的 finally
        # 因 CancelledError 被 swallow 而延迟执行。
        task_map = {asyncio.create_task(poll_one(t)): t for t in due}
        done, pending = await asyncio.wait(
            task_map.keys(),
            timeout=self.device_timeout + 2,
        )
        cancelled_done = set()
        still_pending = set(pending)
        for t in pending:
            t.cancel()
        if pending:
            cancelled_done, still_pending = await asyncio.wait(pending, timeout=1)

        success_count = 0
        # 收集异常（仅 done 的任务需要检查）
        for t in done:
            success = False
            try:
                success = bool(t.result())
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            except Exception as e:
                logger.error(f"Device poll raised: {e}")
            if success:
                success_count += 1
            self._finish_target_poll(task_map[t], success)

        for t in cancelled_done:
            self._finish_target_poll(task_map[t], False)

        for t in still_pending:
            self._finish_target_poll(task_map[t], False, keep_inflight=True)

        logger.info(
            f"Interface tick: {len(due)} due / {len(targets)} tracked, "
            f"{success_count} ok, {len(still_pending)} timeout"
        )

    def _load_targets(self) -> List[Dict]:
        """加载需要轮询的设备（N+1 优化版本，批量加载 monitored 接口）"""
        db = next(get_db())
        try:
            devices = db.query(Device).filter(
                Device.snmp_enabled == True,  # noqa: E712
                Device.ip.isnot(None),
                Device.snmp_community.isnot(None),
            ).all()
            if not devices:
                return []

            # 一次查完所有 monitored 接口，避免每台设备单独查一次
            device_ids = [d.id for d in devices]
            all_ifaces = db.query(DeviceInterface).filter(
                DeviceInterface.device_id.in_(device_ids),
                DeviceInterface.monitored == True,  # noqa: E712
            ).all()

            ifaces_by_device: Dict[int, list] = {}
            for iface in all_ifaces:
                ifaces_by_device.setdefault(iface.device_id, []).append(iface)

            result = []
            for d in devices:
                dev_ifaces = ifaces_by_device.get(d.id, [])
                if not dev_ifaces:
                    continue
                result.append({
                    "id": d.id,
                    "name": d.name,
                    "ip": d.ip,
                    "community": d.snmp_community,
                    "device_type": d.device_type or "",
                    "if_indexes": [i.if_index for i in dev_ifaces],
                })
            return result
        finally:
            db.close()

    async def _poll_device(self, dev: Dict):
        ip = dev["ip"]
        community = dev["community"]
        monitored = set(dev["if_indexes"])
        svc = get_snmp_service()
        oid_sem = asyncio.Semaphore(20)

        async def get(oid, idx):
            async with oid_sem:
                return await svc.snmp_get_async(ip, community, f"{oid}.{idx}", timeout=self.snmp_timeout)

        async def walk(oid):
            return await svc.snmp_walk_async(ip, community, oid, timeout=self.snmp_timeout)

        async def poll_index(idx):
            # 只采集被监控接口的实例 OID，避免每 30s walk 整张接口表。
            values = await asyncio.gather(
                get(OID_IF_OPER_STATUS, idx),
                get(OID_IF_ADMIN_STATUS, idx),
                get(OID_IF_HC_IN_OCTETS, idx),
                get(OID_IF_HC_OUT_OCTETS, idx),
                get(OID_IF_IN_OCTETS, idx),
                get(OID_IF_OUT_OCTETS, idx),
                get(OID_IF_HIGH_SPEED, idx),
                get(OID_IF_SPEED, idx),
                get(OID_IF_IN_ERRORS, idx),
                get(OID_IF_OUT_ERRORS, idx),
                return_exceptions=True,
            )
            # CancelledError 是 BaseException，不会被 return_exceptions 吞掉，
            # 但仍可能出现在结果列表中（Python 3.12+）。发现后立即传播。
            if any(isinstance(v, BaseException) and not isinstance(v, Exception) for v in values):
                raise asyncio.CancelledError()
            values = [None if isinstance(value, Exception) else value for value in values]
            oper, admin, hc_in, hc_out, in32, out32, high_speed, speed_bps, in_err, out_err = values

            in_octets = _to_int(hc_in)
            out_octets = _to_int(hc_out)
            if in_octets is None:
                in_octets = _to_int(in32)
            if out_octets is None:
                out_octets = _to_int(out32)

            if oper is None and in_octets is None and out_octets is None:
                return idx, None

            spd_mbps = _to_int(high_speed)
            if not spd_mbps:
                raw_speed_bps = _to_int(speed_bps)
                spd_mbps = int(raw_speed_bps / 1_000_000) if raw_speed_bps else None

            return idx, {
                "oper": oper_status_text(oper),
                "admin": oper_status_text(admin),
                "in_octets": in_octets,
                "out_octets": out_octets,
                "speed_mbps": spd_mbps,
                "in_errors": _to_int(in_err),
                "out_errors": _to_int(out_err),
            }

        async def poll_missing_with_walk(missing_indexes):
            if not missing_indexes:
                return {}

            oper, admin, in_oct, out_oct, speed, speed_lo, in_err, out_err = await asyncio.gather(
                walk(OID_IF_OPER_STATUS),
                walk(OID_IF_ADMIN_STATUS),
                walk(OID_IF_HC_IN_OCTETS),
                walk(OID_IF_HC_OUT_OCTETS),
                walk(OID_IF_HIGH_SPEED),
                walk(OID_IF_SPEED),
                walk(OID_IF_IN_ERRORS),
                walk(OID_IF_OUT_ERRORS),
            )

            fallback_in = fallback_out = None
            if not in_oct or not out_oct:
                fallback_in, fallback_out = await asyncio.gather(
                    walk(OID_IF_IN_OCTETS) if not in_oct else asyncio.sleep(0, result=None),
                    walk(OID_IF_OUT_OCTETS) if not out_oct else asyncio.sleep(0, result=None),
                )
            if not in_oct and fallback_in:
                in_oct = fallback_in
            if not out_oct and fallback_out:
                out_oct = fallback_out

            fallback_readings = {}
            for idx in missing_indexes:
                key = str(idx)
                spd_mbps = _to_int(speed.get(key))
                if not spd_mbps:
                    spd_bps = _to_int(speed_lo.get(key))
                    spd_mbps = int(spd_bps / 1_000_000) if spd_bps else None
                reading = {
                    "oper": oper_status_text(oper.get(key, "")),
                    "admin": oper_status_text(admin.get(key, "")),
                    "in_octets": _to_int(in_oct.get(key)),
                    "out_octets": _to_int(out_oct.get(key)),
                    "speed_mbps": spd_mbps,
                    "in_errors": _to_int(in_err.get(key)),
                    "out_errors": _to_int(out_err.get(key)),
                }
                if reading["oper"] != "unknown" or reading["in_octets"] is not None or reading["out_octets"] is not None:
                    fallback_readings[idx] = reading
            return fallback_readings

        now = datetime.utcnow()
        results = await asyncio.gather(*[poll_index(idx) for idx in monitored])
        readings = {idx: reading for idx, reading in results if reading is not None}

        missing_indexes = [
            idx for idx in monitored
            if idx not in readings
            or readings[idx].get("in_octets") is None
            or readings[idx].get("out_octets") is None
        ]
        if missing_indexes:
            fallback_readings = await poll_missing_with_walk(missing_indexes)
            readings.update(fallback_readings)
            if fallback_readings:
                logger.debug(f"SNMP {ip} walk fallback filled {len(fallback_readings)}/{len(missing_indexes)} monitored interfaces")

        if not readings:
            logger.debug(f"SNMP {ip} monitored interfaces no response, skip")
            return False

        with self._db_lock:
            await asyncio.to_thread(self._persist_readings, dev["id"], readings, now)
        return True

    def _persist_readings(self, device_id: int, readings: Dict[int, Dict], now: datetime):
        db = next(get_db())
        try:
            device = db.query(Device).filter(Device.id == device_id).first()
            changes = []
            incident_events = []
            for idx, r in readings.items():
                iface = db.query(DeviceInterface).filter(
                    DeviceInterface.device_id == device_id,
                    DeviceInterface.if_index == idx,
                ).first()
                if not iface:
                    continue

                # 速率计算
                in_bps = out_bps = None
                in_util = out_util = None
                if (iface.last_sample_at and iface.last_in_octets is not None
                        and r["in_octets"] is not None and r["out_octets"] is not None):
                    dt = (now - iface.last_sample_at).total_seconds()
                    if dt > 0:
                        in_delta = _counter_delta(iface.last_in_octets, r["in_octets"])
                        out_delta = _counter_delta(iface.last_out_octets, r["out_octets"])
                        in_bps = int(in_delta * 8 / dt)
                        out_bps = int(out_delta * 8 / dt)
                        # 计数器翻转/重置保护：超过 400Gbps 视为异常，丢弃本次样本
                        if in_bps > 400_000_000_000 or out_bps > 400_000_000_000:
                            in_bps = out_bps = None
                        else:
                            spd = r["speed_mbps"] or iface.speed_mbps
                            if spd and spd > 0:
                                cap = spd * 1_000_000
                                in_util = round(min(in_bps / cap * 100, 100), 2)
                                out_util = round(min(out_bps / cap * 100, 100), 2)

                old_oper = iface.oper_status
                new_oper = r["oper"]

                # 更新接口最近值
                iface.oper_status = new_oper
                iface.admin_status = r["admin"]
                if r["speed_mbps"]:
                    iface.speed_mbps = r["speed_mbps"]
                iface.last_in_octets = r["in_octets"]
                iface.last_out_octets = r["out_octets"]
                iface.last_sample_at = now
                iface.last_check = now
                iface.last_in_errors = r["in_errors"]
                iface.last_out_errors = r["out_errors"]
                if in_bps is not None:
                    iface.last_in_bps = in_bps
                    iface.last_out_bps = out_bps
                    iface.last_in_util = in_util
                    iface.last_out_util = out_util
                    db.add(InterfaceTrafficSample(
                        interface_id=iface.id,
                        device_id=device_id,
                        ts=now,
                        in_bps=in_bps,
                        out_bps=out_bps,
                        in_util=in_util,
                        out_util=out_util,
                        in_errors=r["in_errors"],
                        out_errors=r["out_errors"],
                        oper_status=new_oper,
                    ))

                if old_oper and old_oper != new_oper and new_oper in ("up", "down"):
                    changes.append((iface.if_index, iface.if_name, bool(iface.is_uplink), old_oper, new_oper))
                    incident_events.append({
                        "if_index": iface.if_index,
                        "if_name": iface.if_name,
                        "is_uplink": bool(iface.is_uplink),
                        "new_oper": new_oper,
                        "peer_device_id": iface.peer_device_id,
                        "peer_device_name": iface.peer_device_name,
                        "peer_if_name": iface.peer_if_name,
                    })

            db.commit()

            # 提交成功后推送 oper_status 变化（上行口掉线立即上大屏）
            for if_index, if_name, is_uplink, old_oper, new_oper in changes:
                self._broadcast_interface_change(device, device_id, if_index, if_name, is_uplink, old_oper, new_oper)

            # 接口 up/down 变化进入故障工单闭环（与 Trap 路径一致）
            if incident_events and device:
                self._upsert_interface_incidents(db, device, incident_events)
        except Exception as e:
            logger.error(f"Persist interface readings failed (device {device_id}): {e}")
            db.rollback()
        finally:
            db.close()

    def _broadcast_interface_change(self, device, device_id, if_index, if_name, is_uplink, old_oper, new_oper):
        try:
            from app.features.websocket.router import broadcast_device_status_sync
            broadcast_device_status_sync({
                "event": "interface_status_change",
                "device_id": device_id,
                "device_name": device.name if device else "",
                "if_index": if_index,
                "if_name": if_name or "",
                "is_uplink": is_uplink,
                "old_status": old_oper,
                "new_status": new_oper,
                "timestamp": datetime.utcnow().isoformat(),
            })
        except Exception as e:
            logger.error(f"Failed to push interface status: {e}")

    def _upsert_interface_incidents(self, db, device, incident_events: List[Dict]):
        """接口 oper_status 变化进入故障工单闭环（轮询路径，与 Trap 一致）"""
        try:
            from app.services.incident_automation import MonitorEvent, upsert_fault_from_monitor_event
            for ev in incident_events:
                upsert_fault_from_monitor_event(db, MonitorEvent(
                    source_type="interface_poll",
                    event_type="link_up" if ev["new_oper"] == "up" else "link_down",
                    device_id=device.id,
                    device_name=device.name,
                    ip=device.ip,
                    if_index=ev["if_index"],
                    if_name=ev["if_name"],
                    peer_device_id=ev["peer_device_id"],
                    peer_device_name=ev["peer_device_name"],
                    peer_if_name=ev["peer_if_name"],
                    raw={"is_uplink": ev["is_uplink"]},
                ))
        except Exception as e:
            logger.warning(f"接口轮询自动故障工单处理失败: {e}")

    # ===== 接口发现（API 触发）=====
    def discover_interfaces(self, device_id: int) -> Dict:
        """SNMP walk ifName/ifDescr，落库 device_interfaces（幂等 upsert）"""
        if not SNMP_AVAILABLE:
            return {"ok": False, "error": "SNMP 库不可用（puresnmp 未安装）"}
        db = next(get_db())
        try:
            device = db.query(Device).filter(Device.id == device_id).first()
            if not device:
                return {"ok": False, "error": "设备不存在"}
            if not (device.snmp_enabled and device.ip and device.snmp_community):
                return {"ok": False, "error": "设备未启用 SNMP 或缺少团体名/IP"}

            svc = get_snmp_service()

            def walk(oid):
                return asyncio.run(svc.snmp_walk_async(device.ip, device.snmp_community, oid, timeout=self.snmp_timeout))

            names = walk(OID_IF_NAME)
            descrs = walk(OID_IF_DESCR)
            oper = walk(OID_IF_OPER_STATUS)

            source = names or descrs
            if not source:
                return {"ok": False, "error": "SNMP 无响应或无接口（检查团体名/ACL）"}

            count = 0
            for idx_str, name in source.items():
                try:
                    if_index = int(idx_str)
                except (ValueError, TypeError):
                    continue
                iface = db.query(DeviceInterface).filter(
                    DeviceInterface.device_id == device_id,
                    DeviceInterface.if_index == if_index,
                ).first()
                if not iface:
                    iface = DeviceInterface(device_id=device_id, if_index=if_index)
                    db.add(iface)
                if names:
                    iface.if_name = str(name)
                if idx_str in descrs:
                    iface.if_descr = str(descrs.get(idx_str))
                iface.oper_status = oper_status_text(oper.get(idx_str, ""))
                iface.last_check = datetime.utcnow()
                count += 1
            db.commit()
            return {"ok": True, "discovered": count}
        except Exception as e:
            db.rollback()
            logger.error(f"Discover interfaces failed (device {device_id}): {e}")
            return {"ok": False, "error": str(e)}
        finally:
            db.close()

    def discover_neighbors(self, device_id: int) -> Dict:
        """基于 CDP + LLDP 自动发现邻居，回写对端关联并推断上行口

        CDP 优先（含对端管理 IP，匹配最准）；LLDP 作为补充覆盖非 Cisco 设备。
        """
        if not SNMP_AVAILABLE:
            return {"ok": False, "error": "SNMP 库未安装（puresnmp）"}
        db = next(get_db())
        try:
            device = db.query(Device).filter(Device.id == device_id).first()
            if not device:
                return {"ok": False, "error": "设备不存在"}
            if not (device.snmp_enabled and device.ip and device.snmp_community):
                return {"ok": False, "error": "设备未启用 SNMP 或缺少团体名/IP"}

            svc = get_snmp_service()
            community = device.snmp_community

            def walk(oid):
                return asyncio.run(svc.snmp_walk_raw_async(device.ip, community, oid, timeout=self.snmp_timeout))

            # CDP 优先，LLDP 补充；按本地接口去重（CDP 已覆盖的接口不再被 LLDP 覆盖）
            raw_neighbors = self._collect_cdp(walk) + self._collect_lldp(walk)
            if not raw_neighbors:
                return {"ok": False, "error": "CDP/LLDP 无响应（检查 cdp run / lldp run / 团体名）"}

            self_rank = _tier_rank(getattr(device, "device_type", None))
            neighbors = []
            matched = 0
            uplinks_marked = 0
            seen_ifaces = set()   # 已处理的本地接口（按 if_index），CDP 先于 LLDP

            for n in raw_neighbors:
                iface = self._resolve_local_iface(db, device_id, n)
                if iface is None:
                    continue
                if iface.if_index in seen_ifaces:
                    continue
                seen_ifaces.add(iface.if_index)

                remote_host = n.get("remote_host") or ""
                remote_port = n.get("remote_port") or ""
                remote_ip = n.get("remote_ip") or ""
                remote_platform = n.get("remote_platform") or ""

                # 匹配系统内对端设备：先 IP，再主机名（含去域名）
                peer = None
                if remote_ip:
                    peer = db.query(Device).filter(Device.ip == remote_ip).first()
                if peer is None and remote_host:
                    short = remote_host.split(".")[0]
                    peer = db.query(Device).filter(
                        func.lower(Device.name) == remote_host.lower()
                    ).first()
                    if peer is None and short:
                        peer = db.query(Device).filter(
                            func.lower(Device.name) == short.lower()
                        ).first()

                iface.peer_device_name = remote_host or None
                iface.peer_ip = remote_ip or None
                iface.peer_if_name = remote_port or None
                iface.neighbor_source = n.get("source")
                iface.neighbor_updated_at = datetime.utcnow()

                is_uplink = False
                if peer is not None:
                    matched += 1
                    iface.peer_device_id = peer.id
                    peer_rank = _tier_rank(getattr(peer, "device_type", None))
                    if peer_rank >= self_rank:
                        is_uplink = True
                        if not iface.is_uplink:
                            uplinks_marked += 1
                        iface.is_uplink = True
                        iface.monitored = True

                neighbors.append({
                    "local_if_index": iface.if_index,
                    "remote_ip": remote_ip,
                    "remote_host": remote_host,
                    "remote_port": remote_port,
                    "remote_platform": remote_platform,
                    "source": n.get("source"),
                    "peer_device_id": peer.id if peer else None,
                    "is_uplink": is_uplink,
                })

            # 清理陈旧对端：线缆被拔掉/改接后，旧邻居不再出现在 CDP/LLDP 结果里，
            # 但接口上原先写入的 peer_* 不会自动消失，会导致数据链路仍按旧拓扑
            # 画到旧对端（并误判为断开、显示红色）。这里把本次未再发现邻居、
            # 但之前由 CDP/LLDP 写入过对端的接口清空。
            cleared = 0
            stale_ifaces = db.query(DeviceInterface).filter(
                DeviceInterface.device_id == device_id,
                DeviceInterface.neighbor_source.isnot(None),
            ).all()
            for si in stale_ifaces:
                if si.if_index in seen_ifaces:
                    continue
                old_peer_id = si.peer_device_id
                si.peer_device_id = None
                si.peer_device_name = None
                si.peer_ip = None
                si.peer_if_name = None
                si.neighbor_source = None
                si.neighbor_updated_at = datetime.utcnow()
                si.is_uplink = False
                si.monitored = False
                cleared += 1

                # 同时清理对端设备上回指本机的接口。
                # 注意：不能依赖 peer_if_name/if_name 做字符串匹配，因为 Cisco 设备
                # 的 SNMP ifName 返回短格式（Gi0/2）而 CDP 返回长格式（GigabitEthernet0/2），
                # 导致端口名无法直接比较。改用 device_id + peer_device_id 配对定位。
                if old_peer_id:
                    reciprocal = db.query(DeviceInterface).filter(
                        DeviceInterface.device_id == old_peer_id,
                        DeviceInterface.peer_device_id == device_id,
                    ).all()
                    for ri in reciprocal:
                        ri.peer_device_id = None
                        ri.peer_device_name = None
                        ri.peer_ip = None
                        ri.peer_if_name = None
                        ri.neighbor_source = None
                        ri.neighbor_updated_at = datetime.utcnow()
                        ri.is_uplink = False
                        ri.monitored = False
                        cleared += 1

            db.commit()
            return {
                "ok": True,
                "neighbors": neighbors,
                "found": len(neighbors),
                "matched": matched,
                "uplinks_marked": uplinks_marked,
                "cleared": cleared,
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Discover neighbors failed (device {device_id}): {e}")
            return {"ok": False, "error": str(e)}
        finally:
            db.close()

    def _collect_cdp(self, walk) -> List[Dict]:
        """采集 CISCO-CDP-MIB 邻居 → [{local_if_index, remote_ip, remote_host, remote_port, remote_platform, source}]"""
        addr = walk(OID_CDP_ADDRESS)
        dev_id = walk(OID_CDP_DEVICE_ID)
        dev_port = walk(OID_CDP_DEVICE_PORT)
        platform = walk(OID_CDP_PLATFORM)
        out = []
        for suffix in (set(dev_id) | set(addr) | set(dev_port)):
            if_index = _cdp_local_ifindex(suffix)
            if if_index is None:
                continue
            out.append({
                "local_if_index": if_index,
                "local_if_name": None,
                "remote_ip": _decode_ip(addr.get(suffix)),
                "remote_host": _decode_str(dev_id.get(suffix)),
                "remote_port": _decode_str(dev_port.get(suffix)),
                "remote_platform": _decode_str(platform.get(suffix)),
                "source": "cdp",
            })
        return out

    def _collect_lldp(self, walk) -> List[Dict]:
        """采集 LLDP-MIB 邻居 → [{local_if_name/local_if_index, remote_host, remote_port, ...}]

        LLDP 本地端口号(lldpLocPortNum)不一定等于 ifIndex，故用 lldpLocPortId 映射成端口名，
        在写库阶段按 if_name 匹配 DeviceInterface。
        """
        rem_port = walk(OID_LLDP_REM_PORT_ID)
        rem_port_desc = walk(OID_LLDP_REM_PORT_DESC)
        rem_sys = walk(OID_LLDP_REM_SYS_NAME)
        rem_sys_desc = walk(OID_LLDP_REM_SYS_DESC)
        loc_port_id = walk(OID_LLDP_LOC_PORT_ID)   # {portNum: 端口名}

        # 本地端口号 → 端口名映射
        loc_map = {}
        for k, v in loc_port_id.items():
            try:
                loc_map[int(k.lstrip(".").split(".")[0])] = _decode_str(v)
            except (ValueError, TypeError):
                continue

        out = []
        for suffix in (set(rem_sys) | set(rem_port)):
            port_num = _lldp_local_portnum(suffix)
            if port_num is None:
                continue
            local_if_name = loc_map.get(port_num)
            remote_port = _decode_str(rem_port_desc.get(suffix)) or _decode_str(rem_port.get(suffix))
            out.append({
                # 若 portNum 恰好等于 ifIndex，写库阶段也会兜底尝试
                "local_if_index": port_num if not local_if_name else None,
                "local_if_name": local_if_name,
                "remote_ip": "",
                "remote_host": _decode_str(rem_sys.get(suffix)),
                "remote_port": remote_port,
                "remote_platform": _decode_str(rem_sys_desc.get(suffix))[:120],
                "source": "lldp",
            })
        return out

    def _resolve_local_iface(self, db, device_id: int, n: Dict) -> Optional[DeviceInterface]:
        """把邻居记录解析到本地 DeviceInterface 行（按 if_index 或 if_name）"""
        if n.get("local_if_index") is not None:
            iface = db.query(DeviceInterface).filter(
                DeviceInterface.device_id == device_id,
                DeviceInterface.if_index == n["local_if_index"],
            ).first()
            if not iface:
                iface = DeviceInterface(device_id=device_id, if_index=n["local_if_index"])
                db.add(iface)
                db.flush()
            return iface
        name = n.get("local_if_name")
        if name:
            iface = db.query(DeviceInterface).filter(
                DeviceInterface.device_id == device_id,
                func.lower(DeviceInterface.if_name) == name.lower(),
            ).first()
            if iface:
                return iface
            return db.query(DeviceInterface).filter(
                DeviceInterface.device_id == device_id,
                DeviceInterface.if_name.ilike(f"%{name}%"),
            ).first()
        return None


def _to_int(val) -> Optional[int]:
    if val is None:
        return None
    try:
        return int(str(val).strip())
    except (ValueError, TypeError):
        return None


def _counter_delta(prev: Optional[int], curr: Optional[int]) -> int:
    """处理 64 位计数器翻转"""
    if prev is None or curr is None:
        return 0
    if curr >= prev:
        return curr - prev
    return (COUNTER64_MAX - prev) + curr


_interface_monitor: Optional[InterfaceMonitor] = None


def get_interface_monitor() -> InterfaceMonitor:
    global _interface_monitor
    if _interface_monitor is None:
        _interface_monitor = InterfaceMonitor()
    return _interface_monitor


def start_interface_monitor():
    monitor = get_interface_monitor()
    monitor.start()
    return monitor


def stop_interface_monitor():
    if _interface_monitor:
        _interface_monitor.stop()
