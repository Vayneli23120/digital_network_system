"""
Tests for Monitor3D incident command summary helpers.
"""

from app.services.incident_insights import build_impact_scope, build_root_cause_candidates
from app.shared.models import FaultRecord


def _fault(**kwargs):
    defaults = {
        "id": 1,
        "fault_no": "INC-20260627-0001",
        "device_id": 1,
        "device_name": "Access-01",
        "severity": "major",
        "status": "assigned",
        "incident_type": "device_down",
        "source_event": "device_unreachable",
        "event_count": 1,
        "review_required": True,
    }
    defaults.update(kwargs)
    return FaultRecord(**defaults)


def test_root_cause_candidates_group_multiple_device_down_faults():
    candidates = build_root_cause_candidates([
        _fault(id=1, device_id=1, device_name="Access-01"),
        _fault(id=2, device_id=2, device_name="Access-02"),
        _fault(id=3, device_id=3, device_name="Access-03", severity="warning"),
    ])

    assert candidates
    grouped = next(item for item in candidates if "多设备同时离线" in item["candidate"])
    assert grouped["impacted_devices"] == 3
    assert grouped["confidence"] > 0.6


def test_root_cause_candidates_prioritize_core_critical_fault():
    candidates = build_root_cause_candidates([
        _fault(id=1, device_id=1, device_name="Access-01", severity="major"),
        _fault(
            id=2,
            device_id=2,
            device_name="Core-01",
            severity="critical",
            incident_type="uplink_down",
            source_event="link_down",
            if_name="Gi1/0/48",
        ),
    ])

    assert candidates[0]["device_id"] == 2
    assert "Core-01" in candidates[0]["candidate"]
    assert "critical/core signal" in candidates[0]["evidence"]


def test_root_cause_candidates_fallback_to_single_active_fault():
    candidates = build_root_cause_candidates([
        _fault(id=7, device_id=7, device_name="AP-01", severity="warning", incident_type="other"),
    ])

    assert len(candidates) == 1
    assert candidates[0]["fault_id"] == 7
    assert candidates[0]["impacted_devices"] == 1


def test_impact_scope_empty_faults():
    scope = build_impact_scope([])

    assert scope["level"] == "none"
    assert scope["impacted_devices"] == []
    assert scope["primary_fault"] is None


def test_impact_scope_single_device():
    scope = build_impact_scope([
        _fault(id=4, device_id=4, device_name="Access-04", severity="major"),
    ])

    assert scope["level"] == "major"
    assert scope["summary"] == "Access-04 受影响"
    assert scope["impacted_devices"][0]["device_id"] == 4
    assert scope["primary_fault"]["fault_id"] == 4


def test_impact_scope_multiple_devices_counts_severity():
    scope = build_impact_scope([
        _fault(id=1, device_id=1, device_name="Core-01", severity="critical"),
        _fault(id=2, device_id=2, device_name="Access-02", severity="major"),
        _fault(id=3, device_id=3, device_name="AP-03", severity="warning"),
    ])

    assert scope["level"] == "critical"
    assert len(scope["impacted_devices"]) == 3
    assert scope["severity_counts"]["critical"] == 1
    assert scope["severity_counts"]["major"] == 1
    assert scope["primary_fault"]["device_id"] == 1