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


def test_interface_poll_uplink_down_creates_fault(db_session, monkeypatch):
    """接口轮询检测到上行口 down 也应自动建单（修复：之前只广播不建单）。"""
    monkeypatch.setattr("app.services.incident_automation.notify_incident", lambda *args, **kwargs: None)
    device = _add_device(db_session)

    fault = upsert_fault_from_monitor_event(db_session, MonitorEvent(
        source_type="interface_poll",
        event_type="link_down",
        device_id=device.id,
        device_name=device.name,
        ip=device.ip,
        if_index=10,
        if_name="GigabitEthernet0/1",
        raw={"is_uplink": True},
    ))

    assert fault is not None
    assert fault.status == "assigned"
    assert fault.severity == "critical"  # 上行口 + 核心交换机
    assert fault.incident_type == "uplink_down"
    assert fault.source_type == "interface_poll"
    assert fault.source_key == f"device:{device.id}:if:10:link_down"
    assert fault.if_index == 10


def test_interface_poll_link_up_resolves_existing_fault(db_session, monkeypatch):
    """同一上行口先 down（Trap 或轮询）后 up（轮询）应恢复同一张工单，不重复建单。"""
    monkeypatch.setattr("app.services.incident_automation.notify_incident", lambda *args, **kwargs: None)
    device = _add_device(db_session)

    down_fault = upsert_fault_from_monitor_event(db_session, MonitorEvent(
        source_type="trap",
        event_type="link_down",
        device_id=device.id,
        if_index=10,
        if_name="GigabitEthernet0/1",
        raw={"is_uplink": True},
    ))
    up_fault = upsert_fault_from_monitor_event(db_session, MonitorEvent(
        source_type="interface_poll",
        event_type="link_up",
        device_id=device.id,
        if_index=10,
        if_name="GigabitEthernet0/1",
        raw={"is_uplink": True},
        occurred_at=datetime.utcnow() + timedelta(minutes=2),
    ))

    assert up_fault is not None
    assert up_fault.id == down_fault.id
    assert up_fault.status == "resolved"
    assert db_session.query(FaultRecord).count() == 1


def test_quick_recovery_is_marked_flap_false_positive(db_session, monkeypatch):
    """故障在抑制窗口内自动恢复 -> 标记 false_positive 且不发送恢复通知。"""
    notes = []
    monkeypatch.setattr(
        "app.services.incident_automation.notify_incident",
        lambda *args, **kwargs: notes.append(kwargs.get("recovered")),
    )
    device = _add_device(db_session)

    created = upsert_fault_from_monitor_event(db_session, MonitorEvent(
        source_type="reachability",
        event_type="device_unreachable",
        device_id=device.id,
        occurred_at=datetime.utcnow(),
    ))
    recovered = upsert_fault_from_monitor_event(db_session, MonitorEvent(
        source_type="reachability",
        event_type="device_recovered",
        device_id=device.id,
        occurred_at=datetime.utcnow() + timedelta(seconds=30),  # < 90s 抑制窗口
    ))

    assert recovered.id == created.id
    assert recovered.status == "resolved"
    assert recovered.false_positive is True
    assert recovered.review_required is False
    assert "抖动抑制" in (recovered.resolution or "")
    # 只在建单时通知一次（recovered=False），恢复通知被抑制
    assert notes == [False]


def test_sustained_outage_recovery_is_not_flap(db_session, monkeypatch):
    """故障存续超过抑制窗口 -> 正常恢复并发送恢复通知，不标记 false_positive。"""
    notes = []
    monkeypatch.setattr(
        "app.services.incident_automation.notify_incident",
        lambda *args, **kwargs: notes.append(kwargs.get("recovered")),
    )
    device = _add_device(db_session)

    created = upsert_fault_from_monitor_event(db_session, MonitorEvent(
        source_type="reachability",
        event_type="device_unreachable",
        device_id=device.id,
        occurred_at=datetime.utcnow(),
    ))
    recovered = upsert_fault_from_monitor_event(db_session, MonitorEvent(
        source_type="reachability",
        event_type="device_recovered",
        device_id=device.id,
        occurred_at=datetime.utcnow() + timedelta(minutes=10),  # > 90s
    ))

    assert recovered.id == created.id
    assert recovered.status == "resolved"
    assert recovered.false_positive is False
    assert notes == [False, True]