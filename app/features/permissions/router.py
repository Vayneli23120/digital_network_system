"""
权限管理 API - RBAC 权限系统

提供权限和角色的 CRUD 操作，以及权限检查接口
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel, Field
from datetime import datetime
from loguru import logger

from app.shared.database import get_db
from app.shared.models import Role, Permission, User
from app.shared.dependencies import (
    check_user_permission, check_user_permissions, get_user_all_permissions,
    require_permission, require_superuser
)
from app.features.auth.router import get_current_user_from_token
from app.features.auth.identity import Principal, get_current_principal
from app.features.permissions.security import (
    ensure_user_manageable,
    resolve_assignable_roles,
)

router = APIRouter(prefix="/api/permissions", tags=["permissions"])
require_role_write = require_permission("role:write")
require_role_delete = require_permission("role:delete")
require_user_write = require_permission("user:write")


# =============================================================================
# 扩展权限定义 - 覆盖所有模块
# =============================================================================

EXTENDED_PERMISSIONS = [
    # 设备管理
    {"name": "device:read", "resource": "device", "action": "read", "description": "查看设备"},
    {"name": "device:write", "resource": "device", "action": "write", "description": "创建/编辑设备"},
    {"name": "device:delete", "resource": "device", "action": "delete", "description": "删除设备"},
    {"name": "device:import", "resource": "device", "action": "import", "description": "导入设备"},
    {"name": "device:export", "resource": "device", "action": "export", "description": "导出设备"},
    {"name": "device:photo", "resource": "device", "action": "photo", "description": "管理设备照片"},

    # 备份管理
    {"name": "backup:read", "resource": "backup", "action": "read", "description": "查看备份"},
    {"name": "backup:execute", "resource": "backup", "action": "execute", "description": "执行备份"},
    {"name": "backup:batch", "resource": "backup", "action": "batch", "description": "批量备份"},
    {"name": "backup:delete", "resource": "backup", "action": "delete", "description": "删除备份"},

    # 配置部署
    {"name": "config:read", "resource": "config", "action": "read", "description": "查看配置"},
    {"name": "config:deploy", "resource": "config", "action": "deploy", "description": "部署配置"},
    {"name": "config:rollback", "resource": "config", "action": "rollback", "description": "回滚配置"},
    {"name": "deploy_history:delete", "resource": "deploy_history", "action": "delete", "description": "删除部署历史"},

    # 故障管理
    {"name": "fault:read", "resource": "fault", "action": "read", "description": "查看故障"},
    {"name": "fault:write", "resource": "fault", "action": "write", "description": "创建/编辑故障"},
    {"name": "fault:delete", "resource": "fault", "action": "delete", "description": "删除故障"},
    {"name": "fault:analyze", "resource": "fault", "action": "analyze", "description": "AI分析故障"},

    # 维修管理
    {"name": "maintenance:read", "resource": "maintenance", "action": "read", "description": "查看维修"},
    {"name": "maintenance:write", "resource": "maintenance", "action": "write", "description": "创建/编辑维修"},
    {"name": "maintenance:delete", "resource": "maintenance", "action": "delete", "description": "删除维修"},
    {"name": "maintenance:transition", "resource": "maintenance", "action": "transition", "description": "维修状态流转"},

    # 备件管理
    {"name": "spare_part:read", "resource": "spare_part", "action": "read", "description": "查看备件"},
    {"name": "spare_part:write", "resource": "spare_part", "action": "write", "description": "创建/编辑备件"},
    {"name": "spare_part:delete", "resource": "spare_part", "action": "delete", "description": "删除备件"},
    {"name": "spare_movement:read", "resource": "spare_movement", "action": "read", "description": "查看备件出入库"},
    {"name": "spare_movement:write", "resource": "spare_movement", "action": "write", "description": "备件出入库"},

    # 配置模板
    {"name": "template:read", "resource": "template", "action": "read", "description": "查看模板"},
    {"name": "template:write", "resource": "template", "action": "write", "description": "创建/编辑模板"},
    {"name": "template:delete", "resource": "template", "action": "delete", "description": "删除模板"},
    {"name": "template:render", "resource": "template", "action": "render", "description": "渲染模板"},

    # 凭证管理
    {"name": "credential:read", "resource": "credential", "action": "read", "description": "查看凭证"},
    {"name": "credential:write", "resource": "credential", "action": "write", "description": "创建/编辑凭证"},
    {"name": "credential:delete", "resource": "credential", "action": "delete", "description": "删除凭证"},

    # 工作流
    {"name": "workflow:read", "resource": "workflow", "action": "read", "description": "查看工作流"},
    {"name": "workflow:write", "resource": "workflow", "action": "write", "description": "创建/编辑工作流"},
    {"name": "workflow:delete", "resource": "workflow", "action": "delete", "description": "删除工作流"},
    {"name": "workflow:trigger", "resource": "workflow", "action": "trigger", "description": "触发工作流"},

    # 计划性运维
    {"name": "planned_task:read", "resource": "planned_task", "action": "read", "description": "查看计划任务"},
    {"name": "planned_task:write", "resource": "planned_task", "action": "write", "description": "创建/编辑计划任务"},
    {"name": "planned_task:delete", "resource": "planned_task", "action": "delete", "description": "删除计划任务"},
    {"name": "planned_task:execute", "resource": "planned_task", "action": "execute", "description": "执行计划任务"},

    # 监控大屏
    {"name": "floor_plan:read", "resource": "floor_plan", "action": "read", "description": "查看平面图"},
    {"name": "floor_plan:write", "resource": "floor_plan", "action": "write", "description": "创建/编辑平面图"},
    {"name": "floor_plan:delete", "resource": "floor_plan", "action": "delete", "description": "删除平面图"},

    # 日志
    {"name": "log:read", "resource": "log", "action": "read", "description": "查看日志"},
    {"name": "log:clear", "resource": "log", "action": "clear", "description": "清理日志"},
    {"name": "tool_log:read", "resource": "tool_log", "action": "read", "description": "查看工具日志"},
    {"name": "tool_log:clear", "resource": "tool_log", "action": "clear", "description": "清理工具日志"},

    # 用户管理
    {"name": "user:read", "resource": "user", "action": "read", "description": "查看用户"},
    {"name": "user:write", "resource": "user", "action": "write", "description": "创建/编辑用户"},
    {"name": "user:delete", "resource": "user", "action": "delete", "description": "删除用户"},

    # 角色权限
    {"name": "role:read", "resource": "role", "action": "read", "description": "查看角色"},
    {"name": "role:write", "resource": "role", "action": "write", "description": "创建/编辑角色"},
    {"name": "role:delete", "resource": "role", "action": "delete", "description": "删除角色"},

    # 系统管理
    {"name": "admin:all", "resource": "admin", "action": "all", "description": "超级管理员权限"},
    {"name": "alert:manage", "resource": "alert", "action": "manage", "description": "管理告警设置"},
    {"name": "system_config:read", "resource": "system_config", "action": "read", "description": "查看系统配置"},
    {"name": "system_config:write", "resource": "system_config", "action": "write", "description": "修改系统配置"},
    {"name": "slo:read", "resource": "slo", "action": "read", "description": "查看 SLO 配置"},
    {"name": "slo:write", "resource": "slo", "action": "write", "description": "修改 SLO 配置"},
    {"name": "system_ops:read", "resource": "system_ops", "action": "read", "description": "查看系统诊断"},
    {"name": "system_ops:write", "resource": "system_ops", "action": "write", "description": "执行系统运维操作"},
    {"name": "compliance:check", "resource": "compliance", "action": "check", "description": "合规检查"},

    # AI 功能权限
    {"name": "ai:use", "resource": "ai", "action": "use", "description": "使用AI功能"},
    {"name": "ai:config", "resource": "ai", "action": "config", "description": "配置AI服务"},
    {"name": "ai:compliance", "resource": "ai", "action": "compliance", "description": "AI合规审核"},

    # 导航权限 - 运维监控 (overview)
    {"name": "nav_overview:dashboard", "resource": "nav_overview", "action": "dashboard", "description": "菜单：仪表板"},
    {"name": "nav_overview:operations", "resource": "nav_overview", "action": "operations", "description": "菜单：运维总览"},
    {"name": "nav_overview:monitor_3d", "resource": "nav_overview", "action": "monitor_3d", "description": "菜单：3D数字孪生"},
    {"name": "nav_overview:device_health", "resource": "nav_overview", "action": "device_health", "description": "菜单：设备健康评分"},
    {"name": "nav_overview:ai_analysis", "resource": "nav_overview", "action": "ai_analysis", "description": "菜单：AI分析中心"},
    {"name": "nav_overview:workflows", "resource": "nav_overview", "action": "workflows", "description": "菜单：自动化工作流"},

    # 导航权限 - 设备管理 (devices)
    {"name": "nav_devices:list", "resource": "nav_devices", "action": "list", "description": "菜单：设备管理"},
    {"name": "nav_devices:discovery", "resource": "nav_devices", "action": "discovery", "description": "菜单：设备发现"},
    {"name": "nav_devices:backups", "resource": "nav_devices", "action": "backups", "description": "菜单：备份管理"},
    {"name": "nav_devices:faults", "resource": "nav_devices", "action": "faults", "description": "菜单：故障管理"},
    {"name": "nav_devices:maintenance", "resource": "nav_devices", "action": "maintenance", "description": "菜单：维修管理"},
    {"name": "nav_devices:planned_maintenance", "resource": "nav_devices", "action": "planned_maintenance", "description": "菜单：计划性运维"},

    # 导航权限 - 配置管理 (config)
    {"name": "nav_config:console", "resource": "nav_config", "action": "console", "description": "菜单：Console配置"},
    {"name": "nav_config:deploy", "resource": "nav_config", "action": "deploy", "description": "菜单：配置部署"},
    {"name": "nav_config:templates", "resource": "nav_config", "action": "templates", "description": "菜单：配置模板"},
    {"name": "nav_config:credentials", "resource": "nav_config", "action": "credentials", "description": "菜单：SSH凭证"},
    {"name": "nav_config:compliance", "resource": "nav_config", "action": "compliance", "description": "菜单：配置合规"},
    {"name": "nav_config:tool_logs", "resource": "nav_config", "action": "tool_logs", "description": "菜单：工具日志"},

    # 导航权限 - 备件管理 (spare)
    {"name": "nav_spare:spare_parts", "resource": "nav_spare", "action": "spare_parts", "description": "菜单：备件管理"},
    {"name": "nav_spare:movements", "resource": "nav_spare", "action": "movements", "description": "菜单：出入库历史"},
    {"name": "nav_spare:scrap_inventory", "resource": "nav_spare", "action": "scrap_inventory", "description": "菜单：报废库存"},

    # 导航权限 - 系统设置 (system)
    {"name": "nav_system:notifications", "resource": "nav_system", "action": "notifications", "description": "菜单：通知中心"},
    {"name": "nav_system:logs", "resource": "nav_system", "action": "logs", "description": "菜单：系统日志"},
    {"name": "nav_system:alert_settings", "resource": "nav_system", "action": "alert_settings", "description": "菜单：告警通知"},
    {"name": "nav_system:system_settings", "resource": "nav_system", "action": "system_settings", "description": "菜单：系统设置"},
    {"name": "nav_system:system_help", "resource": "nav_system", "action": "system_help", "description": "菜单：系统帮助"},
    {"name": "nav_system:users", "resource": "nav_system", "action": "users", "description": "菜单：用户管理"},
    {"name": "nav_system:permissions", "resource": "nav_system", "action": "permissions", "description": "菜单：角色权限"},
]


# =============================================================================
# 导航权限分组常量
# 与前端 Layout.vue 的菜单结构一一对应，供预置角色复用，避免逐个角色手抄字符串
# =============================================================================

NAV_OVERVIEW = [
    "nav_overview:dashboard", "nav_overview:operations", "nav_overview:monitor_3d",
    "nav_overview:device_health", "nav_overview:ai_analysis", "nav_overview:workflows",
]
NAV_DEVICES = [
    "nav_devices:list", "nav_devices:discovery", "nav_devices:backups",
    "nav_devices:faults", "nav_devices:maintenance", "nav_devices:planned_maintenance",
]
NAV_CONFIG = [
    "nav_config:console", "nav_config:deploy", "nav_config:templates",
    "nav_config:credentials", "nav_config:compliance", "nav_config:tool_logs",
]
NAV_SPARE = [
    "nav_spare:spare_parts", "nav_spare:movements", "nav_spare:scrap_inventory",
]
# 所有角色都应该能看到的系统菜单（只读性质）
NAV_SYSTEM_COMMON = [
    "nav_system:notifications", "nav_system:logs", "nav_system:system_help",
]
# 非管理员可管理的告警设置菜单；通用系统配置只由 admin:all 默认放行。
NAV_SYSTEM_SETTINGS = [
    "nav_system:alert_settings",
]
# 账号与权限治理菜单（nav_system:users / nav_system:permissions）只授予 admin，
# admin 通过 admin:all 绕过导航过滤，因此不需要在预置角色里显式列出

# 导航权限的显示名，按「完整权限名」索引。
# 不能复用 action_labels：nav 的 action 是页面名（deploy / compliance / logs ...），
# 与功能权限的 action 命名空间重叠，同一张表里会互相覆盖
NAV_LABELS = {
    "nav_overview:dashboard": "仪表板",
    "nav_overview:operations": "运维总览",
    "nav_overview:monitor_3d": "3D数字孪生",
    "nav_overview:device_health": "设备健康评分",
    "nav_overview:ai_analysis": "AI分析中心",
    "nav_overview:workflows": "自动化工作流",
    "nav_devices:list": "设备管理",
    "nav_devices:discovery": "设备发现",
    "nav_devices:backups": "备份管理",
    "nav_devices:faults": "故障管理",
    "nav_devices:maintenance": "维修管理",
    "nav_devices:planned_maintenance": "计划性运维",
    "nav_config:console": "Console配置",
    "nav_config:deploy": "配置部署",
    "nav_config:templates": "配置模板",
    "nav_config:credentials": "SSH凭证",
    "nav_config:compliance": "配置合规",
    "nav_config:tool_logs": "工具日志",
    "nav_spare:spare_parts": "备件管理",
    "nav_spare:movements": "出入库历史",
    "nav_spare:scrap_inventory": "报废库存",
    "nav_system:notifications": "通知中心",
    "nav_system:logs": "系统日志",
    "nav_system:alert_settings": "告警通知",
    "nav_system:system_settings": "系统设置",
    "nav_system:system_help": "系统帮助",
    "nav_system:users": "用户管理",
    "nav_system:permissions": "角色权限",
}

# 导航权限按 tab 的展示顺序，与前端顶部标签顺序一致（前端排序用）
NAV_RESOURCE_ORDER = ["nav_overview", "nav_devices", "nav_config", "nav_spare", "nav_system"]


# 预定义角色
PRESET_ROLES = [
    {
        "name": "admin",
        "description": "系统管理员 - 拥有所有权限",
        "is_system": True,
        "permissions": ["admin:all"]
    },
    {
        "name": "operator",
        "description": "运维工程师 - 可执行运维操作",
        "is_system": True,
        "permissions": [
            "device:read", "device:write", "device:photo",
            "backup:read", "backup:execute", "backup:batch",
            "config:read", "config:deploy", "config:rollback",
            "fault:read", "fault:write", "fault:analyze",
            "maintenance:read", "maintenance:write", "maintenance:transition",
            "spare_part:read", "spare_part:write", "spare_movement:read", "spare_movement:write",
            "template:read", "template:write", "template:render",
            "workflow:read", "workflow:trigger",
            "planned_task:read", "planned_task:execute",
            "log:read", "tool_log:read",
            "ai:use", "ai:compliance",
            # 导航：除用户/角色管理外全部可见（operator 无 user:* / role:* 功能权限）
            *NAV_OVERVIEW, *NAV_DEVICES, *NAV_CONFIG, *NAV_SPARE,
            *NAV_SYSTEM_COMMON, *NAV_SYSTEM_SETTINGS,
        ]
    },
    {
        "name": "viewer",
        "description": "只读用户 - 仅查看权限",
        "is_system": True,
        "permissions": [
            "device:read", "backup:read", "config:read",
            "fault:read", "maintenance:read", "spare_part:read", "spare_movement:read",
            "template:read", "workflow:read", "planned_task:read",
            "log:read", "tool_log:read", "floor_plan:read",
            # 导航：只保留与只读功能权限对应的菜单
            # （不含设备发现/Console/部署/凭证等写操作入口，也不含用户与角色管理）
            "nav_overview:dashboard", "nav_overview:operations", "nav_overview:monitor_3d",
            "nav_overview:device_health", "nav_overview:workflows",
            "nav_devices:list", "nav_devices:backups", "nav_devices:faults",
            "nav_devices:maintenance", "nav_devices:planned_maintenance",
            "nav_config:templates", "nav_config:compliance", "nav_config:tool_logs",
            *NAV_SPARE,
            *NAV_SYSTEM_COMMON,
        ]
    },
    {
        "name": "device_manager",
        "description": "设备管理员 - 管理设备和备份",
        "is_system": False,
        "permissions": [
            "device:read", "device:write", "device:delete", "device:import", "device:export", "device:photo",
            "backup:read", "backup:execute", "backup:batch", "backup:delete",
            "config:read",
            # 导航：设备域全部 + 概览中与设备相关的页面
            "nav_overview:dashboard", "nav_overview:operations", "nav_overview:device_health",
            "nav_overview:monitor_3d",
            *NAV_DEVICES,
            *NAV_SYSTEM_COMMON,
        ]
    },
    {
        "name": "fault_handler",
        "description": "故障处理员 - 管理故障和维修",
        "is_system": False,
        "permissions": [
            "device:read", "backup:read", "config:read",
            "fault:read", "fault:write", "fault:delete", "fault:analyze",
            "maintenance:read", "maintenance:write", "maintenance:delete", "maintenance:transition",
            # 导航：故障与维修相关页面
            "nav_overview:dashboard", "nav_overview:operations", "nav_overview:device_health",
            "nav_devices:list", "nav_devices:backups", "nav_devices:faults",
            "nav_devices:maintenance", "nav_devices:planned_maintenance",
            *NAV_SYSTEM_COMMON,
        ]
    },
]


# =============================================================================
# Pydantic 模型
# =============================================================================

class PermissionResponse(BaseModel):
    """权限响应模型"""
    id: int
    name: str
    description: Optional[str]
    resource: str
    action: str
    created_at: datetime

    class Config:
        from_attributes = True


class PermissionCreate(BaseModel):
    """权限创建请求"""
    name: str = Field(..., min_length=3, max_length=100, description="权限标识")
    description: Optional[str] = Field(None, max_length=500, description="权限描述")
    resource: str = Field(..., min_length=1, max_length=50, description="资源类型")
    action: str = Field(..., min_length=1, max_length=50, description="操作类型")


class RoleResponse(BaseModel):
    """角色响应模型"""
    id: int
    name: str
    description: Optional[str]
    is_system: bool
    permissions: List[PermissionResponse] = []
    user_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RoleCreate(BaseModel):
    """角色创建请求"""
    name: str = Field(..., min_length=2, max_length=100, description="角色名称")
    description: Optional[str] = Field(None, max_length=500, description="角色描述")
    permission_ids: List[int] = Field(default=[], description="权限ID列表")


class RoleUpdate(BaseModel):
    """角色更新请求"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    permission_ids: Optional[List[int]] = Field(None, description="权限ID列表")


class UserRoleUpdate(BaseModel):
    """用户角色更新请求"""
    role_ids: List[int] = Field(..., description="角色ID列表")


class RoleUserResponse(BaseModel):
    """角色用户信息"""
    id: int
    username: str
    email: Optional[str]
    full_name: Optional[str]
    is_active: bool


class UserPermissionsResponse(BaseModel):
    """用户权限响应"""
    user_id: int
    username: str
    is_superuser: bool
    permissions: List[str]
    roles: List[dict]


# =============================================================================
# 初始化函数
# =============================================================================

def init_permissions_and_roles(db: Session, reset_system_roles: bool = False) -> dict:
    """
    初始化权限和角色数据

    幂等且默认非破坏性：
      - 权限：增量补齐缺失项，不删除已有权限
      - 角色：缺失的预置角色会被创建
      - 系统角色（is_system=True）：默认只补齐缺失的预置权限，**不会**删除管理员
        在界面上额外授予的权限。因为导航可见权限是允许管理员自定义的，
        旧实现的「与预置不一致就整体重建」会静默还原这些定制
      - 非系统角色：完全交由管理员维护，此函数不做任何权限调整

    Args:
        db: 数据库会话
        reset_system_roles: 显式要求把系统角色的权限强制重置为预置值
            （破坏性操作，会丢弃对 admin / operator / viewer 的自定义授权）

    Returns:
        初始化结果统计
    """
    result = {
        "permissions_created": 0,
        "roles_created": 0,
        "roles_updated": 0,
        "roles_reset": 0,
    }

    # ---------------- 权限：增量补齐 ----------------
    existing_names = {p.name for p in db.query(Permission).all()}

    if not existing_names:
        logger.info("权限表为空，初始化预定义权限...")

    for perm_data in EXTENDED_PERMISSIONS:
        if perm_data["name"] in existing_names:
            continue
        db.add(Permission(
            name=perm_data["name"],
            description=perm_data.get("description"),
            resource=perm_data["resource"],
            action=perm_data["action"]
        ))
        result["permissions_created"] += 1

    if result["permissions_created"] > 0:
        db.commit()
        logger.info(f"补齐 {result['permissions_created']} 个权限")

    # ---------------- 角色 ----------------
    perm_by_name = {p.name: p for p in db.query(Permission).all()}

    def resolve(perm_names) -> list:
        """把权限名解析成 Permission 对象，忽略清单里不存在的名字"""
        resolved = []
        for name in perm_names:
            perm = perm_by_name.get(name)
            if perm is None:
                logger.warning(f"预置角色引用了不存在的权限，已跳过: {name}")
                continue
            resolved.append(perm)
        return resolved

    for role_data in PRESET_ROLES:
        role = db.query(Role).filter(Role.name == role_data["name"]).first()
        expected = role_data.get("permissions", [])

        # 缺失的预置角色：直接创建
        if role is None:
            role = Role(
                name=role_data["name"],
                description=role_data.get("description"),
                is_system=role_data.get("is_system", False)
            )
            db.add(role)
            db.flush()
            role.permissions.extend(resolve(expected))
            result["roles_created"] += 1
            continue

        # 非系统角色由管理员自行维护，不做任何调整
        if not role_data.get("is_system"):
            continue

        current = {p.name for p in role.permissions}

        if reset_system_roles:
            # 破坏性：强制与预置定义一致
            if current != set(expected):
                role.permissions.clear()
                role.permissions.extend(resolve(expected))
                result["roles_reset"] += 1
            continue

        # 默认：只补齐缺失项，保留管理员的自定义授权
        missing = [name for name in expected if name not in current]
        if missing:
            role.permissions.extend(resolve(missing))
            result["roles_updated"] += 1
            logger.info(f"角色 {role.name} 补齐 {len(missing)} 个预置权限")

    if any(result[k] for k in ("roles_created", "roles_updated", "roles_reset")):
        db.commit()
        logger.info(
            "角色初始化完成: 新建 {created} / 补齐 {updated} / 重置 {reset}".format(
                created=result["roles_created"],
                updated=result["roles_updated"],
                reset=result["roles_reset"],
            )
        )

    return result


# =============================================================================
# 初始化端点
# =============================================================================

@router.post("/init")
async def init_permissions_system(
    reset_system_roles: bool = False,
    # 用 admin:all 而不是 require_superuser()：靠 admin 角色（admin:all）管理系统的
    # 管理员账号不一定把 is_superuser 置了位，require_superuser() 会把他们挡在外面，
    # 导致界面上的「初始化权限系统」按钮直接 403。
    # require_permission 内部已经放行 is_superuser，覆盖两种管理员
    _: None = Depends(require_permission("admin:all")),
    db: Session = Depends(get_db)
):
    """
    初始化权限系统（补齐权限清单与预置角色）

    幂等操作，可重复调用：
      - 补齐缺失的权限与缺失的预置角色
      - 系统角色只补齐缺失的预置权限，保留管理员的自定义授权
      - reset_system_roles=true 时才会把系统角色强制重置为预置值（破坏性）

    需要超级管理员权限（auth_enabled=false 时不做校验）
    """
    try:
        result = init_permissions_and_roles(db, reset_system_roles=reset_system_roles)
        return {
            "success": True,
            "message": "权限系统初始化完成",
            "result": result
        }
    except Exception as e:
        logger.error(f"初始化权限系统失败: {e}")
        raise HTTPException(status_code=500, detail=f"初始化失败: {str(e)}")


@router.get("/init-status")
async def get_init_status(db: Session = Depends(get_db)):
    """
    获取权限系统初始化状态

    无需权限
    """
    permissions_count = db.query(Permission).count()
    roles_count = db.query(Role).count()

    return {
        "initialized": permissions_count > 0 and roles_count > 0,
        "permissions_count": permissions_count,
        "roles_count": roles_count,
        "expected_permissions": len(EXTENDED_PERMISSIONS),
        "expected_roles": len(PRESET_ROLES)
    }


# =============================================================================
# 权限管理 API
# =============================================================================

@router.get("/permissions", response_model=List[PermissionResponse])
async def list_permissions(
    resource: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    获取权限列表
    """
    query = db.query(Permission)

    if resource:
        query = query.filter(Permission.resource == resource)

    permissions = query.offset(skip).limit(limit).all()
    return permissions


@router.post("/permissions", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
async def create_permission(
    permission_data: PermissionCreate,
    _: None = Depends(require_role_write),
    db: Session = Depends(get_db)
):
    """
    创建新权限
    """
    # 检查权限名是否已存在
    existing = db.query(Permission).filter(Permission.name == permission_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="权限名已存在")

    permission = Permission(
        name=permission_data.name,
        description=permission_data.description,
        resource=permission_data.resource,
        action=permission_data.action
    )
    db.add(permission)
    db.commit()
    db.refresh(permission)

    return permission


@router.get("/permissions/{permission_id}", response_model=PermissionResponse)
async def get_permission(
    permission_id: int,
    db: Session = Depends(get_db)
):
    """
    获取权限详情
    """
    permission = db.query(Permission).filter(Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(status_code=404, detail="权限不存在")

    return permission


@router.delete("/permissions/{permission_id}")
async def delete_permission(
    permission_id: int,
    _: None = Depends(require_role_delete),
    db: Session = Depends(get_db)
):
    """
    删除权限
    """
    permission = db.query(Permission).filter(Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(status_code=404, detail="权限不存在")

    db.delete(permission)
    db.commit()

    return {"success": True, "message": "权限删除成功"}


@router.get("/resources")
async def list_resource_types(db: Session = Depends(get_db)):
    """
    获取所有资源类型列表

    无需权限 - 供前端展示
    """
    resources = db.query(Permission.resource).distinct().all()
    resource_names = [r[0] for r in resources]

    # 资源中文名称映射
    resource_labels = {
        "device": "设备管理",
        "backup": "备份管理",
        "config": "配置管理",
        "deploy_history": "部署历史",
        "fault": "故障管理",
        "maintenance": "维修管理",
        "spare_part": "备件管理",
        "spare_movement": "备件流转",
        "template": "配置模板",
        "credential": "凭证管理",
        "workflow": "工作流",
        "planned_task": "计划任务",
        "floor_plan": "监控大屏",
        "log": "系统日志",
        "tool_log": "工具日志",
        "user": "用户管理",
        "role": "角色权限",
        "admin": "系统管理",
        "alert": "告警设置",
        "system_config": "系统配置",
        "slo": "SLO 配置",
        "system_ops": "系统运维",
        "compliance": "合规检查",
        "ai": "AI功能",
    }

    return {
        "resources": [
            {"name": r, "label": resource_labels.get(r, r)}
            for r in sorted(resource_names)
        ]
    }


# =============================================================================
# 角色管理 API
# =============================================================================

@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(
    include_system: bool = True,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    获取角色列表

    无需权限 - 供用户分配角色时选择
    """
    query = db.query(Role).options(joinedload(Role.permissions))

    if not include_system:
        query = query.filter(Role.is_system == False)

    roles = query.offset(skip).limit(limit).all()

    # 计算每个角色的用户数量
    result = []
    for role in roles:
        user_count = db.query(User).filter(User.roles.any(Role.id == role.id)).count()
        result.append({
            "id": role.id,
            "name": role.name,
            "description": role.description,
            "is_system": role.is_system,
            "permissions": role.permissions,
            "user_count": user_count,
            "created_at": role.created_at,
            "updated_at": role.updated_at
        })

    return result


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_data: RoleCreate,
    _: None = Depends(require_role_write),
    db: Session = Depends(get_db)
):
    """
    创建新角色

    注意：此接口不需要特定权限检查，因为只有在系统设置中才能访问
    """
    # 检查角色名是否已存在
    existing = db.query(Role).filter(Role.name == role_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="角色名已存在")

    role = Role(
        name=role_data.name,
        description=role_data.description,
        is_system=False
    )

    # 关联权限
    if role_data.permission_ids:
        permissions = db.query(Permission).filter(Permission.id.in_(role_data.permission_ids)).all()
        role.permissions = permissions

    db.add(role)
    db.commit()
    db.refresh(role)

    return {
        "id": role.id,
        "name": role.name,
        "description": role.description,
        "is_system": role.is_system,
        "permissions": role.permissions,
        "user_count": 0,
        "created_at": role.created_at,
        "updated_at": role.updated_at
    }


@router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(role_id: int, db: Session = Depends(get_db)):
    """
    获取角色详情

    无需权限 - 供前端显示角色信息
    """
    role = db.query(Role).options(joinedload(Role.permissions)).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")

    user_count = db.query(User).filter(User.roles.any(Role.id == role.id)).count()

    return {
        "id": role.id,
        "name": role.name,
        "description": role.description,
        "is_system": role.is_system,
        "permissions": role.permissions,
        "user_count": user_count,
        "created_at": role.created_at,
        "updated_at": role.updated_at
    }


@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    role_update: RoleUpdate,
    _: None = Depends(require_role_write),
    db: Session = Depends(get_db)
):
    """
    更新角色信息

    注意：此接口不需要特定权限检查，因为只有在系统设置中才能访问
    系统设置页面本身只对管理员开放
    """
    role = db.query(Role).options(joinedload(Role.permissions)).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")

    # 系统角色不能修改名称（只有名称真正改变时才拒绝）
    if role.is_system and role_update.name and role_update.name != role.name:
        raise HTTPException(status_code=400, detail="系统角色不能修改名称")

    # 只有名称真正改变时才更新
    if role_update.name and role_update.name != role.name:
        existing = db.query(Role).filter(Role.name == role_update.name, Role.id != role_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="角色名已存在")
        role.name = role_update.name

    if role_update.description is not None:
        role.description = role_update.description

    if role_update.permission_ids is not None:
        permissions = db.query(Permission).filter(Permission.id.in_(role_update.permission_ids)).all()
        role.permissions = permissions

    role.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(role)

    user_count = db.query(User).filter(User.roles.any(Role.id == role.id)).count()

    return {
        "id": role.id,
        "name": role.name,
        "description": role.description,
        "is_system": role.is_system,
        "permissions": role.permissions,
        "user_count": user_count,
        "created_at": role.created_at,
        "updated_at": role.updated_at
    }


@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: int,
    _: None = Depends(require_role_delete),
    db: Session = Depends(get_db)
):
    """
    删除角色

    注意: 系统角色不能删除
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")

    if role.is_system:
        raise HTTPException(status_code=400, detail="系统角色不能删除")

    # 检查是否有用户使用该角色
    user_count = db.query(User).filter(User.roles.any(Role.id == role.id)).count()
    if user_count > 0:
        raise HTTPException(status_code=400, detail=f"有 {user_count} 个用户使用该角色，请先移除用户角色")

    db.delete(role)
    db.commit()

    return {"success": True, "message": "角色删除成功"}


@router.get("/roles/{role_id}/users", response_model=List[RoleUserResponse])
async def get_role_users(
    role_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    获取拥有指定角色的用户列表
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")

    users = db.query(User).filter(User.roles.any(Role.id == role_id)).offset(skip).limit(limit).all()

    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "full_name": u.full_name,
            "is_active": u.is_active
        }
        for u in users
    ]


@router.post("/roles/{role_id}/clone")
async def clone_role(
    role_id: int,
    new_name: str,
    _: None = Depends(require_role_write),
    db: Session = Depends(get_db)
):
    """
    克隆角色
    """
    role = db.query(Role).options(joinedload(Role.permissions)).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")

    # 检查新名称是否已存在
    existing = db.query(Role).filter(Role.name == new_name).first()
    if existing:
        raise HTTPException(status_code=400, detail="角色名已存在")

    new_role = Role(
        name=new_name,
        description=f"复制自 {role.name}",
        is_system=False,
        permissions=role.permissions.copy()
    )

    db.add(new_role)
    db.commit()
    db.refresh(new_role)

    return {
        "success": True,
        "role": {
            "id": new_role.id,
            "name": new_role.name,
            "description": new_role.description,
            "is_system": new_role.is_system,
            "permission_count": len(new_role.permissions)
        }
    }


# =============================================================================
# 用户角色管理 API
# =============================================================================

@router.get("/users/{user_id}/roles", response_model=List[RoleResponse])
async def get_user_roles(user_id: int, db: Session = Depends(get_db)):
    """
    获取用户的角色列表

    无需权限 - 供前端显示用户角色
    """
    user = db.query(User).options(joinedload(User.roles).joinedload(Role.permissions)).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    return [
        {
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "is_system": r.is_system,
            "permissions": r.permissions,
            "user_count": 0,
            "created_at": r.created_at,
            "updated_at": r.updated_at
        }
        for r in user.roles
    ]


@router.put("/users/{user_id}/roles")
async def update_user_roles(
    user_id: int,
    role_update: UserRoleUpdate,
    _: None = Depends(require_user_write),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """
    更新用户的角色分配
    """
    user = ensure_user_manageable(db, user_id, principal)

    user.roles = resolve_assignable_roles(db, role_update.role_ids, principal)

    db.commit()

    return {
        "success": True,
        "user_id": user_id,
        "role_ids": role_update.role_ids,
        "message": "用户角色更新成功"
    }


@router.post("/users/{user_id}/roles/{role_id}")
async def add_role_to_user(
    user_id: int,
    role_id: int,
    _: None = Depends(require_user_write),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """
    为用户添加单个角色
    """
    user = ensure_user_manageable(db, user_id, principal)

    role = resolve_assignable_roles(db, [role_id], principal)[0]

    if role in user.roles:
        raise HTTPException(status_code=400, detail="用户已拥有该角色")

    user.roles.append(role)
    db.commit()

    return {"success": True, "message": "角色添加成功"}


@router.delete("/users/{user_id}/roles/{role_id}")
async def remove_role_from_user(
    user_id: int,
    role_id: int,
    _: None = Depends(require_user_write),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """
    移除用户的某个角色
    """
    user = ensure_user_manageable(db, user_id, principal)

    role = resolve_assignable_roles(db, [role_id], principal)[0]

    if role not in user.roles:
        raise HTTPException(status_code=400, detail="用户未拥有该角色")

    user.roles.remove(role)
    db.commit()

    return {"success": True, "message": "角色移除成功"}


# =============================================================================
# 权限检查 API
# =============================================================================

@router.get("/check/{permission}")
async def check_permission_endpoint(
    permission: str,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    """
    检查当前用户是否拥有指定权限

    返回权限检查结果，供前端判断按钮显示
    """
    if not current_user:
        # 认证关闭时返回允许
        return {
            "permission": permission,
            "has_permission": True,
            "reason": "auth_disabled"
        }

    has_perm = check_user_permission(current_user.id, permission, db)

    return {
        "permission": permission,
        "has_permission": has_perm,
        "user_id": current_user.id,
        "username": current_user.username,
        "is_superuser": current_user.is_superuser
    }


@router.get("/check-batch")
async def check_permissions_batch(
    permissions: str,  # 逗号分隔的权限列表
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    """
    批量检查多个权限

    供前端一次性检查多个按钮的权限
    """
    permission_list = permissions.split(",") if permissions else []

    if not current_user:
        # 认证关闭时返回全部允许
        return {
            "permissions": {p: True for p in permission_list},
            "reason": "auth_disabled"
        }

    result = check_user_permissions(current_user.id, permission_list, db)

    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "is_superuser": current_user.is_superuser,
        "permissions": result
    }


@router.get("/my-permissions", response_model=UserPermissionsResponse)
async def get_my_permissions(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db)
):
    """
    获取当前用户的所有权限列表

    供前端渲染菜单与按钮可见性。身份只由统一 principal 解析；
    正式环境仅接受 JWT，X-User 只在显式 debug 开发旁路中生效。
    """
    current_user = principal.user
    if not current_user:
        return {
            "user_id": 0,
            "username": principal.username,
            "is_superuser": True,
            "permissions": ["admin:all"],
            "roles": [{"id": 0, "name": "developer", "description": "显式 debug 开发旁路"}]
        }

    permissions = get_user_all_permissions(current_user.id, db)

    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "is_superuser": current_user.is_superuser,
        "permissions": permissions,
        "roles": [{"id": r.id, "name": r.name, "description": r.description} for r in current_user.roles]
    }


# =============================================================================
# 预定义角色和权限信息 (供参考)
# =============================================================================

@router.get("/defaults/roles")
async def get_default_roles_info():
    """
    获取系统预定义角色信息

    此接口无需认证，用于前端展示角色说明
    """
    return {
        "roles": PRESET_ROLES
    }


@router.get("/defaults/permissions")
async def get_default_permissions_info(db: Session = Depends(get_db)):
    """
    获取系统权限清单

    此接口无需认证，用于前端展示权限说明
    返回数据库中的实际权限（包含 id）
    """
    # 资源中文名称映射
    resource_labels = {
        "device": "设备管理",
        "backup": "备份管理",
        "config": "配置管理",
        "deploy_history": "部署历史",
        "fault": "故障管理",
        "maintenance": "维修管理",
        "spare_part": "备件管理",
        "spare_movement": "备件流转",
        "template": "配置模板",
        "credential": "凭证管理",
        "workflow": "工作流",
        "planned_task": "计划任务",
        "floor_plan": "监控大屏",
        "log": "系统日志",
        "tool_log": "工具日志",
        "user": "用户管理",
        "role": "角色权限",
        "admin": "系统管理",
        "alert": "告警设置",
        "system_config": "系统配置",
        "slo": "SLO 配置",
        "system_ops": "系统运维",
        "compliance": "合规检查",
        "ai": "AI功能",
        "nav_overview": "运维监控",
        "nav_devices": "设备管理",
        "nav_config": "配置管理",
        "nav_spare": "备件管理",
        "nav_system": "系统设置",
    }

    # 操作中文名称映射
    action_labels = {
        "read": "查看",
        "write": "创建/编辑",
        "delete": "删除",
        "execute": "执行",
        "batch": "批量操作",
        "import": "导入",
        "export": "导出",
        "deploy": "部署",
        "rollback": "回滚",
        "analyze": "分析",
        "transition": "状态流转",
        "trigger": "触发",
        "photo": "照片管理",
        "render": "渲染",
        "clear": "清理",
        "manage": "管理",
        "check": "检查",
        "all": "全部权限",
        "use": "使用",
        "config": "配置",
    }

    # 从数据库获取实际权限数据（包含 id）
    permissions = db.query(Permission).order_by(Permission.resource, Permission.action).all()
    permissions_data = [
        {
            "id": p.id,
            "name": p.name,
            "resource": p.resource,
            "action": p.action,
            "description": p.description
        }
        for p in permissions
    ]

    return {
        "resource_labels": resource_labels,
        "action_labels": action_labels,
        # 导航权限的标签按「完整权限名」索引，而不是复用 action_labels：
        # nav 的 action 是页面名（deploy / compliance ...），与功能权限的 action
        # 命名空间重叠，混在一张表里会互相覆盖
        "nav_labels": NAV_LABELS,
        # 导航分组/条目的展示顺序，与前端顶部标签与侧边栏顺序一致
        "nav_resource_order": NAV_RESOURCE_ORDER,
        "nav_order": list(NAV_LABELS.keys()),
        "permissions": permissions_data
    }


# =============================================================================
# 数据导出
# =============================================================================

@router.get("/export")
async def export_permissions_data(db: Session = Depends(get_db)):
    """
    导出权限配置数据（用于备份或迁移）
    """
    permissions = db.query(Permission).all()
    roles = db.query(Role).options(joinedload(Role.permissions)).all()

    return {
        "permissions": [
            {
                "id": p.id,
                "name": p.name,
                "resource": p.resource,
                "action": p.action,
                "description": p.description
            }
            for p in permissions
        ],
        "roles": [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "is_system": r.is_system,
                "permissions": [p.name for p in r.permissions]
            }
            for r in roles
        ]
    }