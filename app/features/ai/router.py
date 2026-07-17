"""AI分析 API 路由

提供AI分析相关接口，基于 Google ADK 框架：
- 故障分析
- 健康评分分析
- 维修总结生成
- 预测性维护建议
- 根因分析
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timedelta
from loguru import logger

from app.shared.database import get_db
from app.shared.models import AIAnalysisRecord, Device, FaultRecord, MaintenanceRecord, AIConfig
from app.features.ai.dependencies import require_ai_use, require_ai_config

# ADK 导入
from app.services.adk.runner import adk_runner
from app.services.adk.config import adk_config
from app.services.adk.agents import (
    fault_analysis_agent,
    root_cause_agent,
    health_agent,
    maintenance_agent,
    predictive_agent,
)

router = APIRouter(prefix="/api/ai", tags=["ai"])


# ===== Request Models =====

class AnalyzeFaultRequest(BaseModel):
    """故障分析请求"""
    fault_id: int
    auto_create_maintenance: bool = False


class AnalyzeHealthRequest(BaseModel):
    """健康评分分析请求"""
    device_id: int
    update_health_score: bool = True


class PredictiveMaintenanceRequest(BaseModel):
    """预测性维护请求"""
    device_id: int
    create_pm_task: bool = False


class CustomAnalysisRequest(BaseModel):
    """自定义分析请求"""
    analysis_type: str
    target_type: str
    target_id: int
    custom_prompt: Optional[str] = None


# ===== AI Config Info =====

@router.get("/config")
async def get_ai_config(
    db: Session = Depends(get_db),
    user = Depends(require_ai_config)
):
    """获取当前 AI 配置信息"""
    config = db.query(AIConfig).filter(AIConfig.is_active == True).first()
    if not config:
        return {
            "configured": False,
            "message": "未配置 AI 服务"
        }

    return {
        "configured": True,
        "provider": config.provider,
        "model_name": config.model_name,
        "base_url": config.base_url,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "is_default": config.is_default
    }


@router.get("/providers")
async def list_providers():
    """列出支持的 AI Provider"""
    return {
        "providers": [
            {"name": "openai", "models": ["gpt-4o", "gpt-4o-mini", "gpt-4"]},
            {"name": "anthropic", "models": ["claude-3-haiku", "claude-3-sonnet", "claude-3-opus", "claude-3.5-sonnet"]},
            {"name": "deepseek", "models": ["deepseek-chat", "deepseek-reasoner"]},
        ],
        "adk_supported": True
    }


@router.get("/recommendations")
async def get_operational_recommendations(limit: int = 8, db: Session = Depends(get_db)):
    """大屏 AI 建议卡（规则聚合，无需模型即可返回，未配置 AI 时仍可用）。"""
    from app.services.ai_triage import build_operational_recommendations, ai_available

    cards = build_operational_recommendations(db, limit=limit)
    return {
        "ai_configured": ai_available(),
        "total": len(cards),
        "items": cards,
    }


@router.get("/briefing")
async def get_operational_briefing(limit: int = 8, db: Session = Depends(get_db)):
    """运营研判简报：规则卡片 + 可选的 AI 综合研判（未配置 AI 时回落为纯卡片）。

    AI 研判结果缓存 5 分钟，避免每次刷新都重复调用模型消耗 token。
    """
    from app.services.ai_triage import generate_operational_briefing
    from app.shared.cache import cache, _cache_key

    key = _cache_key("ai:briefing", limit=limit)
    cached = cache.get(key)
    if cached is not None:
        return cached

    result = await generate_operational_briefing(db, limit=limit)
    # 有 AI 研判时缓存 15 分钟；没有时短缓存(60s)，便于配置后尽快生效
    cache.set(key, result, ttl=900 if result.get("ai_briefing") else 60)
    return result


# ===== Fault Analysis =====

@router.post("/analyze-fault")
async def analyze_fault(
    request: AnalyzeFaultRequest,
    db: Session = Depends(get_db),
    user = Depends(require_ai_use)
):
    """使用 ADK Agent 分析故障记录"""
    fault = db.query(FaultRecord).filter(FaultRecord.id == request.fault_id).first()
    if not fault:
        raise HTTPException(status_code=404, detail="故障记录不存在")

    device_name = fault.device.name if fault.device else "Unknown"

    result = await adk_runner.run_agent(
        agent=fault_analysis_agent,
        user_id=user.username if user else "system",
        message=f"请分析故障 ID={request.fault_id}，设备名称={device_name}",
        analysis_type="fault",
        target_type="fault",
        target_id=request.fault_id,
        db=db
    )

    if result["success"]:
        # 解析 JSON 结果
        parsed = adk_runner.parse_json_response(result["response"])
        if parsed:
            # 更新故障记录
            fault.ai_root_cause = parsed.get("root_cause", "")
            fault.ai_recommendation = "\n".join(parsed.get("recommendations", []))
            db.commit()

            result["parsed_result"] = parsed

    return result


@router.post("/analyze-fault-root-cause")
async def analyze_fault_root_cause(
    fault_id: int,
    db: Session = Depends(get_db),
    user = Depends(require_ai_use)
):
    """深度根因分析"""
    fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()
    if not fault:
        raise HTTPException(status_code=404, detail="故障记录不存在")

    device_name = fault.device.name if fault.device else "Unknown"

    result = await adk_runner.run_agent(
        agent=root_cause_agent,
        user_id=user.username if user else "system",
        message=f"请对故障 ID={fault_id} 进行深度根因分析，设备名称={device_name}",
        analysis_type="root_cause",
        target_type="fault",
        target_id=fault_id,
        db=db
    )

    if result["success"]:
        parsed = adk_runner.parse_json_response(result["response"])
        if parsed:
            result["parsed_result"] = parsed

    return result


@router.get("/faults/{fault_id}/analysis")
async def get_fault_analysis(fault_id: int, db: Session = Depends(get_db)):
    """获取故障的AI分析结果"""
    fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()
    if not fault:
        raise HTTPException(status_code=404, detail="故障记录不存在")

    # 查询最近的AI分析记录
    record = db.query(AIAnalysisRecord).filter(
        AIAnalysisRecord.analysis_type == 'fault',
        AIAnalysisRecord.target_type == 'fault',
        AIAnalysisRecord.target_id == fault_id
    ).order_by(AIAnalysisRecord.created_at.desc()).first()

    if record:
        return {
            "fault_id": fault_id,
            "fault_title": fault.title,
            "has_analysis": True,
            "ai_provider": record.ai_provider,
            "model": record.model_name,
            "result": record.output_result[:500] if record.output_result else None,
            "processing_time_ms": record.processing_time_ms,
            "analyzed_at": record.created_at.isoformat(),
            "ai_root_cause": fault.ai_root_cause,
            "ai_recommendation": fault.ai_recommendation
        }
    else:
        return {
            "fault_id": fault_id,
            "fault_title": fault.title,
            "has_analysis": False,
            "ai_root_cause": fault.ai_root_cause,
            "ai_recommendation": fault.ai_recommendation
        }


# ===== Health Analysis =====

@router.post("/analyze-health")
async def analyze_health(
    request: AnalyzeHealthRequest,
    db: Session = Depends(get_db),
    user = Depends(require_ai_use)
):
    """AI辅助健康评分分析"""
    device = db.query(Device).filter(Device.id == request.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")

    result = await adk_runner.run_agent(
        agent=health_agent,
        user_id=user.username if user else "system",
        message=f"请分析设备 ID={request.device_id} 的健康状况，设备名称={device.name}",
        analysis_type="health",
        target_type="device",
        target_id=request.device_id,
        db=db
    )

    if result["success"]:
        parsed = adk_runner.parse_json_response(result["response"])
        if parsed and request.update_health_score:
            # 更新设备健康评分
            health_score = parsed.get("health_score", 100)
            device.health_score = health_score
            db.commit()
            result["updated_health_score"] = health_score
            result["parsed_result"] = parsed

    return result


# ===== Predictive Maintenance =====

@router.post("/predictive-maintenance")
async def predictive_maintenance(
    request: PredictiveMaintenanceRequest,
    db: Session = Depends(get_db),
    user = Depends(require_ai_use)
):
    """预测性维护分析"""
    device = db.query(Device).filter(Device.id == request.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")

    result = await adk_runner.run_agent(
        agent=predictive_agent,
        user_id=user.username if user else "system",
        message=f"请对设备 ID={request.device_id} 进行预测性维护分析，设备名称={device.name}",
        analysis_type="predictive",
        target_type="device",
        target_id=request.device_id,
        db=db
    )

    if result["success"]:
        parsed = adk_runner.parse_json_response(result["response"])
        if parsed:
            result["parsed_result"] = parsed

    return result


# ===== Maintenance Summary =====

@router.post("/generate-summary")
async def generate_maintenance_summary(
    maintenance_id: int,
    db: Session = Depends(get_db),
    user = Depends(require_ai_use)
):
    """生成维修总结报告"""
    maintenance = db.query(MaintenanceRecord).filter(
        MaintenanceRecord.id == maintenance_id
    ).first()
    if not maintenance:
        raise HTTPException(status_code=404, detail="维修记录不存在")

    device_name = maintenance.device.name if maintenance.device else "Unknown"

    result = await adk_runner.run_agent(
        agent=maintenance_agent,
        user_id=user.username if user else "system",
        message=f"请生成维修总结，维修记录 ID={maintenance_id}，设备名称={device_name}",
        analysis_type="maintenance",
        target_type="maintenance",
        target_id=maintenance_id,
        db=db
    )

    if result["success"]:
        parsed = adk_runner.parse_json_response(result["response"])
        if parsed:
            result["parsed_result"] = parsed

    return result


# ===== Analysis History =====

@router.get("/history")
async def get_analysis_history(
    analysis_type: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """获取AI分析历史记录"""
    query = db.query(AIAnalysisRecord)

    if analysis_type:
        query = query.filter(AIAnalysisRecord.analysis_type == analysis_type)
    if target_type:
        query = query.filter(AIAnalysisRecord.target_type == target_type)
    if target_id:
        query = query.filter(AIAnalysisRecord.target_id == target_id)

    records = query.order_by(AIAnalysisRecord.created_at.desc()).limit(limit).all()

    history = []
    for record in records:
        history.append({
            "id": record.id,
            "analysis_type": record.analysis_type,
            "target_type": record.target_type,
            "target_id": record.target_id,
            "provider": record.ai_provider,
            "model": record.model_name,
            "status": record.status,
            "processing_time_ms": record.processing_time_ms,
            "created_at": record.created_at.isoformat(),
        })

    return {
        "total": len(history),
        "history": history
    }


# ===== Dashboard Stats =====

@router.get("/dashboard")
async def get_ai_dashboard(db: Session = Depends(get_db)):
    """获取AI分析Dashboard统计"""
    # 统计近24小时
    twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)

    records = db.query(AIAnalysisRecord).filter(
        AIAnalysisRecord.created_at >= twenty_four_hours_ago
    ).all()

    total_calls = len(records)
    success_count = len([r for r in records if r.status == 'completed'])

    # 按分析类型统计
    by_type = {}
    for r in records:
        if r.analysis_type not in by_type:
            by_type[r.analysis_type] = {'count': 0, 'success': 0}
        by_type[r.analysis_type]['count'] += 1
        if r.status == 'completed':
            by_type[r.analysis_type]['success'] += 1

    # 按Provider统计
    by_provider = {}
    for r in records:
        if r.ai_provider not in by_provider:
            by_provider[r.ai_provider] = {'calls': 0}
        by_provider[r.ai_provider]['calls'] += 1

    return {
        "period": "24h",
        "total_calls": total_calls,
        "success_count": success_count,
        "success_rate": round(success_count / total_calls * 100 if total_calls > 0 else 0, 1),
        "by_analysis_type": by_type,
        "by_provider": by_provider,
        "adk_enabled": True
    }


# ===== Check AI Status =====

@router.get("/status")
async def check_ai_status(db: Session = Depends(get_db)):
    """检查 AI 服务状态"""
    is_configured = adk_config.is_configured()
    config = db.query(AIConfig).filter(AIConfig.is_active == True).first()

    return {
        "configured": is_configured,
        "provider": config.provider if config else None,
        "model": config.model_name if config else None,
        "adk_available": True
    }