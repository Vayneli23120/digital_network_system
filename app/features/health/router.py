"""设备健康评分 API 路由"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.shared.database import get_db
from app.shared.models import Device, DeviceHealthScore
from app.services.health import calculate_device_health, calculate_all_devices_health

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("/devices/{device_id}")
async def get_device_health(device_id: int, db: Session = Depends(get_db)):
    """
    获取单个设备的健康评分

    Returns:
        - health_score: 0-100 健康评分
        - risk_level: low/medium/high/critical
        - trend: improving/stable/declining
        - score_factors: 各因素评分详情
        - recommendations: 建议列表
    """
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")

    # 获取最新健康评分记录
    latest_record = db.query(DeviceHealthScore).filter(
        DeviceHealthScore.device_id == device_id
    ).order_by(DeviceHealthScore.last_calculated_at.desc()).first()

    if latest_record:
        return {
            "device_id": device.id,
            "device_name": device.name,
            "health_score": latest_record.health_score,
            "risk_level": latest_record.risk_level,
            "trend": latest_record.trend,
            "score_factors": latest_record.get_score_factors_dict(),
            "recommendations": latest_record.get_recommendations_list(),
            "ai_analysis_text": latest_record.ai_analysis_text,
            "last_calculated_at": latest_record.last_calculated_at.isoformat(),
            "device_status": device.status,
            "lifecycle_stage": device.lifecycle_stage
        }
    else:
        # 没有记录时返回默认值
        return {
            "device_id": device.id,
            "device_name": device.name,
            "health_score": device.health_score or 100,
            "risk_level": device.risk_level or "low",
            "trend": "stable",
            "score_factors": {},
            "recommendations": [],
            "ai_analysis_text": None,
            "last_calculated_at": None,
            "device_status": device.status,
            "lifecycle_stage": device.lifecycle_stage
        }


@router.post("/devices/{device_id}/calculate")
async def calculate_single_device_health(
    device_id: int,
    include_ai: bool = False,
    db: Session = Depends(get_db)
):
    """
    计算单个设备健康评分（并保存记录）

    Args:
        device_id: 设备ID
        include_ai: 是否包含AI分析结果
    """
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")

    result = calculate_device_health(db, device_id, include_ai)

    if not result:
        raise HTTPException(status_code=500, detail="计算健康评分失败")

    return result


@router.post("/calculate-all")
async def calculate_all_health(
    include_ai: bool = False,
    limit: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    批量计算所有设备健康评分

    Args:
        include_ai: 是否包含AI分析
        limit: 限制计算数量（可选）
    """
    results = calculate_all_devices_health(db, include_ai)

    if limit:
        results = results[:limit]

    return {
        "total": len(results),
        "results": results,
        "calculated_at": datetime.utcnow().isoformat()
    }


@router.get("/devices/{device_id}/history")
async def get_health_history(
    device_id: int,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    获取设备健康评分历史记录
    """
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")

    records = db.query(DeviceHealthScore).filter(
        DeviceHealthScore.device_id == device_id
    ).order_by(DeviceHealthScore.last_calculated_at.desc()).limit(limit).all()

    history = []
    for record in records:
        history.append({
            "id": record.id,
            "health_score": record.health_score,
            "risk_level": record.risk_level,
            "trend": record.trend,
            "score_factors": record.get_score_factors_dict(),
            "recommendations": record.get_recommendations_list(),
            "last_calculated_at": record.last_calculated_at.isoformat()
        })

    return {
        "device_id": device_id,
        "device_name": device.name,
        "history": history,
        "count": len(history)
    }


@router.get("/dashboard")
async def get_health_dashboard(db: Session = Depends(get_db)):
    """
    获取健康评分Dashboard统计数据

    Returns:
        - 总设备数、各风险等级设备数
        - 平均健康评分
        - 健康评分分布
        - 风险设备列表
    """
    devices = db.query(Device).filter(Device.status != 'retired').all()

    # 统计各风险等级数量
    risk_counts = {
        'low': 0,
        'medium': 0,
        'high': 0,
        'critical': 0
    }

    # 健康评分分布
    score_distribution = {
        'excellent': 0,  # 90-100
        'good': 0,       # 70-89
        'fair': 0,       # 50-69
        'poor': 0        # 0-49
    }

    # 风险设备列表
    risky_devices = []

    total_health_score = 0
    devices_with_score = 0

    for device in devices:
        # 使用最新健康评分
        health_score = device.health_score or 100
        risk_level = device.risk_level or 'low'

        # 统计风险等级
        if risk_level in risk_counts:
            risk_counts[risk_level] += 1

        # 统计评分分布
        if health_score >= 90:
            score_distribution['excellent'] += 1
        elif health_score >= 70:
            score_distribution['good'] += 1
        elif health_score >= 50:
            score_distribution['fair'] += 1
        else:
            score_distribution['poor'] += 1

        # 计算平均分
        total_health_score += health_score
        devices_with_score += 1

        # 收集高风险设备
        if risk_level in ['high', 'critical']:
            risky_devices.append({
                "id": device.id,
                "name": device.name,
                "health_score": health_score,
                "risk_level": risk_level,
                "status": device.status
            })

    avg_health_score = total_health_score / devices_with_score if devices_with_score > 0 else 100

    return {
        "total_devices": len(devices),
        "average_health_score": round(avg_health_score, 1),
        "risk_distribution": risk_counts,
        "score_distribution": score_distribution,
        "risky_devices": risky_devices[:10],  # 最多返回10个
        "last_updated": datetime.utcnow().isoformat()
    }


@router.get("/risk-devices")
async def get_risk_devices(
    risk_level: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    获取高风险设备列表

    Args:
        risk_level: 指定风险等级筛选（可选）
        limit: 返回数量限制
    """
    query = db.query(Device).filter(Device.status != 'retired')

    if risk_level:
        query = query.filter(Device.risk_level == risk_level)
    else:
        # 默认返回 high 和 critical
        query = query.filter(Device.risk_level.in_(['high', 'critical']))

    devices = query.order_by(Device.health_score.asc()).limit(limit).all()

    result = []
    for device in devices:
        # 获取最新健康记录的建议
        latest_record = db.query(DeviceHealthScore).filter(
            DeviceHealthScore.device_id == device.id
        ).order_by(DeviceHealthScore.last_calculated_at.desc()).first()

        result.append({
            "id": device.id,
            "name": device.name,
            "ip": device.ip,
            "health_score": device.health_score or 100,
            "risk_level": device.risk_level or 'low',
            "status": device.status,
            "lifecycle_stage": device.lifecycle_stage,
            "recommendations": latest_record.get_recommendations_list() if latest_record else [],
            "last_health_check": device.last_health_check.isoformat() if device.last_health_check else None
        })

    return {
        "total": len(result),
        "devices": result
    }