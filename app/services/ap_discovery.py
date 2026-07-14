"""
AP 发现与在线判定（基于交换机 CDP/LLDP 邻居）

设计背景：瘦 AP 由 WLC 管理、不开 SSH，直接探测会失败。但瘦 AP 接在接入交换机
的端口上并默认发送 CDP，所以交换机的 CDP/LLDP 邻居表天然包含 AP 的名称/型号/IP。

本模块职责：
- is_ap_neighbor：根据 CDP 平台/主机名特征判定某个邻居是否为 AP（纯函数，可离线测试）
- upsert_ap_from_neighbor：从交换机邻居记录自动创建/更新 AP 设备
- sync_ap_online_status：以 AP 所连交换机端口的 oper_status 判定 AP 在线/离线

AP 只监控“是否在线”，不监控详细状态；在线判据 = 所连交换机端口 up（近实时，
走现有 SNMP/Prometheus 采集），CDP 负责发现与身份。
"""

import os
import re
from datetime import datetime
from typing import Optional

from loguru import logger
from sqlalchemy import func

from app.shared.models import Device, DeviceInterface

# Cisco AP 平台/型号特征（CDP cdpCachePlatform / LLDP sysDesc）
AP_PLATFORM_PATTERNS = [
    r"\bAIR-",                  # Aironet: AIR-AP2802I, AIR-CAP3702
    r"AIRONET",
    r"\bC9(1\d{2})",            # Catalyst 9100 系列 AP：C9120 / C9130 / C9115
    r"\bCW9\d",                 # Catalyst Wireless：CW9163 等
]
# 实验室/自定义：主机名匹配（PNETLab 模拟 AP 用），可用环境变量覆盖。
# 默认匹配含独立 "ap" 词元的主机名（office-ap-01 / ap-3f-12），但不误伤 "apc"(控制器)。
AP_HOSTNAME_PATTERN = os.environ.get("AP_HOSTNAME_PATTERN", r"(^|[-_])ap([-_]|\d|$)")

_platform_re = re.compile("|".join(AP_PLATFORM_PATTERNS), re.IGNORECASE)
_hostname_re = re.compile(AP_HOSTNAME_PATTERN, re.IGNORECASE)


def is_ap_neighbor(platform: str = "", host: str = "", capabilities: str = "") -> bool:
    """根据 CDP/LLDP 邻居特征判定是否为 AP（纯函数）。

    判据（任一命中即视为 AP）：
    - platform 命中 Cisco AP 型号特征（AIR-/Aironet/C91xx/CW9x）
    - CDP capabilities 含 WLAN / Trans-Bridge（AP 典型能力）
    - 主机名命中 AP 词元（供实验室模拟；可用 AP_HOSTNAME_PATTERN 覆盖）
    """
    platform = platform or ""
    host = host or ""
    capabilities = (capabilities or "").lower()

    if platform and _platform_re.search(platform):
        return True
    if "wlan" in capabilities or "trans-bridge" in capabilities or "trans bridge" in capabilities:
        return True
    if host and _hostname_re.search(host):
        return True
    return False


def upsert_ap_from_neighbor(db, neighbor: dict, switch_device: Device) -> Optional[Device]:
    """从交换机 CDP/LLDP 邻居创建/更新 AP 设备记录。

    先按 IP、再按主机名匹配已有设备；都没有则新建 device_type='ap' 记录。
    返回 AP Device（供调用方设置 peer 关联），无法确定身份时返回 None。
    """
    host = (neighbor.get("remote_host") or "").strip()
    ip = (neighbor.get("remote_ip") or "").strip()
    platform = (neighbor.get("remote_platform") or "").strip()
    if not host and not ip:
        return None

    ap = None
    if ip:
        ap = db.query(Device).filter(Device.ip == ip).first()
    if ap is None and host:
        ap = db.query(Device).filter(func.lower(Device.name) == host.lower()).first()

    if ap is None:
        # name 唯一约束：优先用主机名，冲突时回退附加 IP/端口后缀
        name = host or (f"AP-{ip}" if ip else "")
        if not name:
            return None
        if db.query(Device).filter(func.lower(Device.name) == name.lower()).first():
            suffix = ip or str(neighbor.get("local_if_index") or "")
            name = f"{name}-{suffix}" if suffix else name
        ap = Device(
            name=name[:100],
            ip=ip or None,
            model=platform[:100] or None,
            device_type="ap",
            deployment_status="in-use",
            reachability="unknown",
            reachability_method="cdp",
            monitor_tier="low",
        )
        db.add(ap)
        try:
            db.flush()
        except Exception as exc:
            db.rollback()
            logger.warning("Auto-create AP from neighbor failed (%s/%s): %s", host, ip, exc)
            return None
        logger.info("Auto-created AP from CDP/LLDP: %s (%s) via %s", ap.name, ap.ip or "-", switch_device.name)
    else:
        # 已存在：仅补齐缺失信息，不覆盖已有的设备类型/名称
        if ip and not ap.ip:
            ap.ip = ip
        if platform and not ap.model:
            ap.model = platform[:100]

    return ap


def sync_ap_online_status(db) -> int:
    """根据 AP 所连交换机端口的 oper_status 刷新 AP 在线状态。返回更新条数。

    在线判据：某台交换机上 peer_device_id == ap.id 的接口（AP 上联口）oper_status：
    up → reachable；down → unreachable；其它 → unknown。
    """
    aps = db.query(Device).filter(Device.device_type == "ap").all()
    if not aps:
        return 0

    now = datetime.utcnow()
    updated = 0
    for ap in aps:
        port = (
            db.query(DeviceInterface)
            .filter(DeviceInterface.peer_device_id == ap.id)
            .order_by(DeviceInterface.last_check.desc())
            .first()
        )
        if port is None:
            continue
        oper = (port.oper_status or "").lower()
        if oper == "up":
            new_reach = "reachable"
        elif oper == "down":
            new_reach = "unreachable"
        else:
            new_reach = "unknown"

        if ap.reachability != new_reach:
            ap.reachability = new_reach
            updated += 1
        ap.last_reachability_check = now
        ap.reachability_method = "cdp"

    return updated
