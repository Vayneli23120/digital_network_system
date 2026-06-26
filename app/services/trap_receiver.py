"""
SNMP Trap 接收器（阶段 B）- 秒级 linkDown/linkUp

监听 UDP/162，解析设备主动上报的 linkDown/linkUp Trap，
即时更新对应接口 oper_status 并通过 WebSocket 推送（复用 interface_status_change 事件）。

不依赖 pysnmp/puresnmp：内置极简 BER/ASN.1 解码，仅解析 v1/v2c Trap PDU，
提取来源 IP（UDP 源地址）+ snmpTrapOID(或 v1 generic-trap) + ifIndex。

设备侧需配置（示例 Cisco）：
  snmp-server host <server-ip> version 2c <community>
  snmp-server enable traps snmp linkdown linkup
  interface <uplink>
   snmp trap link-status
并放行 UDP/162 到本服务器。绑定 162 端口需要 root（或 setcap），
否则可用环境变量 SNMP_TRAP_PORT 指定高位端口测试。
"""

import os
import socket
import threading
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any

from loguru import logger

from app.shared.database import get_db
from app.shared.models import Device, DeviceInterface

# ===== 标准 Trap OID =====
SNMP_TRAP_OID = "1.3.6.1.6.3.1.1.4.1.0"   # snmpTrapOID.0
LINKDOWN_OID = "1.3.6.1.6.3.1.1.5.3"
LINKUP_OID = "1.3.6.1.6.3.1.1.5.4"
IFTABLE_PREFIX = "1.3.6.1.2.1.2.2.1."      # ifTable 列前缀（末段为 ifIndex）

# ===== 极简 BER 解码 =====


def _read_len(data: bytes, i: int) -> Tuple[int, int]:
    b = data[i]
    i += 1
    if not (b & 0x80):
        return b, i
    n = b & 0x7F
    length = 0
    for _ in range(n):
        length = (length << 8) | data[i]
        i += 1
    return length, i


def _read_tlv(data: bytes, i: int) -> Tuple[int, bytes, int]:
    tag = data[i]
    i += 1
    length, i = _read_len(data, i)
    value = data[i:i + length]
    return tag, value, i + length


def _decode_int(b: bytes) -> int:
    if not b:
        return 0
    return int.from_bytes(b, "big", signed=True)


def _decode_oid(b: bytes) -> str:
    if not b:
        return ""
    first = b[0]
    parts = [str(first // 40), str(first % 40)]
    val = 0
    for c in b[1:]:
        val = (val << 7) | (c & 0x7F)
        if not (c & 0x80):
            parts.append(str(val))
            val = 0
    return ".".join(parts)


def parse_snmp_trap(packet: bytes) -> Optional[Dict[str, Any]]:
    """解析 v1/v2c Trap，返回 {version, community, varbinds:[(oid,tag,value)], v1_generic?}"""
    try:
        tag, body, _ = _read_tlv(packet, 0)
        if tag != 0x30:  # outer SEQUENCE
            return None
        i = 0
        _, ver_b, i = _read_tlv(body, i)        # version INTEGER
        version = _decode_int(ver_b)
        _, comm_b, i = _read_tlv(body, i)       # community OCTET STRING
        community = comm_b.decode("latin1", "ignore")
        pdu_tag, pdu, i = _read_tlv(body, i)    # PDU

        if pdu_tag == 0xA4:                     # v1 Trap-PDU
            return _parse_v1_trap(pdu, community, version)
        if pdu_tag not in (0xA7, 0xA6):         # v2c Trap / Inform
            return None
        return _parse_v2_pdu(pdu, community, version)
    except (IndexError, ValueError):
        return None


def _read_varbinds(vbl: bytes) -> List[Tuple[str, int, bytes]]:
    varbinds = []
    k = 0
    while k < len(vbl):
        t, vb, k = _read_tlv(vbl, k)
        if t != 0x30:
            continue
        m = 0
        _, oid_b, m = _read_tlv(vb, m)
        vt, val_b, m = _read_tlv(vb, m)
        varbinds.append((_decode_oid(oid_b), vt, val_b))
    return varbinds


def _parse_v2_pdu(pdu: bytes, community: str, version: int) -> Dict[str, Any]:
    j = 0
    _, _, j = _read_tlv(pdu, j)   # request-id
    _, _, j = _read_tlv(pdu, j)   # error-status
    _, _, j = _read_tlv(pdu, j)   # error-index
    _, vbl, j = _read_tlv(pdu, j)  # varbind list
    return {"version": version, "community": community, "varbinds": _read_varbinds(vbl)}


def _parse_v1_trap(pdu: bytes, community: str, version: int) -> Dict[str, Any]:
    i = 0
    _, _, i = _read_tlv(pdu, i)        # enterprise OID
    _, _, i = _read_tlv(pdu, i)        # agent-addr (IpAddress)
    _, gen_b, i = _read_tlv(pdu, i)    # generic-trap INTEGER
    _, _, i = _read_tlv(pdu, i)        # specific-trap INTEGER
    _, _, i = _read_tlv(pdu, i)        # time-stamp TimeTicks
    _, vbl, i = _read_tlv(pdu, i)      # varbind list
    return {
        "version": version,
        "community": community,
        "v1_generic": _decode_int(gen_b),
        "varbinds": _read_varbinds(vbl),
    }


def extract_link_event(parsed: Dict[str, Any]) -> Tuple[Optional[str], Optional[int]]:
    """从解析结果提取 (event:'up'|'down'|None, if_index|None)"""
    event = None
    if_index = None

    # v1：generic-trap 2=linkDown 3=linkUp
    g = parsed.get("v1_generic")
    if g == 2:
        event = "down"
    elif g == 3:
        event = "up"

    for oid, vt, val in parsed.get("varbinds", []):
        # v2c：snmpTrapOID 指明 linkDown/linkUp
        if oid == SNMP_TRAP_OID and vt == 0x06:
            trap_oid = _decode_oid(val)
            if trap_oid == LINKDOWN_OID:
                event = "down"
            elif trap_oid == LINKUP_OID:
                event = "up"
        # ifTable 任意列变量，末段即 ifIndex
        elif oid.startswith(IFTABLE_PREFIX):
            suffix = oid[len(IFTABLE_PREFIX):].split(".")
            if suffix:
                try:
                    if_index = int(suffix[-1])
                except ValueError:
                    pass

    return event, if_index


class TrapReceiver:
    """UDP/162 SNMP Trap 接收器（线程 + 阻塞 socket）"""

    def __init__(self):
        self._sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self.bind_host = os.getenv("SNMP_TRAP_BIND", "0.0.0.0")
        self.bind_port = int(os.getenv("SNMP_TRAP_PORT", "162"))
        # 可选：仅接受指定 community（留空表示全部接受）
        self.community = os.getenv("SNMP_TRAP_COMMUNITY", "").strip()
        self._db_lock = threading.Lock()
        self.received = 0
        self.applied = 0

    def start(self):
        if self._running:
            logger.warning("Trap receiver already running")
            return
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((self.bind_host, self.bind_port))
            sock.settimeout(1.0)
            self._sock = sock
        except PermissionError:
            logger.warning(
                f"绑定 UDP/{self.bind_port} 需要 root 权限（或 setcap cap_net_bind_service），"
                f"Trap 接收器未启动；可设 SNMP_TRAP_PORT 用高位端口测试"
            )
            self._sock = None
            return
        except OSError as e:
            logger.warning(f"Trap 接收器绑定 {self.bind_host}:{self.bind_port} 失败: {e}")
            self._sock = None
            return

        self._running = True
        self._thread = threading.Thread(target=self._serve, name="snmp-trap-rx", daemon=True)
        self._thread.start()
        logger.info(f"SNMP Trap 接收器已启动 (UDP {self.bind_host}:{self.bind_port})")

    def stop(self):
        self._running = False
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
        logger.info("SNMP Trap 接收器已停止")

    def diagnostics(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "bind": f"{self.bind_host}:{self.bind_port}",
            "received": self.received,
            "applied": self.applied,
            "community_filter": bool(self.community),
        }

    # ===== 内部 =====
    def _serve(self):
        while self._running and self._sock:
            try:
                data, addr = self._sock.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                break
            self.received += 1
            try:
                self._handle_packet(data, addr[0])
            except Exception as e:
                logger.debug(f"Trap 处理失败 from {addr}: {e}")

    def _handle_packet(self, data: bytes, src_ip: str):
        parsed = parse_snmp_trap(data)
        if not parsed:
            return
        if self.community and parsed.get("community") != self.community:
            logger.debug(f"Trap community 不匹配，忽略 from {src_ip}")
            return
        event, if_index = extract_link_event(parsed)
        if event is None or if_index is None:
            return
        with self._db_lock:
            self._apply_link_event(src_ip, if_index, event)

    def _apply_link_event(self, src_ip: str, if_index: int, event: str):
        new_oper = "up" if event == "up" else "down"
        db = next(get_db())
        try:
            device = db.query(Device).filter(Device.ip == src_ip).first()
            if not device:
                logger.debug(f"Trap 源 {src_ip} 未匹配到设备")
                return
            iface = db.query(DeviceInterface).filter(
                DeviceInterface.device_id == device.id,
                DeviceInterface.if_index == if_index,
            ).first()
            old_oper = iface.oper_status if iface else None
            if iface:
                iface.oper_status = new_oper
                iface.last_check = datetime.utcnow()
                db.commit()
            self.applied += 1
            # 秒级推送（即使接口未发现也推送，让大屏即时感知）
            if old_oper != new_oper:
                self._broadcast(device, if_index, iface, old_oper, new_oper)
                logger.info(f"Trap link{event} {device.name} ifIndex={if_index} ({old_oper}->{new_oper})")
        except Exception as e:
            db.rollback()
            logger.error(f"应用 Trap 链路事件失败: {e}")
        finally:
            db.close()

    def _broadcast(self, device, if_index, iface, old_oper, new_oper):
        try:
            from app.features.websocket.router import broadcast_device_status_sync
            broadcast_device_status_sync({
                "event": "interface_status_change",
                "device_id": device.id,
                "device_name": device.name,
                "if_index": if_index,
                "if_name": (iface.if_name if iface else "") or "",
                "is_uplink": bool(iface.is_uplink) if iface else False,
                "old_status": old_oper or "unknown",
                "new_status": new_oper,
                "source": "trap",
                "timestamp": datetime.utcnow().isoformat(),
            })
        except Exception as e:
            logger.error(f"推送 Trap 接口状态失败: {e}")


_trap_receiver: Optional[TrapReceiver] = None


def get_trap_receiver() -> TrapReceiver:
    global _trap_receiver
    if _trap_receiver is None:
        _trap_receiver = TrapReceiver()
    return _trap_receiver


def start_trap_receiver():
    receiver = get_trap_receiver()
    receiver.start()
    return receiver


def stop_trap_receiver():
    if _trap_receiver:
        _trap_receiver.stop()
