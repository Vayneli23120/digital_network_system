"""Monitor3D traffic heat-layer helpers."""

from datetime import datetime, timedelta
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from app.shared.models import Device, DeviceInterface
from app.shared.time_utils import utc_iso


STALE_AFTER = timedelta(minutes=10)


def classify_traffic_heat(
    in_util: Optional[float],
    out_util: Optional[float],
    oper_status: Optional[str] = None,
    sample_at: Optional[datetime] = None,
    now: Optional[datetime] = None,
    device_reachability: Optional[str] = None,
) -> dict:
    """Classify the latest interface state for the Monitor3D heat layer."""
    now = now or datetime.utcnow()
    status = (oper_status or "unknown").lower()
    reachability = (device_reachability or "").lower()
    # 设备不可达时，SNMP 无法把接口 oper_status 置为 down（探测本身失败），
    # 此时应直接按“中断”呈现，而不是沿用旧的 up 状态被判成空闲/过期。
    if status == "down" or reachability == "unreachable":
        return {
            "level": "down",
            "utilization": max([value for value in [in_util, out_util] if value is not None], default=0.0),
            "color": "#ef4444",
            "width": 5,
            "particle_speed": 0,
            "stale": False,
        }

    utilization = max([value for value in [in_util, out_util] if value is not None], default=0.0)
    stale = sample_at is None or sample_at < now - STALE_AFTER
    if stale:
        return {
            "level": "stale",
            "utilization": 0.0,
            "color": "#64748b",
            "width": 1,
            "particle_speed": 0,
            "stale": True,
        }
    if utilization >= 80:
        return {
            "level": "critical",
            "utilization": utilization,
            "color": "#f97316",
            "width": 6,
            "particle_speed": 1.4,
            "stale": False,
        }
    if utilization >= 60:
        return {
            "level": "high",
            "utilization": utilization,
            "color": "#facc15",
            "width": 4,
            "particle_speed": 1.0,
            "stale": False,
        }
    if utilization >= 20:
        return {
            "level": "normal",
            "utilization": utilization,
            "color": "#22d3ee",
            "width": 3,
            "particle_speed": 0.7,
            "stale": False,
        }
    return {
        "level": "low",
        "utilization": utilization,
        "color": "#22c55e",
        "width": 2,
        "particle_speed": 0.4,
        "stale": False,
    }


def dominant_direction(in_bps: Optional[int], out_bps: Optional[int]) -> str:
    in_bps = in_bps or 0
    out_bps = out_bps or 0
    if in_bps == out_bps:
        return "balanced"
    return "in" if in_bps > out_bps else "out"


def build_traffic_heat_items(db: Session, plan_device_ids: Optional[Iterable[int]] = None) -> list[dict]:
    query = db.query(DeviceInterface, Device).join(Device, Device.id == DeviceInterface.device_id).filter(
        DeviceInterface.monitored == True,  # noqa: E712
    )
    if plan_device_ids is not None:
        device_ids = list(plan_device_ids)
        if not device_ids:
            return []
        query = query.filter(DeviceInterface.device_id.in_(device_ids))

    now = datetime.utcnow()
    items = []
    for iface, device in query.all():
        heat = classify_traffic_heat(
            iface.last_in_util,
            iface.last_out_util,
            iface.oper_status,
            iface.last_sample_at,
            now,
            device.reachability,
        )
        items.append({
            "device_id": iface.device_id,
            "device_name": device.name,
            "if_index": iface.if_index,
            "if_name": iface.if_name,
            "peer_device_id": iface.peer_device_id,
            "peer_device_name": iface.peer_device_name,
            "peer_if_name": iface.peer_if_name,
            "is_uplink": bool(iface.is_uplink),
            "oper_status": iface.oper_status,
            "last_sample_at": utc_iso(iface.last_sample_at),
            "in_bps": iface.last_in_bps,
            "out_bps": iface.last_out_bps,
            "in_util": iface.last_in_util,
            "out_util": iface.last_out_util,
            "direction": dominant_direction(iface.last_in_bps, iface.last_out_bps),
            **heat,
        })

    level_order = {"critical": 0, "down": 1, "high": 2, "normal": 3, "low": 4, "stale": 5}
    return sorted(items, key=lambda item: (level_order.get(item["level"], 9), -(item["utilization"] or 0)))