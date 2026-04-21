"""
Tests for the console serial service

These tests verify the console port management and command sending logic
without requiring actual serial hardware.
"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from app.services.console_service import ConsoleService, find_console_port


class TestConsoleServiceListPorts:
    """Test the list_ports method"""

    def test_list_ports_returns_available_ports(self):
        """Test that list_ports returns detected serial ports"""
        service = ConsoleService()

        mock_ports = [
            MagicMock(device="COM3", description="USB Serial Device", hwid="USB VID:PID=0403:6001"),
            MagicMock(device="COM4", description="Standard Serial Port", hwid="ACPI\\PNP0501"),
        ]

        with patch("app.services.console_service.list_ports.comports", return_value=mock_ports):
            ports = service.list_ports()
            assert len(ports) == 2
            assert ports[0]["device"] == "COM3"
            assert ports[1]["device"] == "COM4"

    def test_list_ports_empty(self):
        """Test that list_ports returns empty list when no ports found"""
        service = ConsoleService()

        with patch("app.services.console_service.list_ports.comports", return_value=[]):
            ports = service.list_ports()
            assert ports == []


class TestConsoleServiceConnect:
    """Test the connect method"""

    def test_connect_success(self):
        """Test successful serial connection"""
        service = ConsoleService()

        mock_serial = MagicMock()
        mock_config = MagicMock()
        mock_config.console.bytesize = 8
        mock_config.console.parity = "N"
        mock_config.console.stopbits = 1

        with patch("app.services.console_service.get_config", return_value=mock_config):
            with patch("app.services.console_service.serial.Serial", return_value=mock_serial) as mock_serial_cls:
                result = service.connect("COM3", baudrate=9600)

                assert result is True
                assert service.port == "COM3"
                mock_serial_cls.assert_called_once()

    def test_connect_failure(self):
        """Test connection failure"""
        service = ConsoleService()

        mock_config = MagicMock()
        mock_config.console.bytesize = 8
        mock_config.console.parity = "N"
        mock_config.console.stopbits = 1

        from serial import SerialException

        with patch("app.services.console_service.get_config", return_value=mock_config):
            with patch("app.services.console_service.serial.Serial", side_effect=SerialException("Port not found")):
                result = service.connect("COM99")
                assert result is False


class TestConsoleServiceDisconnect:
    """Test the disconnect method"""

    def test_disconnect_open_connection(self):
        """Test disconnecting an open connection"""
        service = ConsoleService()
        service.serial_conn = MagicMock()
        service.serial_conn.is_open = True
        service.port = "COM3"

        service.disconnect()

        service.serial_conn.close.assert_called_once()
        assert service.port is None

    def test_disconnect_no_connection(self):
        """Test disconnect when no connection exists"""
        service = ConsoleService()
        service.serial_conn = None
        service.port = None

        # Should not raise
        service.disconnect()
        assert service.port is None


class TestConsoleServiceSendCommand:
    """Test the send_command method"""

    def test_send_command_success(self):
        """Test sending a command and reading response"""
        service = ConsoleService()

        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.in_waiting = 0  # Will be checked in the while loop
        mock_serial.read.return_value = b"hostname Test-Switch\r\n"

        service.serial_conn = mock_serial
        service.port = "COM3"

        with patch("time.sleep"):
            # First call to in_waiting returns some data, then 0
            mock_serial.in_waiting = 20
            response = service.send_command("show run | include hostname")

            mock_serial.write.assert_called_once()
            mock_serial.reset_input_buffer.assert_called_once()

    def test_send_command_not_connected(self):
        """Test sending command without connection raises error"""
        service = ConsoleService()
        service.serial_conn = None

        with pytest.raises(RuntimeError, match="未连接到 Console 口"):
            service.send_command("show version")


class TestConsoleServiceConfigMode:
    """Test configuration mode methods"""

    def test_enter_config_mode(self):
        """Test entering configuration mode"""
        service = ConsoleService()
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.in_waiting = 0
        service.serial_conn = mock_serial

        with patch.object(service, "send_command", return_value=""):
            result = service.enter_config_mode()
            assert result is True

    def test_exit_config_mode(self):
        """Test exiting configuration mode"""
        service = ConsoleService()
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.in_waiting = 0
        service.serial_conn = mock_serial

        with patch.object(service, "send_command", return_value=""):
            result = service.exit_config_mode()
            assert result is True

    def test_save_config(self):
        """Test saving configuration"""
        service = ConsoleService()
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.in_waiting = 0
        service.serial_conn = mock_serial

        with patch.object(service, "send_command", return_value=""):
            result = service.save_config()
            assert result is True


class TestConsoleServiceDeployConfig:
    """Test the deploy_config method"""

    def test_deploy_config_success(self):
        """Test successful config deployment"""
        service = ConsoleService()
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.in_waiting = 0
        service.serial_conn = mock_serial

        commands = ["hostname SW-01", "interface Gi0/1", "description Test"]

        with patch.object(service, "enter_config_mode", return_value=True):
            with patch.object(service, "send_commands"):
                with patch.object(service, "exit_config_mode", return_value=True):
                    with patch.object(service, "save_config", return_value=True):
                        result = service.deploy_config(commands)

                        assert result["success"] is True
                        assert result["total_commands"] == 3
                        assert result["executed_commands"] == 3
                        assert result["errors"] == []

    def test_deploy_config_failure(self):
        """Test config deployment failure"""
        service = ConsoleService()
        mock_serial = MagicMock()
        mock_serial.is_open = True
        service.serial_conn = mock_serial

        commands = ["hostname SW-01"]

        with patch.object(service, "enter_config_mode", side_effect=Exception("Timeout")):
            result = service.deploy_config(commands)

            assert result["success"] is False
            assert len(result["errors"]) > 0


class TestFindConsolePort:
    """Test the find_console_port helper function"""

    def test_find_console_port_ftdi(self):
        """Test finding an FTDI-based console port"""
        mock_ports = [
            MagicMock(device="COM3", description="USB Serial Device (FTDI)", hwid="USB VID:PID=0403:6001"),
            MagicMock(device="COM4", description="Standard Serial Port", hwid="ACPI\\PNP0501"),
        ]

        with patch("app.services.console_service.list_ports.comports", return_value=mock_ports):
            port = find_console_port()
            assert port == "COM3"

    def test_find_console_port_cp210(self):
        """Test finding a CP210x-based console port"""
        mock_ports = [
            MagicMock(device="COM5", description="CP2102 USB to UART", hwid="USB VID:PID=10C4:EA60"),
        ]

        with patch("app.services.console_service.list_ports.comports", return_value=mock_ports):
            port = find_console_port()
            assert port == "COM5"

    def test_find_console_port_no_special_chip(self):
        """Test fallback to first available port when no special chip found"""
        mock_ports = [
            MagicMock(device="COM1", description="Standard Serial Port", hwid="ACPI\\PNP0501"),
        ]

        with patch("app.services.console_service.list_ports.comports", return_value=mock_ports):
            port = find_console_port()
            assert port == "COM1"

    def test_find_console_port_no_ports(self):
        """Test returning None when no ports available"""
        with patch("app.services.console_service.list_ports.comports", return_value=[]):
            port = find_console_port()
            assert port is None
