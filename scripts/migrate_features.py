#!/usr/bin/env python3
"""Feature-first migration: app/routers/ + app/services/ → app/features/*/"""

import shutil
from pathlib import Path

BASE = Path(__file__).parent.parent


def ensure_dir(p):
    Path(p).parent.mkdir(parents=True, exist_ok=True)


def copy_file(src, dst):
    s = BASE / src
    d = BASE / dst
    ensure_dir(d)
    shutil.copy2(s, d)
    print(f"  {src} → {dst}")


def write_init(path, docstring=""):
    (BASE / path).write_text(f'"""{docstring}"""  # noqa: F401\n')
    print(f"  {path} (new)")


def fix_shared(content):
    fixes = [
        ("from .config import", "from app.shared.config import"),
        ("from .database import", "from app.shared.database import"),
        ("from .models import", "from app.shared.models import"),
        ("from .exceptions import", "from app.shared.exceptions import"),
        ("from .db_init import", "from app.shared.db_init import"),
        ("from .cache import", "from app.shared.cache import"),
    ]
    for old, new in fixes:
        content = content.replace(old, new)
    return content


def fix_feature(content):
    fixes = [
        ("from ..config import", "from app.shared.config import"),
        ("from ..database import", "from app.shared.database import"),
        ("from ..models import", "from app.shared.models import"),
        ("from ..exceptions import", "from app.shared.exceptions import"),
        ("from ..db_init import", "from app.shared.db_init import"),
        ("from ..cache import", "from app.shared.cache import"),
        ("from ..middleware", "from app.shared.middleware"),
        ("from ..services.email_service", "from app.services.email_service"),
        ("from ..services.notification_service", "from app.services.notification_service"),
        ("from ..services.device_service", "from .device_service"),
        ("from ..services.backup_service", "from .backup_service"),
        ("from ..services.netmiko_service", "from .netmiko_service"),
        ("from ..services.template_service", "from .template_service"),
        ("from ..services.credential_service", "from .credential_service"),
        ("from ..services.deploy_service", "from .deploy_service"),
        ("from ..services.console_service", "from .console_service"),
        ("from ..services.dashboard_service", "from .dashboard_service"),
        ("from ..services.log_service", "from .log_service"),
        ("from ..services.tool_executor", "from .tool_executor"),
        ("from ..services.spare_part_service", "from .spare_part_service"),
        ("from ..services.discovery_service", "from .discovery_service"),
        ("from ..services.compliance_service", "from .compliance_service"),
    ]
    for old, new in fixes:
        content = content.replace(old, new)
    return content


# ============================================================
# 1. Shared infrastructure
# ============================================================
print("=== 1. Shared ===")
for f in ["config.py", "database.py", "models.py", "exceptions.py", "db_init.py"]:
    copy_file(f"app/{f}", f"app/shared/{f}")
    c = (BASE / f"app/shared/{f}").read_text()
    (BASE / f"app/shared/{f}").write_text(fix_shared(c))

copy_file("app/services/cache.py", "app/shared/cache.py")
c = (BASE / "app/shared/cache.py").read_text()
(BASE / "app/shared/cache.py").write_text(fix_shared(c))

for f in ["auth_middleware.py", "rate_limiter.py"]:
    copy_file(f"app/middleware/{f}", f"app/shared/middleware/{f}")
    c = (BASE / f"app/shared/middleware/{f}").read_text()
    c = c.replace("from ..config import", "from app.shared.config import")
    c = c.replace("from app.config import", "from app.shared.config import")
    c = c.replace("from ..models", "from app.shared.models")
    c = c.replace("from ..services.cache", "from app.shared.cache")
    (BASE / f"app/shared/middleware/{f}").write_text(c)

write_init("app/shared/__init__.py", "Shared")
write_init("app/shared/middleware/__init__.py", "Middleware")

# ============================================================
# 2. Features
# ============================================================
print("\n=== 2. Features ===")
FEATS = [
    ("devices", "app/routers/devices.py", ["app/services/device_service.py"]),
    ("backups", "app/routers/backups.py", ["app/services/backup_service.py", "app/services/netmiko_service.py"]),
    ("faults", "app/routers/faults.py", []),
    ("maintenance", "app/routers/maintenance.py", []),
    ("templates", "app/routers/templates.py", ["app/services/template_service.py"]),
    ("credentials", "app/routers/credentials.py", ["app/services/credential_service.py"]),
    ("deploy", "app/routers/deploy.py", ["app/services/deploy_service.py"]),
    ("console", "app/routers/console.py", ["app/services/console_service.py"]),
    ("dashboard", "app/routers/dashboard.py", ["app/services/dashboard_service.py"]),
    ("logs", "app/routers/logs.py", ["app/services/log_service.py"]),
    ("auth", "app/routers/auth.py", []),
    ("permissions", "app/routers/permissions.py", []),
    ("tool_logs", "app/routers/tool_logs.py", ["app/services/tool_executor.py"]),
    ("spare_parts", "app/routers/spare_parts.py", ["app/services/spare_part_service.py"]),
    ("spare_movements", "app/routers/spare_movements.py", []),
    ("discovery", "app/routers/discovery.py", ["app/services/discovery_service.py"]),
    ("alerts", "app/routers/alerts.py", []),
    ("compliance", "app/routers/compliance.py", ["app/services/compliance_service.py"]),
    ("websocket", "app/routers/websocket.py", []),
]

for feat, router_file, svc_files in FEATS:
    feat_dir = BASE / f"app/features/{feat}"
    feat_dir.mkdir(parents=True, exist_ok=True)
    write_init(f"app/features/{feat}/__init__.py", feat)
    if router_file:
        copy_file(router_file, f"app/features/{feat}/router.py")
        c = (BASE / f"app/features/{feat}/router.py").read_text()
        (BASE / f"app/features/{feat}/router.py").write_text(fix_feature(c))
    for svc_file in svc_files:
        svc_name = Path(svc_file).stem
        copy_file(svc_file, f"app/features/{feat}/{svc_name}.py")
        c = (BASE / f"app/features/{feat}/{svc_name}.py").read_text()
        (BASE / f"app/features/{feat}/{svc_name}.py").write_text(fix_feature(c))

# Cross-cutting services stay in app/services/
print("\n=== 3. Cross-cutting ===")
for svc in ["email_service.py", "notification_service.py", "wechat_work_service.py", "dingtalk_service.py"]:
    p = BASE / f"app/services/{svc}"
    if p.exists():
        c = p.read_text()
        c = c.replace("from ..config import", "from app.shared.config import")
        c = c.replace("from ..services.cache", "from app.shared.cache")
        p.write_text(c)
        print(f"  ✅ {svc}")

# ============================================================
# 4. main.py
# ============================================================
print("\n=== 4. main.py ===")
m = (BASE / "app/main.py").read_text()
m = m.replace("from .config import get_config", "from .shared.config import get_config")
m = m.replace("from .database import get_db_manager", "from .shared.database import get_db_manager")
m = m.replace("from .exceptions import register_exception_handlers", "from .shared.exceptions import register_exception_handlers")
m = m.replace("from .db_init import init_default_templates", "from .shared.db_init import init_default_templates")
m = m.replace("from .middleware.auth_middleware import auth_middleware", "from .shared.middleware.auth_middleware import auth_middleware")
m = m.replace("from .middleware.rate_limiter import RateLimitMiddleware", "from .shared.middleware.rate_limiter import RateLimitMiddleware")

old = """from .routers import (
    devices_router,
    backups_router,
    faults_router,
    maintenance_router,
    templates_router,
    credentials_router,
    deploy_router,
    console_router,
    dashboard_router,
    logs_router,
    # v1.1 新增路由
    auth_router,
    permissions_router,
    tool_logs_router,
    spare_parts_router,
    spare_movements_router,
    compliance_router,
    websocket_router,
    discovery_router,
    alerts_router,
)"""
new = """from .features.devices.router import router as devices_router
from .features.backups.router import router as backups_router
from .features.faults.router import router as faults_router
from .features.maintenance.router import router as maintenance_router
from .features.templates.router import router as templates_router
from .features.credentials.router import router as credentials_router
from .features.deploy.router import router as deploy_router
from .features.console.router import router as console_router
from .features.dashboard.router import router as dashboard_router
from .features.logs.router import router as logs_router
from .features.auth.router import router as auth_router
from .features.permissions.router import router as permissions_router
from .features.tool_logs.router import router as tool_logs_router
from .features.spare_parts.router import router as spare_parts_router
from .features.spare_movements.router import router as spare_movements_router
from .features.compliance.router import router as compliance_router
from .features.websocket.router import router as websocket_router
from .features.discovery.router import router as discovery_router
from .features.alerts.router import router as alerts_router"""
m = m.replace(old, new)
m = m.replace("from .middleware.rate_limiter import get_rate_limiter", "from .shared.middleware.rate_limiter import get_rate_limiter")
m = m.replace("from .services.cache import cache", "from .shared.cache import cache")
(BASE / "app/main.py").write_text(m)
print("  ✅ main.py updated")

# ============================================================
# 5. Tests
# ============================================================
print("\n=== 5. Tests ===")
import glob
SVC_MAP = {
    "device_service": "features.devices.device_service",
    "backup_service": "features.backups.backup_service",
    "template_service": "features.templates.template_service",
    "dashboard_service": "features.dashboard.dashboard_service",
    "spare_part_service": "features.spare_parts.spare_part_service",
    "log_service": "features.logs.log_service",
    "compliance_service": "features.compliance.compliance_service",
    "console_service": "features.console.console_service",
    "credential_service": "features.credentials.credential_service",
    "deploy_service": "features.deploy.deploy_service",
    "discovery_service": "features.discovery.discovery_service",
    "netmiko_service": "features.backups.netmiko_service",
    "tool_executor": "features.tool_logs.tool_executor",
}
for tf in glob.glob(str(BASE / "tests/test_*.py")):
    c = Path(tf).read_text()
    c = c.replace("from app.config import", "from app.shared.config import")
    c = c.replace("from app.database import", "from app.shared.database import")
    c = c.replace("from app.models import", "from app.shared.models import")
    c = c.replace("from app.exceptions import", "from app.shared.exceptions import")
    c = c.replace("from app.services.cache import", "from app.shared.cache import")
    c = c.replace("from app.middleware", "from app.shared.middleware")
    for old_svc, new_svc in SVC_MAP.items():
        c = c.replace(f"from app.services.{old_svc} import", f"from app.{new_svc} import")
    Path(tf).write_text(c)
    print(f"  ✅ {Path(tf).name}")

print("\n" + "=" * 60)
print("✅ Migration complete!")
print("=" * 60)
print("Next: run tests to verify")
