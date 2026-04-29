"""
工具执行日志查询 API

提供日志的查询、搜索、导出功能。
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel

from app.shared.database import get_db
from app.shared.models import LogEntry

router = APIRouter(prefix="/api/tool-logs", tags=["工具日志"])


class LogEntryResponse(BaseModel):
    id: int
    timestamp: datetime
    tool_type: str
    operation: str
    target: Optional[str]
    status: str
    log_content: Optional[str]
    duration_ms: Optional[int]
    created_by: Optional[str]

    class Config:
        from_attributes = True


class LogStatsResponse(BaseModel):
    total: int
    success: int
    failed: int
    running: int
    avg_duration_ms: Optional[float]
    by_tool_type: dict


@router.get("/", response_model=List[LogEntryResponse])
async def list_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    tool_type: Optional[str] = Query(None, description="工具类型: napalm/netmiko/jira"),
    status: Optional[str] = Query(None, description="状态: running/success/failed"),
    target: Optional[str] = Query(None, description="目标设备"),
    created_by: Optional[str] = Query(None, description="操作用户"),
    start_time: Optional[datetime] = Query(None, description="起始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    db: Session = Depends(get_db)
):
    """查询工具执行日志列表"""
    query = db.query(LogEntry)

    if tool_type:
        query = query.filter(LogEntry.tool_type == tool_type)
    if status:
        query = query.filter(LogEntry.status == status)
    if target:
        query = query.filter(LogEntry.target.contains(target))
    if created_by:
        query = query.filter(LogEntry.created_by == created_by)
    if start_time:
        query = query.filter(LogEntry.timestamp >= start_time)
    if end_time:
        query = query.filter(LogEntry.timestamp <= end_time)

    logs = query.order_by(desc(LogEntry.timestamp)).offset(skip).limit(limit).all()
    return logs


@router.get("/search")
async def search_logs(
    keyword: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """全文搜索日志"""
    logs = db.query(LogEntry).filter(
        LogEntry.log_content.contains(keyword)
    ).order_by(desc(LogEntry.timestamp)).limit(limit).all()
    return logs


@router.get("/{log_id}", response_model=LogEntryResponse)
async def get_log(log_id: int, db: Session = Depends(get_db)):
    """获取单条日志详情"""
    log = db.query(LogEntry).filter(LogEntry.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="日志不存在")
    return log


@router.get("/stats/summary", response_model=LogStatsResponse)
async def get_log_stats(
    days: int = Query(7, ge=1, le=365, description="统计最近N天"),
    db: Session = Depends(get_db)
):
    """获取日志统计摘要"""
    from datetime import timedelta
    from sqlalchemy import func

    cutoff = datetime.utcnow() - timedelta(days=days)
    total = db.query(LogEntry).filter(LogEntry.timestamp >= cutoff).count()
    success = db.query(LogEntry).filter(LogEntry.timestamp >= cutoff, LogEntry.status == "success").count()
    failed = db.query(LogEntry).filter(LogEntry.timestamp >= cutoff, LogEntry.status == "failed").count()
    running = db.query(LogEntry).filter(LogEntry.timestamp >= cutoff, LogEntry.status == "running").count()

    avg_duration = db.query(func.avg(LogEntry.duration_ms)).filter(
        LogEntry.timestamp >= cutoff,
        LogEntry.duration_ms.isnot(None)
    ).scalar()

    # 按工具类型统计
    by_tool = {}
    for tool in ["netmiko", "napalm", "jira"]:
        count = db.query(LogEntry).filter(
            LogEntry.timestamp >= cutoff,
            LogEntry.tool_type == tool
        ).count()
        by_tool[tool] = count

    return LogStatsResponse(
        total=total,
        success=success,
        failed=failed,
        running=running,
        avg_duration_ms=round(float(avg_duration), 2) if avg_duration else None,
        by_tool_type=by_tool
    )


@router.delete("/cleanup")
async def cleanup_old_logs(
    days: int = Query(30, ge=1, description="清理N天前的日志"),
    db: Session = Depends(get_db)
):
    """清理过期日志"""
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(days=days)
    deleted = db.query(LogEntry).filter(LogEntry.timestamp < cutoff).delete()
    db.commit()
    return {"deleted": deleted, "message": f"已清理 {days} 天前的 {deleted} 条日志"}
