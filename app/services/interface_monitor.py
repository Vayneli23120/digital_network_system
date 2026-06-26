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
from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

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

COUNTER64_MAX = 2 ** 64


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
        self.poll_interval = 60          # 轮询周期（秒）
        self.max_concurrency = 20        # 并发设备数
        self.snmp_timeout = 3
        self._db_lock = threading.Lock()

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
                lambda: asyncio.run(self._poll_all()),
                trigger=IntervalTrigger(seconds=self.poll_interval),
                id="interface_poll",
                name="SNMP接口轮询",
                replace_existing=True,
            )
            self.scheduler.start()
            self._running = True
            logger.info(f"Interface monitor started (interval={self.poll_interval}s)")
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

    # ===== 轮询 =====
    async def _poll_all(self):
        targets = self._load_targets()
        if not targets:
            logger.debug("No SNMP-monitored interfaces to poll")
            return

        sem = asyncio.Semaphore(self.max_concurrency)

        async def _poll_one(dev):
            async with sem:
                try:
                    await self._poll_device(dev)
                except Exception as e:
                    logger.error(f"Poll device {dev['name']} failed: {e}")

        await asyncio.gather(*[_poll_one(d) for d in targets], return_exceptions=True)
        logger.info(f"Interface poll completed for {len(targets)} devices")

    def _load_targets(self) -> List[Dict]:
        """加载需要轮询的设备（snmp_enabled 且至少有一个 monitored 接口）"""
        db = next(get_db())
        try:
            devices = db.query(Device).filter(
                Device.snmp_enabled == True,  # noqa: E712
                Device.ip.isnot(None),
                Device.snmp_community.isnot(None),
            ).all()
            result = []
            for d in devices:
                ifaces = db.query(DeviceInterface).filter(
                    DeviceInterface.device_id == d.id,
                    DeviceInterface.monitored == True,  # noqa: E712
                ).all()
                if not ifaces:
                    continue
                result.append({
                    "id": d.id,
                    "name": d.name,
                    "ip": d.ip,
                    "community": d.snmp_community,
                    "if_indexes": [i.if_index for i in ifaces],
                })
            return result
        finally:
            db.close()

    async def _poll_device(self, dev: Dict):
        ip = dev["ip"]
        community = dev["community"]
        monitored = set(dev["if_indexes"])
        svc = get_snmp_service()

        async def walk(oid):
            return await svc.snmp_walk_async(ip, community, oid, timeout=self.snmp_timeout)

        oper = await walk(OID_IF_OPER_STATUS)
        admin = await walk(OID_IF_ADMIN_STATUS)
        in_oct = await walk(OID_IF_HC_IN_OCTETS)
        out_oct = await walk(OID_IF_HC_OUT_OCTETS)
        speed = await walk(OID_IF_HIGH_SPEED)
        in_err = await walk(OID_IF_IN_ERRORS)
        out_err = await walk(OID_IF_OUT_ERRORS)

        if not oper and not in_oct:
            logger.debug(f"SNMP {ip} 无响应，跳过")
            return

        now = datetime.utcnow()
        readings = {}
        for idx in monitored:
            key = str(idx)
            readings[idx] = {
                "oper": oper_status_text(oper.get(key, "")),
                "admin": oper_status_text(admin.get(key, "")),
                "in_octets": _to_int(in_oct.get(key)),
                "out_octets": _to_int(out_oct.get(key)),
                "speed_mbps": _to_int(speed.get(key)),
                "in_errors": _to_int(in_err.get(key)),
                "out_errors": _to_int(out_err.get(key)),
            }

        with self._db_lock:
            await asyncio.to_thread(self._persist_readings, dev["id"], readings, now)

    def _persist_readings(self, device_id: int, readings: Dict[int, Dict], now: datetime):
        db = next(get_db())
        try:
            device = db.query(Device).filter(Device.id == device_id).first()
            changes = []
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

            db.commit()

            # 提交成功后推送 oper_status 变化（上行口掉线立即上大屏）
            for if_index, if_name, is_uplink, old_oper, new_oper in changes:
                self._broadcast_interface_change(device, device_id, if_index, if_name, is_uplink, old_oper, new_oper)
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
