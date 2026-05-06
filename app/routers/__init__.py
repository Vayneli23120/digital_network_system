"""
Router aggregation module.

Re-exports feature module routers for registration in main.py.
"""

from app.features.devices.router import router as devices_router
from app.features.backups.router import router as backups_router
from app.features.faults.router import router as faults_router
from app.features.maintenance.router import router as maintenance_router
from app.features.templates.router import router as templates_router
from app.features.credentials.router import router as credentials_router
from app.features.deploy.router import router as deploy_router
from app.features.console.router import router as console_router
from app.features.dashboard.router import router as dashboard_router
from app.features.logs.router import router as logs_router
from app.features.auth.router import router as auth_router
from app.features.permissions.router import router as permissions_router
from app.features.tool_logs.router import router as tool_logs_router
from app.features.spare_parts.router import router as spare_parts_router
from app.features.spare_movements.router import router as spare_movements_router
from app.features.compliance.router import router as compliance_router
from app.features.websocket.router import router as websocket_router
from app.features.discovery.router import router as discovery_router
from app.features.alerts.router import router as alerts_router
from app.features.planned_maintenance.router import router as planned_maintenance_router
from app.features.scan.router import router as scan_router
from app.features.monitor_screen.router import router as monitor_screen_router
