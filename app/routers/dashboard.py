"""Dashboard router"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..services.dashboard_service import get_dashboard_summary as svc_get_dashboard_summary
from ..services.dashboard_service import get_fault_trend as svc_get_fault_trend

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
async def get_dashboard_summary(db: Session = Depends(get_db)):
    """获取 Dashboard 摘要数据"""
    return svc_get_dashboard_summary(db)


@router.get("/fault-trend")
async def get_fault_trend(
    db: Session = Depends(get_db),
    time_range: str = "30d",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """获取故障趋势数据

    Args:
        time_range: 时间范围 - 7d(近 7 天), 30d(近 30 天), 3m(近 3 个月), 1y(近 1 年), custom(自定义)
        start_date: 自定义开始日期 (YYYY-MM-DD)
        end_date: 自定义结束日期 (YYYY-MM-DD)
    """
    return svc_get_fault_trend(db, time_range=time_range, start_date=start_date, end_date=end_date)
