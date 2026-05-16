"""Credential management router"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.shared.database import get_db
from app.shared.models import CredentialGroup
from .credential_service import encrypt_password, decrypt_password

router = APIRouter(prefix="/api/credentials", tags=["credentials"])


@router.get("")
async def list_credentials():
    """获取所有凭证组（不返回密码）"""
    db: Session = next(get_db())

    try:
        credentials = db.query(CredentialGroup).order_by(
            CredentialGroup.created_at.desc()
        ).all()

        return {
            "items": [
                {
                    "id": c.id,
                    "name": c.name,
                    "description": c.description,
                    "username": c.username,
                    "created_at": c.created_at.isoformat(),
                    "updated_at": c.updated_at.isoformat()
                }
                for c in credentials
            ]
        }
    finally:
        db.close()


@router.post("")
async def create_credential(credential: dict):
    """创建新的凭证组"""
    db: Session = next(get_db())

    try:
        # 检查名称是否已存在
        existing = db.query(CredentialGroup).filter(
            CredentialGroup.name == credential.get("name")
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="凭证组名称已存在")

        # 加密密码
        password_encrypted = encrypt_password(credential.get("password", ""))
        enable_password = credential.get("enable_password")
        enable_password_encrypted = encrypt_password(enable_password) if enable_password else None

        new_credential = CredentialGroup(
            name=credential.get("name"),
            description=credential.get("description", ""),
            username=credential.get("username", ""),
            password_encrypted=password_encrypted,
            enable_password_encrypted=enable_password_encrypted
        )

        db.add(new_credential)
        db.commit()
        db.refresh(new_credential)

        return {"id": new_credential.id, "message": "凭证组创建成功"}
    finally:
        db.close()


@router.get("/{cred_id}")
async def get_credential(cred_id: int):
    """获取凭证组详情（包含密码明文）"""
    db: Session = next(get_db())

    try:
        credential = db.query(CredentialGroup).filter(
            CredentialGroup.id == cred_id
        ).first()

        if not credential:
            raise HTTPException(status_code=404, detail="凭证组不存在")

        # 尝试解密密码，失败时返回空密码提示用户重新输入
        try:
            password = decrypt_password(credential.password_encrypted)
        except Exception:
            password = ''

        try:
            enable_password = decrypt_password(credential.enable_password_encrypted) if credential.enable_password_encrypted else None
        except Exception:
            enable_password = None

        return {
            "id": credential.id,
            "name": credential.name,
            "description": credential.description,
            "username": credential.username,
            "password": password,
            "enable_password": enable_password,
            "decrypt_warning": not password,  # 如果密码解密失败，提示用户
            "created_at": credential.created_at.isoformat(),
            "updated_at": credential.updated_at.isoformat()
        }
    finally:
        db.close()


@router.put("/{cred_id}")
async def update_credential(cred_id: int, credential: dict):
    """更新凭证组"""
    db: Session = next(get_db())

    try:
        cred = db.query(CredentialGroup).filter(
            CredentialGroup.id == cred_id
        ).first()

        if not cred:
            raise HTTPException(status_code=404, detail="凭证组不存在")

        # 更新字段
        cred.name = credential.get("name", cred.name)
        cred.description = credential.get("description", cred.description)
        cred.username = credential.get("username", cred.username)

        # 如果提供了新密码，更新加密密码
        if credential.get("password"):
            cred.password_encrypted = encrypt_password(credential.get("password"))
        if credential.get("enable_password"):
            cred.enable_password_encrypted = encrypt_password(credential.get("enable_password"))
        elif credential.get("enable_password") == "":
            cred.enable_password_encrypted = None

        db.commit()
        db.refresh(cred)

        return {"message": "凭证组更新成功"}
    finally:
        db.close()


@router.delete("/{cred_id}")
async def delete_credential(cred_id: int):
    """删除凭证组"""
    db: Session = next(get_db())

    try:
        credential = db.query(CredentialGroup).filter(
            CredentialGroup.id == cred_id
        ).first()

        if not credential:
            raise HTTPException(status_code=404, detail="凭证组不存在")

        db.delete(credential)
        db.commit()

        return {"message": "凭证组删除成功"}
    finally:
        db.close()
