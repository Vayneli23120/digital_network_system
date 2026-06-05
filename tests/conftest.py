"""
Pytest configuration and shared fixtures

支持 SQLite（默认）和 PostgreSQL（TEST_DATABASE_URL 环境变量）测试。
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
def test_db_url():
    """
    测试数据库 URL

    - 默认使用内存 SQLite（CI 环境友好）
    - 可通过 TEST_DATABASE_URL 环境变量指定 PostgreSQL
    """
    return os.getenv(
        "TEST_DATABASE_URL",
        "sqlite:///:memory:"  # 默认内存 SQLite
    )


@pytest.fixture
def db_manager(test_db_url):
    """
    测试数据库管理器 — function 级别

    每个测试独立数据库，测试后清理。
    """
    from app.shared.database import DatabaseManager
    from app.shared.models import Base

    manager = DatabaseManager(db_url=test_db_url, echo=False)
    manager.init_db()
    yield manager

    # Cleanup - 仅 SQLite 时清理，PostgreSQL 保留数据
    manager.engine.dispose()


@pytest.fixture
def db_session(db_manager):
    """
    每个测试函数独立事务，测试后回滚

    确保测试之间数据隔离，不互相影响。
    """
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
    from app.shared.models import User
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


# PostgreSQL 专用测试标记
def pytest_configure(config):
    """注册自定义标记"""
    config.addinivalue_line(
        "markers", "postgresql: mark test as requiring PostgreSQL database"
    )


def pytest_collection_modifyitems(config, items):
    """
    处理 PostgreSQL 专用测试

    如果未配置 TEST_DATABASE_URL 且有 postgresql 标记的测试，
    则跳过这些测试。
    """
    test_db_url = os.getenv("TEST_DATABASE_URL", "")

    skip_pg = pytest.mark.skip(reason="需要 PostgreSQL：设置 TEST_DATABASE_URL 环境变量")

    for item in items:
        if "postgresql" in item.keywords and "postgresql" not in test_db_url:
            item.add_marker(skip_pg)