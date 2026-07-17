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


@pytest.mark.asyncio
async def test_briefing_returns_cards_without_ai_when_unconfigured(db_session, monkeypatch):
    weak = Device(name="BRIEF-WEAK", ip="192.0.2.93", health_score=30)
    db_session.add(weak)
    db_session.flush()
    monkeypatch.setattr(ai_triage, "ai_available", lambda: False)

    result = await ai_triage.generate_operational_briefing(db_session)

    assert result["ai_configured"] is False
    assert result["ai_briefing"] is None
    assert result["total"] >= 1


@pytest.mark.asyncio
async def test_briefing_adds_ai_synthesis_when_configured(db_session, monkeypatch):
    weak = Device(name="BRIEF-HOT", ip="192.0.2.94", health_score=25)
    db_session.add(weak)
    db_session.flush()
    monkeypatch.setattr(ai_triage, "ai_available", lambda: True)

    async def fake_chat(**kwargs):
        return {
            "success": True,
            "response": '{"briefing": "多台设备健康度告急", '
            '"priorities": ["优先处理核心设备", "检查机柜散热"], '
            '"insight": "过热与低健康度集中在同一区域"}',
        }

    monkeypatch.setattr(ai_triage.adk_runner, "chat", fake_chat)

    result = await ai_triage.generate_operational_briefing(db_session)

    assert result["ai_configured"] is True
    assert result["ai_briefing"]["briefing"] == "多台设备健康度告急"
    assert len(result["ai_briefing"]["priorities"]) == 2
    assert result["ai_briefing"]["insight"]


@pytest.mark.asyncio
async def test_briefing_degrades_on_model_failure(db_session, monkeypatch):
    weak = Device(name="BRIEF-FAIL", ip="192.0.2.95", health_score=20)
    db_session.add(weak)
    db_session.flush()
    monkeypatch.setattr(ai_triage, "ai_available", lambda: True)

    async def failing_chat(**kwargs):
        return {"success": False, "error": "timeout"}

    monkeypatch.setattr(ai_triage.adk_runner, "chat", failing_chat)

    result = await ai_triage.generate_operational_briefing(db_session)

    assert result["ai_briefing"] is None
    assert result["ai_error"] == "timeout"


@pytest.mark.asyncio
async def test_executive_narrative_none_when_unconfigured(monkeypatch):
    monkeypatch.setattr(ai_triage, "ai_available", lambda: False)

    result = await ai_triage.generate_executive_narrative(
        {"availability": {"value": 99.5, "unit": "%", "status": "good"}}
    )

    assert result is None


@pytest.mark.asyncio
async def test_executive_narrative_generated_when_configured(monkeypatch):
    monkeypatch.setattr(ai_triage, "ai_available", lambda: True)

    async def fake_chat(**kwargs):
        return {
            "success": True,
            "response": '{"narrative": "整体可用率达标，故障处理时长偏高需关注", '
            '"highlights": ["可用率99.5%", "MTTR偏高"]}',
        }

    monkeypatch.setattr(ai_triage.adk_runner, "chat", fake_chat)

    result = await ai_triage.generate_executive_narrative(
        {
            "availability": {"value": 99.5, "unit": "%", "status": "good"},
            "mttr_hours": {"value": 9, "unit": "h", "status": "warning"},
        }
    )

    assert result["narrative"].startswith("整体可用率")
    assert len(result["highlights"]) == 2


@pytest.mark.asyncio
async def test_executive_narrative_none_when_no_kpi_values(monkeypatch):
    monkeypatch.setattr(ai_triage, "ai_available", lambda: True)

    result = await ai_triage.generate_executive_narrative(
        {"availability": {"value": None, "unit": "%"}}
    )

    assert result is None
