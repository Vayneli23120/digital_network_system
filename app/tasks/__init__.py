"""
Celery 任务模块

包含：
- ai_tasks: AI 分析任务
- notification_tasks: 通知发送任务（占位，待实现）
- scheduled_tasks: 定时任务（占位，待实现）

批次二·步骤5：backup_tasks / deploy_tasks 已下线——celery worker 无法携带操作者
会话级 SSH 凭证，与「密码不存储在服务器上」原则互斥；备份与部署统一走同步端点。

注意：这里不再在导入时生成占位模块文件。
原实现用 `Path.write_text()` 写入中文 docstring，在默认编码为 cp1252/GBK 的
Windows 上会抛 UnicodeEncodeError，导致整个 app.tasks 包无法导入（Celery 任务
与相关测试全部失败）；在 Linux 上则会静默生成未纳入版本控制的源文件。
占位模块现在是仓库里的真实文件。
"""

# 延迟导入各任务模块，避免循环依赖
__all__ = [
    "ai_tasks",
    "notification_tasks",
    "scheduled_tasks",
]
