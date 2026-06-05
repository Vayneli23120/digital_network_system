"""
核心基础设施模块

包含：
- celery_app: Celery 任务队列实例
- command_guard: 设备命令安全守卫
"""

from app.core.celery_app import celery_app, get_celery_app

__all__ = ["celery_app", "get_celery_app"]