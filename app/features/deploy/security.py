"""Deploy 输入路径与权限相关的安全辅助函数。"""

from pathlib import Path
from typing import Optional, Union

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.features.auth.identity import (
    Principal,
    development_auth_bypass_enabled,
    resolve_token_principal,
)
from app.core.command_guard import validate_commands
from app.shared.config import get_config
from app.shared.dependencies import check_user_permission


class UnsafeBackupPathError(ValueError):
    """备份路径不在配置的备份根目录内。"""


def authorize_deploy_token(token: Optional[str], db: Session) -> Principal:
    """校验 WebSocket 部署身份及 config:deploy 权限。"""
    principal = resolve_token_principal(token, db)
    if development_auth_bypass_enabled():
        return principal
    if principal.user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="需要认证")
    if principal.user.is_superuser or check_user_permission(
        principal.user.id,
        "config:deploy",
        db,
    ):
        return principal
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")


def parse_deploy_commands(config: str) -> list[str]:
    """按现有部署语义把配置文本转为命令列表。"""
    commands = []
    for line in config.strip().splitlines():
        command = line.strip()
        if not command or command.startswith(("!", "#")):
            continue
        if command in {"configure terminal", "end", "exit"}:
            continue
        commands.append(command)
    return commands


def validate_deploy_config(config: str, devices: list[dict]) -> None:
    """针对所有目标厂商执行命令守卫；发现危险命令即拒绝整个部署。"""
    commands = parse_deploy_commands(config)
    vendors = {str(device.get("vendor") or "cisco").lower() for device in devices}
    for vendor in vendors or {"cisco"}:
        validate_commands(
            commands,
            vendor=vendor,
            context="HTTP configuration deployment",
        )


def resolve_backup_file(
    requested_path: Union[str, Path],
    backup_root: Union[str, Path, None] = None,
) -> Path:
    """把客户端提供的备份文件限制在配置的备份目录内。"""
    if not requested_path:
        raise UnsafeBackupPathError("备份文件路径不能为空")

    root = Path(backup_root or get_config().storage.backup_dir).resolve()
    candidate = Path(requested_path)
    if not candidate.is_absolute():
        direct_candidate = candidate.resolve(strict=False)
        try:
            direct_candidate.relative_to(root)
            candidate = direct_candidate
        except ValueError:
            candidate = root / candidate

    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise UnsafeBackupPathError("备份文件路径超出允许目录") from exc

    if not resolved.exists() or not resolved.is_file():
        raise FileNotFoundError("备份文件不存在")
    return resolved
