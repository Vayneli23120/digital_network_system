"""
Tests for monitor-event incident automation.

These tests intentionally avoid real devices, Trap receivers, and notification
channels so the MVP can be validated while the test environment is offline.
"""

from datetime import datetime, timedelta

from app.services.incident_automation import MonitorEvent, upsert_fault_from_monitor_event
from app.shared.models import Device, FaultRecord


def _add_device(db_session, name="SW-Core-01", ip="10.0.0.1", device_type="core_switch"):
    device = Device(name=name, ip=ip, device_type=device_type, status="online")
    db_session.add(device)
    db_session.commit()
    db_session.refresh(device)
    return device


def test_device_unreachable_creates_assigned_fault(db_session, monkeypatch):
    monkeypatch.setattr("app.services.incident_automation.notify_incident", lambda *args, **kwargs: None)
    device = _add_device(db_session)

    fault = upsert_fault_from_monitor_event(db_session, MonitorEvent(
        source_type="reachability",
        event_type="device_unreachable",
        device_id=device.id,
        device_name=device.name,
        ip=device.ip,
    ))

    assert fault is not None
    assert fault.status == "assigned"
    assert fault.severity == "critical"
    assert fault.fault_type == "network"
    assert fault.incident_type == "device_down"
    assert fault.source_type == "reachability"
    assert fault.source_key == f"device:{device.id}:unreachable"
    assert fault.source_event == "device_unreachable"
    assert fault.event_count == 1
    assert fault.review_required is True
    assert fault.recommendation


def test_duplicate_unreachable_event_updates_existing_fault(db_session, monkeypatch):
    monkeypatch.setattr("app.services.incident_automation.notify_incident", lambda *args, **kwargs: None)
    device = _add_device(db_session)

    first_fault = upsert_fault_from_monitor_event(db_session, MonitorEvent(
        source_type="reachability",
        event_type="device_unreachable",
        device_id=device.id,
        occurred_at=datetime.utcnow(),
    ))
    second_fault = upsert_fault_from_monitor_event(db_session, MonitorEvent(
        source_type="reachability",
        event_type="device_unreachable",
        device_id=device.id,
        occurred_at=datetime.utcnow() + timedelta(minutes=1),
    ))

    faults = db_session.query(FaultRecord).all()
    assert len(faults) == 1
    assert second_fault.id == first_fault.id
    assert second_fault.event_count == 2
    assert "第 2 次" in second_fault.diagnosis_text


def test_device_recovered_resolves_open_fault(db_session, monkeypatch):
    monkeypatch.setattr("app.services.incident_automation.notify_incident", lambda *args, **kwargs: None)
    device = _add_device(db_session)

    created_fault = upsert_fault_from_monitor_event(db_session, MonitorEvent(
        source_type="reachability",
        event_type="device_unreachable",
        device_id=device.id,
    ))
    resolved_fault = upsert_fault_from_monitor_event(db_session, MonitorEvent(
        source_type="reachability",
        event_type="device_recovered",
        device_id=device.id,
        occurred_at=datetime.utcnow() + timedelta(minutes=5),
    ))

    assert resolved_fault.id == created_fault.id
    assert resolved_fault.status == "resolved"
    assert resolved_fault.resolved_at is not None
    assert resolved_fault.event_count == 2
    assert "device_recovered" in resolved_fault.resolution


def test_recovered_without_open_fault_returns_none(db_session, monkeypatch):
    monkeypatch.setattr("app.services.incident_automation.notify_incident", lambda *args, **kwargs: None)
    device = _add_device(db_session)

    fault = upsert_fault_from_monitor_event(db_session, MonitorEvent(
        source_type="reachability",
        event_type="device_recovered",
        device_id=device.id,
    ))

    assert fault is None
    assert db_session.query(FaultRecord).count() == 0