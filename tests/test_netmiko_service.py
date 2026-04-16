"""
Tests for Netmiko SSH service

These tests mock the actual SSH connections to avoid requiring
real network devices during testing.
"""

import pytest
from unittest.mock import patch, MagicMock
from app.models import Device


class MockConnectHandler:
    """Mock Netmiko ConnectHandler for testing"""

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self._connected = True
        self._config = """!
hostname Test-Switch
!
interface GigabitEthernet0/1
 description Test Port
!
end
"""

    def enable(self):
        pass

    def send_command(self, command):
        if "show running-config" in command or "show running" in command:
            return self._config
        elif "show version" in command:
            return """Cisco IOS Software, Version 15.2
System returned to ROM by power-on
Processor board ID: FCW1234A5BC
"""
        return ""

    def send_config_set(self, commands):
        return "config term\n" + "\n".join(str(c) for c in commands) + "\nend\n"

    def save_config(self):
        return "Building configuration...\n[OK]"

    def disconnect(self):
        self._connected = False


@pytest.fixture
def netmiko_service():
    """Create a NetmikoService instance with mocked connection"""
    with patch("app.services.netmiko_service.ConnectHandler", MockConnectHandler):
        from app.services.netmiko_service import NetmikoService
        service = NetmikoService()
        yield service


@pytest.fixture
def sample_device():
    """Create a sample device for testing"""
    return MagicMock(spec=Device)


class TestNetmikoServiceConnect:
    """Test Netmiko connection functionality"""

    def test_connect_success(self, netmiko_service, sample_device):
        """Test successful connection to a device"""
        sample_device.ip = "192.168.1.1"
        sample_device.name = "Test-SW-01"

        credentials = {
            "username": "admin",
            "password": "secret",
            "secret": "enable_secret"
        }

        conn = netmiko_service.connect(sample_device, credentials)

        assert conn is not None
        assert netmiko_service.connection is not None

    def test_get_device_params(self, netmiko_service, sample_device):
        """Test device parameter construction"""
        sample_device.ip = "192.168.1.1"
        sample_device.name = "Test-SW-01"

        credentials = {"username": "admin", "password": "secret", "secret": "enable"}

        params = netmiko_service.get_device_params(sample_device, credentials)

        assert params["device_type"] == "cisco_ios"
        assert params["host"] == "192.168.1.1"
        assert params["username"] == "admin"
        assert params["password"] == "secret"
        assert params["secret"] == "enable"

    def test_disconnect(self, netmiko_service, sample_device):
        """Test disconnecting from a device"""
        sample_device.ip = "192.168.1.1"
        sample_device.name = "Test-SW-01"

        credentials = {"username": "admin", "password": "secret"}
        netmiko_service.connect(sample_device, credentials)
        netmiko_service.disconnect()

        assert netmiko_service.connection is None


class TestNetmikoServiceGetConfig:
    """Test getting configuration from devices"""

    def test_get_running_config(self, netmiko_service, sample_device):
        """Test retrieving running configuration"""
        sample_device.ip = "192.168.1.1"
        sample_device.name = "Test-SW-01"

        credentials = {"username": "admin", "password": "secret"}
        netmiko_service.connect(sample_device, credentials)

        config = netmiko_service.get_running_config()

        assert "hostname Test-Switch" in config
        assert "interface GigabitEthernet0/1" in config

    def test_get_running_config_not_connected(self, netmiko_service):
        """Test getting config without connection raises error"""
        with pytest.raises(RuntimeError) as exc_info:
            netmiko_service.get_running_config()

        assert "未连接到设备" in str(exc_info.value)


class TestNetmikoServiceSaveConfig:
    """Test saving configuration on devices"""

    def test_save_config(self, netmiko_service, sample_device):
        """Test saving configuration (write memory)"""
        sample_device.ip = "192.168.1.1"
        sample_device.name = "Test-SW-01"

        credentials = {"username": "admin", "password": "secret"}
        netmiko_service.connect(sample_device, credentials)

        result = netmiko_service.save_config()

        assert "[OK]" in result

    def test_save_config_not_connected(self, netmiko_service):
        """Test saving config without connection raises error"""
        with pytest.raises(RuntimeError) as exc_info:
            netmiko_service.save_config()

        assert "未连接到设备" in str(exc_info.value)


class TestBackupDeviceConfig:
    """Test the backup_device_config function"""

    def test_backup_device_config_success(self, sample_device):
        """Test successful device configuration backup"""
        from app.services.netmiko_service import backup_device_config

        sample_device.ip = "192.168.1.1"
        sample_device.name = "Test-SW-01"
        sample_device.device_type = "cisco_ios"

        credentials = {"username": "admin", "password": "secret"}

        with patch("app.services.netmiko_service.ConnectHandler", MockConnectHandler):
            result = backup_device_config(sample_device, credentials, "./backups")

            assert result["success"] is True
            assert "file_path" in result
            assert "file_size" in result
            assert "md5_hash" in result

    def test_backup_device_config_connection_failure(self, sample_device):
        """Test backup failure due to connection error"""
        from app.services.netmiko_service import backup_device_config
        from netmiko import NetmikoTimeoutException

        sample_device.ip = "192.168.1.1"
        sample_device.name = "Test-SW-01"

        credentials = {"username": "admin", "password": "wrong_password"}

        def mock_connect_failure(**kwargs):
            raise NetmikoTimeoutException("Connection timed out")

        with patch("app.services.netmiko_service.ConnectHandler", mock_connect_failure):
            result = backup_device_config(sample_device, credentials, "./backups")

            assert result["success"] is False
            assert "timed out" in result["message"].lower() or "timeout" in result["message"].lower()


class TestNetmikoServiceMultiDevice:
    """Test handling multiple devices"""

    def test_connect_multiple_devices_sequential(self, netmiko_service):
        """Test connecting to multiple devices sequentially"""
        devices = []
        for i in range(3):
            device = MagicMock(spec=Device)
            device.ip = f"192.168.1.{i+1}"
            device.name = f"SW-0{i+1}"
            devices.append(device)

        credentials = {"username": "admin", "password": "secret"}

        for device in devices:
            conn = netmiko_service.connect(device, credentials)
            assert conn is not None
            netmiko_service.disconnect()

        assert netmiko_service.connection is None
