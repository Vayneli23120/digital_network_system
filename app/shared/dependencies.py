"""
权限检查依赖函数

提供 FastAPI 依赖用于保护需要特定权限的端点
"""

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.shared.database import get_db
from app.shared.config import get_config
from app.shared.models import User, Role, Permission
from app.features.auth.router import get_current_user_from_token

config = get_config()


def check_user_permission(user_id: int, permission_name: str, db: Session) -> bool:
    """
    检查用户是否拥有指定权限

    Args:
        user_id: 用户 ID
        permission_name: 权限名称，如 "device:read"
        db: 数据库会话

    Returns:
        True 如果用户拥有该权限，否则 False
    """
    user = db.query(User).options(
        joinedload(User.roles)
    ).options(
        joinedload(User.roles).joinedload(Role.permissions)
    ).filter(User.id == user_id).first()

    if not user:
        return False

    # 超级管理员拥有所有权限
    if user.is_superuser:
        return True

    # 检查用户角色中的权限
    for role in user.roles:
        for permission in role.permissions:
            if permission.name == permission_name:
                return True
            # admin:all 权限包含所有权限
            if permission.name == "admin:all":
                return True

    return False


def check_user_permissions(user_id: int, permission_names: list, db: Session) -> dict:
    """
    检查用户是否拥有多个权限

    Args:
        user_id: 用户 ID
        permission_names: 权限名称列表
        db: 数据库会话

    Returns:
        dict: {permission_name: bool} 结果字典
    """
    user = db.query(User).options(
        joinedload(User.roles)
    ).options(
        joinedload(User.roles).joinedload(Role.permissions)
    ).filter(User.id == user_id).first()

    if not user:
        return {p: False for p in permission_names}

    # 超级管理员拥有所有权限
    if user.is_superuser:
        return {p: True for p in permission_names}

    # 收集用户所有权限
    user_permissions = set()
    has_admin_all = False

    for role in user.roles:
        for permission in role.permissions:
            if permission.name == "admin:all":
                has_admin_all = True
            user_permissions.add(permission.name)

    # 如果有 admin:all，所有权限为 True
    if has_admin_all:
        return {p: True for p in permission_names}

    return {p: p in user_permissions for p in permission_names}


def get_user_all_permissions(user_id: int, db: Session) -> list:
    """
    获取用户拥有的所有权限列表

    Args:
        user_id: 用户 ID
        db: 数据库会话

    Returns:
        list: 权限名称列表
    """
    user = db.query(User).options(
        joinedload(User.roles)
    ).options(
        joinedload(User.roles).joinedload(Role.permissions)
    ).filter(User.id == user_id).first()

    if not user:
        return []

    # 超级管理员拥有所有权限
    if user.is_superuser:
        return ["admin:all"]

    permissions = set()
    for role in user.roles:
        for permission in role.permissions:
            permissions.add(permission.name)

    return list(permissions)


def require_permission(permission_name: str):
    """
    权限检查依赖，用于保护端点

    使用方式:
        @router.delete("/history/{id}")
        async def delete_history(
            history_id: int,
            _: None = Depends(require_permission("deploy_history:delete")),
            db: Session = Depends(get_db)
        ):
            ...

    Args:
        permission_name: 需要的权限名称

    Returns:
        FastAPI 依赖函数
    """
    async def permission_checker(
        current_user: User = Depends(get_current_user_from_token),
        db: Session = Depends(get_db)
    ):
        # 认证关闭时允许所有操作
        if not config.security.auth_enabled:
            return None

        # 未登录用户拒绝
        if not current_user:
            raise HTTPException(status_code=401, detail="需要认证")

        # 超级管理员绕过检查
        if current_user.is_superuser:
            return current_user

        # 检查权限
        if check_user_permission(current_user.id, permission_name, db):
            return current_user

        raise HTTPException(status_code=403, detail="权限不足")

    return permission_checker


def require_permissions(permission_names: list):
    """
    多权限检查依赖 - 需要满足其中任意一个

    Args:
        permission_names: 需要的权限名称列表（满足任意一个即可）

    Returns:
        FastAPI 依赖函数
    """
    async def permission_checker(
        current_user: User = Depends(get_current_user_from_token),
        db: Session = Depends(get_db)
    ):
        # 认证关闭时允许所有操作
        if not config.security.auth_enabled:
            return None

        # 未登录用户拒绝
        if not current_user:
            raise HTTPException(status_code=401, detail="需要认证")

        # 超级管理员绕过检查
        if current_user.is_superuser:
            return current_user

        # 检查是否拥有任意一个权限
        for perm_name in permission_names:
            if check_user_permission(current_user.id, perm_name, db):
                return current_user

        raise HTTPException(
            status_code=403,
            detail=f"需要以下权限之一: {', '.join(permission_names)}"
        )

    return permission_checker


def require_superuser():
    """
    超级管理员检查依赖

    只允许超级管理员访问

    Returns:
        FastAPI 依赖函数
    """
    async def superuser_checker(
        current_user: User = Depends(get_current_user_from_token),
        db: Session = Depends(get_db)
    ):
        # 认证关闭时允许所有操作
        if not config.security.auth_enabled:
            return None

        # 未登录用户拒绝
        if not current_user:
            raise HTTPException(status_code=401, detail="需要认证")

        # 只有超级管理员可以访问
        if current_user.is_superuser:
            return current_user

        raise HTTPException(status_code=403, detail="需要超级管理员权限")

    return superuser_checker