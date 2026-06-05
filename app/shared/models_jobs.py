"""
作业数据模型

统一作业记录表 —— 所有设备操作的执行记录。
"""

import uuid
import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List

from app.shared.models import Base


class Job(Base):
    """
    统一作业记录表

    所有设备操作（备份/部署/合规扫描/发现/健康检查/命令执行）必须通过此模型记录。
    """
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_type = Column(String(50), nullable=False, index=True)
    # job_type 枚举: backup, deploy, compliance_scan, discovery, health_check, command_exec

    status = Column(String(20), default="pending", index=True)
    # status 枚举: pending, queued, running, success, failed, cancelled, timeout, partial

    # 目标设备（单设备或多设备）
    device_id = Column(Integer, nullable=True, index=True)
    device_ids_json = Column(Text, nullable=True)  # JSON 数组字符串，批量作业

    # 关联的变更单（可选）
    change_request_id = Column(Integer, nullable=True)

    # Celery 任务 ID
    celery_task_id = Column(String(255), nullable=True, index=True)

    # 执行参数（JSON）
    parameters_json = Column(Text, nullable=True)

    # 执行结果（JSON）
    result_json = Column(Text, nullable=True)

    # 操作人
    operator = Column(String(100), nullable=True)

    # 进度百分比
    progress_percent = Column(Integer, default=0)

    # 日志输出
    log_output = Column(Text, nullable=True)

    # 错误信息
    error_message = Column(String(500), nullable=True)

    # 时间戳
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_parameters(self) -> Optional[Dict]:
        """解析参数 JSON"""
        if self.parameters_json:
            return json.loads(self.parameters_json)
        return None

    def set_parameters(self, params: Dict):
        """设置参数 JSON"""
        self.parameters_json = json.dumps(params)

    def get_result(self) -> Optional[Dict]:
        """解析结果 JSON"""
        if self.result_json:
            return json.loads(self.result_json)
        return None

    def set_result(self, result: Dict):
        """设置结果 JSON"""
        self.result_json = json.dumps(result)

    def get_device_ids(self) -> List[int]:
        """解析设备 ID 列表"""
        if self.device_ids_json:
            return json.loads(self.device_ids_json)
        return []

    def set_device_ids(self, ids: List[int]):
        """设置设备 ID 列表"""
        self.device_ids_json = json.dumps(ids)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（API 返回）"""
        return {
            "id": self.id,
            "job_type": self.job_type,
            "status": self.status,
            "device_id": self.device_id,
            "device_ids": self.get_device_ids(),
            "celery_task_id": self.celery_task_id,
            "progress_percent": self.progress_percent,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "result": self.get_result(),
            "operator": self.operator,
        }


# JobType 和 JobStatus 枚举（用于类型检查）
class JobType:
    BACKUP = "backup"
    DEPLOY = "deploy"
    COMPLIANCE_SCAN = "compliance_scan"
    DISCOVERY = "discovery"
    HEALTH_CHECK = "health_check"
    COMMAND_EXEC = "command_exec"
    CONFIG_COLLECT = "config_collect"


class JobStatus:
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    PARTIAL = "partial"  # 批量作业部分成功


def create_job(
    db: Session,
    job_type: str,
    device_id: Optional[int] = None,
    device_ids: Optional[List[int]] = None,
    operator: str = "system",
    parameters: Optional[Dict] = None,
) -> Job:
    """
    创建新作业记录

    Args:
        db: 数据库会话
        job_type: 作业类型
        device_id: 单设备 ID
        device_ids: 批量设备 ID 列表
        operator: 操作人
        parameters: 执行参数

    Returns:
        Job 实例
    """
    job = Job(
        id=str(uuid.uuid4()),
        job_type=job_type,
        status=JobStatus.PENDING,
        device_id=device_id,
        operator=operator,
    )

    if device_ids:
        job.set_device_ids(device_ids)

    if parameters:
        job.set_parameters(parameters)

    db.add(job)
    db.commit()
    db.refresh(job)

    return job


def update_job_status(
    db: Session,
    job_id: str,
    status: str,
    result: Optional[Dict] = None,
    error_message: Optional[str] = None,
    progress_percent: Optional[int] = None,
) -> Optional[Job]:
    """
    更新作业状态

    Args:
        db: 数据库会话
        job_id: 作业 ID
        status: 新状态
        result: 执行结果
        error_message: 错误信息
        progress_percent: 进度百分比

    Returns:
        更新后的 Job 实例，或 None（未找到）
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return None

    job.status = status
    job.updated_at = datetime.utcnow()

    if status == JobStatus.RUNNING:
        job.started_at = datetime.utcnow()

    if status in (JobStatus.SUCCESS, JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.TIMEOUT):
        job.completed_at = datetime.utcnow()

    if result:
        job.set_result(result)

    if error_message:
        job.error_message = error_message

    if progress_percent is not None:
        job.progress_percent = progress_percent

    db.commit()
    db.refresh(job)

    return job