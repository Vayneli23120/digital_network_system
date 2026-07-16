"""PostgreSQL validation for transactional metric retention behavior."""

from datetime import datetime
from uuid import uuid4

import pytest

from app.services.metric_retention import delete_expired_metric_samples_batch
from app.shared.models import (
    Device,
    DeviceInterface,
    DeviceMetricSample,
    InterfaceTrafficSample,
)


@pytest.mark.postgresql
def test_metric_retention_deletes_expired_rows_and_preserves_cutoff(db_manager):
    session = db_manager.get_session()
    test_id = uuid4().hex
    cutoff = datetime(1900, 1, 1)
    try:
        device = Device(
            name=f"METRIC-RETENTION-PG-{test_id}",
            ip="192.0.2.52",
        )
        session.add(device)
        session.flush()
        interface = DeviceInterface(
            device_id=device.id,
            if_index=1,
            if_name="Gi0/1",
        )
        session.add(interface)
        session.flush()

        session.add_all([
            DeviceMetricSample(
                device_id=device.id,
                ts=datetime(1899, 12, 31, 23, 59, 59),
            ),
            DeviceMetricSample(device_id=device.id, ts=cutoff),
            InterfaceTrafficSample(
                device_id=device.id,
                interface_id=interface.id,
                ts=datetime(1899, 12, 31, 23, 59, 59),
            ),
            InterfaceTrafficSample(
                device_id=device.id,
                interface_id=interface.id,
                ts=cutoff,
            ),
        ])
        session.flush()

        deleted = delete_expired_metric_samples_batch(
            session,
            cutoff,
            batch_size=1,
        )

        assert deleted == {
            "device_metric_samples": 1,
            "interface_traffic_samples": 1,
        }
        assert session.query(DeviceMetricSample).filter(
            DeviceMetricSample.device_id == device.id
        ).one().ts == cutoff
        assert session.query(InterfaceTrafficSample).filter(
            InterfaceTrafficSample.device_id == device.id
        ).one().ts == cutoff

    finally:
        session.rollback()
        session.close()