"""
Tests for connection_monitor.py
"""
from unittest.mock import patch

from app.services.connection_monitor import (
    WARN_THRESHOLD,
    CRITICAL_THRESHOLD,
    _format_rows,
    run_connection_check,
)


class TestFormatRows:
    def test_format_rows(self):
        rows = [
            (123, 45, "SELECT * FROM devices", "backend", "10.0.0.1"),
            (456, 120, "UPDATE faults SET status='x'", "", ""),
        ]
        text = _format_rows(rows)
        assert "pid=123" in text
        assert "持有时长=45s" in text
        assert "SELECT * FROM devices" in text
        assert "pid=456" in text
        assert "持有时长=120s" in text


def _fake_rows(n):
    return [(i, 10, f"query {i}", "app", "") for i in range(n)]


class TestRunConnectionCheck:
    def test_no_leak_does_not_notify(self):
        with patch("app.services.connection_monitor._idle_in_transaction_rows", return_value=[]), \
             patch("app.services.connection_monitor._notify_admin") as mock_notify:
            run_connection_check()
        mock_notify.assert_not_called()

    def test_warn_threshold_does_not_notify(self):
        with patch("app.services.connection_monitor._idle_in_transaction_rows",
                   return_value=_fake_rows(WARN_THRESHOLD)), \
             patch("app.services.connection_monitor._notify_admin") as mock_notify:
            run_connection_check()
        mock_notify.assert_not_called()

    def test_critical_threshold_notifies_admin(self):
        with patch("app.services.connection_monitor._idle_in_transaction_rows",
                   return_value=_fake_rows(CRITICAL_THRESHOLD)), \
             patch("app.services.connection_monitor._notify_admin") as mock_notify:
            run_connection_check()
        mock_notify.assert_called_once()

    def test_query_failure_is_silent(self):
        with patch("app.services.connection_monitor._idle_in_transaction_rows",
                   side_effect=Exception("pg down")), \
             patch("app.services.connection_monitor._notify_admin") as mock_notify:
            run_connection_check()
        mock_notify.assert_not_called()
