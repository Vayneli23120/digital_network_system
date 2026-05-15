"""
部署历史 API
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.deploy import DeployTask, DeployDeviceRecord

router = APIRouter(prefix="/deploy-history", tags=["deploy-history"])


@router.get("/tasks")
async def list_deploy_tasks(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    mode: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取部署任务历史列表"""
    query = db.query(DeployTask)

    if status:
        query = query.filter(DeployTask.status == status)
    if mode:
        query = query.filter(DeployTask.mode == mode)

    total = query.count()
    tasks = query.order_by(desc(DeployTask.created_at)) \
                 .offset((page - 1) * size) \
                 .limit(size) \
                 .all()

    return {
        "total": total,
        "items": [task.to_dict() for task in tasks],
        "page": page,
        "size": size
    }


@router.get("/tasks/{task_id}")
async def get_deploy_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取单个部署任务详情"""
    task = db.query(DeployTask).filter(DeployTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return task.to_dict()


@router.get("/tasks/{task_id}/devices")
async def get_task_devices(
    task_id: str,
    include_logs: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取任务的所有设备执行记录"""
    task = db.query(DeployTask).filter(DeployTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    records = db.query(DeployDeviceRecord) \
                .filter(DeployDeviceRecord.task_id == task_id) \
                .all()

    return {
        "task_id": task_id,
        "devices": [record.to_dict(include_logs=include_logs) for record in records]
    }


@router.get("/tasks/{task_id}/logs")
async def get_device_logs(
    task_id: str,
    device_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取设备CLI日志"""
    query = db.query(DeployDeviceRecord) \
              .filter(DeployDeviceRecord.task_id == task_id)

    if device_id:
        query = query.filter(DeployDeviceRecord.device_id == device_id)

    records = query.all()

    return {
        "task_id": task_id,
        "logs": [
            {
                "device_id": r.device_id,
                "device_name": r.device_name,
                "logs": r.cli_logs
            }
            for r in records
        ]
    }


@router.delete("/tasks/{task_id}")
async def delete_deploy_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除部署任务（及其设备记录）"""
    task = db.query(DeployTask).filter(DeployTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 只允许删除已完成的任务
    if task.status in ["running"]:
        raise HTTPException(status_code=400, detail="Cannot delete running task")

    db.delete(task)
    db.commit()

    return {"success": True, "message": "Task deleted"}
