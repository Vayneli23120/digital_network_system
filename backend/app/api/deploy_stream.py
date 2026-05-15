"""
配置部署任务管理和实时流推送模块
"""
import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/deploy", tags=["deploy"])

# 内存中的任务存储（生产环境应使用Redis）
deploy_tasks: Dict[str, dict] = {}

class DeployTaskManager:
    """部署任务管理器"""

    @staticmethod
    def create_task(deploy_data: dict) -> str:
        """创建新的部署任务"""
        task_id = str(uuid.uuid4())
        task = {
            "id": task_id,
            "status": "pending",  # pending, running, completed, failed, aborted
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "deploy_data": deploy_data,
            "devices": {},
            "summary": {
                "total": len(deploy_data.get("target_devices", [])),
                "success": 0,
                "failed": 0,
                "warnings": []
            },
            "event_queue": asyncio.Queue(),
            "is_aborted": False
        }

        # 初始化设备状态
        for device_id in deploy_data.get("target_devices", []):
            task["devices"][str(device_id)] = {
                "device_id": device_id,
                "status": "pending",
                "progress": 0,
                "message": "",
                "cli_logs": [],
                "start_time": None,
                "end_time": None
            }

        deploy_tasks[task_id] = task
        return task_id

    @staticmethod
    def get_task(task_id: str) -> Optional[dict]:
        """获取任务信息"""
        return deploy_tasks.get(task_id)

    @staticmethod
    async def update_device_progress(task_id: str, device_id: str, progress: int, message: str = ""):
        """更新设备执行进度"""
        task = deploy_tasks.get(task_id)
        if task:
            device = task["devices"].get(str(device_id))
            if device:
                device["progress"] = progress
                if message:
                    device["message"] = message
                await task["event_queue"].put({
                    "type": "device_progress",
                    "device_id": device_id,
                    "progress": progress,
                    "message": message,
                    "timestamp": datetime.now().isoformat()
                })

    @staticmethod
    async def add_cli_output(task_id: str, device_id: str, cli_output: str, log_type: str = "info"):
        """添加CLI输出日志"""
        task = deploy_tasks.get(task_id)
        if task:
            device = task["devices"].get(str(device_id))
            if device:
                log_entry = {
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "content": cli_output,
                    "type": log_type
                }
                device["cli_logs"].append(log_entry)
                await task["event_queue"].put({
                    "type": "device_cli",
                    "device_id": device_id,
                    "cli_output": cli_output,
                    "timestamp": log_entry["timestamp"],
                    "log_type": log_type
                })

    @staticmethod
    async def device_started(task_id: str, device_id: str, device_info: dict):
        """设备开始执行"""
        task = deploy_tasks.get(task_id)
        if task:
            device = task["devices"].get(str(device_id))
            if device:
                device["status"] = "running"
                device["start_time"] = datetime.now().isoformat()
                device["device_name"] = device_info.get("name", "")
                device["device_ip"] = device_info.get("ip", "")
                await task["event_queue"].put({
                    "type": "device_start",
                    "device_id": device_id,
                    "device_name": device_info.get("name", ""),
                    "device_ip": device_info.get("ip", ""),
                    "message": f"开始部署到 {device_info.get('name', '')}",
                    "timestamp": datetime.now().isoformat()
                })

    @staticmethod
    async def device_completed(task_id: str, device_id: str, success: bool, message: str = ""):
        """设备执行完成"""
        task = deploy_tasks.get(task_id)
        if task:
            device = task["devices"].get(str(device_id))
            if device:
                device["status"] = "completed" if success else "failed"
                device["end_time"] = datetime.now().isoformat()
                if success:
                    device["progress"] = 100
                    task["summary"]["success"] += 1
                else:
                    task["summary"]["failed"] += 1

                await task["event_queue"].put({
                    "type": "device_complete" if success else "device_failed",
                    "device_id": device_id,
                    "success": success,
                    "message": message,
                    "timestamp": datetime.now().isoformat()
                })

    @staticmethod
    async def complete_task(task_id: str, success: bool, message: str = ""):
        """完成任务"""
        task = deploy_tasks.get(task_id)
        if task:
            task["status"] = "completed" if success else "failed"
            task["updated_at"] = datetime.now().isoformat()
            await task["event_queue"].put({
                "type": "execution_complete",
                "success": success,
                "message": message,
                "summary": task["summary"],
                "timestamp": datetime.now().isoformat()
            })
            # 发送结束标记
            await task["event_queue"].put(None)

    @staticmethod
    async def abort_task(task_id: str):
        """中止任务"""
        task = deploy_tasks.get(task_id)
        if task:
            task["is_aborted"] = True
            task["status"] = "aborted"
            task["updated_at"] = datetime.now().isoformat()
            await task["event_queue"].put({
                "type": "execution_aborted",
                "summary": task["summary"],
                "timestamp": datetime.now().isoformat()
            })
            await task["event_queue"].put(None)


@router.post("/execute-stream")
async def execute_deploy_stream(
    deploy_data: dict,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    创建带实时流的部署任务
    """
    try:
        # 创建任务
        task_id = DeployTaskManager.create_task(deploy_data)

        # 在后台启动部署任务
        background_tasks.add_task(
            run_deploy_task,
            task_id,
            deploy_data,
            db
        )

        return {
            "success": True,
            "task_id": task_id,
            "message": "部署任务已创建",
            "is_production": deploy_data.get("is_production", False),
            "parallel_limit": deploy_data.get("parallel_limit", 1)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/execute/{task_id}/stream")
async def get_execution_stream(task_id: str):
    """
    SSE 流端点：实时推送部署进度和CLI输出
    """
    async def event_generator():
        task = DeployTaskManager.get_task(task_id)
        if not task:
            yield f"data: {json.dumps({'type': 'error', 'message': 'Task not found'})}\n\n"
            return

        try:
            while True:
                # 从队列获取事件
                event = await asyncio.wait_for(
                    task["event_queue"].get(),
                    timeout=300.0  # 5分钟超时
                )

                if event is None:  # 结束标记
                    break

                yield f"data: {json.dumps(event)}\n\n"

                # 如果是完成或中止事件，结束流
                if event["type"] in ["execution_complete", "execution_aborted"]:
                    break

        except asyncio.TimeoutError:
            yield f"data: {json.dumps({'type': 'error', 'message': 'Stream timeout'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/execute/{task_id}/abort")
async def abort_deploy_task(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    中止部署任务
    """
    task = DeployTaskManager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task["status"] not in ["pending", "running"]:
        raise HTTPException(status_code=400, detail=f"Task is already {task['status']}")

    await DeployTaskManager.abort_task(task_id)
    return {"success": True, "message": "任务已中止"}


@router.get("/execute/{task_id}/status")
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    获取任务状态
    """
    task = DeployTaskManager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "id": task["id"],
        "status": task["status"],
        "devices": task["devices"],
        "summary": task["summary"],
        "created_at": task["created_at"],
        "updated_at": task["updated_at"]
    }


async def run_deploy_task(task_id: str, deploy_data: dict, db: Session):
    """
    后台执行部署任务
    """
    task = deploy_tasks.get(task_id)
    if not task:
        return

    task["status"] = "running"
    parallel_limit = deploy_data.get("parallel_limit", 1)
    is_production = deploy_data.get("is_production", False)

    try:
        device_ids = deploy_data.get("target_devices", [])

        # 生产环境串行执行，非生产环境可并行
        if is_production or parallel_limit == 1:
            # 串行执行
            for device_id in device_ids:
                if task.get("is_aborted"):
                    break
                await execute_device(task_id, device_id, deploy_data, db)
        else:
            # 并行执行（限制并发数）
            semaphore = asyncio.Semaphore(parallel_limit)

            async def execute_with_limit(device_id):
                async with semaphore:
                    if not task.get("is_aborted"):
                        await execute_device(task_id, device_id, deploy_data, db)

            await asyncio.gather(*[
                execute_with_limit(did) for did in device_ids
            ])

        # 任务完成
        success = task["summary"]["failed"] == 0 and not task.get("is_aborted")
        await DeployTaskManager.complete_task(
            task_id,
            success,
            "部署完成" if success else "部署失败"
        )

    except Exception as e:
        await DeployTaskManager.complete_task(task_id, False, str(e))


async def execute_device(task_id: str, device_id: int, deploy_data: dict, db: Session):
    """
    执行单个设备的部署
    """
    from app.services.deploy_service_stream import DeployService
    from app.services.device_service import DeviceService

    try:
        # 获取设备信息
        device = DeviceService.get_device(db, device_id)
        if not device:
            await DeployTaskManager.device_completed(
                task_id, device_id, False, "设备不存在"
            )
            return

        # 通知开始
        await DeployTaskManager.device_started(
            task_id, device_id,
            {"name": device.name, "ip": device.ip}
        )

        # 执行部署（带CLI回显）
        result = await DeployService.execute_deploy_with_stream(
            db=db,
            device_id=device_id,
            deploy_data=deploy_data,
            cli_callback=lambda line, log_type="info": asyncio.create_task(
                DeployTaskManager.add_cli_output(task_id, device_id, line, log_type)
            ),
            progress_callback=lambda progress, msg: asyncio.create_task(
                DeployTaskManager.update_device_progress(task_id, device_id, progress, msg)
            )
        )

        # 通知完成
        await DeployTaskManager.device_completed(
            task_id, device_id,
            result.get("success", False),
            result.get("message", "")
        )

    except Exception as e:
        await DeployTaskManager.device_completed(
            task_id, device_id, False, str(e)
        )
