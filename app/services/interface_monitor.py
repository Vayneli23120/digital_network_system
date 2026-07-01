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

# 设备层级排名：数值越大越靠核心；对端排名 > 本端排名 → 该接口判为上行口
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

        # 虚拟设备/老镜像常无 64 位计数器或 ifHighSpeed，按需回退到 32 位
        if not in_oct:
            in_oct = await walk(OID_IF_IN_OCTETS)
        if not out_oct:
            out_oct = await walk(OID_IF_OUT_OCTETS)
        speed_lo = await walk(OID_IF_SPEED)

        if not oper and not in_oct:
            logger.debug(f"SNMP {ip} 无响应，跳过")
            return

        now = datetime.utcnow()
        readings = {}
        for idx in monitored:
            key = str(idx)
            # 速率：优先 ifHighSpeed(Mbps)，为 0/空时回退 ifSpeed(bps)
            spd_mbps = _to_int(speed.get(key))
            if not spd_mbps:
                spd_bps = _to_int(speed_lo.get(key))
                spd_mbps = int(spd_bps / 1_000_000) if spd_bps else None
            readings[idx] = {
                "oper": oper_status_text(oper.get(key, "")),
                "admin": oper_status_text(admin.get(key, "")),
                "in_octets": _to_int(in_oct.get(key)),
                "out_octets": _to_int(out_oct.get(key)),
                "speed_mbps": spd_mbps,
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
                    if peer_rank > self_rank:
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
