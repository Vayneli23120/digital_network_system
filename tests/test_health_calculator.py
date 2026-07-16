"""Tests for the device health score calculator, including temperature weighting."""

from datetime import datetime, timedelta

from app.services.health.calculator import HealthScoreCalculator
from app.shared.models import Device, DeviceMetricSample


def _device(db):
    device = Device(name="HEALTH-TEMP-01", ip="192.0.2.70")
    db.add(device)
    db.flush()
    return device


def _add_temp(db, device, celsius, *, hours_ago=1):
    db.add(DeviceMetricSample(
        device_id=device.id,
        ts=datetime.utcnow() - timedelta(hours=hours_ago),
        temperature_c=celsius,
    ))
    db.flush()


def test_weights_sum_to_one():
    total = sum(HealthScoreCalculator.WEIGHTS.values())
    assert round(total, 6) == 1.0
    assert HealthScoreCalculator.WEIGHTS['temperature'] == max(
        HealthScoreCalculator.WEIGHTS.values()
    )


def test_missing_temperature_is_neutral(db_session):
    device = _device(db_session)
    calc = HealthScoreCalculator(db_session)

    score = calc._calculate_temperature_score(device)
    details = calc._get_temperature_details(device)

    assert score == 100
    assert details['has_data'] is False


def test_high_temperature_drops_health_score(db_session):
    device = _device(db_session)
    _add_temp(db_session, device, 90.0)
    calc = HealthScoreCalculator(db_session)

    temp_score = calc._calculate_temperature_score(device)
    health_score, factors, risk = calc.calculate(device)

    assert temp_score == 5
    assert factors['temperature']['details']['peak_c'] == 90.0
    # A healthy new device with only an overheating signal must be pulled down.
    assert health_score < 80
    assert risk in {"medium", "high", "critical"}


def test_cool_temperature_keeps_full_score(db_session):
    device = _device(db_session)
    _add_temp(db_session, device, 38.0)
    calc = HealthScoreCalculator(db_session)

    assert calc._calculate_temperature_score(device) == 100


def test_peak_uses_worst_sample_in_window(db_session):
    device = _device(db_session)
    _add_temp(db_session, device, 40.0, hours_ago=5)
    _add_temp(db_session, device, 78.0, hours_ago=2)
    calc = HealthScoreCalculator(db_session)

    assert calc._peak_temperature(device) == 78.0
    assert calc._calculate_temperature_score(device) == 20
