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
    device_type = Column(String(50), default="switch", index=True)  # uce, office_switch, ap, wlc, core_switch, server_switch, router, pa, ftd, other
    purchase_date = Column(DateTime)
    vendor = Column(String(200))
    purchase_cost = Column(DECIMAL(10, 2), default=0)
    photo_dir = Column(String(500))
    credential_group = Column(String(50), default="default")
    last_backup_time = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ===== 企业级智能运维扩展字段 =====
    # 模块序列号（JSON格式存储多个模块）
    modules = Column(Text)  # JSON: [{"type": "main", "serial_number": "SN001"}, {"type": "power", "serial_number": "SN002"}]
    # 健康评分
    health_score = Column(Integer, default=100)  # 0-100 健康评分
    risk_level = Column(String(20), default="low", index=True)  # low/medium/high/critical
    last_health_check = Column(DateTime)  # 最后健康检查时间
    # 生命周期
    uptime_days = Column(Integer, default=0)  # 运行天数
    warranty_expire = Column(DateTime)  # 保修到期时间
    lifecycle_stage = Column(String(20), default="new", index=True)  # new/active/aging/retired
    # AI分析
    ai_last_analyzed = Column(DateTime)  # AI最后分析时间

    # 关系
    backups = relationship("BackupRecord", back_populates="device", cascade="all, delete-orphan")
    faults = relationship("FaultRecord", back_populates="device", cascade="all, delete-orphan")
    maintenances = relationship("MaintenanceRecord", back_populates="device", cascade="all, delete-orphan")
    photos = relationship("DevicePhoto", back_populates="device", cascade="all, delete-orphan")
    nodes = relationship("DeviceNode", back_populates="device", cascade="all, delete-orphan")
    health_records = relationship("DeviceHealthScore", back_populates="device", cascade="all, delete-orphan")
    spare_relations = relationship("DeviceSpareRelation", back_populates="device", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Device(name='{self.name}', ip='{self.ip}', status='{self.status}', health={self.health_score})>"

    def get_modules_list(self):
        """解析模块序列号JSON"""
        if self.modules:
            try:
                import json
                return json.loads(self.modules)
            except:
                return []
        return []

    def set_modules_list(self, modules_list):
        """设置模块序列号JSON"""
        if modules_list:
            import json
            self.modules = json.dumps(modules_list)
        else:
            self.modules = None


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
    status = Column(String(20), default="open", index=True)  # open, assigned, accepted, diagnosing, resolving, transferred, resolved, closed
    maintenance_id = Column(Integer, ForeignKey("maintenance_records.id"), nullable=True)  # 关联的维修单
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    device_name = Column(String(100))

    # ===== 流程管理字段 =====
    assigned_to = Column(String(100), index=True)  # 指派负责人
    assigned_at = Column(DateTime)  # 指派时间
    accepted_at = Column(DateTime)  # 接收确认时间
    diagnosing_at = Column(DateTime)  # 开始诊断时间
    transferred_at = Column(DateTime)  # 转维修时间
    resolved_at = Column(DateTime)  # 解决时间
    closed_at = Column(DateTime)  # 关闭时间

    # ===== 诊断信息 =====
    fault_type = Column(String(20))  # 故障类型：hardware/software/config/network/other
    diagnosis_text = Column(Text)  # 诊断内容
    diagnosis_result = Column(String(50))  # 诊断结论：config_issue/need_replace/need_upgrade/field_check

    # ===== AI分析增强字段 =====
    ai_analysis_result = Column(Text)  # JSON格式AI分析结果
    ai_root_cause = Column(Text)  # AI分析根因
    ai_recommendation = Column(String(50))  # AI建议：repair/watch/ignore
    ai_confidence = Column(DECIMAL(3, 2))  # AI置信度 0.00-1.00
    incident_type = Column(String(20))  # 故障类型：hardware/software/config/network
    auto_created_maintenance = Column(Boolean, default=False)  # 是否自动创建了维修单

    # 关系
    device = relationship("Device", back_populates="faults")
    maintenance = relationship("MaintenanceRecord", foreign_keys=[maintenance_id])

    def __repr__(self):
        return f"<FaultRecord(fault_no='{self.fault_no}', device='{self.device_name}')>"

    def get_ai_analysis_dict(self):
        """解析AI分析结果JSON"""
        if self.ai_analysis_result:
            try:
                import json
                return json.loads(self.ai_analysis_result)
            except:
                return {}
        return {}


class MaintenanceRecord(Base):
    """维修记录表"""
    __tablename__ = "maintenance_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"), index=True)
    maint_no = Column(String(50), unique=True, nullable=False)
    maint_type = Column(String(20), index=True)  # preventive, corrective, upgrade, emergency
    maint_time = Column(DateTime, index=True)
    title = Column(String(200))  # 维修单标题
    problem_description = Column(Text)  # 问题描述
    solution = Column(Text)  # 解决方案/维修过程
    technician = Column(String(100))  # 维修人员
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
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    device_name = Column(String(100))

    # ===== 自动化/AI增强字段 =====
    auto_created = Column(Boolean, default=False)  # 是否由工作流自动创建
    ai_recommended = Column(Boolean, default=False)  # 是否由AI推荐创建

    # ===== 状态流转系统字段 =====
    # 维修状态
    status = Column(String(20), default="created", index=True)  # created, diagnosing, repairing, verifying, completed, cancelled
    # 状态时间戳
    diagnosing_at = Column(DateTime)
    repairing_at = Column(DateTime)
    verifying_at = Column(DateTime)
    completed_at = Column(DateTime)
    cancelled_at = Column(DateTime)
    # 流程信息
    current_owner = Column(String(100))  # 当前负责人
    priority = Column(String(10), default="P3", index=True)  # P1/P2/P3/P4 优先级
    sla_deadline = Column(DateTime)  # SLA截止时间

    # ===== 半自动状态机字段 =====
    # 诊断信息
    diagnosis_text = Column(Text)  # 诊断描述内容
    diagnosis_result = Column(String(50))  # 诊断结论: fault_found, no_fault, need_replace, need_upgrade

    # 维修动作 (JSON数组)
    repair_actions = Column(Text)  # [{"action": "更换SFP模块", "parts": "SFP-001", "operator": "Vayne", "time": "..."}]

    # 验证信息
    verification_result = Column(String(20))  # passed, failed, partial
    verification_notes = Column(Text)  # 验证备注
    verify_passed = Column(Boolean, default=False)  # 是否通过验证

    # 关系
    device = relationship("Device", back_populates="maintenances")
    fault = relationship("FaultRecord", foreign_keys=[fault_id])
    events = relationship("MaintenanceEvent", back_populates="maintenance", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<MaintenanceRecord(maint_no='{self.maint_no}', status='{self.status}')>"

    def get_progress_percent(self):
        """计算进度百分比"""
        status_percent = {
            'created': 20,
            'diagnosing': 40,
            'repairing': 60,
            'verifying': 80,
            'completed': 100,
            'cancelled': 0
        }
        return status_percent.get(self.status, 20)


class MaintenanceEvent(Base):
    """维修事件时间线表 - 记录维修过程中的每个事件"""
    __tablename__ = "maintenance_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    maintenance_id = Column(Integer, ForeignKey("maintenance_records.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(20), nullable=False)  # created, diagnosing, repairing, verifying, completed, cancelled
    event_time = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    operator = Column(String(100))  # 操作人
    notes = Column(String(500))  # 事件备注
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    maintenance = relationship("MaintenanceRecord", back_populates="events")

    def __repr__(self):
        return f"<MaintenanceEvent(maint_id={self.maintenance_id}, type={self.event_type})>"


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


class SparePartMovement(Base):
    """备件出入库记录表"""
    __tablename__ = "spare_part_movements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    part_id = Column(Integer, ForeignKey("spare_parts.id", ondelete="CASCADE"), nullable=False, index=True)
    movement_type = Column(String(10), nullable=False)  # in / out / scrap_in / scrap_out
    quantity = Column(Integer, nullable=False)
    serial_number = Column(String(100), nullable=True)  # 序列号（扫码出库时记录）
    po_number = Column(String(100), nullable=True)  # PO号（关联采购订单）
    session_code = Column(String(20), nullable=True, index=True)  # 扫码会话码（关联同批次出库）
    reason = Column(String(500), nullable=True)  # 出入库原因
    operator = Column(String(100), nullable=True)  # 操作人
    reference = Column(String(200), nullable=True)  # 关联设备/工单等
    target_device_id = Column(Integer, ForeignKey("devices.id", ondelete="SET NULL"), nullable=True)  # 出库目标设备
    source_device_id = Column(Integer, ForeignKey("devices.id", ondelete="SET NULL"), nullable=True)  # 返回件来源设备
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    part = relationship("SparePart", back_populates="movements")
    target_device = relationship("Device", foreign_keys=[target_device_id])
    source_device = relationship("Device", foreign_keys=[source_device_id])

    def __repr__(self):
        return f"<SparePartMovement(part_id={self.part_id}, type={self.movement_type}, qty={self.quantity}, sn={self.serial_number})>"


class SparePartInstance(Base):
    """备件实例表 - 存储每个备件个体的序列号、PO号等信息"""
    __tablename__ = "spare_part_instances"

    id = Column(Integer, primary_key=True, autoincrement=True)
    part_id = Column(Integer, ForeignKey("spare_parts.id", ondelete="CASCADE"), nullable=False, index=True)
    serial_number = Column(String(100), unique=True, nullable=False, index=True)  # 序列号（唯一）
    po_number = Column(String(100), nullable=True, index=True)  # 采购订单号
    unit_price = Column(DECIMAL(10, 2), default=0)  # 该实例的采购价格（入库时可填写）
    status = Column(String(20), default="in_stock", index=True)  # in_stock(库存) / inuse(在设备上) / pending_scrap(待报废) / scrapped(已报废)
    location = Column(String(200), nullable=True)  # 存放位置
    in_stock_at = Column(DateTime, nullable=True)  # 入库时间
    out_at = Column(DateTime, nullable=True)  # 出库时间
    # 设备安装相关字段
    installed_device_id = Column(Integer, ForeignKey("devices.id", ondelete="SET NULL"), nullable=True)  # 当前安装设备
    installed_at = Column(DateTime, nullable=True)  # 安装时间
    installed_by = Column(String(100), nullable=True)  # 安装操作人
    removed_from_device_id = Column(Integer, ForeignKey("devices.id", ondelete="SET NULL"), nullable=True)  # 拆卸来源设备
    removed_at = Column(DateTime, nullable=True)  # 拆卸时间
    # 维修/任务关联字段（保留原有）
    out_to_maintenance = Column(Integer, ForeignKey("maintenance_records.id", ondelete="SET NULL"), nullable=True)  # 出库到维修单
    out_to_task = Column(Integer, ForeignKey("maintenance_tasks.id", ondelete="SET NULL"), nullable=True)  # 出库到运维任务
    notes = Column(String(500), nullable=True)  # 备注
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    part = relationship("SparePart", back_populates="instances")
    installed_device = relationship("Device", foreign_keys=[installed_device_id])
    removed_from_device = relationship("Device", foreign_keys=[removed_from_device_id])

    def __repr__(self):
        return f"<SparePartInstance(serial={self.serial_number}, status={self.status})>"


class SparePart(Base):
    """备件资产表 - 存储备件型号基础信息"""
    __tablename__ = "spare_parts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, index=True)
    part_number = Column(String(100), unique=True, nullable=False, index=True)  # 型号（唯一）
    category = Column(String(100), nullable=True, index=True)  # 模块/电源/线缆/其他
    manufacturer = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    quantity_in_stock = Column(Integer, default=0, nullable=False)
    min_quantity = Column(Integer, default=0)  # 最低库存预警值
    unit_price = Column(DECIMAL(10, 2), default=0)
    location = Column(String(200), nullable=True)  # 默认存放位置
    status = Column(String(20), default="active")  # active, inactive, depleted
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 一对多关系
    movements = relationship("SparePartMovement", back_populates="part", cascade="all, delete-orphan")
    instances = relationship("SparePartInstance", back_populates="part", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<SparePart(name='{self.name}', qty={self.quantity_in_stock})>"


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


# =============================================================================
# 系统监控大屏模型
# =============================================================================

class FloorPlan(Base):
    """平面图表 - 存储工厂平面图图片"""
    __tablename__ = "floor_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)  # 平面图名称，如"一楼车间"
    image_path = Column(String(500), nullable=False)  # 图片存储路径
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    nodes = relationship("DeviceNode", back_populates="floor_plan", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<FloorPlan(name='{self.name}', id={self.id})>"


class DeviceNode(Base):
    """设备节点表 - 存储设备在平面图上的位置"""
    __tablename__ = "device_nodes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    floor_plan_id = Column(Integer, ForeignKey("floor_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    x_percent = Column(DECIMAL(5, 2), nullable=False)  # X坐标百分比 (0-100)
    y_percent = Column(DECIMAL(5, 2), nullable=False)  # Y坐标百分比 (0-100)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    device = relationship("Device", back_populates="nodes")
    floor_plan = relationship("FloorPlan", back_populates="nodes")

    def __repr__(self):
        return f"<DeviceNode(device_id={self.device_id}, x={self.x_percent}, y={self.y_percent})>"


# =============================================================================
# 企业级智能运维扩展模型
# =============================================================================

class DeviceHealthScore(Base):
    """设备健康评分表 - 记录设备健康评分历史"""
    __tablename__ = "device_health_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    health_score = Column(Integer, nullable=False)  # 0-100
    score_factors = Column(Text)  # JSON格式评分因素 {"fault_freq": 30, "repair_freq": 20, ...}
    risk_level = Column(String(20), nullable=False, index=True)  # low/medium/high/critical
    trend = Column(String(20), default="stable")  # improving/stable/declining
    ai_analysis_text = Column(Text)  # AI分析结果
    recommendations = Column(Text)  # JSON格式建议列表
    last_calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    device = relationship("Device", back_populates="health_records")

    def __repr__(self):
        return f"<DeviceHealthScore(device_id={self.device_id}, score={self.health_score}, risk={self.risk_level})>"

    def get_score_factors_dict(self):
        """解析评分因素JSON"""
        if self.score_factors:
            try:
                import json
                return json.loads(self.score_factors)
            except:
                return {}
        return {}

    def get_recommendations_list(self):
        """解析建议列表JSON"""
        if self.recommendations:
            try:
                import json
                return json.loads(self.recommendations)
            except:
                return []
        return []


class AIAnalysisRecord(Base):
    """AI分析记录表 - 记录所有AI分析调用"""
    __tablename__ = "ai_analysis_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_type = Column(String(50), nullable=False, index=True)  # fault/root_cause/health/pm_recommend/summary
    target_type = Column(String(50), nullable=False, index=True)  # device/fault/maintenance
    target_id = Column(Integer, nullable=False, index=True)
    input_data = Column(Text)  # JSON格式输入数据
    ai_provider = Column(String(50))  # deepseek/claude/qwen/openai
    model_name = Column(String(100))  # 模型名称
    output_result = Column(Text)  # JSON格式输出结果
    confidence_score = Column(DECIMAL(3, 2))  # 0.00-1.00 置信度
    processing_time_ms = Column(Integer)  # 处理耗时毫秒
    tokens_used = Column(Integer)  # Token使用量
    cost = Column(DECIMAL(10, 4))  # 成本（元）
    status = Column(String(20), default="completed")  # pending/completed/failed
    error_message = Column(Text)  # 错误信息
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<AIAnalysisRecord(type={self.analysis_type}, target={self.target_type}:{self.target_id})>"

    def get_input_dict(self):
        """解析输入数据JSON"""
        if self.input_data:
            try:
                import json
                return json.loads(self.input_data)
            except:
                return {}
        return {}

    def get_output_dict(self):
        """解析输出结果JSON"""
        if self.output_result:
            try:
                import json
                return json.loads(self.output_result)
            except:
                return {}
        return {}


class WorkflowRule(Base):
    """自动化工作流规则表"""
    __tablename__ = "workflow_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500))
    trigger_type = Column(String(50), nullable=False, index=True)  # fault_created/device_health_low/maintenance_completed
    trigger_conditions = Column(Text)  # JSON格式触发条件 {"health_score": {"<": 60}}
    action_type = Column(String(50), nullable=False)  # create_maintenance/create_pm_task/send_alert/update_health
    action_config = Column(Text)  # JSON格式动作配置
    is_active = Column(Boolean, default=True, index=True)
    priority = Column(Integer, default=100)  # 规则优先级，数字越小优先级越高
    execution_count = Column(Integer, default=0)  # 执行次数统计
    last_triggered_at = Column(DateTime)  # 最后触发时间
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<WorkflowRule(name='{self.name}', trigger={self.trigger_type}, active={self.is_active})>"

    def get_trigger_conditions_dict(self):
        """解析触发条件JSON"""
        if self.trigger_conditions:
            try:
                import json
                return json.loads(self.trigger_conditions)
            except:
                return {}
        return {}

    def get_action_config_dict(self):
        """解析动作配置JSON"""
        if self.action_config:
            try:
                import json
                return json.loads(self.action_config)
            except:
                return {}
        return {}


class DeviceSpareRelation(Base):
    """设备-备件关系表 - 记录设备上安装的备件"""
    __tablename__ = "device_spare_relations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    spare_instance_id = Column(Integer, ForeignKey("spare_part_instances.id", ondelete="SET NULL"), nullable=True, index=True)
    part_number = Column(String(100))  # 备件型号（冗余，方便查询）
    part_name = Column(String(200))  # 备件名称（冗余）
    serial_number = Column(String(100))  # 序列号
    position = Column(String(100))  # 安装位置描述
    installed_at = Column(DateTime, nullable=False)  # 安装时间
    installed_by = Column(String(100))  # 安装操作人
    status = Column(String(20), default="active", index=True)  # active/removed/failed
    removed_at = Column(DateTime)  # 移除时间
    removed_by = Column(String(100))  # 移除操作人
    removal_reason = Column(String(200))  # 移除原因
    maintenance_id = Column(Integer, ForeignKey("maintenance_records.id"), nullable=True)  # 关联维修单
    notes = Column(String(500))  # 备注
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    device = relationship("Device", back_populates="spare_relations")
    spare_instance = relationship("SparePartInstance")
    maintenance = relationship("MaintenanceRecord")

    def __repr__(self):
        return f"<DeviceSpareRelation(device={self.device_id}, part={self.part_number}, status={self.status})>"


class Notification(Base):
    """系统通知表"""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user = Column(String(100), nullable=False, index=True)  # 接收用户
    type = Column(String(50), nullable=False, index=True)  # fault_assigned/maintenance_created/etc
    title = Column(String(200), nullable=False)
    content = Column(Text)
    reference_type = Column(String(50))  # fault/maintenance/device
    reference_id = Column(Integer)  # 关联记录ID
    read = Column(Boolean, default=False, index=True)
    read_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<Notification(user='{self.user}', type='{self.type}')>"


class DeployHistory(Base):
    """部署历史主表 - 记录每次部署/回滚/重新部署操作"""
    __tablename__ = "deploy_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    username = Column(String(100), nullable=True)  # 操作用户名（冗余，方便显示）
    operation_type = Column(String(20), nullable=False, index=True)  # deploy/rollback/redeploy
    engine = Column(String(20), nullable=False)  # napalm/netmiko
    mode = Column(String(20))  # merge/replace/snippet/template/backup
    target_devices = Column(Text)  # JSON: [{id, name, ip}]
    success = Column(Boolean, nullable=False)  # 整体是否成功
    total_devices = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    parent_id = Column(Integer, ForeignKey("deploy_history.id", ondelete="SET NULL"), nullable=True)  # 关联父记录
    deploy_config = Column(Text)  # JSON: 部署配置（用于重新部署）
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # 关系
    device_results = relationship("DeployDeviceResult", back_populates="deploy_history", cascade="all, delete-orphan")
    children = relationship("DeployHistory", backref="parent", remote_side=[id])

    def __repr__(self):
        return f"<DeployHistory(id={self.id}, type={self.operation_type}, user={self.username})>"

    def get_target_devices_list(self):
        """解析目标设备JSON"""
        if self.target_devices:
            try:
                import json
                return json.loads(self.target_devices)
            except:
                return []
        return []

    def get_deploy_config_dict(self):
        """解析部署配置JSON"""
        if self.deploy_config:
            try:
                import json
                return json.loads(self.deploy_config)
            except:
                return {}
        return {}


class DeployDeviceResult(Base):
    """部署设备执行结果表 - 记录每个设备的部署结果"""
    __tablename__ = "deploy_device_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    deploy_id = Column(Integer, ForeignKey("deploy_history.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(Integer, nullable=False, index=True)
    device_name = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False)  # completed/failed/skipped
    rollback_available = Column(Boolean, default=False)
    rollback_status = Column(String(20), default="pending")  # pending/rolled_back
    cli_output = Column(Text)  # CLI 输出内容
    diff_output = Column(Text)  # 配置差异
    error_message = Column(Text)  # 错误信息
    execution_time_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    deploy_history = relationship("DeployHistory", back_populates="device_results")

    def __repr__(self):
        return f"<DeployDeviceResult(deploy_id={self.deploy_id}, device={self.device_name}, status={self.status})>"
