"""Dashboard router — 带缓存"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional

from app.shared.database import get_db
from .dashboard_service import get_dashboard_summary as svc_get_dashboard_summary
from .dashboard_service import get_fault_trend as svc_get_fault_trend
from ..services.cache import cache, _DASHBOARD_TTL, _TREND_TTL, _cache_key

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


@router.post("/cache/clear")
async def clear_dashboard_cache():
    """清除 Dashboard 缓存（在数据变更后调用）"""
    count = cache.invalidate_prefix("dashboard:")
    return {"cleared": count, "message": f"已清除 {count} 个 Dashboard 缓存项"}
