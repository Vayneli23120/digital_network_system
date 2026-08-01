"""Devices WebSocket authorization helpers."""

from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.features.auth.identity import (
    Principal,
    development_auth_bypass_enabled,
    resolve_token_principal,
)
from app.shared.dependencies import check_user_permission


def authorize_device_read_token(token: Optional[str], db: Session) -> Principal:
    """Authorize a non-HTTP channel for device:read access."""
    principal = resolve_token_principal(token, db)
    if development_auth_bypass_enabled():
        return principal
    if principal.user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="需要认证")
    if principal.user.is_superuser or check_user_permission(
        principal.user.id,
        "device:read",
        db,
    ):
        return principal
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")
