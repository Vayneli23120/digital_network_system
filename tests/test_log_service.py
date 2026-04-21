"""
Tests for log_service.py
"""

import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime, timedelta

from app.services.log_service import LogService, get_log_service


@pytest.fixture
def temp_log_dir():
    """Create a temporary directory with test log files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir)

        # Create sample log files with Loguru-style content
        log_content_1 = """2026-04-20 10:00:00.000 | INFO     | app.main:startup_event:103 - Network Automation System v1.0.0 启动
2026-04-20 10:00:01.100 | DEBUG    | app.config:load_config:50 - Configuration loaded from config.yaml
2026-04-20 10:00:02.200 | WARNING  | app.services.netmiko_service:connect:45 - Connection timeout, retrying
2026-04-20 10:00:03.300 | ERROR    | app.services.backup_service:backup:80 - Backup failed for device SW-01
2026-04-20 10:00:04.400 | INFO     | app.routers.devices:create_device:150 - Device created: SW-Core-01
2026-04-20 10:00:05.500 | INFO     | app.services.deploy_service:deploy:200 - Deployment started on 3 devices
"""
        log_content_2 = """2026-04-19 08:00:00.000 | INFO     | app.main:startup_event:103 - Network Automation System v1.0.0 启动
2026-04-19 08:00:01.000 | ERROR    | app.services.discovery_service:discover:100 - Discovery failed: timeout
2026-04-19 08:00:02.000 | INFO     | app.routers.backups:backup_device:60 - Backup completed for SW-02
"""
        with open(log_dir / "app.log", "w", encoding="utf-8") as f:
            f.write(log_content_1)
        with open(log_dir / "app_20260419.log", "w", encoding="utf-8") as f:
            f.write(log_content_2)

        # Create a non-log file that should be ignored
        with open(log_dir / "readme.txt", "w") as f:
            f.write("This is not a log file")

        yield str(log_dir)


class TestGetLogFiles:
    def test_get_log_files(self, temp_log_dir):
        service = LogService(log_dir=temp_log_dir)
        result = service.get_log_files(days=7)
        assert len(result) == 2
        assert all(r["filename"].endswith(".log") for r in result)

    def test_get_log_files_by_days(self, temp_log_dir):
        service = LogService(log_dir=temp_log_dir)
        # Only recent logs (within 1 day)
        result = service.get_log_files(days=1)
        # The newer log should be included
        assert len(result) >= 1

    def test_get_log_files_empty(self, temp_log_dir):
        service = LogService(log_dir=temp_log_dir)
        result = service.get_log_files(days=7)
        assert isinstance(result, list)


class TestReadLogFile:
    def test_read_log_file_all_lines(self, temp_log_dir):
        service = LogService(log_dir=temp_log_dir)
        result = service.read_log_file("app.log", lines=100)
        assert len(result) == 6  # 6 log lines

    def test_read_log_file_limited_lines(self, temp_log_dir):
        service = LogService(log_dir=temp_log_dir)
        result = service.read_log_file("app.log", lines=3)
        assert len(result) <= 3

    def test_read_log_file_filter_by_level(self, temp_log_dir):
        service = LogService(log_dir=temp_log_dir)
        result = service.read_log_file("app.log", level="ERROR")
        assert all(r["level"] == "ERROR" for r in result)
        assert len(result) == 1

    def test_read_log_file_filter_by_level_info(self, temp_log_dir):
        service = LogService(log_dir=temp_log_dir)
        result = service.read_log_file("app.log", level="INFO")
        assert all(r["level"] == "INFO" for r in result)
        assert len(result) == 3

    def test_read_log_file_not_found(self, temp_log_dir):
        service = LogService(log_dir=temp_log_dir)
        result = service.read_log_file("nonexistent.log")
        assert result == []

    def test_read_log_file_parsed_fields(self, temp_log_dir):
        service = LogService(log_dir=temp_log_dir)
        result = service.read_log_file("app.log", lines=1)
        entry = result[0]
        assert "timestamp" in entry
        assert "level" in entry
        assert "message" in entry
        assert "模块" in entry["module"] or "app" in entry["module"]


class TestParseLogLine:
    def test_parse_loguru_format(self, temp_log_dir):
        service = LogService(log_dir=temp_log_dir)
        line = "2026-04-20 10:00:00.000 | INFO     | app.main:startup_event:103 - System started"
        result = service._parse_log_line(line)
        assert result["timestamp"] == "2026-04-20 10:00:00.000"
        assert result["level"] == "INFO"
        assert result["module"] == "app.main"
        assert result["function"] == "startup_event"
        assert result["line"] == 103
        assert result["message"] == "System started"

    def test_parse_empty_line(self, temp_log_dir):
        service = LogService(log_dir=temp_log_dir)
        result = service._parse_log_line("")
        assert result is None

    def test_parse_unparseable_line(self, temp_log_dir):
        service = LogService(log_dir=temp_log_dir)
        result = service._parse_log_line("This is just plain text")
        assert result is not None
        assert result["level"] == "RAW"
        assert result["message"] == "This is just plain text"


class TestSearchLogs:
    def test_search_by_keyword(self, temp_log_dir):
        service = LogService(log_dir=temp_log_dir)
        result = service.search_logs("Backup", days=7)
        assert len(result) >= 2  # At least 2 lines contain "Backup"

    def test_search_case_insensitive(self, temp_log_dir):
        service = LogService(log_dir=temp_log_dir)
        result_lower = service.search_logs("backup", days=7)
        result_upper = service.search_logs("BACKUP", days=7)
        assert len(result_lower) == len(result_upper)

    def test_search_with_level_filter(self, temp_log_dir):
        service = LogService(log_dir=temp_log_dir)
        result = service.search_logs("started", level="INFO")
        assert all(r["level"] == "INFO" for r in result)

    def test_search_no_results(self, temp_log_dir):
        service = LogService(log_dir=temp_log_dir)
        result = service.search_logs("NONEXISTENT_KEYWORD_XYZ")
        assert result == []


class TestGetLatestLogs:
    def test_get_latest_logs(self, temp_log_dir):
        service = LogService(log_dir=temp_log_dir)
        result = service.get_latest_logs(count=10)
        assert isinstance(result, list)
        # Sorted by timestamp descending
        if len(result) >= 2:
            assert result[0]["timestamp"] >= result[-1]["timestamp"]

    def test_get_latest_logs_with_level_filter(self, temp_log_dir):
        service = LogService(log_dir=temp_log_dir)
        result = service.get_latest_logs(count=10, level="ERROR")
        assert all(r["level"] == "ERROR" for r in result)


class TestClearOldLogs:
    def test_clear_old_logs_recent(self, temp_log_dir):
        service = LogService(log_dir=temp_log_dir)
        # Logs are fresh (just created), shouldn't be cleared
        cleared = service.clear_old_logs(days=30)
        assert cleared == 0


class TestGetLogService:
    def test_get_log_service_singleton(self):
        # Reset global state
        import app.services.log_service as log_module
        log_module._log_service = None

        service1 = get_log_service()
        service2 = get_log_service()
        assert service1 is service2
        assert isinstance(service1, LogService)

        # Reset after test
        log_module._log_service = None
