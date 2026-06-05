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

router = APIRouter(prefix="/api/permissions", tags=["permissions"])


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
    {"name": "compliance:check", "resource": "compliance", "action": "check", "description": "合规检查"},

    # AI 功能权限
    {"name": "ai:use", "resource": "ai", "action": "use", "description": "使用AI功能"},
    {"name": "ai:config", "resource": "ai", "action": "config", "description": "配置AI服务"},
    {"name": "ai:compliance", "resource": "ai", "action": "compliance", "description": "AI合规审核"},
]

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
            "spare_part:read", "spare_part:write", "spare_movement:write",
            "template:read", "template:write", "template:render",
            "workflow:read", "workflow:trigger",
            "planned_task:read", "planned_task:execute",
            "log:read", "tool_log:read",
            "ai:use", "ai:compliance",  # AI 功能权限
        ]
    },
    {
        "name": "viewer",
        "description": "只读用户 - 仅查看权限",
        "is_system": True,
        "permissions": [
            "device:read", "backup:read", "config:read",
            "fault:read", "maintenance:read", "spare_part:read",
            "template:read", "workflow:read", "planned_task:read",
            "log:read", "tool_log:read", "floor_plan:read",
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

def init_permissions_and_roles(db: Session) -> dict:
    """
    初始化权限和角色数据

    如果表为空，自动插入预定义权限和角色

    Args:
        db: 数据库会话

    Returns:
        初始化结果统计
    """
    result = {"permissions_created": 0, "roles_created": 0, "roles_updated": 0}

    # 检查权限表是否为空
    existing_permissions = db.query(Permission).count()

    if existing_permissions == 0:
        logger.info("权限表为空，初始化预定义权限...")
        for perm_data in EXTENDED_PERMISSIONS:
            perm = Permission(
                name=perm_data["name"],
                description=perm_data.get("description"),
                resource=perm_data["resource"],
                action=perm_data["action"]
            )
            db.add(perm)
            result["permissions_created"] += 1

        db.commit()
        logger.info(f"创建 {result['permissions_created']} 个权限")

    # 检查角色表是否为空
    existing_roles = db.query(Role).count()

    if existing_roles == 0:
        logger.info("角色表为空，初始化预定义角色...")
        for role_data in PRESET_ROLES:
            role = Role(
                name=role_data["name"],
                description=role_data.get("description"),
                is_system=role_data.get("is_system", False)
            )
            db.add(role)
            db.flush()

            # 关联权限
            for perm_name in role_data.get("permissions", []):
                perm = db.query(Permission).filter(Permission.name == perm_name).first()
                if perm:
                    role.permissions.append(perm)

            result["roles_created"] += 1

        db.commit()
        logger.info(f"创建 {result['roles_created']} 个角色")
    else:
        # 检查是否需要更新系统角色的权限
        for role_data in PRESET_ROLES:
            if role_data.get("is_system"):
                role = db.query(Role).filter(Role.name == role_data["name"]).first()
                if role:
                    current_perm_names = {p.name for p in role.permissions}
                    expected_perm_names = set(role_data.get("permissions", []))

                    if current_perm_names != expected_perm_names:
                        role.permissions.clear()
                        for perm_name in role_data.get("permissions", []):
                            perm = db.query(Permission).filter(Permission.name == perm_name).first()
                            if perm:
                                role.permissions.append(perm)
                        result["roles_updated"] += 1

        if result["roles_updated"] > 0:
            db.commit()
            logger.info(f"更新 {result['roles_updated']} 个系统角色权限")

    return result


# =============================================================================
# 初始化端点
# =============================================================================

@router.post("/init")
async def init_permissions_system(db: Session = Depends(get_db)):
    """
    初始化权限系统（自动创建权限和角色数据）

    首次使用时调用此接口初始化预定义权限和角色
    """
    try:
        result = init_permissions_and_roles(db)
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
    db: Session = Depends(get_db)
):
    """
    更新用户的角色分配
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    roles = db.query(Role).filter(Role.id.in_(role_update.role_ids)).all()
    user.roles = roles

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
    db: Session = Depends(get_db)
):
    """
    为用户添加单个角色
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")

    if role in user.roles:
        raise HTTPException(status_code=400, detail="用户已拥有该角色")

    user.roles.append(role)
    db.commit()

    return {"success": True, "message": "角色添加成功"}


@router.delete("/users/{user_id}/roles/{role_id}")
async def remove_role_from_user(
    user_id: int,
    role_id: int,
    db: Session = Depends(get_db)
):
    """
    移除用户的某个角色
    """
    user = db.query(User).options(joinedload(User.roles)).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")

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
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    """
    获取当前用户的所有权限列表

    供前端显示用户权限信息
    """
    if not current_user:
        # 认证关闭时返回模拟权限
        return {
            "user_id": 0,
            "username": "guest",
            "is_superuser": True,
            "permissions": ["admin:all"],
            "roles": [{"id": 1, "name": "admin", "description": "系统管理员"}]
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
        "compliance": "合规检查",
        "ai": "AI功能",
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