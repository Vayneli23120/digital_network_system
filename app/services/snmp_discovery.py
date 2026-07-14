"""
SNMP 发现服务 — 接口发现 + CDP/LLDP 邻居发现（按需触发）

职责（均由 API 按需触发，非周期轮询）：
- discover_interfaces：walk ifName/ifDescr/ifOperStatus，落库 device_interfaces
- discover_neighbors：walk CDP + LLDP 邻居表，回写对端关联并推断上行口

设计说明：
流量/状态的周期采集已迁移到 Prometheus + snmp_exporter（见 prometheus_connector.py），
本模块只保留“按需的一次性 SNMP walk”类操作（接口/邻居发现），这类拓扑发现是
用户手动触发的即时任务，用即时 SNMP walk 最直接，无需经过时序库。

SNMP 传输复用 app.features.devices.snmp_service（puresnmp）。
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger
from sqlalchemy import func

from app.shared.database import get_db
from app.shared.models import Device, DeviceInterface
from app.features.devices.snmp_service import get_snmp_service, SNMP_AVAILABLE
from app.services.ap_discovery import is_ap_neighbor, upsert_ap_from_neighbor

# 一次性发现操作的 SNMP 超时（秒）
SNMP_TIMEOUT = 8

# ===== 标准 IF-MIB OID（列前缀，walk 返回 {ifIndex: value}）=====
OID_IF_DESCR = "1.3.6.1.2.1.2.2.1.2"
OID_IF_OPER_STATUS = "1.3.6.1.2.1.2.2.1.8"
OID_IF_NAME = "1.3.6.1.2.1.31.1.1.1.1"

# ===== CISCO-CDP-MIB cdpCacheTable（索引 = ifIndex.deviceIndex）=====
OID_CDP_ADDRESS = "1.3.6.1.4.1.9.9.23.1.2.1.1.4"      # cdpCacheAddress（对端 IP）
OID_CDP_DEVICE_ID = "1.3.6.1.4.1.9.9.23.1.2.1.1.6"    # cdpCacheDeviceId（对端主机名）
OID_CDP_DEVICE_PORT = "1.3.6.1.4.1.9.9.23.1.2.1.1.7"  # cdpCacheDevicePort（对端端口名）
OID_CDP_PLATFORM = "1.3.6.1.4.1.9.9.23.1.2.1.1.8"     # cdpCachePlatform（对端型号）

# ===== LLDP-MIB（标准，覆盖非 Cisco）=====
# lldpRemTable 索引 = lldpRemTimeMark.lldpRemLocalPortNum.lldpRemIndex
OID_LLDP_REM_PORT_ID = "1.0.8802.1.1.2.1.4.1.1.7"     # lldpRemPortId（对端端口）
OID_LLDP_REM_PORT_DESC = "1.0.8802.1.1.2.1.4.1.1.8"   # lldpRemPortDesc
OID_LLDP_REM_SYS_NAME = "1.0.8802.1.1.2.1.4.1.1.9"    # lldpRemSysName（对端主机名）
OID_LLDP_REM_SYS_DESC = "1.0.8802.1.1.2.1.4.1.1.10"   # lldpRemSysDesc（对端描述/型号）
# lldpLocPortTable 索引 = lldpLocPortNum；lldpLocPortId 通常即本地端口名
OID_LLDP_LOC_PORT_ID = "1.0.8802.1.1.2.1.3.7.1.3"     # lldpLocPortId

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
    return str(v).strip()


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


# ===== 接口发现（API 触发）=====
def discover_interfaces(device_id: int) -> Dict:
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
            return asyncio.run(svc.snmp_walk_async(device.ip, device.snmp_community, oid, timeout=SNMP_TIMEOUT))

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


def discover_neighbors(device_id: int) -> Dict:
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
            return asyncio.run(svc.snmp_walk_raw_async(device.ip, community, oid, timeout=SNMP_TIMEOUT))

        # CDP 优先，LLDP 补充；按本地接口去重（CDP 已覆盖的接口不再被 LLDP 覆盖）
        raw_neighbors = _collect_cdp(walk) + _collect_lldp(walk)
        if not raw_neighbors:
            return {"ok": False, "error": "CDP/LLDP 无响应（检查 cdp run / lldp run / 团体名）"}

        self_rank = _tier_rank(getattr(device, "device_type", None))
        neighbors = []
        matched = 0
        uplinks_marked = 0
        aps_synced = 0
        seen_ifaces = set()   # 已处理的本地接口（按 if_index），CDP 先于 LLDP

        for n in raw_neighbors:
            iface = _resolve_local_iface(db, device_id, n)
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

            # 未匹配到系统内设备，但 CDP/LLDP 特征判定为 AP → 自动建 AP 记录。
            # AP 在线状态后续由所连交换机端口 oper_status 推导（sync_ap_online_status）；
            # 此刻能看到 CDP 邻居即说明端口 up，先置 reachable。
            if peer is None and is_ap_neighbor(remote_platform, remote_host):
                peer = upsert_ap_from_neighbor(db, n, device)
                if peer is not None:
                    peer.reachability = "reachable"
                    peer.last_reachability_check = datetime.utcnow()
                    peer.reachability_method = "cdp"
                    aps_synced += 1

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
            "aps_synced": aps_synced,
            "cleared": cleared,
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Discover neighbors failed (device {device_id}): {e}")
        return {"ok": False, "error": str(e)}
    finally:
        db.close()


def _collect_cdp(walk) -> List[Dict]:
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


def _collect_lldp(walk) -> List[Dict]:
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


def _resolve_local_iface(db, device_id: int, n: Dict) -> Optional[DeviceInterface]:
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
