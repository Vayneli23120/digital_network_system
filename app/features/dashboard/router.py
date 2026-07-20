"""Dashboard router — 带缓存"""

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from typing import Optional

from app.shared.database import get_db
from .dashboard_service import get_dashboard_summary as svc_get_dashboard_summary
from .dashboard_service import get_fault_trend as svc_get_fault_trend
from .dashboard_service import get_cost_trend as svc_get_cost_trend
from .dashboard_service import get_top_fault_devices as svc_get_top_fault_devices
from .dashboard_service import get_executive_summary as svc_get_executive_summary
from app.shared.cache import cache, _DASHBOARD_TTL, _TREND_TTL, _cache_key

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
async def get_dashboard_summary(db: Session = Depends(get_db)):
    """获取 Dashboard 摘要数据（30s 缓存）"""
    key = _cache_key("dashboard:summary")
    result = cache.get(key)
    if result is not None:
        return result

    result = svc_get_dashboard_summary(db)
    cache.set(key, result, ttl=_DASHBOARD_TTL)
    return result


@router.get("/cost-trend")
async def get_cost_trend(db: Session = Depends(get_db), months: int = 6):
    """获取近 N 个月运维成本趋势（60s 缓存）"""
    key = _cache_key("dashboard:cost-trend", months=months)
    result = cache.get(key)
    if result is not None:
        return result

    result = svc_get_cost_trend(db, months=months)
    cache.set(key, result, ttl=_TREND_TTL)
    return result


@router.get("/top-fault-devices")
async def get_top_fault_devices(db: Session = Depends(get_db), days: int = 30, limit: int = 5, only_active: bool = False):
    """获取近 N 天故障最多的设备（60s 缓存）。only_active=true 时仅统计未闭环故障。"""
    key = _cache_key("dashboard:top-fault-devices", days=days, limit=limit, only_active=only_active)
    result = cache.get(key)
    if result is not None:
        return result

    result = svc_get_top_fault_devices(db, days=days, limit=limit, only_active=only_active)
    cache.set(key, result, ttl=_TREND_TTL)
    return result


@router.get("/fault-trend")
async def get_fault_trend(
    db: Session = Depends(get_db),
    time_range: str = "30d",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """获取故障趋势数据（60s 缓存）

    Args:
        time_range: 时间范围 - 7d(近 7 天), 30d(近 30 天), 3m(近 3 个月), 1y(近 1 年), custom(自定义)
        start_date: 自定义开始日期 (YYYY-MM-DD)
        end_date: 自定义结束日期 (YYYY-MM-DD)
    """
    key = _cache_key("dashboard:fault-trend", time_range=time_range, start_date=start_date, end_date=end_date)
    result = cache.get(key)
    if result is not None:
        return result

    result = svc_get_fault_trend(db, time_range=time_range, start_date=start_date, end_date=end_date)
    cache.set(key, result, ttl=_TREND_TTL)
    return result


@router.get("/executive-summary")
async def get_executive_summary(
    db: Session = Depends(get_db),
    time_range: str = "30d"
):
    """管理层聚合接口 - 返回所有核心 KPI（30s 缓存）

    Args:
        time_range: 时间范围 - 7d, 30d, 90d, 12m

    Returns:
        {
            "kpis": {
                "availability": {value, unit, target, threshold, trend, status},
                "active_faults": {...},
                "sla_rate": {...},
                "mttr_hours": {...},
                ...
            },
            "summary_text": "风险提示：...",
            "root_cause_distribution": {...},
            "recurring_devices": [...]
        }
    """
    key = _cache_key("dashboard:executive-summary", time_range=time_range)
    result = cache.get(key)
    if result is not None:
        return result

    result = svc_get_executive_summary(db, time_range=time_range)
    cache.set(key, result, ttl=_DASHBOARD_TTL)
    return result


@router.get("/ai-summary")
async def get_ai_executive_summary(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    time_range: str = "30d",
):
    """领导层 AI 经营摘要：模板摘要立即返回，AI 摘要后台生成。

    不再把模型思考时间阻塞在请求里；若已有缓存 AI 摘要则一并返回，
    否则 ai_pending=true，前端轮询拉取。
    """
    from app.services.ai_triage import ai_available, refresh_executive_summary_cache

    key = _cache_key("dashboard:ai-summary", time_range=time_range)
    cached = cache.get(key)
    ai_narrative = cached.get("ai_summary") if isinstance(cached, dict) else None
    # 已有缓存条目（成功或冷却中）则不重复触发，避免每次进页都重新生成
    attempted = isinstance(cached, dict)

    summary = svc_get_executive_summary(db, time_range=time_range)
    result = {
        "ai_configured": ai_available(),
        "ai_summary": ai_narrative,
        "fallback_text": summary.get("summary_text"),
        "range": time_range,
        "ai_pending": False,
    }

    if ai_available() and ai_narrative is None and not attempted:
        result["ai_pending"] = True
        background_tasks.add_task(refresh_executive_summary_cache, key, time_range)

    return result


@router.get("/realtime-status")
async def get_realtime_status(db: Session = Depends(get_db)):
    """实时基础设施状态 - 当前在线率 + 进行中故障 + 按厂区聚合（短缓存）。"""
    from .dashboard_service import get_realtime_status as svc_get_realtime_status
    key = _cache_key("dashboard:realtime-status")
    result = cache.get(key)
    if result is not None:
        return result
    result = svc_get_realtime_status(db)
    cache.set(key, result, ttl=15)
    return result


@router.get("/alerts")
async def get_alerts(db: Session = Depends(get_db)):
    """获取实时告警列表（高危故障 + 备份超期 + 系统健康）"""
    key = _cache_key("dashboard:alerts")
    result = cache.get(key)
    if result is not None:
        return result

    from .dashboard_service import get_alerts as svc_get_alerts
    result = svc_get_alerts(db)
    cache.set(key, result, ttl=30)  # 30秒缓存
    return result


@router.post("/cache/clear")
async def clear_dashboard_cache():
    """清除 Dashboard 缓存（在数据变更后调用）"""
    count = cache.invalidate_prefix("dashboard:")
    return {"cleared": count, "message": f"已清除 {count} 个 Dashboard 缓存项"}


@router.get("/network-overview")
async def network_overview(db: Session = Depends(get_db)):
    """网络总览（原生）：全网收发总量 + 在线/离线接口 + 流量 Top 接口。数据源为本系统采集库。"""
    from app.shared.models import Device, DeviceInterface
    key = _cache_key("dashboard:network-overview")
    cached = cache.get(key)
    if cached is not None:
        return cached

    rows = db.query(DeviceInterface, Device).join(
        Device, Device.id == DeviceInterface.device_id
    ).filter(DeviceInterface.monitored == True).all()  # noqa: E712

    total_in = sum((i.last_in_bps or 0) for i, _ in rows)
    total_out = sum((i.last_out_bps or 0) for i, _ in rows)
    up = sum(1 for i, _ in rows if (i.oper_status or "") == "up")
    down = sum(1 for i, _ in rows if (i.oper_status or "") == "down")

    ranked = sorted(
        rows,
        key=lambda r: (r[0].last_in_bps or 0) + (r[0].last_out_bps or 0),
        reverse=True,
    )[:8]
    top = [{
        "device_id": i.device_id,
        "device_name": d.name,
        "if_name": i.if_name or f"if{i.if_index}",
        "in_bps": i.last_in_bps or 0,
        "out_bps": i.last_out_bps or 0,
        "util": max(i.last_in_util or 0, i.last_out_util or 0),
    } for i, d in ranked]

    result = {
        "total_in_bps": total_in,
        "total_out_bps": total_out,
        "iface_up": up,
        "iface_down": down,
        "top": top,
    }
    cache.set(key, result, ttl=15)
    return result


# ============ SLO 配置管理（无迁移，界面直接维护）============

from fastapi import HTTPException
from pydantic import BaseModel
from app.shared.models import ServiceSlo


class SloUpsert(BaseModel):
    service_key: str
    service_name: str
    slo_target: float
    device_types: Optional[str] = None   # 逗号分隔的设备类型；空=全局
    window_days: int = 30
    description: Optional[str] = None
    is_active: bool = True


def _slo_to_dict(s: ServiceSlo) -> dict:
    return {
        "id": s.id,
        "service_key": s.service_key,
        "service_name": s.service_name,
        "slo_target": float(s.slo_target) if s.slo_target is not None else None,
        "device_types": s.device_types or "",
        "window_days": s.window_days,
        "description": s.description,
        "is_active": bool(s.is_active),
    }


@router.get("/slo")
async def list_slo(db: Session = Depends(get_db)):
    """列出所有 SLO 配置"""
    rows = db.query(ServiceSlo).order_by(ServiceSlo.is_active.desc(), ServiceSlo.id).all()
    return {"items": [_slo_to_dict(s) for s in rows]}


@router.post("/slo")
async def create_slo(body: SloUpsert, db: Session = Depends(get_db)):
    """新增 SLO 配置"""
    if db.query(ServiceSlo).filter(ServiceSlo.service_key == body.service_key).first():
        raise HTTPException(status_code=400, detail=f"service_key '{body.service_key}' 已存在")
    slo = ServiceSlo(
        service_key=body.service_key.strip(),
        service_name=body.service_name.strip(),
        slo_target=body.slo_target,
        device_types=(body.device_types or "").strip() or None,
        window_days=body.window_days,
        description=body.description,
        is_active=body.is_active,
    )
    db.add(slo)
    db.commit()
    db.refresh(slo)
    cache.invalidate_prefix("dashboard:")
    return _slo_to_dict(slo)


@router.put("/slo/{slo_id}")
async def update_slo(slo_id: int, body: SloUpsert, db: Session = Depends(get_db)):
    """更新 SLO 配置"""
    slo = db.query(ServiceSlo).filter(ServiceSlo.id == slo_id).first()
    if not slo:
        raise HTTPException(status_code=404, detail="SLO 不存在")
    dup = db.query(ServiceSlo).filter(
        ServiceSlo.service_key == body.service_key, ServiceSlo.id != slo_id
    ).first()
    if dup:
        raise HTTPException(status_code=400, detail=f"service_key '{body.service_key}' 已被占用")
    slo.service_key = body.service_key.strip()
    slo.service_name = body.service_name.strip()
    slo.slo_target = body.slo_target
    slo.device_types = (body.device_types or "").strip() or None
    slo.window_days = body.window_days
    slo.description = body.description
    slo.is_active = body.is_active
    db.commit()
    cache.invalidate_prefix("dashboard:")
    return _slo_to_dict(slo)


@router.delete("/slo/{slo_id}")
async def delete_slo(slo_id: int, db: Session = Depends(get_db)):
    """删除 SLO 配置"""
    slo = db.query(ServiceSlo).filter(ServiceSlo.id == slo_id).first()
    if not slo:
        raise HTTPException(status_code=404, detail="SLO 不存在")
    db.delete(slo)
    db.commit()
    cache.invalidate_prefix("dashboard:")
    return {"ok": True}
