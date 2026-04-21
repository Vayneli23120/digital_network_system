"""
Services 包初始化
"""

from .netmiko_service import NetmikoService, backup_device_config
from .console_service import ConsoleService, find_console_port
from .email_service import EmailAlertService, get_email_service, send_alert
from .credential_service import CredentialService, get_credential_service, encrypt_password, decrypt_password
from .discovery_service import DiscoveryService, get_discovery_service, quick_discovery, DiscoveredDevice
from .backup_service import list_backups, delete_backup
from .device_service import (
    list_devices, create_device, get_device,
    update_device, delete_device, batch_update_devices,
)
from .deploy_service import get_deploy_service
from .compliance_service import ComplianceService
from .template_service import (
    list_templates, get_template, create_template,
    update_template, delete_template, render_template,
)
from .dashboard_service import get_dashboard_summary, get_fault_trend
from .spare_part_service import (
    list_parts, get_part, create_part, update_part, delete_part,
    get_stats, create_movement, list_movements, get_movement,
)

__all__ = [
    # Netmiko
    "NetmikoService",
    "backup_device_config",
    # Console
    "ConsoleService",
    "find_console_port",
    # Email
    "EmailAlertService",
    "get_email_service",
    "send_alert",
    # Credential
    "CredentialService",
    "get_credential_service",
    "encrypt_password",
    "decrypt_password",
    # Discovery
    "DiscoveryService",
    "get_discovery_service",
    "quick_discovery",
    "DiscoveredDevice",
    # Backup
    "list_backups",
    "delete_backup",
    # Device
    "list_devices",
    "create_device",
    "get_device",
    "update_device",
    "delete_device",
    "batch_update_devices",
    # Deploy
    "get_deploy_service",
    # Compliance
    "ComplianceService",
    # Template
    "list_templates",
    "get_template",
    "create_template",
    "update_template",
    "delete_template",
    "render_template",
    # Dashboard
    "get_dashboard_summary",
    "get_fault_trend",
    # Spare Part
    "list_parts",
    "get_part",
    "create_part",
    "update_part",
    "delete_part",
    "get_stats",
    "create_movement",
    "list_movements",
    "get_movement",
]
