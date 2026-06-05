"""
作业监控 API

提供统一的作业查询和取消接口。
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from app.shared.database import get_db
from app.shared.models_jobs import Job, JobType, JobStatus

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("")
def list_jobs(
    job_type: Optional[str] = None,
    status: Optional[str] = None,
    device_id: Optional[int] = None,
    operator: Optional[str] = None,
    skip: int = 0,
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    """
    查询作业列表

    支持按类型、状态、设备、操作人筛选。
    """
    query = db.query(Job).order_by(Job.created_at.desc())

    if job_type:
        query = query.filter(Job.job_type == job_type)
    if status:
        query = query.filter(Job.status == status)
    if device_id:
        query = query.filter(Job.device_id == device_id)
    if operator:
        query = query.filter(Job.operator == operator)

    total = query.count()
    items = query.offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": [job.to_dict() for job in items]
    }


@router.get("/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db)):
    """
    获取单个作业详情
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job.to_dict()


@router.get("/{job_id}/log")
def get_job_log(job_id: str, db: Session = Depends(get_db)):
    """
    获取作业执行日志
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return {
        "job_id": job_id,
        "log_output": job.log_output or "",
        "status": job.status,
    }


@router.post("/{job_id}/cancel")
def cancel_job(job_id: str, db: Session = Depends(get_db)):
    """
    取消正在运行或等待中的作业

    - 调用 Celery control.revoke 撤销任务
    - 更新 Job 状态为 cancelled
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job.status not in (JobStatus.PENDING, JobStatus.QUEUED, JobStatus.RUNNING):
        raise HTTPException(
            status_code=400,
            detail=f"Job is {job.status}, cannot cancel"
        )

    # 撤销 Celery 任务
    if job.celery_task_id:
        try:
            from app.core.celery_app import celery_app
            celery_app.control.revoke(job.celery_task_id, terminate=True)
        except Exception as e:
            # Celery 可能不可用，仅更新数据库状态
            pass

    # 更新状态
    job.status = JobStatus.CANCELLED
    job.completed_at = __import__('datetime').datetime.utcnow()
    db.commit()

    return {
        "success": True,
        "job_id": job_id,
        "status": JobStatus.CANCELLED,
        "message": "Job cancelled"
    }


@router.get("/stats")
def job_stats(
    job_type: Optional[str] = None,
    days: int = Query(7, le=30),
    db: Session = Depends(get_db)
):
    """
    作业统计

    返回指定天数内的作业执行统计。
    """
    from datetime import datetime, timedelta
    from sqlalchemy import func

    start_date = datetime.utcnow() - timedelta(days=days)

    query = db.query(
        Job.job_type,
        Job.status,
        func.count(Job.id).label("count")
    ).filter(Job.created_at >= start_date)

    if job_type:
        query = query.filter(Job.job_type == job_type)

    results = query.group_by(Job.job_type, Job.status).all()

    stats = {}
    for job_type_val, status_val, count in results:
        if job_type_val not in stats:
            stats[job_type_val] = {}
        stats[job_type_val][status_val] = count

    return {
        "days": days,
        "start_date": start_date.isoformat(),
        "stats": stats
    }


@router.get("/types")
def list_job_types():
    """
    获取支持的作业类型列表
    """
    return {
        "types": [
            {"value": JobType.BACKUP, "label": "配置备份"},
            {"value": JobType.DEPLOY, "label": "配置部署"},
            {"value": JobType.COMPLIANCE_SCAN, "label": "合规扫描"},
            {"value": JobType.DISCOVERY, "label": "设备发现"},
            {"value": JobType.HEALTH_CHECK, "label": "健康检查"},
            {"value": JobType.COMMAND_EXEC, "label": "命令执行"},
        ]
    }


@router.get("/statuses")
def list_job_statuses():
    """
    获取支持的作业状态列表
    """
    return {
        "statuses": [
            {"value": JobStatus.PENDING, "label": "等待中", "color": "gray"},
            {"value": JobStatus.QUEUED, "label": "已入队", "color": "blue"},
            {"value": JobStatus.RUNNING, "label": "运行中", "color": "orange"},
            {"value": JobStatus.SUCCESS, "label": "成功", "color": "green"},
            {"value": JobStatus.FAILED, "label": "失败", "color": "red"},
            {"value": JobStatus.CANCELLED, "label": "已取消", "color": "gray"},
            {"value": JobStatus.TIMEOUT, "label": "超时", "color": "red"},
            {"value": JobStatus.PARTIAL, "label": "部分成功", "color": "yellow"},
        ]
    }