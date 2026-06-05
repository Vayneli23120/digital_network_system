"""
配置备份 Celery 任务

将备份操作从同步 API 改为异步 Celery 任务执行。
"""

import json
from datetime import datetime
from loguru import logger

from app.core.celery_app import celery_app


@celery_app.task(
    bind=True,
    name="app.tasks.backup_tasks.backup_device",
    max_retries=2,
    default_retry_delay=30,
    acks_late=True,
    queue="device_ops",
)
def backup_device(self, job_id: str, device_id: int, operator: str = "system"):
    """
    异步备份单个设备配置

    Args:
        job_id: Job 表记录 ID，用于更新状态
        device_id: 目标设备 ID
        operator: 操作人
    """
    from app.shared.database import get_db_manager
    from app.shared.models_jobs import Job, JobStatus, update_job_status
    from app.shared.models import Device
    from app.features.backups.netmiko_service import NetmikoService
    from app.features.credentials.credential_service import CredentialService

    db_manager = get_db_manager()

    with db_manager.session_scope() as db:
        # 更新 Job 状态为 running
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return {"success": False, "error": "Job not found"}

        job.status = JobStatus.RUNNING
        job.started_at = datetime.utcnow()
        job.celery_task_id = self.request.id
        db.commit()

        # 获取设备信息
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            update_job_status(
                db, job_id, JobStatus.FAILED,
                error_message=f"Device {device_id} not found"
            )
            return {"success": False, "error": f"Device {device_id} not found"}

        try:
            # 获取凭证
            cred_service = CredentialService(db)
            credentials = cred_service.get_credentials_for_device(device)

            # 执行备份（复用现有 NetmikoService）
            netmiko_svc = NetmikoService()
            result = netmiko_svc.backup_device(device, credentials, operator)

            # 更新 Job 状态
            if result.get("success"):
                update_job_status(
                    db, job_id, JobStatus.SUCCESS,
                    result=result
                )
                logger.info(f"Backup job {job_id} completed successfully for device {device.name}")

                # ===== 备份成功后触发 RAG 索引 =====
                from app.shared.config import get_config
                config = get_config()
                if config.database.is_postgresql:
                    # 异步索引到知识库
                    from app.tasks.ai_tasks import index_device_config_task
                    backup_content = result.get("config_content", "")
                    if backup_content:
                        index_device_config_task.delay(
                            device_id=device_id,
                            device_name=device.name,
                            config_content=backup_content,
                            vendor=device.vendor or "cisco",
                        )
                        logger.info(f"RAG indexing task triggered for device {device.name}")

            else:
                update_job_status(
                    db, job_id, JobStatus.FAILED,
                    error_message=result.get("error", "Unknown error")
                )
                logger.error(f"Backup job {job_id} failed for device {device.name}")

            return result

        except Exception as exc:
            logger.error(f"Backup task failed for device {device_id}: {exc}")
            try:
                update_job_status(
                    db, job_id, JobStatus.FAILED,
                    error_message=str(exc)
                )
                # 重试任务
                self.retry(exc=exc)
            except self.MaxRetriesExceededError:
                logger.error(f"Backup job {job_id} exceeded max retries")
                return {"success": False, "error": str(exc)}


@celery_app.task(
    bind=True,
    name="app.tasks.backup_tasks.backup_devices_batch",
    acks_late=True,
    queue="device_ops",
)
def backup_devices_batch(self, job_id: str, device_ids: list, operator: str = "system"):
    """
    批量备份设备配置

    使用 Celery group 并发执行多个单设备备份任务。

    Args:
        job_id: 主 Job ID
        device_ids: 设备 ID 列表
        operator: 操作人
    """
    from celery import group
    from app.shared.database import get_db_manager
    from app.shared.models_jobs import Job, JobStatus, update_job_status

    db_manager = get_db_manager()

    with db_manager.session_scope() as db:
        # 更新主 Job 状态
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = JobStatus.RUNNING
            job.started_at = datetime.utcnow()
            db.commit()

        # 创建子任务组
        subtasks = group(
            backup_device.s(f"{job_id}-{i}", device_id, operator)
            for i, device_id in enumerate(device_ids)
        )

        # 执行子任务组
        result_group = subtasks.apply_async()

        logger.info(f"Batch backup job {job_id} started with {len(device_ids)} devices")

        return {
            "success": True,
            "job_id": job_id,
            "device_count": len(device_ids),
            "group_id": result_group.id,
        }