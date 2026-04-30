"""
数据库模型定义
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean,
    DECIMAL, ForeignKey, Index, CheckConstraint, Table
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class Device(Base):
    """设备表"""
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    ip = Column(String(50), index=True)
    model = Column(String(100))
    serial_number = Column(String(100))
    location = Column(String(200))
    role = Column(String(50), index=True)  # access, distribution, core
    status = Column(String(50), default="online", index=True)  # online, offline, maintenance, retired
    purchase_date = Column(DateTime)
    vendor = Column(String(200))
    purchase_cost = Column(DECIMAL(10, 2), default=0)
    photo_dir = Column(String(500))
    credential_group = Column(String(50), default="default")
    last_backup_time = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    backups = relationship("BackupRecord", back_populates="device", cascade="all, delete-orphan")
    faults = relationship("FaultRecord", back_populates="device", cascade="all, delete-orphan")
    maintenances = relationship("MaintenanceRecord", back_populates="device", cascade="all, delete-orphan")
    photos = relationship("DevicePhoto", back_populates="device", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Device(name='{self.name}', ip='{self.ip}', status='{self.status}')>"


class BackupRecord(Base):
    """备份记录表"""
    __tablename__ = "backup_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"), index=True)
    backup_file = Column(String(500), nullable=False)
    file_size = Column(Integer)
    md5_hash = Column(String(64))
    has_change = Column(Boolean, default=False)
    diff_file = Column(String(500))
    config_snapshot = Column(Text)  # 配置快照文本
    backup_time = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    operator = Column(String(100))
    device_name = Column(String(100))

    # 关系
    device = relationship("Device", back_populates="backups")

    def __repr__(self):
        return f"<BackupRecord(device_name='{self.device_name}', time='{self.backup_time}')>"


class FaultRecord(Base):
    """故障记录表"""
    __tablename__ = "fault_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"), index=True)
    fault_no = Column(String(50), unique=True, nullable=False)
    fault_time = Column(DateTime, index=True)
    description = Column(Text)
    severity = Column(String(20), index=True)  # critical, major, minor, warning
    downtime_minutes = Column(Integer, default=0)
    impact = Column(Text)
    resolution = Column(Text)
    cost = Column(DECIMAL(10, 2), default=0)
    reporter = Column(String(100))
    status = Column(String(20), default="open", index=True)  # open, investigating, resolved, closed
    maintenance_id = Column(Integer, ForeignKey("maintenance_records.id"), nullable=True)  # 关联的维修单
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    device_name = Column(String(100))

    # 关系
    device = relationship("Device", back_populates="faults")
    maintenance = relationship("MaintenanceRecord", foreign_keys=[maintenance_id])

    def __repr__(self):
        return f"<FaultRecord(fault_no='{self.fault_no}', device='{self.device_name}')>"


class MaintenanceRecord(Base):
    """维修记录表"""
    __tablename__ = "maintenance_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"), index=True)
    maint_no = Column(String(50), unique=True, nullable=False)
    maint_type = Column(String(20), index=True)  # preventive, corrective, upgrade, emergency
    maint_time = Column(DateTime, index=True)
    parts_replaced = Column(Text)
    parts_cost = Column(DECIMAL(10, 2), default=0)
    labor_hours = Column(DECIMAL(5, 2), default=0)
    labor_cost = Column(DECIMAL(10, 2), default=0)
    vendor = Column(String(200))
    description = Column(Text)
    post_status = Column(String(50))
    operator = Column(String(100))
    fault_id = Column(Integer, ForeignKey("fault_records.id"), nullable=True)  # 关联的故障单
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    device_name = Column(String(100))

    # 关系
    device = relationship("Device", back_populates="maintenances")
    fault = relationship("FaultRecord", foreign_keys=[fault_id])

    def __repr__(self):
        return f"<MaintenanceRecord(maint_no='{self.maint_no}', device='{self.device_name}')>"


class DevicePhoto(Base):
    """设备照片表"""
    __tablename__ = "device_photos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"))
    photo_path = Column(String(500), nullable=False)
    photo_type = Column(String(20))  # front, back, label, rack, other
    upload_date = Column(DateTime, default=datetime.utcnow)
    uploader = Column(String(100))
    device_name = Column(String(100))

    # 关系
    device = relationship("Device", back_populates="photos")

    def __repr__(self):
        return f"<DevicePhoto(device='{self.device_name}', type='{self.photo_type}')>"


class AuditLog(Base):
    """操作审计表"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    operator = Column(String(100))
    action = Column(String(100), nullable=False)
    target_type = Column(String(50))
    target_id = Column(Integer)
    details = Column(Text)
    ip_address = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<AuditLog(action='{self.action}', operator='{self.operator}')>"


class ConfigTemplate(Base):
    """配置模板表"""
    __tablename__ = "config_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    template_content = Column(Text, nullable=False)
    variables = Column(Text)  # JSON 格式的变量定义
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ConfigTemplate(name='{self.name}')>"


class CredentialGroup(Base):
    """SSH 凭证组表"""
    __tablename__ = "credential_groups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(500))
    username = Column(String(100), nullable=False)
    password_encrypted = Column(String(500), nullable=False)  # 加密存储密码
    enable_password_encrypted = Column(String(500))  # 加密存储 enable 密码
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<CredentialGroup(name='{self.name}')>"


# =============================================================================
# 用户权限系统模型 (预留，v1.1 启用)
# =============================================================================

user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True)
)

role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True)
)


class User(Base):
    """
    用户表 - 预留用于 v1.1 的认证系统

    功能预留说明：
    - 当前版本 (v1.0) 不启用用户认证
    - v1.1 将支持 JWT/OAuth2 认证
    - 支持多角色分配
    - 密码使用 bcrypt 加密
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(200), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=False)  # bcrypt hash
    full_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 多对多关系：用户 <-> 角色
    roles = relationship("Role", secondary=user_roles, back_populates="users")

    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"


class Role(Base):
    """
    角色表 - 预留用于 v1.1 的 RBAC 权限系统

    功能预留说明：
    - 支持预定义角色 (admin, operator, viewer)
    - 支持自定义角色
    - 多对多关联权限
    """
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(String(500), nullable=True)
    is_system = Column(Boolean, default=False)  # 系统内置角色，不可删除
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 多对多关系
    users = relationship("User", secondary=user_roles, back_populates="roles")
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")

    def __repr__(self):
        return f"<Role(name='{self.name}')>"


class Permission(Base):
    """
    权限表 - 预留用于 v1.1 的细粒度权限控制

    权限格式: resource:action
    示例:
    - device:read    # 查看设备
    - device:write   # 创建设备
    - device:delete  # 删除设备
    - backup:execute # 执行备份
    - config:deploy  # 部署配置
    """
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(String(500), nullable=True)
    resource = Column(String(50), nullable=False, index=True)  # 资源类型: device, backup, config 等
    action = Column(String(50), nullable=False)  # 操作: read, write, delete, execute 等
    created_at = Column(DateTime, default=datetime.utcnow)

    # 多对多关系
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")

    def __repr__(self):
        return f"<Permission(name='{self.name}')>"


class UserSession(Base):
    """
    用户会话表 - 预留用于 v1.1 的会话管理

    支持功能:
    - JWT Token 黑名单
    - 会话追踪
    - 强制下线
    """
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_jti = Column(String(100), unique=True, nullable=False, index=True)  # JWT ID
    token_type = Column(String(20), default="access")  # access/refresh
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    revoked = Column(Boolean, default=False)
    revoked_at = Column(DateTime, nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)

    # 关系
    user = relationship("User", backref="sessions")

    def __repr__(self):
        return f"<UserSession(user_id={self.user_id}, jti='{self.token_jti[:8]}...')>"


class LogEntry(Base):
    """工具执行日志表 - 记录 napalm/netmiko/jira 等工具的执行日志"""
    __tablename__ = "log_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    tool_type = Column(String(50), nullable=False, index=True)  # napalm, netmiko, jira
    operation = Column(String(200), nullable=False)  # 执行的操作描述
    target = Column(String(200), nullable=True)  # 目标设备/工单等
    status = Column(String(20), nullable=False, default="running")  # running, success, failed
    log_content = Column(Text, nullable=True)  # 完整日志内容
    duration_ms = Column(Integer, nullable=True)  # 执行耗时（毫秒）
    created_by = Column(String(100), nullable=True)  # 操作用户

    def __repr__(self):
        return f"<LogEntry(tool={self.tool_type}, op={self.operation}, status={self.status})>"


class SparePart(Base):
    """备件资产表"""
    __tablename__ = "spare_parts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, index=True)
    part_number = Column(String(100), unique=True, nullable=False, index=True)
    serial_number = Column(String(100), nullable=True, index=True)  # 序列号，用于扫码枪识别
    po_number = Column(String(100), nullable=True, index=True)  # 采购订单号
    category = Column(String(100), nullable=True, index=True)  # 模块/电源/线缆/其他
    manufacturer = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    quantity_in_stock = Column(Integer, default=0, nullable=False)
    min_quantity = Column(Integer, default=0)  # 最低库存预警值
    unit_price = Column(DECIMAL(10, 2), default=0)
    location = Column(String(200), nullable=True)  # 存放位置
    status = Column(String(20), default="active")  # active, inactive, depleted
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 一对多关系
    movements = relationship("SparePartMovement", back_populates="part", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<SparePart(name='{self.name}', qty={self.quantity_in_stock})>"


class SparePartMovement(Base):
    """备件出入库记录表"""
    __tablename__ = "spare_part_movements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    part_id = Column(Integer, ForeignKey("spare_parts.id", ondelete="CASCADE"), nullable=False, index=True)
    movement_type = Column(String(10), nullable=False)  # in / out
    quantity = Column(Integer, nullable=False)
    reason = Column(String(500), nullable=True)  # 出入库原因
    operator = Column(String(100), nullable=True)  # 操作人
    reference = Column(String(200), nullable=True)  # 关联工单/设备编号等
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    part = relationship("SparePart", back_populates="movements")

    def __repr__(self):
        return f"<SparePartMovement(part_id={self.part_id}, type={self.movement_type}, qty={self.quantity})>"


class MaintenancePlan(Base):
    """维护计划表 - 计划性运维"""
    __tablename__ = "maintenance_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="SET NULL"), nullable=True)
    device_name = Column(String(100))
    plan_type = Column(String(20), nullable=False, index=True)  # routine_check, parts_replace, vendor_service
    cycle_days = Column(Integer, default=30)
    next_date = Column(DateTime, nullable=False, index=True)
    data_basis = Column(Text)  # 数据依据（为什么做）
    auto_generate = Column(Boolean, default=True)
    status = Column(String(20), default="active", index=True)  # active, paused, completed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    tasks = relationship("MaintenanceTask", back_populates="plan", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<MaintenancePlan(name='{self.name}', type='{self.plan_type}')>"


class MaintenanceTask(Base):
    """运维任务表 - 计划性运维的具体执行任务"""
    __tablename__ = "maintenance_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_id = Column(Integer, ForeignKey("maintenance_plans.id", ondelete="SET NULL"), nullable=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="SET NULL"), nullable=True)
    device_name = Column(String(100))
    task_no = Column(String(50), unique=True, nullable=False)
    scheduled_date = Column(DateTime, nullable=False, index=True)
    actual_date = Column(DateTime)
    status = Column(String(20), default="pending", index=True)  # pending, in_progress, completed, skipped, overdue
    maintenance_id = Column(Integer, ForeignKey("maintenance_records.id"), nullable=True)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    plan = relationship("MaintenancePlan", back_populates="tasks")
    maintenance = relationship("MaintenanceRecord")

    def __repr__(self):
        return f"<MaintenanceTask(task_no='{self.task_no}', status='{self.status}')>"
