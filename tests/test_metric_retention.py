"""Tests for bounded metric sample retention."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import inspect

from app.services.metric_retention import delete_expired_metric_samples_batch
from app.services import prometheus_connector as connector_module
from app.services.prometheus_connector import PrometheusConnector
from app.shared.models import (
    Device,
    DeviceInterface,
    DeviceMetricSample,
    InterfaceTrafficSample,
)


def test_retention_deletes_only_expired_rows_in_bounded_batches(db_session):
    cutoff = datetime(2026, 4, 17, 12, 0, 0)
    device = Device(name="Retention-Device", ip="192.0.2.50")
    db_session.add(device)
    db_session.flush()
    interface = DeviceInterface(device_id=device.id, if_index=1, if_name="Gi0/1")
    db_session.add(interface)
    db_session.flush()

    for offset in (2, 1):
        expired_at = cutoff - timedelta(days=offset)
        db_session.add(DeviceMetricSample(device_id=device.id, ts=expired_at))
        db_session.add(
            InterfaceTrafficSample(
                device_id=device.id,
                interface_id=interface.id,
                ts=expired_at,
            )
        )

    for retained_at in (cutoff, cutoff + timedelta(seconds=1)):
        db_session.add(DeviceMetricSample(device_id=device.id, ts=retained_at))
        db_session.add(
            InterfaceTrafficSample(
                device_id=device.id,
                interface_id=interface.id,
                ts=retained_at,
            )
        )
    db_session.flush()

    first = delete_expired_metric_samples_batch(
        db_session,
        cutoff,
        batch_size=1,
    )
    second = delete_expired_metric_samples_batch(
        db_session,
        cutoff,
        batch_size=1,
    )
    third = delete_expired_metric_samples_batch(
        db_session,
        cutoff,
        batch_size=1,
    )

    assert first == {
        "device_metric_samples": 1,
        "interface_traffic_samples": 1,
    }
    assert second == first
    assert third == {
        "device_metric_samples": 0,
        "interface_traffic_samples": 0,
    }
    assert [row.ts for row in db_session.query(DeviceMetricSample).all()] == [
        cutoff,
        cutoff + timedelta(seconds=1),
    ]
    assert [row.ts for row in db_session.query(InterfaceTrafficSample).all()] == [
        cutoff,
        cutoff + timedelta(seconds=1),
    ]


def test_retention_rejects_unbounded_batch_size(db_session):
    with pytest.raises(ValueError, match="batch_size"):
        delete_expired_metric_samples_batch(
            db_session,
            datetime.utcnow(),
            batch_size=0,
        )


def test_device_metric_retention_timestamp_is_indexed(db_manager):
    indexes = inspect(db_manager.engine).get_indexes("device_metric_samples")

    assert any(
        index["name"] == "idx_device_metric_ts"
        and index["column_names"] == ["ts"]
        for index in indexes
    )


def test_connector_cleanup_drains_multiple_batches(
    db_manager,
    db_session,
    monkeypatch,
):
    device = Device(name="Retention-Connector-Device", ip="192.0.2.51")
    db_session.add(device)
    db_session.flush()
    expired_at = datetime.utcnow() - timedelta(days=10)
    for _ in range(5):
        db_session.add(DeviceMetricSample(device_id=device.id, ts=expired_at))
    db_session.commit()

    connector = PrometheusConnector(
        "http://prometheus.test",
        metric_retention_days=5,
        metric_cleanup_batch_size=2,
    )
    monkeypatch.setattr(connector_module, "get_db_manager", lambda: db_manager)
    try:
        deleted = connector.cleanup_old_metric_samples()
    finally:
        connector._http.close()

    assert deleted == {
        "device_metric_samples": 5,
        "interface_traffic_samples": 0,
    }
    db_session.expire_all()
    assert db_session.query(DeviceMetricSample).count() == 0