"""统一认证中间件。

正式模式要求有效 JWT；仅 ``app.debug=true`` 且 ``auth_enabled=false``
时允许开发身份旁路。
"""
from functools import wraps
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from app.features.auth.identity import (
    development_auth_bypass_enabled,
    resolve_principal,
)
from app.shared.database import get_db_manager
from starlette.concurrency import run_in_threadpool


PUBLIC_EXACT_PATHS = frozenset({
    "/api/auth/login",
    "/api/auth/status",
    "/api/auth/sso/status",
    "/api/auth/sso/login",
    "/api/auth/sso/callback",
    "/health",
    "/ready",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/",
    "/login",
    "/favicon.ico",
})


def is_public_path(path: str) -> bool:
    """仅放行明确的公共 API 与加载登录页所需的静态资源。"""
    if path in PUBLIC_EXACT_PATHS:
        return True
    if path.startswith(("/assets/", "/docs/")):
        return True
    if path.startswith(("/health/", "/ready/", "/openapi.json/", "/redoc/")):
        return False
    # 告警 Webhook：由 ALERT_WEBHOOK_TOKEN 自行鉴权（fail-closed），
    # 不受 JWT 中间件管辖（Alertmanager 无法携带 JWT）。
    if path.startswith("/api/alerts/webhook/"):
        return True
    # Vue 前端路由本身不含敏感数据；API、照片、代理和扫描终端仍受保护。
    return not path.startswith(("/api/", "/photos/", "/grafana/", "/static/", "/scanner"))


def _authentication_error(detail: str, status_code: int = status.HTTP_401_UNAUTHORIZED) -> JSONResponse:
    headers = {"WWW-Authenticate": "Bearer"} if status_code == status.HTTP_401_UNAUTHORIZED else None
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail},
        headers=headers,
    )


async def auth_middleware(request: Request, call_next):
    """正式环境仅接受 JWT；显式 debug 开发模式允许旁路。"""
    if request.method == "OPTIONS":
        return await call_next(request)

    if development_auth_bypass_enabled():
        return await call_next(request)

    if is_public_path(request.url.path):
        return await call_next(request)

    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return _authentication_error("Missing or invalid authentication token")

    db = get_db_manager().get_session()
    try:
        try:
            credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
            principal = await run_in_threadpool(resolve_principal, request, credentials, db)
            request.state.principal = principal
            request.state.user_id = principal.user_id
        except HTTPException as exc:
            return _authentication_error(str(exc.detail), exc.status_code)
        except Exception:
            return _authentication_error("Token expired or invalid")
        return await call_next(request)
    finally:
        await run_in_threadpool(db.close)


def require_auth(func=None, *, roles=None):
    """
    路由装饰器 - 要求用户登录
    可选参数 roles: 指定允许的角色列表

    用法:
        @router.get("/admin")
        @require_auth(roles=["admin"])
        async def admin_only():
            ...
    """
    def decorator(f):
        @wraps(f)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request")
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if request is None or not getattr(request.state, 'user_id', None):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )

            if roles:
                user_roles = getattr(request.state, 'roles', [])
                if not any(r in user_roles for r in roles):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Insufficient permissions"
                    )

            return await f(*args, **kwargs)
        return wrapper

    if func is not None:
        return decorator(func)
    return decorator
