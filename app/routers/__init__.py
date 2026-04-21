"""Routers module - Export all routers for registration"""

from .devices import router as devices_router
from .backups import router as backups_router
from .faults import router as faults_router
from .maintenance import router as maintenance_router
from .templates import router as templates_router
from .credentials import router as credentials_router
from .deploy import router as deploy_router
from .console import router as console_router
from .dashboard import router as dashboard_router
from .logs import router as logs_router
# v1.1 新增路由
from .auth import router as auth_router
from .permissions import router as permissions_router
from .tool_logs import router as tool_logs_router
from .spare_parts import router as spare_parts_router
from .spare_movements import router as spare_movements_router
from .compliance import router as compliance_router
from .websocket import router as websocket_router
from .discovery import router as discovery_router
from .alerts import router as alerts_router

__all__ = [
    "devices_router",
    "backups_router",
    "faults_router",
    "maintenance_router",
    "templates_router",
    "credentials_router",
    "deploy_router",
    "console_router",
    "dashboard_router",
    "logs_router",
    # v1.1
    "auth_router",
    "permissions_router",
    "tool_logs_router",
    "spare_parts_router",
    "spare_movements_router",
    "compliance_router",
    "websocket_router",
    "discovery_router",
    "alerts_router",
]
