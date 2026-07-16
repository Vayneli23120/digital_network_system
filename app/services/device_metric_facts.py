"""Canonical persistence and query helpers for device performance facts."""

from datetime import datetime
from math import isfinite
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.shared.models import DeviceMetricSample
from app.shared.time_utils import utc_iso


def _number(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def _integer(value: Any) -> Optional[int]:
    number = _number(value)
    return int(number) if number is not None else None


def _collection_status(metrics: Dict[str, Any], primary_values: list[Optional[float]]) -> str:
    if metrics.get("error"):
        return "error"
    if all(value is not None for value in primary_values):
        return "complete"
    if any(value is not None for value in primary_values):
        return "partial"
    return "empty"


def record_device_metric_sample(
    db: Session,
    device_id: int,
    metrics: Dict[str, Any],
    *,
    source: str = "snmp_live",
    ts: Optional[datetime] = None,
) -> DeviceMetricSample:
    """Normalize a collector response into one device metric fact row."""
    cpu_percent = _number((metrics.get("cpu") or {}).get("value"))
    memory = metrics.get("memory") or {}
    memory_percent = _number(memory.get("used_percent"))
    temperature_c = _number((metrics.get("temperature") or {}).get("value"))
    interfaces = metrics.get("interfaces") or {}

    sample = DeviceMetricSample(
        device_id=device_id,
        ts=ts or datetime.utcnow(),
        source=source,
        collection_status=_collection_status(
            metrics,
            [cpu_percent, memory_percent, temperature_c],
        ),
        cpu_percent=cpu_percent,
        memory_percent=memory_percent,
        memory_used_mb=_number(memory.get("used_mb")),
        memory_total_mb=_number(memory.get("total_mb")),
        temperature_c=temperature_c,
        uptime_days=_integer((metrics.get("uptime") or {}).get("uptime_days")),
        interfaces_up=_integer(interfaces.get("up")),
        interfaces_down=_integer(interfaces.get("down")),
        interfaces_total=_integer(interfaces.get("total")),
        total_errors=_integer((metrics.get("errors") or {}).get("total_errors")),
    )
    db.add(sample)
    db.flush()
    return sample


def get_device_metric_samples(
    db: Session,
    device_id: int,
    *,
    limit: int = 60,
) -> list[DeviceMetricSample]:
    """Return the latest device metric facts in chronological order."""
    bounded_limit = max(1, min(limit, 500))
    samples = db.query(DeviceMetricSample).filter(
        DeviceMetricSample.device_id == device_id
    ).order_by(
        DeviceMetricSample.ts.desc(),
        DeviceMetricSample.id.desc(),
    ).limit(bounded_limit).all()
    return list(reversed(samples))


def device_metric_sample_to_dict(sample: DeviceMetricSample) -> Dict[str, Any]:
    return {
        "ts": utc_iso(sample.ts),
        "source": sample.source,
        "collection_status": sample.collection_status,
        "cpu_percent": sample.cpu_percent,
        "memory_percent": sample.memory_percent,
        "memory_used_mb": sample.memory_used_mb,
        "memory_total_mb": sample.memory_total_mb,
        "temperature_c": sample.temperature_c,
        "uptime_days": sample.uptime_days,
        "interfaces_up": sample.interfaces_up,
        "interfaces_down": sample.interfaces_down,
        "interfaces_total": sample.interfaces_total,
        "total_errors": sample.total_errors,
    }