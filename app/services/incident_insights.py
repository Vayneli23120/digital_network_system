"""Incident insight helpers for Monitor3D command views."""

from typing import Dict, List

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