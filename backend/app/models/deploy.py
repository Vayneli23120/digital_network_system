"""
部署任务模型
用于持久化存储配置部署的执行历史
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base


class DeployTask(Base):
    """配置部署任务"""
    __tablename__ = "deploy_tasks"

    id = Column(String(36), primary_key=True)  # UUID
    status = Column(String(20), default="pending")  # pending, running, completed, failed, aborted

    # 部署模式
    mode = Column(String(20))  # backup, template
    backup_file = Column(String(255), nullable=True)
    template_id = Column(Integer, ForeignKey("config_templates.id"), nullable=True)

    # 环境信息
    is_production = Column(Boolean, default=False)
    parallel_limit = Column(Integer, default=1)

    # 执行信息
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.now)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    elapsed_seconds = Column(Integer, default=0)

    # Phase 3: 维护窗口
    scheduled_at = Column(DateTime, nullable=True)
    maintenance_window = Column(String(50), nullable=True)

    # 摘要信息
    total_devices = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)

    # 变量配置
    variables = Column(JSON, default=dict)

    # 创建者
    creator = relationship("User", foreign_keys=[created_by])
    template = relationship("ConfigTemplate", foreign_keys=[template_id])

    # 设备执行记录
    device_records = relationship(
        "DeployDeviceRecord",
        back_populates="task",
        cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "status": self.status,
            "mode": self.mode,
            "is_production": self.is_production,
            "parallel_limit": self.parallel_limit,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "elapsed_seconds": self.elapsed_seconds,
            "summary": {
                "total": self.total_devices,
                "success": self.success_count,
                "failed": self.failed_count
            },
            "created_by": self.creator.username if self.creator else None
        }


class DeployDeviceRecord(Base):
    """设备部署执行记录"""
    __tablename__ = "deploy_device_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(36), ForeignKey("deploy_tasks.id"))
    device_id = Column(Integer, ForeignKey("devices.id"))

    # 设备信息快照
    device_name = Column(String(255))
    device_ip = Column(String(50))

    # 执行状态
    status = Column(String(20), default="pending")  # pending, running, completed, failed, aborted
    progress = Column(Integer, default=0)
    message = Column(Text, nullable=True)

    # 时间戳
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # CLI 日志（可选存储，大量日志可能存文件系统）
    cli_logs = Column(JSON, default=list)

    # 关联
    task = relationship("DeployTask", back_populates="device_records")
    device = relationship("Device")

    def to_dict(self, include_logs=False):
        data = {
            "id": self.id,
            "task_id": self.task_id,
            "device_id": self.device_id,
            "device_name": self.device_name,
            "device_ip": self.device_ip,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }
        if include_logs:
            data["cli_logs"] = self.cli_logs
        return data
