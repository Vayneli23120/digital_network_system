"""
Tests for the email alert service

These tests verify email sending logic without actually sending emails.
"""

import pytest
from unittest.mock import patch, MagicMock, call
from app.services.email_service import EmailAlertService, get_email_service, send_alert


class TestEmailAlertServiceSendEmail:
    """Test the send_email method"""

    def _create_mock_config(self, enabled=True, email_enabled=True):
        """Helper to create a mock config"""
        mock_config = MagicMock()
        mock_config.alerts.enabled = enabled
        mock_email_config = MagicMock()
        mock_email_config.enabled = email_enabled
        mock_email_config.smtp_host = "smtp.test.com"
        mock_email_config.smtp_port = 587
        mock_email_config.use_tls = True
        mock_email_config.username = "test@test.com"
        mock_email_config.password = "password"
        mock_email_config.from_addr = "nas@test.com"
        mock_email_config.recipients = ["admin@test.com"]
        mock_config.alerts.email = mock_email_config
        return mock_config

    def test_send_email_success(self):
        """Test successful email sending"""
        mock_config = self._create_mock_config()

        with patch("app.services.email_service.get_config", return_value=mock_config):
            service = EmailAlertService()

            with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
                mock_server = MagicMock()
                mock_smtp.return_value = mock_server

                result = service.send_email("Test Subject", "Test Body")

                assert result is True
                mock_smtp.assert_called_once_with("smtp.test.com", 587)
                mock_server.starttls.assert_called_once()
                mock_server.login.assert_called_once_with("test@test.com", "password")
                mock_server.sendmail.assert_called_once()
                mock_server.quit.assert_called_once()

    def test_send_email_without_tls(self):
        """Test email sending without TLS"""
        mock_config = self._create_mock_config()
        mock_config.alerts.email.use_tls = False

        with patch("app.services.email_service.get_config", return_value=mock_config):
            service = EmailAlertService()

            with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
                mock_server = MagicMock()
                mock_smtp.return_value = mock_server

                result = service.send_email("Test", "Body")

                assert result is True
                # starttls should NOT be called when use_tls is False
                mock_server.starttls.assert_not_called()

    def test_send_email_disabled_alerts(self):
        """Test sending email when alerts are disabled"""
        mock_config = self._create_mock_config(enabled=False)

        with patch("app.services.email_service.get_config", return_value=mock_config):
            service = EmailAlertService()
            result = service.send_email("Test", "Body")
            assert result is False

    def test_send_email_disabled_email_config(self):
        """Test sending email when email is disabled in config"""
        mock_config = self._create_mock_config(email_enabled=False)

        with patch("app.services.email_service.get_config", return_value=mock_config):
            service = EmailAlertService()
            result = service.send_email("Test", "Body")
            assert result is False

    def test_send_email_no_recipients(self):
        """Test sending email with no recipients"""
        mock_config = self._create_mock_config()
        mock_config.alerts.email.recipients = []

        with patch("app.services.email_service.get_config", return_value=mock_config):
            service = EmailAlertService()
            result = service.send_email("Test", "Body")
            assert result is False

    def test_send_email_custom_recipients(self):
        """Test sending email with custom recipients"""
        mock_config = self._create_mock_config()

        with patch("app.services.email_service.get_config", return_value=mock_config):
            service = EmailAlertService()

            with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
                mock_server = MagicMock()
                mock_smtp.return_value = mock_server

                result = service.send_email("Test", "Body", to_addresses=["custom@test.com"])

                assert result is True
                # Verify sendmail was called with the custom recipient
                call_args = mock_server.sendmail.call_args
                assert "custom@test.com" in str(call_args)

    def test_send_email_html_format(self):
        """Test sending email in HTML format"""
        mock_config = self._create_mock_config()

        with patch("app.services.email_service.get_config", return_value=mock_config):
            service = EmailAlertService()

            with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
                mock_server = MagicMock()
                mock_smtp.return_value = mock_server

                result = service.send_email("Test", "<h1>HTML</h1>", html=True)

                assert result is True
                mock_server.sendmail.assert_called_once()
                # Check that the HTML content was passed
                call_args = mock_server.sendmail.call_args
                assert "<h1>HTML</h1>" in call_args[0][2]

    def test_send_email_smtp_failure(self):
        """Test handling SMTP connection failure"""
        mock_config = self._create_mock_config()

        with patch("app.services.email_service.get_config", return_value=mock_config):
            service = EmailAlertService()

            with patch("app.services.email_service.smtplib.SMTP", side_effect=Exception("Connection refused")):
                result = service.send_email("Test", "Body")
                assert result is False


class TestEmailAlertServiceAlertMethods:
    """Test the specialized alert methods"""

    def _create_mock_config(self):
        mock_config = MagicMock()
        mock_config.alerts.enabled = True
        mock_email_config = MagicMock()
        mock_email_config.enabled = True
        mock_email_config.smtp_host = "smtp.test.com"
        mock_email_config.smtp_port = 587
        mock_email_config.use_tls = True
        mock_email_config.username = "test@test.com"
        mock_email_config.password = "password"
        mock_email_config.from_addr = "nas@test.com"
        mock_email_config.recipients = ["admin@test.com"]
        mock_config.alerts.email = mock_email_config
        return mock_config

    def test_send_backup_failure_alert(self):
        """Test backup failure alert email"""
        mock_config = self._create_mock_config()

        with patch("app.services.email_service.get_config", return_value=mock_config):
            service = EmailAlertService()

            with patch.object(service, "send_email", return_value=True) as mock_send:
                result = service.send_backup_failure_alert("SW-Core-01", "Connection timeout", "admin")

                assert result is True
                mock_send.assert_called_once()
                call_args = mock_send.call_args
                assert "备份失败" in call_args[0][0] or "Backup" in call_args[0][0] or "SW-Core-01" in call_args[0][0]

    def test_send_device_unreachable_alert(self):
        """Test device unreachable alert email"""
        mock_config = self._create_mock_config()

        with patch("app.services.email_service.get_config", return_value=mock_config):
            service = EmailAlertService()

            with patch.object(service, "send_email", return_value=True) as mock_send:
                result = service.send_device_unreachable_alert("SW-Core-01", "192.168.1.1")

                assert result is True
                call_args = mock_send.call_args
                assert "不可达" in call_args[0][0] or "192.168.1.1" in call_args[0][0]

    def test_send_config_change_alert(self):
        """Test config change alert email"""
        mock_config = self._create_mock_config()

        with patch("app.services.email_service.get_config", return_value=mock_config):
            service = EmailAlertService()

            with patch.object(service, "send_email", return_value=True) as mock_send:
                result = service.send_config_change_alert("SW-Core-01", "Changed hostname", "admin")

                assert result is True

    def test_send_fault_alert(self):
        """Test fault alert email"""
        mock_config = self._create_mock_config()

        with patch("app.services.email_service.get_config", return_value=mock_config):
            service = EmailAlertService()

            with patch.object(service, "send_email", return_value=True) as mock_send:
                result = service.send_fault_alert("SW-Core-01", "FAULT-001", "critical", "Device down")

                assert result is True
                call_args = mock_send.call_args
                subject = call_args[0][0]
                assert "严重" in subject or "critical" in subject.lower() or "FAULT" in subject


class TestEmailAlertServiceSingleton:
    """Test the singleton pattern"""

    def test_get_email_service_returns_instance(self):
        """Test get_email_service returns an EmailAlertService instance"""
        import app.services.email_service as mod
        mod._email_service = None

        mock_config = MagicMock()
        mock_config.alerts.enabled = True
        mock_email_config = MagicMock()
        mock_email_config.enabled = True
        mock_email_config.smtp_host = "smtp.test.com"
        mock_email_config.smtp_port = 587
        mock_email_config.use_tls = True
        mock_email_config.username = "test@test.com"
        mock_email_config.password = "password"
        mock_email_config.from_addr = "nas@test.com"
        mock_email_config.recipients = ["admin@test.com"]
        mock_config.alerts.email = mock_email_config

        with patch("app.services.email_service.get_config", return_value=mock_config):
            service = get_email_service()
            assert isinstance(service, EmailAlertService)

    def test_send_alert_function(self):
        """Test the send_alert convenience function"""
        import app.services.email_service as mod
        mod._email_service = None

        mock_config = MagicMock()
        mock_config.alerts.enabled = True
        mock_email_config = MagicMock()
        mock_email_config.enabled = True
        mock_email_config.smtp_host = "smtp.test.com"
        mock_email_config.smtp_port = 587
        mock_email_config.use_tls = True
        mock_email_config.username = "test@test.com"
        mock_email_config.password = "password"
        mock_email_config.from_addr = "nas@test.com"
        mock_email_config.recipients = ["admin@test.com"]
        mock_config.alerts.email = mock_email_config

        with patch("app.services.email_service.get_config", return_value=mock_config):
            with patch("app.services.email_service.smtplib.SMTP"):
                result = send_alert("Test", "Body")
                assert result is True
