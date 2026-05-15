"""
审批工作流模型
"""
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON, Enum, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base


class ApprovalStatus(str, PyEnum):
    """审批状态"""
    DRAFT = "draft"                    # 草稿
    PENDING_APPROVAL = "pending"       # 待审批
    APPROVED = "approved"              # 已批准
    REJECTED = "rejected"              # 已拒绝
    EXECUTING = "executing"            # 执行中
    COMPLETED = "completed"            # 已完成
    FAILED = "failed"                  # 失败
    ROLLED_BACK = "rolled_back"        # 已回滚


class ApprovalLevel(str, PyEnum):
    """审批级别"""
    NONE = "none"                      # 无需审批
    LEVEL_1 = "level_1"                # 一级审批（团队负责人）
    LEVEL_2 = "level_2"                # 二级审批（部门负责人）
    LEVEL_3 = "level_3"                # 三级审批（变更委员会）


class DeployApproval(Base):
    """部署审批记录"""
    __tablename__ = "deploy_approvals"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 关联部署任务
    task_id = Column(String(36), ForeignKey("deploy_tasks.id"), unique=True)

    # 审批级别
    approval_level = Column(Enum(ApprovalLevel), default=ApprovalLevel.LEVEL_1)

    # 当前状态
    status = Column(Enum(ApprovalStatus), default=ApprovalStatus.DRAFT)

    # 申请人
    requester_id = Column(Integer, ForeignKey("users.id"))
    requester = relationship("User", foreign_keys=[requester_id])

    # 审批人
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approver = relationship("User", foreign_keys=[approver_id])

    # 申请时间
    requested_at = Column(DateTime, default=datetime.now)

    # 审批时间
    approved_at = Column(DateTime, nullable=True)

    # 审批意见
    approval_comment = Column(Text, nullable=True)

    # 拒绝原因
    rejection_reason = Column(Text, nullable=True)

    # 审批链（多级审批记录）
    approval_chain = Column(JSON, default=list)  # [{level, approver_id, status, comment, time}]

    # 审批超时时间（小时）
    timeout_hours = Column(Integer, default=24)

    # 最后更新时间
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "approval_level": self.approval_level.value,
            "status": self.status.value,
            "requester": self.requester.username if self.requester else None,
            "approver": self.approver.username if self.approver else None,
            "requested_at": self.requested_at.isoformat() if self.requested_at else None,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "approval_comment": self.approval_comment,
            "rejection_reason": self.rejection_reason,
            "approval_chain": self.approval_chain,
            "timeout_hours": self.timeout_hours,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class ApprovalPolicy(Base):
    """审批策略配置"""
    __tablename__ = "approval_policies"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 策略名称
    name = Column(String(100), nullable=False)

    # 适用条件
    conditions = Column(JSON, default=dict)
    # {
    #   "is_production": true,
    #   "min_device_count": 3,
    #   "device_patterns": ["core", "border"],
    #   "required_approval": true
    # }

    # 审批级别
    approval_level = Column(Enum(ApprovalLevel), default=ApprovalLevel.LEVEL_1)

    # 默认审批人
    default_approvers = Column(JSON, default=list)  # [user_id, user_id, ...]

    # 是否启用
    is_active = Column(Boolean, default=True)

    # 创建时间
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "conditions": self.conditions,
            "approval_level": self.approval_level.value,
            "default_approvers": self.default_approvers,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class ApprovalNotification(Base):
    """审批通知记录"""
    __tablename__ = "approval_notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 关联审批
    approval_id = Column(Integer, ForeignKey("deploy_approvals.id"))

    # 接收人
    user_id = Column(Integer, ForeignKey("users.id"))

    # 通知类型
    notification_type = Column(String(50))  # approval_request, approved, rejected, timeout

    # 通知渠道
    channels = Column(JSON, default=list)  # ["email", "wechat", "sms"]

    # 通知内容
    content = Column(Text)

    # 是否已发送
    is_sent = Column(Boolean, default=False)

    # 发送时间
    sent_at = Column(DateTime, nullable=True)

    # 是否已读
    is_read = Column(Boolean, default=False)

    # 读取时间
    read_at = Column(DateTime, nullable=True)

    # 创建时间
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "approval_id": self.approval_id,
            "user_id": self.user_id,
            "notification_type": self.notification_type,
            "channels": self.channels,
            "content": self.content,
            "is_sent": self.is_sent,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "is_read": self.is_read,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
