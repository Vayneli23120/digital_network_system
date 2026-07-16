"""Tests for the canonical device metric fact layer."""

from datetime import datetime, timedelta

import pytest

from app.features.devices import router as devices_router
from app.features.devices.router import (
    get_device_performance_metric_history,
    get_device_performance_metrics,
)
from app.services.device_metric_facts import (
    get_device_metric_samples,
    record_device_metric_sample,
)
from app.shared.models import Device, DeviceMetricSample


def test_record_device_metric_sample_normalizes_collector_payload(db_session):
    device = Device(name="Metric-Fact-Device", ip="192.0.2.30")
    db_session.add(device)
    db_session.flush()

    sample = record_device_metric_sample(
        db_session,
        device.id,
        {
            "cpu": {"value": "42.5"},
            "memory": {
                "used_percent": 61,
                "used_mb": "512.5",
                "total_mb": 1024,
            },
            "temperature": {"value": 37.2},
            "uptime": {"uptime_days": 12},
            "interfaces": {"up": 24, "down": 2, "total": 26},
            "errors": {"total_errors": 3},
        },
    )

    assert sample.collection_status == "complete"
    assert sample.cpu_percent == 42.5
    assert sample.memory_percent == 61.0
    assert sample.memory_used_mb == 512.5
    assert sample.memory_total_mb == 1024.0
    assert sample.temperature_c == 37.2
    assert sample.uptime_days == 12
    assert sample.interfaces_total == 26
    assert sample.total_errors == 3


def test_metric_history_is_bounded_and_chronological(db_session):
    device = Device(name="Metric-History-Device", ip="192.0.2.31")
    db_session.add(device)
    db_session.flush()
    start = datetime(2026, 7, 16, 8, 0, 0)

    for offset in range(3):
        record_device_metric_sample(
            db_session,
            device.id,
            {"cpu": {"value": 10 + offset}},
            ts=start + timedelta(minutes=offset),
        )

    samples = get_device_metric_samples(db_session, device.id, limit=2)

    assert [sample.cpu_percent for sample in samples] == [11.0, 12.0]
    assert samples[0].ts < samples[1].ts


@pytest.mark.asyncio
async def test_device_metrics_api_preserves_response_and_records_history(
    db_session,
    monkeypatch,
):
    class FakeSNMPService:
        def is_available(self):
            return True

        async def get_device_metrics_async(self, ip, community, vendor):
            return {
                "cpu": {"value": 35.0, "status": "normal"},
                "memory": {"used_percent": 55.0, "status": "normal"},
                "temperature": {"value": 41.0, "status": "warning"},
                "uptime": {"uptime_days": 20, "human": "20天"},
                "interfaces": {"up": 10, "down": 1, "total": 11},
                "errors": {"total_errors": 2, "has_errors": True},
                "uplinks": [],
                "timestamp": "2026-07-16T08:30:00",
            }

    monkeypatch.setattr(
        "app.features.devices.snmp_service.get_snmp_service",
        lambda: FakeSNMPService(),
    )
    device = Device(
        name="Metric-API-Device",
        ip="192.0.2.32",
        vendor="cisco",
        snmp_enabled=True,
        snmp_community="test-read",
    )
    db_session.add(device)
    db_session.commit()

    response = await get_device_performance_metrics(device.id, db_session)

    assert response["cpu"]["value"] == 35.0
    assert response["memory"]["used_percent"] == 55.0
    assert response["temperature"]["value"] == 41.0
    assert response["snmp_available"] is True
    assert response["device_ip"] == device.ip

    sample = db_session.query(DeviceMetricSample).filter(
        DeviceMetricSample.device_id == device.id
    ).one()
    assert sample.collection_status == "complete"

    history = await get_device_performance_metric_history(
        device.id,
        limit=60,
        db=db_session,
    )
    assert history["device_name"] == device.name
    assert history["samples"][0]["cpu_percent"] == 35.0
    assert history["samples"][0]["source"] == "snmp_live"


@pytest.mark.asyncio
async def test_metric_persistence_failure_does_not_break_live_response(
    db_session,
    monkeypatch,
):
    class FakeSNMPService:
        def is_available(self):
            return True

        async def get_device_metrics_async(self, ip, community, vendor):
            return {
                "cpu": {"value": 28.0, "status": "normal"},
                "memory": {"used_percent": None, "status": "unknown"},
                "temperature": {"value": None, "status": "unknown"},
                "uptime": {"uptime_days": 5, "human": "5天"},
                "interfaces": {"up": 4, "down": 0, "total": 4},
                "errors": {"total_errors": 0, "has_errors": False},
                "uplinks": [],
                "timestamp": "2026-07-16T09:00:00",
            }

    monkeypatch.setattr(
        "app.features.devices.snmp_service.get_snmp_service",
        lambda: FakeSNMPService(),
    )

    def fail_persistence(*args, **kwargs):
        raise RuntimeError("metric table unavailable")

    monkeypatch.setattr(
        devices_router,
        "record_device_metric_sample",
        fail_persistence,
    )
    device = Device(
        name="Metric-Fallback-Device",
        ip="192.0.2.33",
        snmp_enabled=True,
        snmp_community="test-read",
    )
    db_session.add(device)
    db_session.commit()

    response = await get_device_performance_metrics(device.id, db_session)

    assert response["cpu"]["value"] == 28.0
    assert response["snmp_available"] is True
    assert response["device_ip"] == device.ip