"""Backup file confinement and bounded text access."""

from pathlib import Path
from typing import Union

from app.shared.config import get_config

MAX_BACKUP_TEXT_BYTES = 5 * 1024 * 1024


class UnsafeBackupRecordPathError(ValueError):
    """A backup record points outside the configured backup directory."""


def backup_root(root: Union[str, Path, None] = None) -> Path:
    return Path(root or get_config().storage.backup_dir).resolve()


def resolve_backup_record_file(
    stored_path: Union[str, Path],
    root: Union[str, Path, None] = None,
    *,
    must_exist: bool = True,
) -> Path:
    if not stored_path:
        raise UnsafeBackupRecordPathError("备份文件路径为空")

    storage_root = backup_root(root)
    raw_path = Path(str(stored_path))
    if raw_path.is_absolute():
        candidate = raw_path
    else:
        direct_candidate = raw_path.resolve(strict=False)
        try:
            direct_candidate.relative_to(storage_root)
            candidate = direct_candidate
        except ValueError:
            candidate = storage_root / raw_path

    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(storage_root)
    except ValueError as exc:
        raise UnsafeBackupRecordPathError("备份文件路径超出允许目录") from exc

    if must_exist and (not resolved.exists() or not resolved.is_file()):
        raise FileNotFoundError("备份文件不存在")
    return resolved


def safe_backup_reference(
    stored_path: Union[str, Path],
    root: Union[str, Path, None] = None,
) -> str:
    resolved = resolve_backup_record_file(stored_path, root, must_exist=False)
    return resolved.relative_to(backup_root(root)).as_posix()


def read_backup_text(
    stored_path: Union[str, Path],
    root: Union[str, Path, None] = None,
    max_bytes: int = MAX_BACKUP_TEXT_BYTES,
) -> str:
    return read_backup_bytes(stored_path, root, max_bytes).decode(
        "utf-8",
        errors="replace",
    )


def read_backup_bytes(
    stored_path: Union[str, Path],
    root: Union[str, Path, None] = None,
    max_bytes: int = MAX_BACKUP_TEXT_BYTES,
) -> bytes:
    backup_path = resolve_backup_record_file(stored_path, root)
    with backup_path.open("rb") as backup_file:
        content = backup_file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise ValueError("备份文件超过安全读取大小限制")
    return content


def delete_backup_file(
    stored_path: Union[str, Path],
    root: Union[str, Path, None] = None,
) -> None:
    backup_path = resolve_backup_record_file(stored_path, root)
    backup_path.unlink()
