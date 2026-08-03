"""
对称加密统一入口（Fernet）

密钥派生：PBKDF2HMAC(SHA256, length=32, salt=b"nas-salt", iterations=100000)，
材料优先取 `security.encryption_key`（ENCRYPTION_KEY 环境变量），未配置时回退
`security.jwt_secret` —— 与历史 `credential_service` 的派生完全一致，保证旧密文
可解。`encryption_key` 独立后，轮换 JWT_SECRET 不再破坏已存凭证/AI Key 密文。

decrypt 侧做两段尝试：先用当前 cipher（encryption_key 优先），失败且配置了
encryption_key 时回退 legacy cipher（jwt_secret 派生），以兼容 JWT 时代写入的密文。
"""

import base64
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.shared.config import get_config


def _derive_fernet(material: str) -> Fernet:
    if not material:
        raise ValueError("Encryption key not configured")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"nas-salt",
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(material.encode()))
    return Fernet(key)


def _resolve_material(config) -> str:
    """选择密钥材料：encryption_key 优先，未配置（None/非字符串）回退 jwt_secret"""
    enc_key = config.security.encryption_key
    if isinstance(enc_key, str) and enc_key:
        return enc_key
    return config.security.jwt_secret


def get_cipher(config=None) -> Fernet:
    """当前加密 cipher：encryption_key 优先，未配置时回退 jwt_secret

    config 可显式传入（如测试 mock / 调用方已持有的实例）；默认取全局配置。
    """
    cfg = config if config is not None else get_config()
    return _derive_fernet(_resolve_material(cfg))


def get_legacy_cipher(config=None) -> Fernet:
    """legacy cipher：恒用 jwt_secret 派生，用于解密 JWT 时代写入的旧密文"""
    cfg = config if config is not None else get_config()
    return _derive_fernet(cfg.security.jwt_secret)


def encrypt_text(plain: str, config=None) -> str:
    """加密为 Fernet token 字符串"""
    return get_cipher(config).encrypt(plain.encode()).decode()


def decrypt_text(token: str, config=None) -> str:
    """解密 Fernet token；新 cipher 失败且配置了 encryption_key 时回退 legacy cipher"""
    try:
        return get_cipher(config).decrypt(token.encode()).decode()
    except InvalidToken:
        cfg = config if config is not None else get_config()
        if isinstance(cfg.security.encryption_key, str) and cfg.security.encryption_key:
            return get_legacy_cipher(config).decrypt(token.encode()).decode()
        raise


def decrypt_or_passthrough(token: str, config=None) -> str:
    """解密；若 token 不是 Fernet 密文（如历史遗留的明文 AI Key）则原样返回"""
    try:
        return decrypt_text(token, config)
    except (InvalidToken, ValueError):
        return token
