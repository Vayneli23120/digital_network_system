"""
Celery 应用实例

队列划分：
- device_ops: 设备操作（备份/部署/执行命令），高优先级
- ai_tasks: AI 分析任务，中优先级，设有超时
- notifications: 通知发送，低优先级
- scheduled: 定时任务（健康检查/合规扫描）
"""

from celery import Celery
from loguru import logger


def create_celery_app() -> Celery:
    """创建 Celery 应用实例"""
    from app.shared.config import get_config

    config = get_config()
    redis_url = config.celery.broker_url

    celery_app = Celery(
        "nas",
        broker=redis_url,
        backend=config.celery.result_backend,
    )

    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_acks_late=True,          # 任务完成后才 ACK，避免 worker 崩溃丢任务
        worker_prefetch_multiplier=1, # 每次只取 1 个任务，避免长任务阻塞
        task_routes={
            "app.tasks.backup_tasks.*": {"queue": "device_ops"},
            "app.tasks.deploy_tasks.*": {"queue": "device_ops"},
            "app.tasks.discovery_tasks.*": {"queue": "device_ops"},
            "app.tasks.ai_tasks.*": {"queue": "ai_tasks"},
            "app.tasks.notification_tasks.*": {"queue": "notifications"},
            "app.tasks.scheduled_tasks.*": {"queue": "scheduled"},
        },
        task_default_queue="device_ops",
        task_time_limit=300,         # 硯超时 5 分钟
        task_soft_time_limit=240,    # 软超时 4 分钟（触发 SoftTimeLimitExceeded）
    )

    logger.info(f"Celery 应用初始化完成，broker: {redis_url}")
    return celery_app


# 全局 Celery 实例（延迟初始化）
_celery_app: Celery | None = None


def get_celery_app() -> Celery:
    """获取 Celery 应用实例（单例）"""
    global _celery_app
    if _celery_app is None:
        _celery_app = create_celery_app()
    return _celery_app


# 直接导出实例（用于 tasks 模块导入）
celery_app = get_celery_app()