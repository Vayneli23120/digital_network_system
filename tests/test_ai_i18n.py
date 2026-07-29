"""Dashboard / Operations 的 AI 研判与风险提示的中英文切换

三类内容的处理方式不同，这里各自都要守住：
1. 静态标签 —— 前端 i18n，不涉及后端
2. 规则引擎生成的建议卡与风险提示 —— 后端返回 i18n key + params，前端按语言渲染
3. LLM 生成的研判正文 —— 语言透传进提示词，由模型直接用目标语言作答，
   并且必须参与缓存键，否则中文用户先访问会把中文结果喂给英文界面
"""

import pytest

import app.shared.models_jobs  # noqa: F401


# ---------------------------------------------------------------------------
# 语言归一化
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("zh", "zh"),
    ("en", "en"),
    ("EN", "en"),
    ("en-US", "en"),
    ("zh_CN", "zh"),
    ("", "zh"),
    (None, "zh"),
    ("ja", "zh"),          # 不支持的语言回退中文，不报错
    ("../etc/passwd", "zh"),
])
def test_normalize_lang(raw, expected):
    from app.services.ai_triage import normalize_lang

    assert normalize_lang(raw) == expected


# ---------------------------------------------------------------------------
# 提示词双语
# ---------------------------------------------------------------------------

def test_both_languages_have_prompts():
    from app.services.ai_triage import (
        _BRIEFING_SYSTEM_PROMPTS, _CARD_MESSAGE_PREFIX,
        _EXEC_SYSTEM_PROMPTS, _KPI_MESSAGE_PREFIX, SUPPORTED_AI_LANGS,
    )

    for lang in SUPPORTED_AI_LANGS:
        assert _BRIEFING_SYSTEM_PROMPTS[lang]
        assert _EXEC_SYSTEM_PROMPTS[lang]
        assert _CARD_MESSAGE_PREFIX[lang]
        assert _KPI_MESSAGE_PREFIX[lang]


def test_english_prompts_ask_for_english_output():
    from app.services.ai_triage import _BRIEFING_SYSTEM_PROMPTS, _EXEC_SYSTEM_PROMPTS

    for prompt in (_BRIEFING_SYSTEM_PROMPTS["en"], _EXEC_SYSTEM_PROMPTS["en"]):
        assert "English" in prompt
        # 英文提示词里不应残留中文，否则模型容易跟着输出中文
        assert not any("\u4e00" <= ch <= "\u9fff" for ch in prompt)


# ---------------------------------------------------------------------------
# 规则卡片带 i18n key
# ---------------------------------------------------------------------------

def _seed_cards_data(db_session):
    from datetime import datetime, timedelta

    from app.shared.models import Device, DeviceMetricSample, FaultRecord, SparePart

    hot = Device(name="SW-HOT-01", ip="10.0.0.11", health_score=95)
    weak = Device(name="SW-WEAK-01", ip="10.0.0.12", health_score=42)
    db_session.add_all([hot, weak])
    db_session.flush()

    db_session.add(DeviceMetricSample(
        device_id=hot.id, ts=datetime.utcnow() - timedelta(hours=1), temperature_c=78.4,
    ))
    db_session.add(FaultRecord(
        fault_no="F-I18N-001", device_id=weak.id, device_name=weak.name,
        severity="critical", status="open", description="Uplink flapping",
    ))
    db_session.add(SparePart(
        name="SFP-10G-LR", part_number="SFP-10G-LR-01",
        quantity_in_stock=1, min_quantity=5,
    ))
    db_session.commit()
    return hot, weak


def test_rule_cards_carry_i18n_keys(db_session):
    from app.services.ai_triage import build_operational_recommendations

    hot, weak = _seed_cards_data(db_session)
    cards = build_operational_recommendations(db_session, limit=10)

    assert cards, "规则卡片不应为空"
    by_category = {c["category"]: c for c in cards}

    temp = by_category["temperature"]
    assert temp["title_key"] == "aiCardTempTitle"
    assert temp["title_params"] == {"device": hot.name}
    assert temp["detail_key"] == "aiCardTempDetail"
    assert temp["detail_params"]["peak"] == 78.4

    health = by_category["health"]
    assert health["title_key"] == "aiCardHealthTitle"
    assert health["detail_params"] == {"score": weak.health_score}

    fault = by_category["fault"]
    assert fault["title_key"] == "aiCardFaultCriticalTitle"
    # 故障描述是用户录入的自由文本，无法翻译，因此没有 detail_key
    assert fault["detail_key"] is None
    assert fault["detail"] == "Uplink flapping"

    spare = by_category["spare"]
    assert spare["title_key"] == "aiCardSpareTitle"
    assert spare["detail_params"] == {"stock": 1, "min": 5}

    # 中文成品字段保留：AI 提示词与旧客户端依赖它
    for card in cards:
        assert card["title"]


# ---------------------------------------------------------------------------
# 风险提示结构化
# ---------------------------------------------------------------------------

def test_executive_summary_exposes_structured_risks(db_session):
    from app.features.dashboard.dashboard_service import get_executive_summary

    summary = get_executive_summary(db_session, time_range="30d")

    assert "summary_risks" in summary
    assert isinstance(summary["summary_risks"], list)
    for item in summary["summary_risks"]:
        assert item["key"]
        assert isinstance(item["params"], dict)
    # 中文成品保留
    assert summary["summary_text"]


# ---------------------------------------------------------------------------
# 缓存键必须区分语言
# ---------------------------------------------------------------------------

def test_cache_key_differs_by_lang():
    from app.shared.cache import _cache_key

    zh = _cache_key("ai:briefing", limit=6, lang="zh")
    en = _cache_key("ai:briefing", limit=6, lang="en")
    assert zh != en, "中英文共用缓存键会把中文研判喂给英文界面"


# ---------------------------------------------------------------------------
# 前端 i18n 键齐备（中英双语都要有）
# ---------------------------------------------------------------------------

def test_frontend_has_both_locales_for_ai_keys():
    import io
    import re
    from pathlib import Path

    repo = Path(__file__).resolve().parent.parent
    loc = io.open(repo / "frontend/src/locales/index.js", encoding="utf-8").read()

    keys = [
        "aiCardTempTitle", "aiCardTempDetail",
        "aiCardHealthTitle", "aiCardHealthDetail",
        "aiCardFaultCriticalTitle", "aiCardFaultMajorTitle",
        "aiCardSpareTitle", "aiCardSpareDetail",
        "riskPrefix", "riskSeparator", "riskNoneStable",
        "riskOfflineDevices", "riskSlaOverdue", "riskLowStock",
        "riskRecurringRate", "riskChangeInducedFaults",
    ]
    for key in keys:
        count = len(re.findall(r"^\s+%s:" % re.escape(key), loc, re.M))
        assert count >= 2, f"{key} 只在 {count} 个语言里定义"


def test_frontend_placeholders_match_backend_params():
    """后端给的 params 必须能填满前端模板里的占位符"""
    import io
    import re
    from pathlib import Path

    repo = Path(__file__).resolve().parent.parent
    loc = io.open(repo / "frontend/src/locales/index.js", encoding="utf-8").read()

    expected = {
        "aiCardTempTitle": {"device"},
        "aiCardTempDetail": {"peak"},
        "aiCardHealthTitle": {"device"},
        "aiCardHealthDetail": {"score"},
        "aiCardFaultCriticalTitle": {"device"},
        "aiCardFaultMajorTitle": {"device"},
        "aiCardSpareTitle": {"part"},
        "aiCardSpareDetail": {"stock", "min"},
        "riskOfflineDevices": {"count"},
        "riskSlaOverdue": {"count"},
        "riskLowStock": {"count"},
        "riskRecurringRate": {"rate"},
        "riskChangeInducedFaults": {"count"},
    }
    for key, params in expected.items():
        for value in re.findall(r"^\s+%s:\s*'([^']*)'" % re.escape(key), loc, re.M):
            found = set(re.findall(r"\{(\w+)\}", value))
            assert found == params, f"{key} 的占位符 {found} 与后端参数 {params} 不一致"
