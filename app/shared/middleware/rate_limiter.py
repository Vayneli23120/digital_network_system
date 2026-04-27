"""
API 限流中间件

简单的基于内存的请求频率限制，防止 API 滥用。
使用滑动窗口算法。
"""

import time
from collections import defaultdict
from typing import Dict, Tuple
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimiter:
    """基于内存的滑动窗口限流器"""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        """
        Args:
            max_requests: 窗口内最大请求数
            window_seconds: 窗口大小（秒）
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # {client_ip: [(timestamp, path), ...]}
        self._requests: Dict[str, list] = defaultdict(list)

    def _cleanup(self, client_ip: str, now: float):
        """清理过期的请求记录"""
        cutoff = now - self.window_seconds
        self._requests[client_ip] = [
            (ts, path) for ts, path in self._requests[client_ip]
            if ts > cutoff
        ]
        # 如果该 IP 没有活跃请求，从 dict 中移除，防止无限增长
        if not self._requests[client_ip]:
            del self._requests[client_ip]

    def is_allowed(self, client_ip: str, path: str) -> Tuple[bool, int]:
        """检查请求是否允许

        Returns:
            (是否允许, 剩余请求数)
        """
        now = time.time()
        self._cleanup(client_ip, now)

        requests_in_window = len(self._requests[client_ip])
        remaining = max(0, self.max_requests - requests_in_window)

        if requests_in_window >= self.max_requests:
            return False, 0

        self._requests[client_ip].append((now, path))
        return True, remaining - 1

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


# 默认限流器：60 请求/分钟
default_limiter = RateLimiter(max_requests=60, window_seconds=60)

# 白名单路径（不限流）
WHITELIST_PATHS = ["/health", "/docs", "/openapi.json", "/redoc"]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI 限流中间件"""

    def __init__(self, app, limiter: RateLimiter = None):
        super().__init__(app)
        self.limiter = limiter or default_limiter

    async def dispatch(self, request: Request, call_next):
        # 跳过白名单
        if any(request.url.path.startswith(p) for p in WHITELIST_PATHS):
            return await call_next(request)

        # 获取客户端 IP
        client_ip = request.client.host
        if request.headers.get("x-forwarded-for"):
            client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()

        allowed, remaining = self.limiter.is_allowed(client_ip, request.url.path)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too Many Requests",
                    "detail": f"请求频率超限，请在 {self.limiter.window_seconds} 秒后重试",
                    "retry_after": self.limiter.window_seconds,
                },
                headers={"Retry-After": str(self.limiter.window_seconds)},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.limiter.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window"] = str(self.limiter.window_seconds)

        return response


def get_rate_limiter():
    """获取默认限流器实例"""
    return default_limiter
