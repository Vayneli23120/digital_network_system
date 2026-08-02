"""
配置部署 Celery 任务

`app/core/celery_app.py` 的 task_routes 将本模块路由到 device_ops 队列。
`deploy_scheduled` 消费 `POST /api/deploy/schedule` 落库的 Job，
按 eta 调度时间真实执行部署（复用 execute_deploy 的实现主体）。
"""

import asyncio
from datetime import datetime
from loguru import logger

from app.core.celery_app import celery_app


@celery_app.task(
    bind=True,
    name="app.tasks.deploy_tasks.deploy_scheduled",
    acks_late=True,
    queue="device_ops",
)
def deploy_scheduled(self, job_id: str, operator: str = "system"):
    """
    执行预约的部署任务

    从 Job.parameters_json 读取 deploy_data，调用部署实现主体，
    执行期间 Job 状态在独立会话中维护（与部署实现主体的会话隔离）。

    Args:
        job_id: Job 表记录 ID
        operator: 操作人（写入部署历史与审计日志）
    """
    from app.shared.database import get_db_manager
    from app.shared.models_jobs import Job, JobStatus, update_job_status

    db_manager = get_db_manager()

    # 阶段1：加载 Job，标记为 running（与部署执行分离的短会话）
    with db_manager.session_scope() as db:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Deploy job {job_id} not found")
            return {"success": False, "error": "Job not found"}

        job.status = JobStatus.RUNNING
        job.started_at = datetime.utcnow()
        job.celery_task_id = self.request.id
        db.commit()

        params = job.get_parameters() or {}
        deploy_data = params.get("deploy_data")

    if not deploy_data:
        with db_manager.session_scope() as db:
            update_job_status(
                db, job_id, JobStatus.FAILED,
                error_message="缺少部署参数 deploy_data",
            )
        logger.error(f"Deploy job {job_id} missing deploy_data in parameters")
        return {"success": False, "error": "deploy_data missing"}

    # 阶段2：执行部署。部署实现内部自开 DB 会话，与 Job 会话独立，
    # 因此这里延迟导入，避免在 worker 侧引入 router 模块。
    from app.features.deploy.router import _run_deploy_impl

    try:
        result = asyncio.run(_run_deploy_impl(deploy_data, operator))
    except Exception as exc:
        logger.error(f"Scheduled deploy failed for job {job_id}: {exc}")
        with db_manager.session_scope() as db:
            update_job_status(
                db, job_id, JobStatus.FAILED,
                error_message=str(exc)[:500],
            )
        return {"success": False, "error": str(exc)}

    success = bool(result.get("success"))
    summary = result.get("summary", {})

    with db_manager.session_scope() as db:
        if success:
            update_job_status(
                db, job_id, JobStatus.SUCCESS,
                result={
                    "summary": summary,
                    "history_id": result.get("history_id"),
                },
            )
            logger.info(f"Deploy job {job_id} completed successfully")
        else:
            update_job_status(
                db, job_id, JobStatus.FAILED,
                error_message="部署失败，请查看服务端日志",
            )
            logger.error(f"Deploy job {job_id} reported failure")

    return result
