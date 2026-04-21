"""
Tests for the device discovery service

These tests verify the ping sweep, TCP scan, and device discovery logic
without requiring actual network connections.
"""

import socket
import pytest
from unittest.mock import patch, MagicMock
from app.services.discovery_service import (
    DiscoveryService,
    DiscoveredDevice,
    get_discovery_service,
    quick_discovery,
)


class TestDiscoveredDevice:
    """Test the DiscoveredDevice dataclass"""

    def test_discovered_device_defaults(self):
        """Test default field values"""
        device = DiscoveredDevice(ip="192.168.1.1")
        assert device.ip == "192.168.1.1"
        assert device.hostname is None
        assert device.model is None
        assert device.vendor == "Unknown"
        assert device.discovery_method == "ping"
        assert device.port == 22
        assert device.is_cisco is False
        assert device.cdp_neighbors == []

    def test_discovered_device_custom_values(self):
        """Test custom field values"""
        device = DiscoveredDevice(
            ip="10.0.0.1",
            hostname="SW-Core-01",
            model="C9300",
            vendor="Cisco",
            discovery_method="netmiko",
            is_cisco=True,
            cdp_neighbors=[{"device_id": "SW-Access-01"}],
        )
        assert device.hostname == "SW-Core-01"
        assert device.model == "C9300"
        assert device.vendor == "Cisco"
        assert device.is_cisco is True
        assert len(device.cdp_neighbors) == 1

    def test_discovered_device_cdp_neighbors_default(self):
        """Test that cdp_neighbors is initialized to empty list, not None"""
        device = DiscoveredDevice(ip="192.168.1.1", cdp_neighbors=None)
        assert device.cdp_neighbors == []


class TestDiscoveryServicePingHost:
    """Test the ping_host method"""

    def test_ping_host_open_port(self):
        """Test ping_host returns True when port 22 is open"""
        service = DiscoveryService(timeout=1.0)

        with patch("socket.socket") as mock_socket:
            mock_instance = MagicMock()
            mock_instance.connect_ex.return_value = 0
            mock_socket.return_value = mock_instance

            result = service.ping_host("192.168.1.1")
            assert result is True
            mock_instance.connect_ex.assert_called_once_with(("192.168.1.1", 22))

    def test_ping_host_closed_port(self):
        """Test ping_host returns False when port 22 is closed"""
        service = DiscoveryService(timeout=1.0)

        with patch("socket.socket") as mock_socket:
            mock_instance = MagicMock()
            mock_instance.connect_ex.return_value = 1
            mock_socket.return_value = mock_instance

            result = service.ping_host("192.168.1.100")
            assert result is False

    def test_ping_host_socket_timeout(self):
        """Test ping_host handles socket timeout gracefully"""
        service = DiscoveryService(timeout=1.0)

        with patch("socket.socket") as mock_socket:
            mock_instance = MagicMock()
            mock_instance.connect_ex.side_effect = socket.timeout()
            mock_socket.return_value = mock_instance

            result = service.ping_host("192.168.1.200")
            assert result is False

    def test_ping_host_socket_error(self):
        """Test ping_host handles socket error gracefully"""
        service = DiscoveryService(timeout=1.0)

        with patch("socket.socket") as mock_socket:
            mock_instance = MagicMock()
            mock_instance.connect_ex.side_effect = socket.error("Connection refused")
            mock_socket.return_value = mock_instance

            result = service.ping_host("192.168.1.200")
            assert result is False


class TestDiscoveryServiceTcpScan:
    """Test the tcp_connect_scan method"""

    def test_tcp_scan_default_ports(self):
        """Test TCP scan on default ports"""
        service = DiscoveryService(timeout=1.0)

        with patch("socket.socket") as mock_socket:
            mock_instance = MagicMock()
            mock_instance.connect_ex.return_value = 0
            mock_socket.return_value = mock_instance

            results = service.tcp_connect_scan("192.168.1.1")
            assert 22 in results
            assert 23 in results
            assert 80 in results
            assert 443 in results
            assert results[22] is True

    def test_tcp_scan_custom_ports(self):
        """Test TCP scan on custom ports"""
        service = DiscoveryService(timeout=1.0)

        with patch("socket.socket") as mock_socket:
            mock_instance = MagicMock()
            mock_instance.connect_ex.return_value = 0
            mock_socket.return_value = mock_instance

            results = service.tcp_connect_scan("192.168.1.1", ports=[22, 8080])
            assert 22 in results
            assert 8080 in results
            assert 23 not in results

    def test_tcp_scan_mixed_results(self):
        """Test TCP scan with some ports open and some closed"""
        service = DiscoveryService(timeout=1.0)

        with patch("socket.socket") as mock_socket:
            mock_instance = MagicMock()
            # connect_ex returns 0 for open, non-zero for closed
            mock_instance.connect_ex.side_effect = [0, 1, 0]  # 22 open, 23 closed, 80 open
            mock_socket.return_value = mock_instance

            results = service.tcp_connect_scan("192.168.1.1", ports=[22, 23, 80])
            assert results[22] is True
            assert results[23] is False
            assert results[80] is True


class TestDiscoveryServicePingSweep:
    """Test the ping_sweep method"""

    def test_ping_sweep_small_subnet(self):
        """Test ping sweep on a small subnet"""
        service = DiscoveryService(timeout=1.0, workers=4)

        with patch.object(service, "ping_host") as mock_ping:
            # Only some hosts respond
            mock_ping.side_effect = lambda ip: ip.endswith(".1") or ip.endswith(".2")

            devices = service.ping_sweep("192.168.1.0/30")  # 2 usable IPs

            assert len(devices) <= 2
            for d in devices:
                assert d.discovery_method == "ping"
                assert d.is_cisco is False

    def test_ping_sweep_returns_discovered_devices(self):
        """Test that ping_sweep returns properly structured DiscoveredDevice objects"""
        service = DiscoveryService(timeout=1.0, workers=2)

        with patch.object(service, "ping_host", return_value=True):
            devices = service.ping_sweep("10.0.0.0/30")

            for device in devices:
                assert isinstance(device, DiscoveredDevice)
                assert device.vendor == "Unknown"
                assert device.discovery_method == "ping"


class TestDiscoveryServiceIdentifyCisco:
    """Test the identify_cisco_device method"""

    def test_identify_cisco_returns_none_without_netmiko(self):
        """Test that identify_cisco_device returns None when netmiko is unavailable"""
        service = DiscoveryService()

        with patch("app.services.discovery_service.NETMIKO_AVAILABLE", False):
            result = service.identify_cisco_device("192.168.1.1", {})
            assert result is None

    def test_identify_cisco_device_success(self):
        """Test successful Cisco device identification"""
        service = DiscoveryService()

        mock_conn = MagicMock()
        mock_conn.send_command.side_effect = [
            "hostname SW-Core-01",
            "Cisco IOS Software, C9300 Software\nSystem image file is \"flash:c9300.bin\"",
        ]

        credentials = {"username": "admin", "password": "secret", "secret": "enable"}

        with patch("app.services.discovery_service.NETMIKO_AVAILABLE", True):
            with patch("app.services.discovery_service.netmiko.ConnectHandler", return_value=mock_conn):
                result = service.identify_cisco_device("192.168.1.1", credentials)

                assert result is not None
                assert result.ip == "192.168.1.1"
                assert result.hostname == "SW-Core-01"
                assert result.vendor == "Cisco"
                assert result.is_cisco is True
                mock_conn.disconnect.assert_called_once()

    def test_identify_cisco_device_connection_failure(self):
        """Test handling of connection failure"""
        service = DiscoveryService()

        with patch("app.services.discovery_service.NETMIKO_AVAILABLE", True):
            with patch("app.services.discovery_service.netmiko.ConnectHandler", side_effect=Exception("Connection refused")):
                result = service.identify_cisco_device("192.168.1.1", {})
                assert result is None


class TestDiscoveryServiceCdpDiscover:
    """Test the cdp_discover method"""

    def test_cdp_discover_returns_empty_without_netmiko(self):
        """Test that cdp_discover returns empty list when netmiko unavailable"""
        service = DiscoveryService()

        with patch("app.services.discovery_service.NETMIKO_AVAILABLE", False):
            result = service.cdp_discover("192.168.1.1", {})
            assert result == []

    def test_cdp_discover_parses_neighbors(self):
        """Test CDP neighbor parsing"""
        service = DiscoveryService()

        mock_conn = MagicMock()
        mock_conn.send_command.return_value = """Device ID: SW-Access-01
Entry address(es):
  IP address: 192.168.1.2
Platform: cisco WS-C2960X, Capabilities: Switch IGMP
Interface: GigabitEthernet1/0/1, Port ID (outgoing port): GigabitEthernet0/1
Device ID: SW-Access-02
Entry address(es):
  IP address: 192.168.1.3
Platform: cisco WS-C2960X, Capabilities: Switch IGMP
"""

        with patch("app.services.discovery_service.NETMIKO_AVAILABLE", True):
            with patch("app.services.discovery_service.netmiko.ConnectHandler", return_value=mock_conn):
                neighbors = service.cdp_discover("192.168.1.1", {})

                assert len(neighbors) == 2
                assert neighbors[0]["device_id"] == "SW-Access-01"
                assert neighbors[1]["device_id"] == "SW-Access-02"

    def test_cdp_discover_connection_failure(self):
        """Test handling of connection failure during CDP discovery"""
        service = DiscoveryService()

        with patch("app.services.discovery_service.NETMIKO_AVAILABLE", True):
            with patch("app.services.discovery_service.netmiko.ConnectHandler", side_effect=Exception("Timeout")):
                result = service.cdp_discover("192.168.1.1", {})
                assert result == []


class TestDiscoveryServiceDiscoverSubnet:
    """Test the comprehensive discover_subnet method"""

    def test_discover_subnet_ping_only(self):
        """Test discovery with only ping sweep (no credentials)"""
        service = DiscoveryService(workers=2)

        with patch.object(service, "ping_sweep") as mock_sweep:
            mock_sweep.return_value = [
                DiscoveredDevice(ip="192.168.1.1"),
                DiscoveredDevice(ip="192.168.1.2"),
            ]

            devices = service.discover_subnet("192.168.1.0/24")

            assert len(devices) == 2
            mock_sweep.assert_called_once_with("192.168.1.0/24")

    def test_discover_subnet_empty_result(self):
        """Test discovery when no hosts found"""
        service = DiscoveryService()

        with patch.object(service, "ping_sweep", return_value=[]):
            devices = service.discover_subnet("10.0.0.0/24")
            assert devices == []


class TestDiscoveryServiceSingleton:
    """Test the singleton pattern for get_discovery_service"""

    def test_get_discovery_service_returns_instance(self):
        """Test that get_discovery_service returns a DiscoveryService instance"""
        import app.services.discovery_service as mod
        mod._discovery_service = None  # reset

        service = get_discovery_service()
        assert isinstance(service, DiscoveryService)

    def test_get_discovery_service_returns_same_instance(self):
        """Test that get_discovery_service returns the same instance on repeated calls"""
        import app.services.discovery_service as mod
        mod._discovery_service = None  # reset

        s1 = get_discovery_service()
        s2 = get_discovery_service()
        assert s1 is s2
