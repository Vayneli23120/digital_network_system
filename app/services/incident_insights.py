"""Incident insight helpers for Monitor3D command views."""

from collections import defaultdict
from typing import Dict, List, Optional

from app.shared.models import FaultRecord


SEVERITY_SCORE = {"minor": 1, "warning": 2, "major": 3, "critical": 4}


def fault_signal_score(fault: FaultRecord) -> float:
    score = float(SEVERITY_SCORE.get(fault.severity or "minor", 1))
    if fault.source_event in ("link_down", "device_unreachable"):
        score += 1.0
    if fault.review_required:
        score += 0.4
    score += min((fault.event_count or 1) - 1, 5) * 0.2
    return score


def build_root_cause_candidates(active_faults: List[FaultRecord]) -> List[Dict]:
    """MVP root-cause candidates aggregated from active fault signals."""
    candidates = []

    device_down_faults = [f for f in active_faults if f.incident_type == "device_down"]
    link_down_faults = [f for f in active_faults if f.incident_type in ("uplink_down", "access_port_down")]
    core_faults = [
        f for f in active_faults
        if (f.severity == "critical" or (f.device_name or "").lower().find("core") >= 0)
        and f.incident_type in ("device_down", "uplink_down")
    ]

    if core_faults:
        lead = max(core_faults, key=fault_signal_score)
        candidates.append({
            "candidate": f"{lead.device_name or lead.fault_no} {lead.incident_type or lead.source_event}",
            "confidence": min(0.95, 0.78 + len(core_faults) * 0.06 + len(device_down_faults) * 0.03),
            "impacted_devices": len({f.device_id for f in active_faults if f.device_id}),
            "fault_id": lead.id,
            "device_id": lead.device_id,
            "severity": lead.severity,
            "evidence": ["critical/core signal", "active fault", lead.source_event or lead.incident_type or "monitor event"],
        })

    if len(device_down_faults) >= 2:
        lead = max(device_down_faults, key=fault_signal_score)
        candidates.append({
            "candidate": "多设备同时离线，疑似共同上游链路或电源域异常",
            "confidence": min(0.9, 0.45 + len(device_down_faults) * 0.08),
            "impacted_devices": len({f.device_id for f in device_down_faults if f.device_id}),
            "fault_id": lead.id,
            "device_id": lead.device_id,
            "severity": lead.severity,
            "evidence": [f"{len(device_down_faults)} active device_down faults", "shared time window", "reachability alerts"],
        })

    if link_down_faults:
        lead = max(link_down_faults, key=fault_signal_score)
        iface = f" {lead.if_name}" if lead.if_name else ""
        candidates.append({
            "candidate": f"{lead.device_name or lead.fault_no}{iface} 链路中断",
            "confidence": min(0.88, 0.5 + fault_signal_score(lead) * 0.06),
            "impacted_devices": 1,
            "fault_id": lead.id,
            "device_id": lead.device_id,
            "severity": lead.severity,
            "evidence": [lead.source_event or "link_down", lead.if_name or "interface", "SNMP/Trap signal"],
        })

    if not candidates and active_faults:
        lead = max(active_faults, key=fault_signal_score)
        candidates.append({
            "candidate": f"{lead.device_name or lead.fault_no} {lead.incident_type or lead.source_event or lead.status}",
            "confidence": min(0.75, 0.35 + fault_signal_score(lead) * 0.06),
            "impacted_devices": 1 if lead.device_id else 0,
            "fault_id": lead.id,
            "device_id": lead.device_id,
            "severity": lead.severity,
            "evidence": ["active fault", lead.source_event or lead.status],
        })

    candidates.sort(key=lambda item: item["confidence"], reverse=True)
    return candidates[:3]


def build_shared_path_edges(active_faults: List[FaultRecord], device_paths: Optional[Dict]) -> List[Dict]:
    """Find shared topology path edges among active device-down faults."""
    if not device_paths:
        return []

    paths = device_paths.get("paths", device_paths)
    if not isinstance(paths, dict):
        return []

    device_down_ids = {
        fault.device_id
        for fault in active_faults
        if fault.device_id and fault.incident_type == "device_down"
    }
    if len(device_down_ids) < 2:
        return []

    edge_hits = defaultdict(lambda: {"devices": set(), "edge": None})
    for device_id in device_down_ids:
        path = paths.get(device_id) or paths.get(str(device_id))
        if not path or not path.get("reachable"):
            continue
        for edge in path.get("edges") or []:
            edge_id = edge.get("id")
            if edge_id is None:
                continue
            edge_hits[edge_id]["devices"].add(device_id)
            edge_hits[edge_id]["edge"] = edge

    shared = []
    for edge_id, data in edge_hits.items():
        if len(data["devices"]) < 2:
            continue
        edge = data["edge"] or {}
        shared.append({
            "edge_id": edge_id,
            "cable_id": edge.get("cable_id"),
            "cable_name": edge.get("cable_name") or f"Edge-{edge_id}",
            "cable_type": edge.get("cable_type"),
            "affected_devices": len(data["devices"]),
            "device_ids": sorted(data["devices"]),
        })

    shared.sort(key=lambda item: item["affected_devices"], reverse=True)
    return shared[:5]


def build_impact_scope(active_faults: List[FaultRecord], device_paths: Optional[Dict] = None) -> Dict:
    """Build an MVP impact scope from active faults.

    This version is intentionally signal-based and does not require live topology
    validation. A later version can enrich it with shared path/edge analysis.
    """
    if not active_faults:
        return {
            "level": "none",
            "summary": "暂无活跃影响",
            "impacted_devices": [],
            "severity_counts": {"critical": 0, "major": 0, "warning": 0, "minor": 0},
            "primary_fault": None,
            "shared_path_edges": [],
        }

    severity_counts = {"critical": 0, "major": 0, "warning": 0, "minor": 0}
    devices = {}
    for fault in active_faults:
        severity = fault.severity or "minor"
        if severity not in severity_counts:
            severity = "minor"
        severity_counts[severity] += 1

        if not fault.device_id:
            continue
        current = devices.get(fault.device_id)
        if not current or fault_signal_score(fault) > current["score"]:
            devices[fault.device_id] = {
                "device_id": fault.device_id,
                "device_name": fault.device_name,
                "severity": fault.severity,
                "fault_id": fault.id,
                "fault_no": fault.fault_no,
                "incident_type": fault.incident_type,
                "source_event": fault.source_event,
                "if_name": fault.if_name,
                "score": fault_signal_score(fault),
            }

    primary = max(active_faults, key=fault_signal_score)
    impacted_devices = sorted(devices.values(), key=lambda item: item["score"], reverse=True)
    for item in impacted_devices:
        item.pop("score", None)

    impacted_count = len(impacted_devices)
    if severity_counts["critical"] > 0 or impacted_count >= 5:
        level = "critical"
    elif severity_counts["major"] > 0 or impacted_count >= 2:
        level = "major"
    elif severity_counts["warning"] > 0:
        level = "warning"
    else:
        level = "minor"

    if impacted_count == 1:
        summary = f"{impacted_devices[0]['device_name'] or '1 台设备'} 受影响"
    else:
        summary = f"{impacted_count} 台设备受影响，{severity_counts['critical']} 个 critical，{severity_counts['major']} 个 major"

    shared_path_edges = build_shared_path_edges(active_faults, device_paths)
    if shared_path_edges:
        top_edge = shared_path_edges[0]
        summary = f"{impacted_count} 台设备受影响，共同经过 {top_edge['cable_name']}"

    return {
        "level": level,
        "summary": summary,
        "impacted_devices": impacted_devices[:10],
        "severity_counts": severity_counts,
        "shared_path_edges": shared_path_edges,
        "primary_fault": {
            "fault_id": primary.id,
            "fault_no": primary.fault_no,
            "device_id": primary.device_id,
            "device_name": primary.device_name,
            "severity": primary.severity,
            "incident_type": primary.incident_type,
            "source_event": primary.source_event,
        },
    }


def build_hot_links(active_faults: List[FaultRecord], limit: int = 5) -> List[Dict]:
    """Return active link-related faults ranked for the Monitor3D command panel."""
    link_faults = [
        fault for fault in active_faults
        if fault.incident_type in ("uplink_down", "access_port_down") or fault.source_event == "link_down"
    ]
    ranked = sorted(link_faults, key=fault_signal_score, reverse=True)

    return [
        {
            "fault_id": fault.id,
            "fault_no": fault.fault_no,
            "device_id": fault.device_id,
            "device_name": fault.device_name,
            "if_index": fault.if_index,
            "if_name": fault.if_name,
            "peer_device_id": fault.peer_device_id,
            "peer_if_name": fault.peer_if_name,
            "severity": fault.severity,
            "status": fault.status,
            "incident_type": fault.incident_type,
            "source_event": fault.source_event,
            "event_count": fault.event_count or 1,
            "score": round(fault_signal_score(fault), 2),
        }
        for fault in ranked[:limit]
    ]