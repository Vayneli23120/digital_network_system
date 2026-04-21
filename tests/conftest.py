"""
Pytest configuration and shared fixtures
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure app package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(autouse=True)
def reset_config():
    """Reset the global config singleton before each test"""
    from app.shared import config as config_module
    config_module._config = None
    yield
    config_module._config = None


@pytest.fixture
def db_manager():
    """Create an in-memory SQLite database manager"""
    from app.shared.database import DatabaseManager
    from app.shared.models import Base

    manager = DatabaseManager(":memory:")
    manager.init_db()
    yield manager
    # Cleanup
    manager.engine.dispose()


@pytest.fixture
def db_session(db_manager):
    """Provide a database session with automatic cleanup"""
    session = db_manager.get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@pytest.fixture
def sample_device_data():
    """Sample device data for testing"""
    return {
        "name": "SW-Core-01",
        "ip": "192.168.1.1",
        "model": "Cisco Catalyst 9300",
        "serial_number": "FCW1234A5BC",
        "location": "Building A, Floor 1",
        "role": "core",
        "status": "online",
        "vendor": "Cisco",
        "credential_group": "default",
    }


@pytest.fixture
def sample_credential_data():
    """Sample credential group data for testing"""
    return {
        "name": "default",
        "description": "Default SSH credentials",
        "username": "admin",
        "password_encrypted": "dGVzdHBhc3N3b3Jk",  # base64 encoded for testing
        "enable_password_encrypted": "ZW5hYmxlcGFzcw==",
    }


@pytest.fixture
def sample_template_data():
    """Sample config template data"""
    return {
        "name": "basic-access-switch",
        "description": "Basic access switch configuration template",
        "template_content": """hostname {{ HOSTNAME }}
enable secret {{ ENABLE_SECRET }}
!
username {{ ADMIN_USERNAME }} privilege 15 secret {{ ADMIN_PASSWORD }}
!
ip domain-name {{ DOMAIN_NAME }}
""",
        "variables": '{"HOSTNAME": "SW-Access-01", "ENABLE_SECRET": "secret123"}',
    }


@pytest.fixture
def sample_user():
    """Sample user for testing"""
    from app.models import User
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash="hashed_password",
        full_name="Test User",
        is_active=True,
        is_superuser=False
    )
    return user


@pytest.fixture
def mock_netmiko(monkeypatch):
    """Mock netmiko ConnectHandler to prevent real SSH connections"""

    class MockConnectHandler:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.connected = True

        def enable(self):
            pass

        def send_command(self, command):
            if "show running-config" in command:
                return "!\nhostname Test-Switch\ninterface GigabitEthernet0/1\n description Test\nend\n"
            return ""

        def send_config_set(self, commands):
            return "config term\n" + "\n".join(str(c) for c in commands) + "\nend\n"

        def save_config(self):
            return "Building configuration...\n[OK]"

        def disconnect(self):
            self.connected = False

    def mock_connect(**kwargs):
        return MockConnectHandler(**kwargs)

    monkeypatch.setattr("app.features.backups.netmiko_service.ConnectHandler", mock_connect)
