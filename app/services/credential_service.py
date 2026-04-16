"""
SSH 凭证管理服务
"""

from cryptography.fernet import Fernet
from typing import Optional
from ..config import get_config


class CredentialService:
    """凭证管理服务 - 用于加密/解密 SSH 密码"""

    def __init__(self):
        self.config = get_config()
        self._cipher: Optional[Fernet] = None

    @property
    def cipher(self) -> Fernet:
        """获取 Fernet 加密实例"""
        if self._cipher is None:
            key = self.config.security.get('encryption_key', '')
            if not key:
                raise ValueError("Encryption key not configured")
            self._cipher = Fernet(key.encode())
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
