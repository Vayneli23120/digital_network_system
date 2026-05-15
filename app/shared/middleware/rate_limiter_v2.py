"""优化的API限流中间件

分层限流策略：
- GET 请求：较宽松（读取操作）
- POST/PUT/DELETE：较严格（写入操作）
- 认证端点：严格限制（防止暴力破解）
"""

import time
from collections import defaultdict
from typing import Dict, Tuple
from fastapi import Request
from starlette.responses import JSONResponse


class TieredRateLimiter:
    """分层限流器 - 根据请求类型使用不同限流策略"""

    def __init__(self):
        # GET 请求：较宽松，适合频繁刷新
        self.get_limiter = RateLimiter(max_requests=120, window_seconds=60)
        # POST/PUT/DELETE：中等严格
        self.write_limiter = RateLimiter(max_requests=30, window_seconds=60)
        # 认证相关：严格限制
        self.auth_limiter = RateLimiter(max_requests=10, window_seconds=60)

    def get_limiter_for_path(self, method: str, path: str) -> 'RateLimiter':
        """根据请求方法和路径选择限流器"""
        # 认证端点
        if path.startswith('/auth') or path.startswith('/login'):
            return self.auth_limiter
        # GET 请求
        if method == 'GET':
            return self.get_limiter
        # 写入操作
        return self.write_limiter


class RateLimiter:
    """基于内存的滑动窗口限流器 - 优化版"""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # {client_ip: [(timestamp, path), ...]}
        self._requests: Dict[str, list] = defaultdict(list)
        # 客户端最后清理时间，防止内存无限增长
        self._last_cleanup: Dict[str, float] = defaultdict(float)
        self._cleanup_interval = 300  # 5分钟清理一次

    def _cleanup(self, client_ip: str, now: float):
        """清理过期的请求记录 - 优化版"""
        # 只在间隔时间后才清理，减少CPU占用
        if now - self._last_cleanup[client_ip] < self._cleanup_interval:
            cutoff = now - self.window_seconds
            # 只保留窗口内的请求
            original_count = len(self._requests[client_ip])
            self._requests[client_ip] = [
                (ts, path) for ts, path in self._requests[client_ip]
                if ts > cutoff
            ]
            # 如果清理后为空，删除该IP记录
            if not self._requests[client_ip]:
                del self._requests[client_ip]
                if client_ip in self._last_cleanup:
                    del self._last_cleanup[client_ip]
            else:
                self._last_cleanup[client_ip] = now

    def is_allowed(self, client_ip: str, path: str) -> Tuple[bool, int, int]:
        """检查请求是否允许

        Returns:
            (是否允许, 剩余请求数, 重试时间)
        """
        now = time.time()
        self._cleanup(client_ip, now)

        requests_in_window = len(self._requests[client_ip])
        remaining = max(0, self.max_requests - requests_in_window)
        retry_after = 0

        if requests_in_window >= self.max_requests:
            # 计算最早过期的时间
            if self._requests[client_ip]:
                oldest = min(ts for ts, _ in self._requests[client_ip])
                retry_after = int(oldest + self.window_seconds - now) + 1
            return False, 0, retry_after

        self._requests[client_ip].append((now, path))
        return True, remaining - 1, 0

    def get_status(self, client_ip: str) -> Dict:
        """获取客户端限流状态"""
        now = time.time()
        self._cleanup(client_ip, now)
        return {
            "client_ip": client_ip,
            "requests_in_window": len(self._requests[client_ip]),
            "max_requests": self.max_requests,
            "window_seconds": self.window_seconds,
            "remaining": max(0, self.max_requests - len(self._requests[client_ip])),
        }


# 分层限流配置
GET_LIMITER = RateLimiter(max_requests=120, window_seconds=60)      # GET: 120/分钟
WRITE_LIMITER = RateLimiter(max_requests=40, window_seconds=60)     # 写入: 40/分钟
AUTH_LIMITER = RateLimiter(max_requests=10, window_seconds=60)    # 认证: 10/分钟

# 白名单路径（不限流）
WHITELIST_PATHS = [
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/static",
]

# 批量查询白名单（允许更高频率）
BATCH_WHITELIST = [
    "/api/dashboard",  # 仪表板聚合数据
]


class RateLimitMiddleware:
    """FastAPI 限流中间件 - 优化版，支持分层限流"""

    def __init__(self, app, get_limiter=None):
        self.app = app
        self.get_limiter = get_limiter or self._default_get_limiter

    def _default_get_limiter(self, method: str, path: str) -> RateLimiter:
        """根据请求选择限流器"""
        # 批量查询端点放宽限制
        if path in BATCH_WHITELIST:
            return GET_LIMITER  # 使用较宽松的GET限流

        # 认证端点严格限制
        if path.startswith("/auth/") or path.startswith("/login"):
            return AUTH_LIMITER

        # 按HTTP方法选择
        if method == "GET":
            return GET_LIMITER
        else:
            return WRITE_LIMITER

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        path = scope.get("path", "")
        method = scope.get("method", "GET")

        # 跳过白名单
        if any(path.startswith(p) for p in WHITELIST_PATHS):
            await self.app(scope, receive, send)
            return

        # 跳过 multipart/form-data 请求（文件上传）
        content_type = (
            headers.get(b"content-type", b"").decode()
            if b"content-type" in headers
            else ""
        )
        if "multipart/form-data" in content_type:
            await self.app(scope, receive, send)
            return

        # 获取客户端 IP
        client = scope.get("client")
        client_ip = client[0] if client else "unknown"
        x_forwarded = headers.get(b"x-forwarded-for")
        if x_forwarded:
            client_ip = x_forwarded.decode().split(",")[0].strip()

        # 选择限流器
        limiter = self.get_limiter(method, path)
        allowed, remaining, retry_after = limiter.is_allowed(client_ip, path)

        if not allowed:
            response = JSONResponse(
                status_code=429,
                content={
                    "error": "Too Many Requests",
                    "detail": f"请求频率超限，请在 {retry_after} 秒后重试",
                    "retry_after": retry_after,
                    "code": "RATE_LIMIT_EXCEEDED",
                },
            )
            await response(scope, receive, send)
            return

        # 添加限流响应头
        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                existing_headers = list(message.get("headers", []))
                existing_headers.append(
                    [b"X-RateLimit-Limit", str(limiter.max_requests).encode()]
                )
                existing_headers.append(
                    [b"X-RateLimit-Remaining", str(remaining).encode()]
                )
                existing_headers.append(
                    [b"X-RateLimit-Window", str(limiter.window_seconds).encode()]
                )
                message["headers"] = existing_headers
            await send(message)

        await self.app(scope, receive, send_with_headers)


def get_rate_limiter():
    """获取默认限流器实例"""
    return GET_LIMITER
