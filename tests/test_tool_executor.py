"""
Tests for the unified tool executor

These tests verify the tool executor's ability to orchestrate netmiko, napalm, and jira calls.
"""

import pytest
from unittest.mock import patch, MagicMock
from app.features.tool_logs.tool_executor import ToolExecutor


@pytest.fixture
def executor():
    """Create a ToolExecutor instance for testing"""
    return ToolExecutor()


@pytest.fixture
def use_test_db(monkeypatch, db_manager):
    """让 get_db_manager() 命中测试库。

    批次三把 tool_executor 从 app/services/ 移到 app/features/tool_logs/ 并改用
    get_db_manager().session_scope()（不再有模块级 get_db），因此旧测试里
    patch("app.services.tool_executor.get_db") / patch("...LogEntry") 全部失效。
    这里沿用 tests/test_batch1_regressions.py 的既有模式：直接替换 database 模块的
    _db_manager 单例指向测试库，LogEntry 用真实模型落库。
    """
    import app.shared.database as database_module

    monkeypatch.setattr(database_module, "_db_manager", db_manager)
    return db_manager


class TestToolExecutorCallbacks:
    """Test callback registration"""

    def test_register_callback(self, executor):
        """Test registering a log callback"""
        callback = MagicMock()
        executor.register_callback(callback)
        assert len(executor._callbacks) == 1
        assert executor._callbacks[0] == callback

    def test_register_multiple_callbacks(self, executor):
        """Test registering multiple callbacks"""
        cb1 = MagicMock()
        cb2 = MagicMock()
        executor.register_callback(cb1)
        executor.register_callback(cb2)
        assert len(executor._callbacks) == 2


class TestToolExecutorNetmiko:
    """Test netmiko command execution"""

    @pytest.mark.asyncio
    async def test_execute_netmiko_success(self, executor, use_test_db):
        """Test successful netmiko command execution"""
        mock_conn = MagicMock()
        mock_conn.send_command.return_value = "interface GigabitEthernet0/1\n  up\n"

        device = {
            "ip": "192.168.1.1",
            "username": "admin",
            "password": "secret",
            "device_type": "cisco_ios",
        }
        commands = ["show interface Gi0/1"]

        with patch("netmiko.ConnectHandler", return_value=mock_conn):
            result = await executor.execute_netmiko(device, commands)

            assert result["success"] is True
            assert "up" in result["output"]
            assert "duration_ms" in result
            mock_conn.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_netmiko_timeout(self, executor, use_test_db):
        """Test netmiko connection timeout"""
        from netmiko.exceptions import NetmikoTimeoutException

        device = {
            "ip": "192.168.1.1",
            "username": "admin",
            "password": "secret",
            "device_type": "cisco_ios",
        }

        with patch("netmiko.ConnectHandler", side_effect=NetmikoTimeoutException("Timeout")):
            result = await executor.execute_netmiko(device, ["show version"])

            assert result["success"] is False
            assert "error" in result
            assert "duration_ms" in result

    @pytest.mark.asyncio
    async def test_execute_netmiko_auth_failure(self, executor, use_test_db):
        """Test netmiko authentication failure"""
        from netmiko.exceptions import NetmikoAuthenticationException

        device = {
            "ip": "192.168.1.1",
            "username": "admin",
            "password": "wrong",
            "device_type": "cisco_ios",
        }

        with patch("netmiko.ConnectHandler", side_effect=NetmikoAuthenticationException("Auth failed")):
            result = await executor.execute_netmiko(device, ["show version"])

            assert result["success"] is False
            assert "Auth failed" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_netmiko_multiple_commands(self, executor, use_test_db):
        """Test executing multiple commands"""
        mock_conn = MagicMock()
        mock_conn.send_command.side_effect = [
            "hostname SW-Core-01",
            "Interface      Status\nGi0/1          up\nGi0/2          down",
        ]

        device = {"ip": "192.168.1.1", "device_type": "cisco_ios"}
        commands = ["show run | include hostname", "show interface status"]

        with patch("netmiko.ConnectHandler", return_value=mock_conn):
            result = await executor.execute_netmiko(device, commands)

            assert result["success"] is True
            assert "SW-Core-01" in result["output"]
            assert mock_conn.send_command.call_count == 2


class TestToolExecutorNapalm:
    """Test NAPALM execution"""

    @pytest.mark.asyncio
    async def test_execute_napalm_success(self, executor, use_test_db):
        """Test successful NAPALM method call"""
        mock_driver_instance = MagicMock()
        mock_driver_instance.get_facts.return_value = {
            "hostname": "SW-Core-01",
            "vendor": "Cisco",
            "model": "C9300",
        }

        # 执行器调用链：get_network_driver("ios") -> driver 类 -> driver(**device) -> 实例
        mock_driver_cls = MagicMock()
        mock_driver_cls.return_value = mock_driver_instance

        device = {"hostname": "192.168.1.1", "username": "admin", "password": "secret"}

        with patch("napalm.get_network_driver", return_value=mock_driver_cls):
            result = await executor.execute_napalm(
                device, "get_facts", operation="Get device facts"
            )

            assert result["success"] is True
            assert result["result"]["hostname"] == "SW-Core-01"
            mock_driver_instance.open.assert_called_once()
            mock_driver_instance.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_napalm_method_not_found(self, executor, use_test_db):
        """Test NAPALM with invalid method name"""
        # 必须用真实 stub 而非 MagicMock：MagicMock 的 getattr 会为任意属性
        # 自动生成子 mock，导致 getattr(instance, method, None) 永远非 None。
        class _NapalmStub:
            def open(self):
                pass

            def close(self):
                pass

        stub = _NapalmStub()
        mock_driver_cls = MagicMock()
        mock_driver_cls.return_value = stub

        device = {"hostname": "192.168.1.1", "username": "admin", "password": "secret"}

        with patch("napalm.get_network_driver", return_value=mock_driver_cls):
            result = await executor.execute_napalm(
                device, "nonexistent_method", operation="Invalid call"
            )

            assert result["success"] is False
            assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_napalm_not_installed(self, executor):
        """Test NAPALM when napalm is not installed"""
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "napalm":
                raise ImportError("No module named 'napalm'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            result = await executor.execute_napalm(
                {"hostname": "192.168.1.1"}, "get_facts"
            )

        assert result["success"] is False
        assert "napalm not installed" in result["error"]


class TestToolExecutorJira:
    """Test JIRA execution"""

    @pytest.mark.asyncio
    async def test_execute_jira_create_issue(self, executor, use_test_db):
        """Test creating a JIRA issue"""
        mock_issue = MagicMock()
        mock_issue.key = "NAS-123"

        mock_jira = MagicMock()
        mock_jira.create_issue.return_value = mock_issue

        issue_data = {
            "fields": {
                "project": {"key": "NAS"},
                "summary": "Test issue",
                "issuetype": {"name": "Task"},
            }
        }

        mock_settings = MagicMock()
        mock_settings.jira_server = "https://jira.test.com"
        mock_settings.jira_username = "admin"
        mock_settings.jira_password = "secret"

        with patch("app.config.settings", mock_settings):
            with patch("jira.JIRA", return_value=mock_jira):
                result = await executor.execute_jira(
                    "create", issue_data, operation="Create test issue"
                )

                assert result["success"] is True
                assert result["issue_key"] == "NAS-123"
                mock_jira.create_issue.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_jira_update_issue(self, executor, use_test_db):
        """Test updating a JIRA issue"""
        mock_issue = MagicMock()
        mock_issue.key = "NAS-123"

        mock_jira = MagicMock()
        mock_jira.issue.return_value = mock_issue

        issue_data = {
            "key": "NAS-123",
            "fields": {"summary": "Updated summary"},
        }

        mock_settings = MagicMock()
        mock_settings.jira_server = "https://jira.test.com"
        mock_settings.jira_username = "admin"
        mock_settings.jira_password = "secret"

        with patch("app.config.settings", mock_settings):
            with patch("jira.JIRA", return_value=mock_jira):
                result = await executor.execute_jira(
                    "update", issue_data, operation="Update test issue"
                )

                assert result["success"] is True
                assert result["issue_key"] == "NAS-123"

    @pytest.mark.asyncio
    async def test_execute_jira_unknown_action(self, executor, use_test_db):
        """Test JIRA with unknown action"""
        mock_settings = MagicMock()
        mock_settings.jira_server = "https://jira.test.com"
        mock_settings.jira_username = "admin"
        mock_settings.jira_password = "secret"

        with patch("app.config.settings", mock_settings):
            with patch("jira.JIRA") as mock_jira_cls:
                mock_jira = MagicMock()
                mock_jira_cls.return_value = mock_jira
                result = await executor.execute_jira(
                    "delete", {}, operation="Invalid action"
                )

                assert result["success"] is False
                assert "Unknown JIRA action" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_jira_not_installed(self, executor):
        """Test JIRA when jira package is not installed"""
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "jira":
                raise ImportError("No module named 'jira'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            result = await executor.execute_jira("create", {})

        assert result["success"] is False
        assert "not installed" in result["error"]


class TestToolExecutorGlobalInstance:
    """Test the global tool_executor instance"""

    def test_global_instance_exists(self):
        """Test that the global tool_executor instance exists"""
        from app.features.tool_logs.tool_executor import tool_executor
        assert isinstance(tool_executor, ToolExecutor)
