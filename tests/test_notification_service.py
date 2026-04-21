"""
Tests for notification_service.py
"""

import pytest
from unittest.mock import MagicMock, patch

from app.services.notification_service import NotificationService, get_notification_service
from app.shared.config import get_config


class TestNotificationService:
    def test_get_channels_status(self, reset_config):
        service = NotificationService()
        status = service.get_channels_status()
        assert "enabled" in status
        assert "channels" in status
        assert "email" in status
        assert "wechat_work" in status
        assert "dingtalk" in status

    def test_notify_fault_critical(self, reset_config):
        """Critical faults should trigger notifications"""
        with patch.object(NotificationService, '_send_email', return_value=True), \
             patch.object(NotificationService, '_send_wechat', return_value=True), \
             patch.object(NotificationService, '_send_dingtalk', return_value=True):
            service = NotificationService()
            service.notify_fault("SW-01", "F-001", "critical", "Device down")
            # Should call all enabled channels for critical

    def test_notify_fault_warning_not_sent(self, reset_config):
        """Warning-level faults should NOT trigger notifications"""
        with patch.object(NotificationService, '_send_email') as mock_email, \
             patch.object(NotificationService, '_send_wechat') as mock_wechat, \
             patch.object(NotificationService, '_send_dingtalk') as mock_dingtalk:
            service = NotificationService()
            service.notify_fault("SW-01", "F-002", "warning", "Minor issue")
            mock_email.assert_not_called()
            mock_wechat.assert_not_called()
            mock_dingtalk.assert_not_called()

    def test_notify_backup_failure(self, reset_config):
        with patch.object(NotificationService, '_send_email', return_value=True), \
             patch.object(NotificationService, '_send_wechat', return_value=True), \
             patch.object(NotificationService, '_send_dingtalk', return_value=True):
            service = NotificationService()
            service.notify_backup_failure("SW-01", "Connection timeout", "admin")
            # Should notify all enabled channels


class TestWeChatWorkService:
    def test_send_text_disabled(self, reset_config):
        from app.services.wechat_work_service import WeChatWorkAlertService
        service = WeChatWorkAlertService()
        result = service.send_text("test")
        assert result is False  # alerts disabled by default

    def test_send_markdown_disabled(self, reset_config):
        from app.services.wechat_work_service import WeChatWorkAlertService
        service = WeChatWorkAlertService()
        result = service.send_markdown("test")
        assert result is False


class TestDingTalkService:
    def test_send_text_disabled(self, reset_config):
        from app.services.dingtalk_service import DingTalkAlertService
        service = DingTalkAlertService()
        result = service.send_text("test")
        assert result is False

    def test_get_signed_url_no_secret(self, reset_config):
        from app.services.dingtalk_service import DingTalkAlertService
        service = DingTalkAlertService()
        service.webhook_url = "https://test.webhook"
        service.secret = ""
        url = service._get_signed_url()
        assert url == "https://test.webhook"


class TestGetNotificationService:
    def test_singleton(self, reset_config):
        import app.services.notification_service as ns
        ns._notification_service = None
        s1 = get_notification_service()
        s2 = get_notification_service()
        assert s1 is s2
        ns._notification_service = None
