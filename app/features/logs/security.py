"""Logs path confinement and non-HTTP channel authorization."""

import asyncio
from pathlib import Path
from typing import Optional, Union

from fastapi import HTTPException, WebSocket, status
from sqlalchemy.orm import Session
from starlette.websockets import WebSocketDisconnect

from app.features.auth.identity import (
    Principal,
    development_auth_bypass_enabled,
    resolve_token_principal,
)
from app.shared.dependencies import check_user_permission
from app.shared.database import get_db_manager


class UnsafeLogPathError(ValueError):
    """A requested log path escapes the configured log directory."""


def resolve_log_file(
    filename: Union[str, Path],
    log_root: Union[str, Path],
    *,
    must_exist: bool = True,
) -> Path:
    """Resolve one plain .log filename inside log_root and reject all escapes."""
    if not filename:
        raise UnsafeLogPathError("日志文件名不能为空")

    filename_text = str(filename)
    candidate_name = Path(filename_text)
    if candidate_name.is_absolute() or candidate_name.name != filename_text:
        raise UnsafeLogPathError("日志文件名无效")
    if candidate_name.suffix.lower() != ".log":
        raise UnsafeLogPathError("仅允许读取 .log 文件")

    root = Path(log_root).resolve()
    resolved = (root / candidate_name).resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise UnsafeLogPathError("日志文件路径超出允许目录") from exc

    if must_exist and (not resolved.exists() or not resolved.is_file()):
        raise FileNotFoundError("日志文件不存在")
    return resolved


def authorize_log_read_token(token: Optional[str], db: Session) -> Principal:
    """Authorize a WebSocket channel for log:read access."""
    principal = resolve_token_principal(token, db)
    if development_auth_bypass_enabled():
        return principal
    if principal.user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="需要认证")
    if principal.user.is_superuser or check_user_permission(
        principal.user.id,
        "log:read",
        db,
    ):
        return principal
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")


async def authenticate_log_websocket(
    websocket: WebSocket,
    timeout_seconds: float = 10.0,
) -> Optional[Principal]:
    """Accept a socket and authenticate its first JSON message."""
    await websocket.accept()
    try:
        payload = await asyncio.wait_for(websocket.receive_json(), timeout=timeout_seconds)
        token = payload.get("access_token") if isinstance(payload, dict) else None
    except (asyncio.TimeoutError, ValueError, WebSocketDisconnect):
        try:
            await websocket.close(code=4401)
        except RuntimeError:
            pass
        return None

    db = get_db_manager().get_session()
    try:
        try:
            principal = await asyncio.to_thread(authorize_log_read_token, token, db)
        except HTTPException as exc:
            await websocket.send_json({
                "event": "auth_error",
                "status_code": exc.status_code,
                "message": str(exc.detail),
            })
            await websocket.close(code=4401 if exc.status_code == 401 else 4403)
            return None
    finally:
        await asyncio.to_thread(db.close)

    await websocket.send_json({
        "event": "authenticated",
        "username": principal.username,
    })
    return principal
