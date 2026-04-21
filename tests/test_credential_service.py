"""
Tests for the credential (encryption) service

These tests verify the Fernet-based password encryption/decryption logic.
"""

import pytest
from unittest.mock import patch, MagicMock
from cryptography.fernet import Fernet
from app.services.credential_service import (
    CredentialService,
    get_credential_service,
    encrypt_password,
    decrypt_password,
)


class TestCredentialServiceEncryption:
    """Test encryption/decryption round-trip"""

    def test_encrypt_decrypt_roundtrip(self):
        """Test that encrypted password can be decrypted back"""
        key = Fernet.generate_key().decode()
        service = CredentialService()

        # Patch config to return our test key
        mock_config = MagicMock()
        mock_config.security = {"encryption_key": key}

        with patch("app.services.credential_service.get_config", return_value=mock_config):
            service = CredentialService()
            original = "MyS3cretP@ssw0rd!"
            encrypted = service.encrypt_password(original)
            decrypted = service.decrypt_password(encrypted)

            assert decrypted == original
            assert encrypted != original

    def test_encrypt_produces_different_ciphertext(self):
        """Test that each encryption produces different ciphertext (Fernet property)"""
        key = Fernet.generate_key().decode()
        mock_config = MagicMock()
        mock_config.security = {"encryption_key": key}

        with patch("app.services.credential_service.get_config", return_value=mock_config):
            service = CredentialService()
            original = "same_password"

            enc1 = service.encrypt_password(original)
            enc2 = service.encrypt_password(original)

            # Fernet includes random IV, so ciphertext differs each time
            assert enc1 != enc2
            # But both decrypt to the same value
            assert service.decrypt_password(enc1) == original
            assert service.decrypt_password(enc2) == original

    def test_encrypt_empty_password(self):
        """Test encryption of empty string"""
        key = Fernet.generate_key().decode()
        mock_config = MagicMock()
        mock_config.security = {"encryption_key": key}

        with patch("app.services.credential_service.get_config", return_value=mock_config):
            service = CredentialService()
            encrypted = service.encrypt_password("")
            decrypted = service.decrypt_password(encrypted)
            assert decrypted == ""

    def test_encrypt_unicode_password(self):
        """Test encryption of unicode passwords"""
        key = Fernet.generate_key().decode()
        mock_config = MagicMock()
        mock_config.security = {"encryption_key": key}

        with patch("app.services.credential_service.get_config", return_value=mock_config):
            service = CredentialService()
            original = "密码测试🔒"
            encrypted = service.encrypt_password(original)
            decrypted = service.decrypt_password(encrypted)
            assert decrypted == original

    def test_encrypt_long_password(self):
        """Test encryption of long passwords"""
        key = Fernet.generate_key().decode()
        mock_config = MagicMock()
        mock_config.security = {"encryption_key": key}

        with patch("app.services.credential_service.get_config", return_value=mock_config):
            service = CredentialService()
            original = "A" * 1000
            encrypted = service.encrypt_password(original)
            decrypted = service.decrypt_password(encrypted)
            assert decrypted == original


class TestCredentialServiceDecryption:
    """Test decryption error handling"""

    def test_decrypt_invalid_token(self):
        """Test decryption of invalid/ tampered token"""
        key = Fernet.generate_key().decode()
        mock_config = MagicMock()
        mock_config.security = {"encryption_key": key}

        with patch("app.services.credential_service.get_config", return_value=mock_config):
            service = CredentialService()

            with pytest.raises(Exception):  # Fernet raises InvalidToken
                service.decrypt_password("invalid-token-data")

    def test_decrypt_with_wrong_key(self):
        """Test decryption with a different key fails"""
        key1 = Fernet.generate_key().decode()
        key2 = Fernet.generate_key().decode()

        mock_config1 = MagicMock()
        mock_config1.security = {"encryption_key": key1}

        mock_config2 = MagicMock()
        mock_config2.security = {"encryption_key": key2}

        with patch("app.services.credential_service.get_config", return_value=mock_config1):
            service1 = CredentialService()
            encrypted = service1.encrypt_password("secret")

        with patch("app.services.credential_service.get_config", return_value=mock_config2):
            service2 = CredentialService()
            with pytest.raises(Exception):
                service2.decrypt_password(encrypted)


class TestCredentialServiceConfig:
    """Test configuration error handling"""

    def test_missing_encryption_key(self):
        """Test error when encryption key is not configured"""
        mock_config = MagicMock()
        mock_config.security = {"encryption_key": ""}

        with patch("app.services.credential_service.get_config", return_value=mock_config):
            service = CredentialService()

            with pytest.raises(ValueError, match="Encryption key not configured"):
                service.encrypt_password("test")


class TestCredentialServiceSingleton:
    """Test the singleton pattern"""

    def test_get_credential_service_returns_instance(self):
        """Test that get_credential_service returns a CredentialService instance"""
        import app.services.credential_service as mod
        mod._credential_service = None  # reset

        key = Fernet.generate_key().decode()
        mock_config = MagicMock()
        mock_config.security = {"encryption_key": key}

        with patch("app.services.credential_service.get_config", return_value=mock_config):
            service = get_credential_service()
            assert isinstance(service, CredentialService)

    def test_get_credential_service_returns_same_instance(self):
        """Test that repeated calls return the same instance"""
        import app.services.credential_service as mod
        mod._credential_service = None

        key = Fernet.generate_key().decode()
        mock_config = MagicMock()
        mock_config.security = {"encryption_key": key}

        with patch("app.services.credential_service.get_config", return_value=mock_config):
            s1 = get_credential_service()
            s2 = get_credential_service()
            assert s1 is s2


class TestConvenienceFunctions:
    """Test the module-level convenience functions"""

    def test_encrypt_password_function(self):
        """Test the encrypt_password convenience function"""
        key = Fernet.generate_key().decode()
        mock_config = MagicMock()
        mock_config.security = {"encryption_key": key}

        import app.services.credential_service as mod
        mod._credential_service = None

        with patch("app.services.credential_service.get_config", return_value=mock_config):
            result = encrypt_password("test123")
            assert isinstance(result, str)
            assert result != "test123"

    def test_decrypt_password_function(self):
        """Test the decrypt_password convenience function"""
        key = Fernet.generate_key().decode()
        mock_config = MagicMock()
        mock_config.security = {"encryption_key": key}

        import app.services.credential_service as mod
        mod._credential_service = None

        with patch("app.services.credential_service.get_config", return_value=mock_config):
            encrypted = encrypt_password("test456")
            decrypted = decrypt_password(encrypted)
            assert decrypted == "test456"
