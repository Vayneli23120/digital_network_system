"""
Network Automation System - FastAPI 主程序

重构后的主程序，仅负责：
- 应用初始化
- 中间件配置
- 异常处理注册
- 路由注册
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from loguru import logger

from .config import get_config
from .database import get_db_manager
from .exceptions import register_exception_handlers
from .db_init import init_default_templates
from .routers import (
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
)
from .middleware.auth_middleware import auth_middleware

# 获取配置
config = get_config()

# 创建 FastAPI 应用
app = FastAPI(
    title=config.app.name,
    version=config.app.version,
    description="Cisco IOS 交换机自动化备份与配置管理平台",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ============ 中间件配置 ============

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 认证中间件（默认关闭，通过 config.yaml security.auth_enabled: true 启用）
if config.security.auth_enabled:
    app.middleware("http")(auth_middleware)

# ============ 异常处理 ============

register_exception_handlers(app)

# ============ 目录初始化 ============

for dir_path in [config.storage.backup_dir, config.storage.photo_dir, config.storage.log_dir]:
    Path(dir_path).mkdir(parents=True, exist_ok=True)

# ============ 静态文件挂载 ============

app.mount("/assets", StaticFiles(directory=config.storage.photo_dir), name="assets")

# ============ 路由注册 ============

app.include_router(devices_router)
app.include_router(backups_router)
app.include_router(faults_router)
app.include_router(maintenance_router)
app.include_router(templates_router)
app.include_router(credentials_router)
app.include_router(deploy_router)
app.include_router(console_router)
app.include_router(dashboard_router)
app.include_router(logs_router)

# v1.1 新增路由
app.include_router(auth_router)
app.include_router(permissions_router)
app.include_router(tool_logs_router)
app.include_router(spare_parts_router)
app.include_router(spare_movements_router)
app.include_router(compliance_router)
app.include_router(websocket_router)
app.include_router(discovery_router)
app.include_router(alerts_router)

# ============ 健康检查 ============


@app.get("/health", tags=["health"])
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "version": config.app.version
    }

# ============ 初始化事件 ============


@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    # 初始化数据库
    db_manager = get_db_manager()
    db_manager.init_db()

    logger.info(f"Network Automation System v{config.app.version} 启动")
    logger.info(f"数据库路径：{config.database.sqlite_path}")
    logger.info(f"备份目录：{config.storage.backup_dir}")

    # 初始化默认配置模板
    init_default_templates()


# ============ 程序入口 ============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
