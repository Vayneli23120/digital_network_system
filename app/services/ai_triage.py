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

import asyncio
import json
import re
from loguru import logger

_SYSTEM_PROMPT = (
    "你是工业网络设备运维专家。基于给定的设备与故障上下文，给出简明的初步"
    "故障预判。只返回 JSON，字段：probable_cause(string)、"
    "recommendations(string 数组，最多4条)、confidence(low/medium/high)。"
    "不要编造未提供的数据。"
)

# =============================================================================
# 双语提示词
#
# AI 生成的正文（研判/简报）无法靠前端 i18n 翻译 —— 它是模型现场写出来的自然
# 语言。所以语言必须透传到提示词里，由模型直接用目标语言作答；同时缓存键要带上
# 语言，否则中文用户先访问会把中文结果喂给英文界面。
# =============================================================================

SUPPORTED_AI_LANGS = ("zh", "en")


def normalize_lang(lang: Optional[str]) -> str:
    """把前端传来的语言标识收敛到受支持的取值，非法值回退中文"""
    if not lang:
        return "zh"
    normalized = str(lang).strip().lower().replace("_", "-").split("-")[0]
    return normalized if normalized in SUPPORTED_AI_LANGS else "zh"


_BRIEFING_SYSTEM_PROMPTS = {
    "zh": (
        "你是工厂网络运维值班主管。基于给定的运营告警卡片列表，产出一份简短的"
        "运营研判。只返回 JSON，字段：briefing(string，一到两句总体判断)、"
        "priorities(string 数组，最多3条按优先级排序的处置建议)、"
        "insight(string，一句跨条目关联洞察，没有则空字符串)。"
        "所有文本用简体中文。只基于给定卡片，不要编造设备或数据。"
    ),
    "en": (
        "You are the shift supervisor for a factory network operations team. "
        "Based on the given operational alert cards, produce a short operational "
        "assessment. Return JSON only, with fields: briefing (string, one or two "
        "sentences of overall judgement), priorities (array of strings, at most 3 "
        "recommended actions ordered by priority), insight (string, one sentence "
        "linking items together, empty string if none). "
        "Write all text in English. Use only the given cards, do not invent "
        "devices or data."
    ),
}

_EXEC_SYSTEM_PROMPTS = {
    "zh": (
        "你是面向管理层的网络运维分析师。基于给定的关键指标(KPI)，用简体中文写一段"
        "面向领导的经营简报。只返回 JSON，字段：narrative(string，2-3句话，客观、"
        "点出风险与趋势)、highlights(string 数组，最多3条关键结论)。"
        "只基于给定指标，不要编造数字。"
    ),
    "en": (
        "You are a network operations analyst writing for senior management. "
        "Based on the given KPIs, write an executive briefing in English. "
        "Return JSON only, with fields: narrative (string, 2-3 sentences, "
        "objective, calling out risks and trends), highlights (array of strings, "
        "at most 3 key conclusions). "
        "Use only the given metrics, do not invent numbers."
    ),
}

# 发给模型的用户消息前缀
_CARD_MESSAGE_PREFIX = {
    "zh": "运营告警卡片如下：\n",
    "en": "Operational alert cards:\n",
}
_KPI_MESSAGE_PREFIX = {
    "zh": "关键指标如下：\n",
    "en": "Key metrics:\n",
}


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

    国际化约定：这些卡片是规则引擎拼出来的固定句式，所以除了中文的
    ``title`` / ``detail``（保留给 AI 提示词和旧客户端）之外，还返回
    ``title_key`` / ``title_params`` / ``detail_key`` / ``detail_params``，
    由前端用 i18n 渲染。这样切换语言时无需重新请求接口，也不必把语言
    状态带进规则引擎。
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
            "title_key": "aiCardTempTitle",
            "title_params": {"device": name},
            "detail_key": "aiCardTempDetail",
            "detail_params": {"peak": peak_c},
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
            "title_key": "aiCardHealthTitle",
            "title_params": {"device": device.name},
            "detail_key": "aiCardHealthDetail",
            "detail_params": {"score": device.health_score},
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
            # 故障描述是用户录入的自由文本，无法翻译，原样透出
            "title_key": (
                "aiCardFaultCriticalTitle" if fault.severity == "critical"
                else "aiCardFaultMajorTitle"
            ),
            "title_params": {"device": fault.device_name},
            "detail_key": None,
            "detail_params": {},
            "link": "/faults?status=open",
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
            "title_key": "aiCardSpareTitle",
            "title_params": {"part": part.name},
            "detail_key": "aiCardSpareDetail",
            "detail_params": {"stock": part.quantity_in_stock, "min": part.min_quantity},
            "link": "/spare-parts?low_stock=true",
        })

    severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    cards.sort(key=lambda c: severity_rank.get(c["severity"], 9))
    return cards[:limit]


async def generate_operational_briefing(db: Session, limit: int = 8, lang: str = "zh") -> Dict:
    """Rule cards + optional AI synthesis for the dashboard.

    Always returns the deterministic cards. When an AI provider is configured
    and reachable, adds an AI ``briefing`` with prioritized actions and a
    cross-item insight; otherwise ``ai_briefing`` is None and the page still
    works from the rule cards alone.

    Args:
        lang: 生成语言（zh / en）。只影响 AI 正文；规则卡片始终带 i18n key，
            由前端翻译。
    """
    lang = normalize_lang(lang)
    cards = build_operational_recommendations(db, limit=limit)
    result: Dict = {
        "ai_configured": ai_available(),
        "total": len(cards),
        "items": cards,
        "ai_briefing": None,
        "lang": lang,
    }

    if not cards or not ai_available():
        return result

    card_lines = [
        f"- [{c['severity']}] {c['category']}: {c['title']} — {c['detail']}"
        for c in cards
    ]
    message = _CARD_MESSAGE_PREFIX[lang] + "\n".join(card_lines)
    chat_result = await adk_runner.chat(
        message=message,
        system_prompt=_BRIEFING_SYSTEM_PROMPTS[lang],
        temperature=0.2,
        max_tokens=700,
        timeout=60,
    )
    if not chat_result.get("success"):
        result["ai_error"] = chat_result.get("error", "AI 调用失败")
        return result

    parsed = _parse_object(chat_result.get("response", ""))
    briefing_text = parsed.get("briefing")
    if briefing_text:
        priorities = parsed.get("priorities") or []
        if isinstance(priorities, str):
            priorities = [priorities]
        result["ai_briefing"] = {
            "briefing": str(briefing_text),
            "priorities": [str(item) for item in priorities][:3],
            "insight": str(parsed.get("insight") or ""),
        }
    return result


def _kpi_lines(kpis: Dict) -> List[str]:
    lines = []
    for key, kpi in (kpis or {}).items():
        if not isinstance(kpi, dict):
            continue
        value = kpi.get("value")
        if value is None:
            continue
        unit = kpi.get("unit") or ""
        status = kpi.get("status") or ""
        lines.append(f"- {key}: {value}{unit} ({status})")
    return lines


async def generate_executive_narrative(kpis: Dict, lang: str = "zh") -> Optional[Dict]:
    """AI leadership narrative from executive KPIs. None when unavailable.

    Args:
        lang: 生成语言（zh / en）
    """
    if not ai_available():
        return None
    lang = normalize_lang(lang)
    lines = _kpi_lines(kpis)
    if not lines:
        return None

    for attempt in range(2):
        chat_result = await adk_runner.chat(
            message=_KPI_MESSAGE_PREFIX[lang] + "\n".join(lines),
            system_prompt=_EXEC_SYSTEM_PROMPTS[lang],
            temperature=0.3,
            max_tokens=600,
            timeout=60,
        )
        if not chat_result.get("success"):
            return None

        parsed = _parse_object(chat_result.get("response", ""))
        narrative = parsed.get("narrative")
        if narrative:
            highlights = parsed.get("highlights") or []
            if isinstance(highlights, str):
                highlights = [highlights]
            return {
                "narrative": str(narrative),
                "highlights": [str(item) for item in highlights][:3],
            }
        # 空/不可解析响应 → 短暂等待后重试一次
        if attempt == 0:
            await asyncio.sleep(2)
    return None


async def refresh_briefing_cache(key: str, limit: int, lang: str = "zh") -> None:
    """Background task: generate AI briefing and populate cache.

    Called via FastAPI BackgroundTasks so the HTTP response returns
    immediately with ai_pending=true while the LLM call runs out-of-band.

    ``key`` 由调用方带上语言，保证中英文各自独立缓存。
    """
    from app.shared.database import get_db_manager
    from app.shared.cache import cache

    try:
        with get_db_manager().session_scope() as db:
            result = await generate_operational_briefing(db, limit=limit, lang=lang)
            ai_briefing = result.get("ai_briefing")
            if ai_briefing:
                cache.set(key, {"ai_briefing": ai_briefing}, ttl=900)
            else:
                # 失败时短缓存 + cooldown 标记，避免前台无效轮询
                cache.set(key, {"ai_briefing": None, "_cooldown": True}, ttl=60)
    except Exception as exc:
        logger.exception("refresh_briefing_cache failed: {}", exc)
        cache.set(key, {"ai_briefing": None, "_cooldown": True}, ttl=60)


async def refresh_executive_summary_cache(key: str, time_range: str, lang: str = "zh") -> None:
    """Background task: generate AI executive summary and populate cache.

    Called via FastAPI BackgroundTasks; prevents the LLM call from blocking
    the HTTP response.

    ``key`` 由调用方带上语言，保证中英文各自独立缓存。
    """
    from app.shared.database import get_db_manager
    from app.shared.cache import cache

    try:
        with get_db_manager().session_scope() as db:
            from app.features.dashboard.dashboard_service import get_executive_summary

            summary = get_executive_summary(db, time_range=time_range)
            ai_summary = await generate_executive_narrative(summary.get("kpis", {}), lang=lang)
            if ai_summary:
                cache.set(key, {"ai_summary": ai_summary}, ttl=900)
            else:
                cache.set(key, {"ai_summary": None, "_cooldown": True}, ttl=60)
    except Exception as exc:
        logger.exception("refresh_executive_summary_cache failed: {}", exc)
        cache.set(key, {"ai_summary": None, "_cooldown": True}, ttl=60)
