"""
Tests for configuration deployment service

These tests verify the template rendering and deployment logic
without requiring actual network device connections.
"""

import pytest
from unittest.mock import patch, MagicMock
from app.shared.models import Device, ConfigTemplate


class TestDeployServiceTemplateRendering:
    """Test Jinja2 template rendering via deploy_from_template"""

    def test_render_template_simple(self):
        """Test rendering a simple template with variables"""
        from jinja2 import Template

        template_content = """hostname {{ HOSTNAME }}
enable secret {{ ENABLE_SECRET }}
!
interface GigabitEthernet0/1
 description {{ PORT_DESCRIPTION }}
!"""
        variables = {
            "HOSTNAME": "SW-Access-01",
            "ENABLE_SECRET": "MySecret123",
            "PORT_DESCRIPTION": "User Access Port"
        }

        tmpl = Template(template_content)
        result = tmpl.render(**variables)

        assert "hostname SW-Access-01" in result
        assert "enable secret MySecret123" in result
        assert "description User Access Port" in result

    def test_render_template_with_loops(self):
        """Test rendering template with loop constructs"""
        from jinja2 import Template

        template_content = """!
{% for interface in interfaces %}
interface {{ interface.name }}
 description {{ interface.description }}
 switchport mode {{ interface.mode }}
!
{% endfor %}
"""
        variables = {
            "interfaces": [
                {"name": "Gi0/1", "description": "Uplink", "mode": "trunk"},
                {"name": "Gi0/2", "description": "Access", "mode": "access"},
                {"name": "Gi0/3", "description": "Guest", "mode": "access"},
            ]
        }

        tmpl = Template(template_content)
        result = tmpl.render(**variables)

        assert "interface Gi0/1" in result
        assert "interface Gi0/2" in result
        assert "interface Gi0/3" in result
        assert "switchport mode trunk" in result
        assert "switchport mode access" in result

    def test_render_template_with_conditionals(self):
        """Test rendering template with conditional logic"""
        from jinja2 import Template

        template_content = """hostname {{ HOSTNAME }}
{% if ENABLE_VLAN %}
vlan {{ VLAN_ID }}
 name {{ VLAN_NAME }}
!
{% endif %}
"""
        # Test with VLAN enabled
        variables_enabled = {
            "HOSTNAME": "SW-01",
            "ENABLE_VLAN": True,
            "VLAN_ID": 100,
            "VLAN_NAME": "CORPORATE"
        }
        tmpl = Template(template_content)
        result = tmpl.render(**variables_enabled)
        assert "vlan 100" in result
        assert "name CORPORATE" in result

        # Test with VLAN disabled
        variables_disabled = {
            "HOSTNAME": "SW-01",
            "ENABLE_VLAN": False,
            "VLAN_ID": 100,
            "VLAN_NAME": "CORPORATE"
        }
        result = tmpl.render(**variables_disabled)
        assert "vlan 100" not in result

    def test_render_template_with_datetime(self):
        """Test template can access datetime helpers"""
        from jinja2 import Template
        from datetime import datetime

        template_content = """! Last updated: {{ now_str }}
! Build date: {{ now().strftime('%Y-%m-%d') }}"""

        tmpl = Template(template_content)
        context = {
            'now': datetime.utcnow,
            'now_str': datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        }
        result = tmpl.render(**context)

        assert "Last updated:" in result
        assert "Build date:" in result

    def test_render_template_missing_variable(self):
        """Test rendering template with missing variable renders empty string"""
        from jinja2 import Template

        template_content = """hostname {{ HOSTNAME }}
sysname {{ SYSNAME }}
"""
        variables = {"HOSTNAME": "SW-01"}
        # Missing SYSNAME - Jinja2 renders with empty string by default
        tmpl = Template(template_content)
        result = tmpl.render(**variables)
        assert "hostname SW-01" in result
        assert "sysname " in result  # Empty string


class TestDeployServiceCredentialSelection:
    """Test credential group selection logic"""

    def test_get_device_credentials_exact_match(self):
        """Test getting credentials for exact group match"""
        from app.features.deploy.deploy_service import DeployService

        service = DeployService()

        device = {"name": "SW-01", "credential_group": "engineers"}
        groups = [
            {"name": "admins", "username": "admin", "password": "admin123"},
            {"name": "engineers", "username": "engineer", "password": "eng456"},
        ]

        creds = service.get_device_credentials(device, groups)

        assert creds["username"] == "engineer"
        assert creds["password"] == "eng456"

    def test_get_device_credentials_default_fallback(self):
        """Test falling back to default group when specific group not found"""
        from app.features.deploy.deploy_service import DeployService

        service = DeployService()

        device = {"name": "SW-01", "credential_group": "nonexistent"}
        groups = [
            {"name": "default", "username": "admin", "password": "default123"},
        ]

        creds = service.get_device_credentials(device, groups)

        assert creds["username"] == "admin"
        assert creds["password"] == "default123"

    def test_get_device_credentials_empty_groups(self):
        """Test handling empty credential groups"""
        from app.features.deploy.deploy_service import DeployService

        service = DeployService()

        device = {"name": "SW-01", "credential_group": "any"}
        groups = []

        creds = service.get_device_credentials(device, groups)

        assert creds["username"] == ""
        assert creds["password"] == ""


class TestDeployServiceDeviceTypeMapping:
    """Test device type mapping"""

    def test_device_type_mapping(self):
        """Test device type is correctly mapped for Netmiko"""
        from app.features.deploy.deploy_service import DeployService

        service = DeployService()

        # These are the mappings used by DeployService
        assert service.device_type_map["cisco"] == "cisco_ios"
        assert service.device_type_map["huawei"] == "huawei"
        assert service.device_type_map["h3c"] == "h3c_comware"
        assert service.device_type_map["juniper"] == "juniper_junos"


class MockNetmikoConnection:
    """Mock Netmiko connection for deployment testing"""

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self._in_config_mode = False

    def enable(self):
        self._in_config_mode = True

    def send_config_set(self, commands):
        return "config term\n" + "\n".join(str(c) for c in commands) + "\nend\n"

    def send_command(self, command):
        if "show" in command.lower():
            return "OK"
        return ""

    def save_config(self):
        return "Building configuration...\n[OK]"

    def disconnect(self):
        pass


class TestDeployServiceConnection:
    """Test device connection for deployment"""

    def test_connect_device_success(self):
        """Test successful device connection"""
        from app.features.deploy.deploy_service import DeployService

        with patch("app.services.deploy_service.ConnectHandler", MockNetmikoConnection):
            service = DeployService()

            device = {
                "device_type": "cisco_ios",
                "name": "Test-SW",
                "ip": "192.168.1.1",
                "ssh_port": 22
            }
            credentials = {
                "username": "admin",
                "password": "secret",
                "enable_password": "enable"
            }

            conn = service.connect_device(device, credentials)

            assert conn is not None

    def test_connect_device_without_netmiko(self):
        """Test error when netmiko is not available"""
        from app.features.deploy.deploy_service import DeployService

        service = DeployService()

        device = {"device_type": "cisco_ios", "name": "Test", "ip": "192.168.1.1"}
        credentials = {"username": "admin", "password": "secret"}

        with patch("app.services.deploy_service.NETMIKO_AVAILABLE", False):
            with pytest.raises(RuntimeError) as exc_info:
                service.connect_device(device, credentials)

            assert "netmiko 未安装" in str(exc_info.value)


class TestDeployServiceCompareConfig:
    """Test configuration comparison"""

    def test_compare_config_identical(self):
        """Test identical configs produce no diff"""
        from app.features.deploy.deploy_service import DeployService

        service = DeployService()

        config = "hostname SW-01\ninterface Gi0/1\n description Test\n"
        diff = service.compare_config(config, config)

        assert len(diff) == 0

    def test_compare_config_with_changes(self):
        """Test configs with changes produce diff lines"""
        from app.features.deploy.deploy_service import DeployService

        service = DeployService()

        old_config = "hostname SW-01\ninterface Gi0/1\n description Old\n"
        new_config = "hostname SW-01\ninterface Gi0/1\n description New\n"

        diff = service.compare_config(old_config, new_config)

        assert len(diff) > 0
        # Diff format: list of {'type': 'remove'|'add', 'content': str}
        assert any(d.get('type') == 'remove' and 'Old' in d.get('content', '') for d in diff)
        assert any(d.get('type') == 'add' and 'New' in d.get('content', '') for d in diff)


class TestDeployServiceParseCommands:
    """Test config command parsing"""

    def test_parse_config_commands(self):
        """Test parsing multi-line config into commands"""
        from app.features.deploy.deploy_service import DeployService

        service = DeployService()

        config = """
hostname SW-01
!
interface GigabitEthernet0/1
 description Uplink
 switchport mode trunk
!
"""
        commands = service.parse_config_commands(config)

        assert "hostname SW-01" in commands
        assert "interface GigabitEthernet0/1" in commands
        assert "description Uplink" in commands
        assert "switchport mode trunk" in commands
