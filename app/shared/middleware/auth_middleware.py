"""
认证中间件 - 预留用于 v1.1 的用户认证系统

当前版本 (v1.0) 不启用认证。
设置 auth_enabled: true 后，所有 API 请求需要携带有效 JWT Token。
"""
from functools import wraps
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from app.shared.config import settings


async def auth_middleware(request: Request, call_next):
    """FastAPI 中间件 - 在 auth_enabled 时拦截未认证请求"""
    if not getattr(settings, 'auth_enabled', False):
        return await call_next(request)

    # 跳过不需要认证的路由
    skip_paths = [
        "/auth/login",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/health",
    ]
    if any(request.url.path.startswith(path) for path in skip_paths):
        return await call_next(request)

    # 验证 Token
    token = request.headers.get("Authorization")
    if not token:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Missing authentication token"}
        )

    try:
        scheme, _, token_value = token.partition(" ")
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid token scheme")

        payload = jwt.decode(
            token_value,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        request.state.user_id = user_id
        request.state.token_payload = payload

    except JWTError:
        raise HTTPException(status_code=401, detail="Token expired or invalid")

    return await call_next(request)


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
