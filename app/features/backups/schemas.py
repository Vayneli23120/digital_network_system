"""Validated request models for backup operations."""

from typing import Optional

from pydantic import BaseModel, Field, PositiveInt


class BackupRequest(BaseModel):
    """操作者会话级 SSH 凭证（仅请求内存，不落库/不入日志）。

    默认（credential_session_required=True）下备份必须携带操作者自己的凭证；
    未提供时后端返回 400，不降级到服务器存储的凭证组。
    """

    username: Optional[str] = None
    password: Optional[str] = None
    secret: Optional[str] = None


class BatchBackupRequest(BackupRequest):
    device_ids: list[PositiveInt] = Field(min_length=1, max_length=100)
