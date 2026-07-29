"""配置部署 Celery 任务（占位，待实现）

`app/core/celery_app.py` 的 task_routes 指向本模块，因此它必须存在且可导入。
实现部署任务时请参考 backup_tasks.py 的范式：
用 `get_db_manager().session_scope()` 管理会话，通过 Job 表记录状态。
"""
