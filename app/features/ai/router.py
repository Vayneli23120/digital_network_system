"""AI分析 API 路由

提供AI分析相关接口：
- 故障分析
- 健康评分分析
- 维修总结生成
- 预测性维护建议
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

from app.shared.database import get_db
from app.shared.models import AIAnalysisRecord, Device, FaultRecord, MaintenanceRecord
from app.services.ai import ai_manager, prompt_manager
from app.services.ai.workflows import get_workflow, list_workflows

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
    template_name: Optional[str] = None
    custom_prompt: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None


# ===== Provider & Template Info =====

@router.get("/providers")
async def list_providers():
    """列出可用的AI Provider"""
    providers = ai_manager.list_providers()
    return {
        "providers": providers,
        "default_provider": ai_manager.default_provider
    }


@router.get("/templates")
async def list_templates():
    """列出可用的Prompt模板"""
    templates = prompt_manager.list_templates()
    details = [prompt_manager.get_template_info(t) for t in templates]
    return {
        "templates": templates,
        "details": details
    }


@router.get("/templates/{template_name}")
async def get_template_info(template_name: str):
    """获取模板详细信息"""
    info = prompt_manager.get_template_info(template_name)
    if not info:
        raise HTTPException(status_code=404, detail="Template not found")
    return info


@router.get("/workflows")
async def list_ai_workflows():
    """列出可用的AI工作流"""
    return {
        "workflows": list_workflows()
    }


# ===== Fault Analysis =====

@router.post("/analyze-fault")
async def analyze_fault(
    request: AnalyzeFaultRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    分析故障记录

    Args:
        request: 包含 fault_id 和是否自动创建维修单的选项
    """
    fault = db.query(FaultRecord).filter(FaultRecord.id == request.fault_id).first()
    if not fault:
        raise HTTPException(status_code=404, detail="故障记录不存在")

    # 执行故障分析工作流
    workflow = get_workflow('fault_analysis')
    if workflow:
        result = await workflow.execute(
            fault_id=request.fault_id,
            db=db,
            auto_create_maintenance=request.auto_create_maintenance
        )
    else:
        # 直接调用AI Manager
        result = await ai_manager.analyze_fault(request.fault_id, db)

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
            "result": record.get_output_dict(),
            "confidence": float(record.confidence_score) if record.confidence_score else None,
            "processing_time_ms": record.processing_time_ms,
            "tokens_used": record.tokens_used,
            "cost": record.cost,
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
    db: Session = Depends(get_db)
):
    """
    AI辅助健康评分分析

    Args:
        request: 包含 device_id 和是否更新健康评分的选项
    """
    device = db.query(Device).filter(Device.id == request.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")

    # 执行健康分析工作流
    workflow = get_workflow('health_analysis')
    if workflow:
        result = await workflow.execute(
            device_id=request.device_id,
            db=db,
            update_health_score=request.update_health_score
        )
    else:
        result = await ai_manager.analyze_device_health(request.device_id, db)

    return result


# ===== Predictive Maintenance =====

@router.post("/predictive-maintenance")
async def predictive_maintenance(
    request: PredictiveMaintenanceRequest,
    db: Session = Depends(get_db)
):
    """
    预测性维护分析

    Args:
        request: 包含 device_id 和是否创建巡检任务的选项
    """
    device = db.query(Device).filter(Device.id == request.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")

    workflow = get_workflow('predictive_maintenance')
    if workflow:
        result = await workflow.execute(
            device_id=request.device_id,
            db=db,
            create_pm_task=request.create_pm_task
        )
    else:
        result = await ai_manager.analyze(
            analysis_type='pm_recommend',
            target_type='device',
            target_id=request.device_id,
            variables={
                'device_name': device.name,
                'device_model': device.device_type,
                'uptime_days': device.uptime_days or 0,
                'health_score': device.health_score or 100
            },
            db=db
        )

    return result


# ===== Maintenance Summary =====

@router.post("/generate-summary")
async def generate_maintenance_summary(maintenance_id: int, db: Session = Depends(get_db)):
    """
    生成维修总结报告

    Args:
        maintenance_id: 维修记录ID
    """
    maintenance = db.query(MaintenanceRecord).filter(
        MaintenanceRecord.id == maintenance_id
    ).first()
    if not maintenance:
        raise HTTPException(status_code=404, detail="维修记录不存在")

    result = await ai_manager.generate_maintenance_summary(maintenance_id, db)
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
    """
    获取AI分析历史记录

    Args:
        analysis_type: 分析类型筛选
        target_type: 目标类型筛选
        target_id: 目标ID筛选
        limit: 返回数量限制
    """
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
            "confidence": float(record.confidence_score) if record.confidence_score else None,
            "processing_time_ms": record.processing_time_ms,
            "tokens_used": record.tokens_used,
            "cost": float(record.cost) if record.cost else 0,
            "created_at": record.created_at.isoformat(),
            "error_message": record.error_message
        })

    return {
        "total": len(history),
        "history": history
    }


# ===== Dashboard Stats =====

@router.get("/dashboard")
async def get_ai_dashboard(db: Session = Depends(get_db)):
    """
    获取AI分析Dashboard统计

    Returns:
        - 总分析次数
        - 成功率
        - 总token使用量
        - 总成本
        - 各类型分析统计
    """
    from datetime import datetime, timedelta

    # 统计近24小时
    twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)

    records = db.query(AIAnalysisRecord).filter(
        AIAnalysisRecord.created_at >= twenty_four_hours_ago
    ).all()

    total_calls = len(records)
    success_count = len([r for r in records if r.status == 'completed'])
    total_tokens = sum(r.tokens_used or 0 for r in records)
    total_cost = sum(float(r.cost) or 0 for r in records)

    # 按分析类型统计
    by_type = {}
    for r in records:
        if r.analysis_type not in by_type:
            by_type[r.analysis_type] = {'count': 0, 'success': 0, 'tokens': 0}
        by_type[r.analysis_type]['count'] += 1
        if r.status == 'completed':
            by_type[r.analysis_type]['success'] += 1
        by_type[r.analysis_type]['tokens'] += r.tokens_used or 0

    # 按Provider统计
    by_provider = {}
    for r in records:
        if r.ai_provider not in by_provider:
            by_provider[r.ai_provider] = {'calls': 0, 'cost': 0}
        by_provider[r.ai_provider]['calls'] += 1
        by_provider[r.ai_provider]['cost'] += float(r.cost) or 0

    return {
        "period": "24h",
        "total_calls": total_calls,
        "success_count": success_count,
        "success_rate": round(success_count / total_calls * 100 if total_calls > 0 else 0, 1),
        "total_tokens": total_tokens,
        "total_cost": round(total_cost, 4),
        "by_analysis_type": by_type,
        "by_provider": by_provider,
        "providers_available": ai_manager.list_providers()
    }


# ===== Custom Analysis =====

@router.post("/custom-analysis")
async def custom_analysis(
    request: CustomAnalysisRequest,
    db: Session = Depends(get_db)
):
    """
    执行自定义AI分析

    Args:
        request: 自定义分析请求参数
    """
    result = await ai_manager.analyze(
        analysis_type=request.analysis_type,
        target_type=request.target_type,
        target_id=request.target_id,
        variables=request.variables or {},
        template_name=request.template_name,
        custom_prompt=request.custom_prompt,
        db=db
    )

    return result