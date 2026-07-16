"""Lightweight AI fault pre-diagnosis and operational recommendation service.

Uses the configured LLM through the existing ADK runner's simple chat path,
so it works with any OpenAI-compatible endpoint (Ollama / vLLM / a local ~30B
model). Everything degrades gracefully when no AI provider is configured.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.services.adk.config import adk_config
from app.services.adk.runner import adk_runner
from app.shared.models import (
    Device,
    DeviceMetricSample,
    FaultRecord,
    SparePart,
)

import json
import re

_SYSTEM_PROMPT = (
    "你是工业网络设备运维专家。基于给定的设备与故障上下文，给出简明的初步"
    "故障预判。只返回 JSON，字段：probable_cause(string)、"
    "recommendations(string 数组，最多4条)、confidence(low/medium/high)。"
    "不要编造未提供的数据。"
)


def ai_available() -> bool:
    """Whether an AI provider is configured."""
    return adk_config.is_configured()


def build_fault_context(db: Session, fault: FaultRecord) -> Dict:
    """Collect structured, non-fabricated context for a fault."""
    device = fault.device or db.query(Device).filter(Device.id == fault.device_id).first()
    context: Dict = {
        "fault_no": fault.fault_no,
        "severity": fault.severity,
        "description": fault.description,
        "device_name": device.name if device else fault.device_name,
        "device_ip": device.ip if device else None,
        "device_model": getattr(device, "model", None) if device else None,
    }

    if device:
        window_start = datetime.utcnow() - timedelta(hours=24)
        latest = db.query(DeviceMetricSample).filter(
            DeviceMetricSample.device_id == device.id
        ).order_by(DeviceMetricSample.ts.desc()).first()
        if latest:
            context["latest_metrics"] = {
                "cpu_percent": latest.cpu_percent,
                "memory_percent": latest.memory_percent,
                "temperature_c": latest.temperature_c,
                "uptime_days": latest.uptime_days,
            }
        peak_temp = db.query(DeviceMetricSample.temperature_c).filter(
            DeviceMetricSample.device_id == device.id,
            DeviceMetricSample.ts >= window_start,
            DeviceMetricSample.temperature_c.isnot(None),
        ).all()
        temps = [row[0] for row in peak_temp if row[0] is not None]
        if temps:
            context["peak_temperature_c_24h"] = round(max(temps), 1)

        recent_faults = db.query(FaultRecord).filter(
            FaultRecord.device_id == device.id,
            FaultRecord.id != fault.id,
            FaultRecord.created_at >= datetime.utcnow() - timedelta(days=30),
        ).count()
        context["recent_faults_30d"] = recent_faults

    return context


def _context_to_message(context: Dict) -> str:
    lines = ["请预判以下网络设备故障："]
    for key, value in context.items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def _parse_object(response: str) -> Dict:
    """Extract the first JSON object from a model response, tolerating fences."""
    if not response:
        return {}
    content = response.strip()
    content = re.sub(r"^```(?:json)?", "", content).strip()
    content = re.sub(r"```$", "", content).strip()
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    try:
        parsed = json.loads(content[start:end + 1])
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


async def pre_diagnose_fault(db: Session, fault: FaultRecord) -> Dict:
    """Produce a concise AI pre-diagnosis for a fault.

    Returns a dict with ``available`` False and a reason when AI is not
    configured or the model call fails, so callers never break.
    """
    if not ai_available():
        return {"available": False, "reason": "未配置 AI 服务"}

    context = build_fault_context(db, fault)
    result = await adk_runner.chat(
        message=_context_to_message(context),
        system_prompt=_SYSTEM_PROMPT,
        temperature=0.2,
        max_tokens=800,
        timeout=60,
    )
    if not result.get("success"):
        return {"available": False, "reason": result.get("error", "AI 调用失败")}

    parsed = _parse_object(result.get("response", ""))
    probable_cause = parsed.get("probable_cause") or ""
    recommendations = parsed.get("recommendations") or []
    if isinstance(recommendations, str):
        recommendations = [recommendations]

    return {
        "available": True,
        "probable_cause": probable_cause,
        "recommendations": [str(item) for item in recommendations][:4],
        "confidence": parsed.get("confidence", "low"),
        "context": context,
    }


def build_operational_recommendations(db: Session, limit: int = 8) -> List[Dict]:
    """Rule-based operational recommendation cards for the dashboard.

    Always returns without needing an LLM, so the dashboard "建议卡" works even
    when no AI provider is configured. Each card is a dict with severity,
    category, title, detail and an optional link target.
    """
    cards: List[Dict] = []

    # Overheating devices (24h peak temperature) — highest operational risk.
    window_start = datetime.utcnow() - timedelta(hours=24)
    hot_rows = db.query(
        DeviceMetricSample.device_id,
        Device.name,
    ).join(Device, Device.id == DeviceMetricSample.device_id).filter(
        DeviceMetricSample.ts >= window_start,
        DeviceMetricSample.temperature_c.isnot(None),
        DeviceMetricSample.temperature_c >= 65,
    ).order_by(DeviceMetricSample.temperature_c.desc()).all()
    seen_hot = set()
    for device_id, name in hot_rows:
        if device_id in seen_hot:
            continue
        seen_hot.add(device_id)
        peak = db.query(DeviceMetricSample.temperature_c).filter(
            DeviceMetricSample.device_id == device_id,
            DeviceMetricSample.ts >= window_start,
            DeviceMetricSample.temperature_c.isnot(None),
        ).order_by(DeviceMetricSample.temperature_c.desc()).first()
        peak_c = round(peak[0], 1) if peak else None
        cards.append({
            "severity": "critical" if (peak_c or 0) >= 80 else "high",
            "category": "temperature",
            "title": f"{name} 温度偏高",
            "detail": f"近24小时峰值 {peak_c}℃，建议检查散热并巡检风扇",
            "link": f"/device-health?device_id={device_id}",
        })

    # Low-health devices.
    low_health = db.query(Device).filter(
        Device.health_score.isnot(None),
        Device.health_score < 60,
    ).order_by(Device.health_score.asc()).limit(limit).all()
    for device in low_health:
        cards.append({
            "severity": "high" if device.health_score >= 40 else "critical",
            "category": "health",
            "title": f"{device.name} 健康度偏低",
            "detail": f"当前健康评分 {device.health_score}，建议安排预防性维护",
            "link": f"/device-health?device_id={device.id}",
        })

    # Open high-severity faults.
    open_faults = db.query(FaultRecord).filter(
        FaultRecord.status.notin_(["resolved", "closed"]),
        FaultRecord.severity.in_(["critical", "major"]),
    ).order_by(FaultRecord.created_at.desc()).limit(limit).all()
    for fault in open_faults:
        cards.append({
            "severity": "critical" if fault.severity == "critical" else "high",
            "category": "fault",
            "title": f"未处理{('严重' if fault.severity == 'critical' else '重要')}故障：{fault.device_name}",
            "detail": (fault.description or "")[:80],
            "link": f"/faults?status=open",
        })

    # Low spare stock.
    low_stock = db.query(SparePart).filter(
        SparePart.min_quantity > 0,
        SparePart.quantity_in_stock <= SparePart.min_quantity,
    ).order_by(SparePart.quantity_in_stock.asc()).limit(limit).all()
    for part in low_stock:
        cards.append({
            "severity": "medium",
            "category": "spare",
            "title": f"备件不足：{part.name}",
            "detail": f"当前库存 {part.quantity_in_stock}，低于最低值 {part.min_quantity}",
            "link": "/spare-parts?low_stock=true",
        })

    severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    cards.sort(key=lambda c: severity_rank.get(c["severity"], 9))
    return cards[:limit]
