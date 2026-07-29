"""Credential management router

安全约定（改动前这四条全部不成立，见 docs/CODE_REVIEW_ISSUES.md 批次二）：

1. **任何接口都不返回 SSH 密码明文**。密码只在后端下发设备时解密使用，
   前端只需要知道"有没有设置过"。原实现的 GET /{id} 直接返回明文，
   叠加当时的无鉴权状态，等于把全网设备的 SSH 密码公开在内网里。
2. 全部接口挂 `credential:*` 权限依赖（`auth_enabled=false` 时依赖会放行，
   开启认证后立即生效）。
3. 请求体用 Pydantic 模型而不是裸 dict，避免 `name=None` 直接撞 NOT NULL。
4. 用 `Depends(get_db)` 而不是 `db = next(get_db())` —— 后者会绕过
   session_scope 的自动提交/回滚/关闭，泄漏连接。
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.shared.database import get_db
from app.shared.dependencies import require_permission
from app.shared.models import CredentialGroup
from .credential_service import encrypt_password

router = APIRouter(prefix="/api/credentials", tags=["credentials"])


class CredentialCreate(BaseModel):
    """凭证组创建请求"""
    name: str = Field(..., min_length=1, max_length=100, description="凭证组名称")
    description: Optional[str] = Field(None, max_length=500)
    username: str = Field(..., min_length=1, max_length=100, description="SSH 用户名")
    password: str = Field(..., min_length=1, description="SSH 密码（仅写入，不会被读回）")
    enable_password: Optional[str] = Field(None, description="enable/特权密码，可选")


class CredentialUpdate(BaseModel):
    """凭证组更新请求

    密码类字段留空表示"保持不变"；要清空 enable 密码请显式传
    `clear_enable_password=true`，避免前端不回填密码导致误清空。
    """
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    username: Optional[str] = Field(None, min_length=1, max_length=100)
    password: Optional[str] = Field(None, description="留空表示不修改")
    enable_password: Optional[str] = Field(None, description="留空表示不修改")
    clear_enable_password: bool = Field(False, description="显式清空 enable 密码")


def _to_public_dict(c: CredentialGroup) -> dict:
    """转换为可以安全返回给前端的结构（不含任何密码）"""
    return {
        "id": c.id,
        "name": c.name,
        "description": c.description,
        "username": c.username,
        # 只暴露"是否已设置"，不暴露内容
        "has_password": bool(c.password_encrypted),
        "has_enable_password": bool(c.enable_password_encrypted),
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


@router.get("")
async def list_credentials(
    _: None = Depends(require_permission("credential:read")),
    db: Session = Depends(get_db),
):
    """获取所有凭证组（不含密码）"""
    credentials = db.query(CredentialGroup).order_by(
        CredentialGroup.created_at.desc()
    ).all()
    return {"items": [_to_public_dict(c) for c in credentials]}


@router.post("")
async def create_credential(
    credential: CredentialCreate,
    _: None = Depends(require_permission("credential:write")),
    db: Session = Depends(get_db),
):
    """创建新的凭证组"""
    existing = db.query(CredentialGroup).filter(
        CredentialGroup.name == credential.name
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="凭证组名称已存在")

    new_credential = CredentialGroup(
        name=credential.name,
        description=credential.description or "",
        username=credential.username,
        password_encrypted=encrypt_password(credential.password),
        enable_password_encrypted=(
            encrypt_password(credential.enable_password)
            if credential.enable_password else None
        ),
    )

    db.add(new_credential)
    db.commit()
    db.refresh(new_credential)

    return {"id": new_credential.id, "message": "凭证组创建成功"}


@router.get("/{cred_id}")
async def get_credential(
    cred_id: int,
    _: None = Depends(require_permission("credential:read")),
    db: Session = Depends(get_db),
):
    """获取凭证组详情

    注意：不返回密码明文。前端编辑时密码框留空即"保持不变"。
    """
    credential = db.query(CredentialGroup).filter(
        CredentialGroup.id == cred_id
    ).first()

    if not credential:
        raise HTTPException(status_code=404, detail="凭证组不存在")

    return _to_public_dict(credential)


@router.put("/{cred_id}")
async def update_credential(
    cred_id: int,
    credential: CredentialUpdate,
    _: None = Depends(require_permission("credential:write")),
    db: Session = Depends(get_db),
):
    """更新凭证组（密码类字段留空表示不修改）"""
    cred = db.query(CredentialGroup).filter(
        CredentialGroup.id == cred_id
    ).first()

    if not cred:
        raise HTTPException(status_code=404, detail="凭证组不存在")

    if credential.name and credential.name != cred.name:
        duplicated = db.query(CredentialGroup).filter(
            CredentialGroup.name == credential.name,
            CredentialGroup.id != cred_id,
        ).first()
        if duplicated:
            raise HTTPException(status_code=400, detail="凭证组名称已存在")
        cred.name = credential.name

    if credential.description is not None:
        cred.description = credential.description
    if credential.username:
        cred.username = credential.username
    if credential.password:
        cred.password_encrypted = encrypt_password(credential.password)

    if credential.clear_enable_password:
        cred.enable_password_encrypted = None
    elif credential.enable_password:
        cred.enable_password_encrypted = encrypt_password(credential.enable_password)

    db.commit()
    db.refresh(cred)

    return {"message": "凭证组更新成功"}


@router.delete("/{cred_id}")
async def delete_credential(
    cred_id: int,
    _: None = Depends(require_permission("credential:delete")),
    db: Session = Depends(get_db),
):
    """删除凭证组"""
    credential = db.query(CredentialGroup).filter(
        CredentialGroup.id == cred_id
    ).first()

    if not credential:
        raise HTTPException(status_code=404, detail="凭证组不存在")

    db.delete(credential)
    db.commit()

    return {"message": "凭证组删除成功"}
