"""Security policy for delegated user-role assignment."""

from typing import Iterable

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.features.auth.identity import Principal
from app.shared.models import Role, User


def _permission_names(user: User) -> set[str]:
    return {
        permission.name
        for role in user.roles
        for permission in role.permissions
    }


def ensure_user_manageable(
    db: Session,
    target_user_id: int,
    principal: Principal,
) -> User:
    target = db.query(User).options(
        joinedload(User.roles).joinedload(Role.permissions)
    ).filter(User.id == target_user_id).first()
    if target is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    if principal.user is None or principal.user.is_superuser:
        return target

    actor = db.query(User).options(
        joinedload(User.roles).joinedload(Role.permissions)
    ).filter(User.id == principal.user.id).first()
    actor_permissions = _permission_names(actor) if actor else set()
    target_is_admin = target.is_superuser or "admin:all" in _permission_names(target)
    if target_is_admin and "admin:all" not in actor_permissions:
        raise HTTPException(status_code=403, detail="只有管理员可以修改管理员账号")
    return target


def resolve_assignable_roles(
    db: Session,
    role_ids: Iterable[int],
    principal: Principal,
) -> list[Role]:
    requested_ids = list(role_ids)
    if len(requested_ids) != len(set(requested_ids)):
        raise HTTPException(status_code=422, detail="角色 ID 不能重复")
    roles = []
    if requested_ids:
        roles = db.query(Role).options(joinedload(Role.permissions)).filter(
            Role.id.in_(requested_ids)
        ).all()
        if len(roles) != len(requested_ids):
            raise HTTPException(status_code=422, detail="包含不存在的角色")

    if principal.user is None or principal.user.is_superuser:
        return roles

    actor = db.query(User).options(
        joinedload(User.roles).joinedload(Role.permissions)
    ).filter(User.id == principal.user.id).first()
    if actor is None:
        raise HTTPException(status_code=401, detail="需要认证")

    actor_permissions = _permission_names(actor)
    if "admin:all" in actor_permissions:
        return roles
    if "role:write" not in actor_permissions:
        raise HTTPException(status_code=403, detail="分配角色需要 role:write 权限")

    assigned_permissions = {
        permission.name
        for role in roles
        for permission in role.permissions
    }
    if "admin:all" in assigned_permissions or not assigned_permissions.issubset(
        actor_permissions
    ):
        raise HTTPException(status_code=403, detail="不能授予超出自身范围的权限")
    return roles