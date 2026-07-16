"""Tests for the graceful AI fault pre-diagnosis service."""

import pytest

from app.services import ai_triage
from app.shared.models import Device, DeviceMetricSample, FaultRecord


def _fault(db):
    device = Device(name="AI-TRIAGE-01", ip="192.0.2.80", model="C9300")
    db.add(device)
    db.flush()
    db.add(DeviceMetricSample(device_id=device.id, temperature_c=82.0, cpu_percent=91.0))
    db.flush()
    fault = FaultRecord(
        device_id=device.id,
        device_name=device.name,
        fault_no="AI-TRIAGE-F1",
        severity="major",
        description="Uplink flapping and high temperature",
        status="diagnosing",
    )
    db.add(fault)
    db.flush()
    return fault


@pytest.mark.asyncio
async def test_pre_diagnose_degrades_when_ai_not_configured(db_session, monkeypatch):
    monkeypatch.setattr(ai_triage, "ai_available", lambda: False)
    fault = _fault(db_session)

    result = await ai_triage.pre_diagnose_fault(db_session, fault)

    assert result["available"] is False
    assert "reason" in result


@pytest.mark.asyncio
async def test_pre_diagnose_returns_structured_result(db_session, monkeypatch):
    fault = _fault(db_session)
    monkeypatch.setattr(ai_triage, "ai_available", lambda: True)

    async def fake_chat(**kwargs):
        return {
            "success": True,
            "response": '{"probable_cause": "光模块过热导致链路抖动", '
            '"recommendations": ["检查机柜散热", "更换光模块", "巡检风扇"], '
            '"confidence": "high"}',
        }

    monkeypatch.setattr(ai_triage.adk_runner, "chat", fake_chat)

    result = await ai_triage.pre_diagnose_fault(db_session, fault)

    assert result["available"] is True
    assert result["probable_cause"] == "光模块过热导致链路抖动"
    assert len(result["recommendations"]) == 3
    assert result["confidence"] == "high"
    assert result["context"]["peak_temperature_c_24h"] == 82.0


@pytest.mark.asyncio
async def test_pre_diagnose_handles_model_failure(db_session, monkeypatch):
    fault = _fault(db_session)
    monkeypatch.setattr(ai_triage, "ai_available", lambda: True)

    async def failing_chat(**kwargs):
        return {"success": False, "error": "connection refused"}

    monkeypatch.setattr(ai_triage.adk_runner, "chat", failing_chat)

    result = await ai_triage.pre_diagnose_fault(db_session, fault)

    assert result["available"] is False
    assert result["reason"] == "connection refused"


def test_recommendations_aggregate_and_sort_by_severity(db_session):
    hot = Device(name="REC-HOT", ip="192.0.2.90", health_score=100)
    weak = Device(name="REC-WEAK", ip="192.0.2.91", health_score=35)
    db_session.add_all([hot, weak])
    db_session.flush()
    db_session.add(DeviceMetricSample(device_id=hot.id, temperature_c=83.0))
    db_session.add(FaultRecord(
        device_id=weak.id,
        device_name=weak.name,
        fault_no="REC-F1",
        severity="critical",
        description="Core switch down",
        status="diagnosing",
    ))
    db_session.flush()

    cards = ai_triage.build_operational_recommendations(db_session)

    categories = {c["category"] for c in cards}
    assert "temperature" in categories
    assert "health" in categories
    assert "fault" in categories
    # Critical cards must sort before lower severities.
    assert cards[0]["severity"] == "critical"


def test_recommendations_empty_when_all_healthy(db_session):
    ok = Device(name="REC-OK", ip="192.0.2.92", health_score=95)
    db_session.add(ok)
    db_session.flush()

    cards = ai_triage.build_operational_recommendations(db_session)

    assert cards == []
