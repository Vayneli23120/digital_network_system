"""批次二·安全 切片 B · 共享加密模块（item 125）

覆盖：
- ENCRYPTION_KEY 环境变量映射到 SecurityConfig.encryption_key
- encrypt/decrypt 往返
- legacy 兼容：jwt_secret 时代密文在配置 encryption_key 后仍可解密
- decrypt_or_passthrough 对非 Fernet 明文原样返回（兼容历史明文 AI Key）
"""

import pytest

import app.shared.config as config_module


@pytest.fixture
def crypto_config(monkeypatch):
    """返回 config 单例，供 monkeypatch encryption_key / jwt_secret"""
    from app.shared.config import get_config

    config = get_config()
    monkeypatch.setattr(config.security, "encryption_key", None)
    monkeypatch.setattr(config.security, "jwt_secret", "legacy-secret-for-tests")
    return config


def test_encryption_key_env_sets_config(monkeypatch):
    monkeypatch.setenv("ENCRYPTION_KEY", "env-derived-enc-key")
    config = config_module.Config()
    config._apply_security_env_overrides()
    assert config.security.encryption_key == "env-derived-enc-key"


def test_roundtrip_with_encryption_key(crypto_config, monkeypatch):
    from app.shared.crypto import decrypt_text, encrypt_text

    monkeypatch.setattr(crypto_config.security, "encryption_key", "new-enc-key-123")
    token = encrypt_text("cisco-secret")
    assert token != "cisco-secret"
    assert decrypt_text(token) == "cisco-secret"


def test_legacy_ciphertext_decrypts_after_rotation(crypto_config, monkeypatch):
    """jwt_secret 时代写入的密文，配置 encryption_key 后仍能解密（回退 legacy key）"""
    from app.shared.crypto import decrypt_text, encrypt_text

    # 1) 无 encryption_key：加密材料 = jwt_secret → 产生 legacy 密文
    legacy_token = encrypt_text("old-password")

    # 2) 引入 encryption_key（模拟轮换密钥）：新密文用新 key，旧密文回退 legacy
    monkeypatch.setattr(crypto_config.security, "encryption_key", "rotated-enc-key")
    assert decrypt_text(legacy_token) == "old-password"

    new_token = encrypt_text("new-password")
    assert decrypt_text(new_token) == "new-password"
    assert new_token != legacy_token


def test_decrypt_or_passthrough_returns_plaintext(crypto_config, monkeypatch):
    """非 Fernet 明文（历史明文 API Key 等）原样返回，不抛错"""
    from app.shared.crypto import decrypt_or_passthrough

    monkeypatch.setattr(crypto_config.security, "encryption_key", "new-enc-key-123")
    assert decrypt_or_passthrough("sk-legacy-plaintext") == "sk-legacy-plaintext"
    assert decrypt_or_passthrough("") == ""
