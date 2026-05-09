"""
Network Automation System - FastAPI 主程序

职责：
- 应用初始化
- 中间件配置（CORS / 限流 / 安全头）
- 异常处理注册
- 路由注册
- 健康检查 / 优雅关闭
"""

import signal
import sys
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from loguru import logger

from .shared.config import get_config
from .shared.database import get_db_manager
from .shared.exceptions import register_exception_handlers
from .shared.db_init import init_default_templates, init_default_roles
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
    auth_router,
    permissions_router,
    tool_logs_router,
    spare_parts_router,
    spare_movements_router,
    compliance_router,
    websocket_router,
    discovery_router,
    alerts_router,
    planned_maintenance_router,
    scan_router,
    monitor_screen_router,
)
from .features.health.router import router as health_router
from .features.ai.router import router as ai_router
from .shared.middleware.auth_middleware import auth_middleware
from .shared.middleware.rate_limiter import RateLimitMiddleware

config = get_config()

app = FastAPI(
    title=config.app.name,
    version=config.app.version,
    description="Cisco IOS 交换机自动化备份与配置管理平台",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ============ 中间件配置 ============

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: 生产环境改为具体域名
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-Request-ID"],
)

if config.security.auth_enabled:
    app.middleware("http")(auth_middleware)

app.add_middleware(RateLimitMiddleware)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """安全头 + Request ID 中间件"""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    response.headers["X-Request-ID"] = request_id
    return response


# ============ 异常处理 ============

register_exception_handlers(app)

# ============ 目录初始化 ============

for dir_path in [config.storage.backup_dir, config.storage.photo_dir, config.storage.log_dir]:
    Path(dir_path).mkdir(parents=True, exist_ok=True)

# ============ 静态文件挂载 ============

# 扫码枪专用静态页面（纯HTML+JS，兼容旧版Chromium）
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# 扫码枪终端路由 - 返回纯HTML页面
@app.get("/scanner", include_in_schema=False)
async def scanner_terminal():
    """扫码枪终端页面（兼容旧版浏览器）"""
    scanner_html = Path(__file__).parent / "static" / "scanner.html"
    if scanner_html.exists():
        from fastapi.responses import FileResponse
        return FileResponse(str(scanner_html), media_type="text/html")
    return {"error": "Scanner page not found"}

# 前端静态文件（Vue SPA）- assets 目录挂载到 /assets
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    frontend_assets = frontend_dist / "assets"
    if frontend_assets.exists():
        app.mount("/assets", StaticFiles(directory=str(frontend_assets)), name="frontend-assets")

# 照片资源 - 挂载到 /photos 避免与前端 assets 冲突
photos_dir = Path(config.storage.photo_dir)
if photos_dir.exists():
    app.mount("/photos", StaticFiles(directory=str(photos_dir)), name="photos")


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
app.include_router(auth_router)
app.include_router(permissions_router)
app.include_router(tool_logs_router)
app.include_router(spare_parts_router)
app.include_router(spare_movements_router)
app.include_router(compliance_router)
app.include_router(websocket_router)
app.include_router(discovery_router)
app.include_router(alerts_router)
app.include_router(planned_maintenance_router)
app.include_router(scan_router)
app.include_router(monitor_screen_router)
app.include_router(health_router)  # 健康评分路由
app.include_router(ai_router)      # AI分析路由


# ============ 健康检查 ============


@app.get("/health", tags=["health"])
async def health_check():
    """Liveness 探针 — 进程是否存活"""
    return {"status": "healthy", "version": config.app.version}


@app.get("/ready", tags=["health"])
async def readiness_check():
    """Readiness 探针 — 服务是否就绪（数据库可达 + Redis 可选）"""
    from sqlalchemy import text

    checks = {}
    overall_ok = True
    try:
        db = get_db_manager()
        with db.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = {"status": "ok"}
    except Exception as e:
        checks["database"] = {"status": "error", "detail": str(e)}
        overall_ok = False

    # Redis 检查（可选，不阻塞就绪状态）
    try:
        from app.shared.redis_cache import get_redis_cache
        rc = get_redis_cache()
        checks["redis"] = {"status": "ok" if rc.available else "not_connected"}
    except Exception as e:
        checks["redis"] = {"status": "error", "detail": str(e)}

    status_code = 200 if overall_ok else 503
    return {
        "status": "ready" if overall_ok else "degraded",
        "checks": checks,
        "version": config.app.version,
    }, status_code


@app.get("/api/rate-limit/status", tags=["health"])
async def rate_limit_status(request: Request):
    """查看当前请求的限流状态"""
    from .shared.middleware.rate_limiter import get_rate_limiter

    limiter = get_rate_limiter()
    return limiter.get_status(request.client.host)


@app.get("/api/cache/stats", tags=["health"])
async def cache_stats():
    """查看缓存统计（内存 + Redis）"""
    from .shared.cache import cache
    from .shared.redis_cache import get_redis_cache

    rc = get_redis_cache()
    return {
        "memory": cache.get_stats(),
        "redis": rc.get_stats(),
    }


@app.post("/api/cache/clear", tags=["health"])
async def cache_clear(prefix: str = None):
    """清除缓存"""
    from .shared.cache import cache

    count = cache.invalidate_prefix(prefix) if prefix else cache.clear()
    return {"cleared": count}


# ============ SPA Fallback ============

@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str):
    """Vue SPA fallback - 返回前端 index.html（仅对非 API 路径）"""
    # 排除 API 和文档路径
    if full_path.startswith(("api/", "docs", "redoc", "openapi", "health", "ready", "scanner", "static")):
        # 让 FastAPI 返回 404
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not found")

    frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
    index_file = frontend_dist / "index.html"
    if index_file.exists():
        from fastapi.responses import FileResponse
        return FileResponse(str(index_file), media_type="text/html")
    return {"error": "Frontend not built"}


# ============ 初始化事件 ============


@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    db_manager = get_db_manager()
    db_manager.init_db()
    logger.info(f"Network Automation System v{config.app.version} 启动")
    logger.info(f"数据库路径：{config.database.sqlite_path}")
    logger.info(f"备份目录：{config.storage.backup_dir}")
    init_default_templates()
    init_default_roles()


# ============ 优雅关闭 ============


def handle_shutdown(signum, frame):
    """处理 SIGTERM/SIGINT 信号"""
    sig_name = signal.Signals(signum).name
    logger.info(f"收到 {sig_name} 信号，开始优雅关闭...")
    try:
        get_db_manager().engine.dispose()
        logger.info("数据库连接池已关闭")
    except Exception as e:
        logger.error(f"关闭数据库连接池失败: {e}")
    try:
        from .shared.cache import cache

        count = cache.clear()
        logger.info(f"缓存已清空 ({count} 个条目)")
    except Exception as e:
        logger.error(f"清空缓存失败: {e}")
    logger.info("优雅关闭完成")


signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
