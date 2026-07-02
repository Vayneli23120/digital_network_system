"""Tests for SNMP interface monitor scheduling behavior."""

import time

import pytest

pytest.importorskip("apscheduler")

from app.services.interface_monitor import InterfaceMonitor


def _target(device_id: int, device_type: str = "switch") -> dict:
    return {
        "id": device_id,
        "name": f"Device-{device_id}",
        "ip": f"10.0.0.{device_id}",
        "community": "public",
        "device_type": device_type,
        "if_indexes": [1],
    }


def test_device_intervals_are_30_or_60_seconds():
    monitor = InterfaceMonitor()

    assert monitor._get_device_interval("core_switch") == 30
    assert monitor._get_device_interval("router") == 30
    assert monitor._get_device_interval("switch") == 60
    assert monitor._get_device_interval("ap") == 60
    assert monitor._get_device_interval(None) == 60


def test_failed_poll_uses_fast_retry_interval():
    monitor = InterfaceMonitor()
    started_at = time.time()

    monitor._finish_target_poll(_target(1, "core_switch"), success=False)

    next_poll_in = monitor._schedule[1] - started_at
    assert 0 < next_poll_in <= monitor.retry_interval + 1


def test_finish_target_poll_records_collector_state():
    monitor = InterfaceMonitor()

    monitor._finish_target_poll(_target(1), success=True, poll_result={
        "ok": True,
        "status": "partial",
        "duration_ms": 1234,
        "poll_mode": "table_snapshot+get",
        "monitored_count": 3,
        "readings_count": 2,
        "missing_counter_count": 1,
        "fallback_count": 1,
    })

    state = monitor.get_poll_state_snapshot()[1]
    assert state["status"] == "partial"
    assert state["duration_ms"] == 1234
    assert state["missing_counter_count"] == 1
    assert state["next_poll_in_seconds"] is not None


def test_claim_due_targets_limits_batch_and_skips_inflight_devices():
    monitor = InterfaceMonitor()
    monitor.max_concurrency = 1
    targets = [_target(1), _target(2)]

    first_batch = monitor._claim_due_targets(targets)
    second_batch = monitor._claim_due_targets(targets)

    assert [target["id"] for target in first_batch] == [1]
    assert [target["id"] for target in second_batch] == [2]