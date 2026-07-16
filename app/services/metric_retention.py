"""Bounded retention helpers for database-backed metric samples."""

from datetime import datetime
from typing import Dict, Type

from sqlalchemy.orm import Session

from app.shared.models import DeviceMetricSample, InterfaceTrafficSample


def _delete_expired_batch(
    db: Session,
    model: Type[DeviceMetricSample] | Type[InterfaceTrafficSample],
    cutoff: datetime,
    batch_size: int,
) -> int:
    ids = [
        row_id
        for row_id, in (
            db.query(model.id)
            .filter(model.ts < cutoff)
            .order_by(model.ts, model.id)
            .limit(batch_size)
            .all()
        )
    ]
    if not ids:
        return 0
    return (
        db.query(model)
        .filter(model.id.in_(ids))
        .delete(synchronize_session=False)
    )


def delete_expired_metric_samples_batch(
    db: Session,
    cutoff: datetime,
    *,
    batch_size: int = 5000,
) -> Dict[str, int]:
    """Delete at most one bounded batch per metric table without committing."""
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")

    return {
        "device_metric_samples": _delete_expired_batch(
            db,
            DeviceMetricSample,
            cutoff,
            batch_size,
        ),
        "interface_traffic_samples": _delete_expired_batch(
            db,
            InterfaceTrafficSample,
            cutoff,
            batch_size,
        ),
    }