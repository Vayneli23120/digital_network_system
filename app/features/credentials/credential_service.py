"""
SSH 凭证管理服务
"""

from cryptography.fernet import Fernet
from typing import Optional
from app.shared.config import get_config


class CredentialService:
    """凭证管理服务 - 用于加密/解密 SSH 密码"""

    def __init__(self):
        self.config = get_config()
        self._cipher: Optional[Fernet] = None

    @property
    def cipher(self) -> Fernet:
        """获取 Fernet 加密实例"""
        if self._cipher is None:
            key = self.config.security.jwt_secret
            if not key:
                raise ValueError("Encryption key not configured")
            # 确保 key 是有效的 Fernet key (32 bytes url-safe base64)
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            import base64
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b"nas-salt",
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(key.encode()))
            self._cipher = Fernet(key)
        return self._cipher

    def encrypt_password(self, password: str) -> str:
        """加密密码"""
        return self.cipher.encrypt(password.encode()).decode()

    def decrypt_password(self, encrypted_password: str) -> str:
        """解密密码"""
        return self.cipher.decrypt(encrypted_password.encode()).decode()


# 全局实例
_credential_service: Optional[CredentialService] = None


def get_credential_service() -> CredentialService:
    """获取凭证服务实例"""
    global _credential_service
    if _credential_service is None:
        _credential_service = CredentialService()
    return _credential_service


def encrypt_password(password: str) -> str:
    """加密密码（便捷函数）"""
    return get_credential_service().encrypt_password(password)


def decrypt_password(encrypted_password: str) -> str:
    """解密密码（便捷函数）"""
    return get_credential_service().decrypt_password(encrypted_password)


def resolve_device_credentials(db, device) -> dict:
    """解析设备的 SSH 凭证（按 device.credential_group，回退到 default）

    返回 netmiko 可直接使用的字段：username / password / secret。

    抽出这个函数是因为凭证解析逻辑此前被各处重复实现，
    Celery 备份任务里那份甚至调用了并不存在的
    `CredentialService(db).get_credentials_for_device(device)`。

    Args:
        db: 数据库会话
        device: Device 实例

    Returns:
        dict: {"username": str, "password": str, "secret": str}

    Raises:
        ValueError: 找不到凭证组，或凭证组缺少用户名/密码
    """
    from app.shared.models import CredentialGroup

    group_name = getattr(device, "credential_group", None) or "default"
    cred_group = db.query(CredentialGroup).filter(
        CredentialGroup.name == group_name
    ).first()

    if not cred_group and group_name != "default":
        cred_group = db.query(CredentialGroup).filter(
            CredentialGroup.name == "default"
        ).first()

    if not cred_group:
        raise ValueError("未配置 SSH 凭证，请先在凭证管理页面添加凭证组")

    credentials = {
        "username": cred_group.username or "",
        "password": decrypt_password(cred_group.password_encrypted) if cred_group.password_encrypted else "",
        "secret": decrypt_password(cred_group.enable_password_encrypted) if cred_group.enable_password_encrypted else "",
    }

    if not credentials["username"]:
        raise ValueError(f"凭证组 '{cred_group.name}' 未设置用户名")
    if not credentials["password"]:
        raise ValueError(f"凭证组 '{cred_group.name}' 未设置密码")

    return credentials
