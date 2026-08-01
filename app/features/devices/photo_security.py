"""设备照片的文件验证、存储和安全删除。"""

import os
from pathlib import Path
from typing import BinaryIO, Union
from uuid import uuid4

from app.shared.config import get_config

MAX_DEVICE_PHOTO_BYTES = 10 * 1024 * 1024
PHOTO_CHUNK_BYTES = 64 * 1024
PHOTO_TYPES = frozenset({"front", "back", "label", "rack", "other"})
CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
EXTENSION_CONTENT_TYPES = {extension: content_type for content_type, extension in CONTENT_TYPE_EXTENSIONS.items()}


class DevicePhotoValidationError(ValueError):
    """照片类型、内容或路径不符合安全要求。"""


def validate_photo_type(photo_type: str) -> str:
    if photo_type not in PHOTO_TYPES:
        raise DevicePhotoValidationError("不支持的照片类型")
    return photo_type


def extension_for_content_type(content_type: str) -> str:
    extension = CONTENT_TYPE_EXTENSIONS.get((content_type or "").lower())
    if extension is None:
        raise DevicePhotoValidationError("仅支持 JPEG、PNG 或 WebP 图片")
    return extension


def _matches_image_signature(content_type: str, header: bytes) -> bool:
    if content_type == "image/jpeg":
        return header.startswith(b"\xff\xd8\xff")
    if content_type == "image/png":
        return header.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/webp":
        return len(header) >= 12 and header.startswith(b"RIFF") and header[8:12] == b"WEBP"
    return False


def photo_root(root: Union[str, Path, None] = None) -> Path:
    return Path(root or get_config().storage.photo_dir).resolve()


def allocate_photo_path(
    device_id: int,
    content_type: str,
    root: Union[str, Path, None] = None,
) -> tuple[Path, str]:
    extension = extension_for_content_type(content_type)
    storage_root = photo_root(root)
    filename = f"{uuid4().hex}{extension}"
    relative_path = Path(str(device_id)) / filename
    return storage_root / relative_path, f"/photos/{relative_path.as_posix()}"


def save_uploaded_photo(
    file_object: BinaryIO,
    destination: Path,
    content_type: str,
    max_bytes: int = MAX_DEVICE_PHOTO_BYTES,
) -> int:
    """流式复制上传内容到临时文件，验证签名后原子落盘。"""
    extension_for_content_type(content_type)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = destination.with_suffix(f"{destination.suffix}.uploading")
    size = 0
    header = b""

    try:
        file_object.seek(0)
        with temporary_path.open("xb") as output:
            while True:
                chunk = file_object.read(PHOTO_CHUNK_BYTES)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    raise DevicePhotoValidationError("照片大小不能超过 10 MB")
                if len(header) < 16:
                    header = (header + chunk)[:16]
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())

        if size == 0:
            raise DevicePhotoValidationError("照片文件不能为空")
        if not _matches_image_signature(content_type, header):
            raise DevicePhotoValidationError("图片内容与声明类型不匹配")

        os.replace(temporary_path, destination)
        return size
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def resolve_stored_photo_path(
    stored_path: Union[str, Path],
    root: Union[str, Path, None] = None,
) -> Path:
    """把新旧照片记录解析到照片根目录内，拒绝目录逃逸。"""
    storage_root = photo_root(root)
    if not stored_path:
        raise DevicePhotoValidationError("照片路径为空")

    stored_path_text = str(stored_path)
    if stored_path_text.startswith("/photos/"):
        candidate = storage_root / stored_path_text.removeprefix("/photos/")
    else:
        raw_path = Path(stored_path_text)
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
        raise DevicePhotoValidationError("照片路径超出允许目录") from exc
    return resolved


def public_photo_url(
    stored_path: str,
    root: Union[str, Path, None] = None,
) -> str:
    resolved = resolve_stored_photo_path(stored_path, root)
    relative_path = resolved.relative_to(photo_root(root))
    return f"/photos/{relative_path.as_posix()}"


def content_type_for_photo_path(path: Path) -> str:
    content_type = EXTENSION_CONTENT_TYPES.get(path.suffix.lower())
    if content_type is None:
        raise DevicePhotoValidationError("照片文件类型无效")
    return content_type


def delete_stored_photo(
    stored_path: str,
    root: Union[str, Path, None] = None,
) -> None:
    resolved = resolve_stored_photo_path(stored_path, root)
    if resolved.exists() and resolved.is_file():
        resolved.unlink()
