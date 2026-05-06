"""API 限流中间件

简单的基于内存的请求频率限制，防止 API 滥用。
使用滑动窗口算法。
"""

import time
from collections import defaultdict
from typing import Dict, Tuple
from fastapi import Request
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


class RateLimitMiddleware:
    """FastAPI 限流中间件 - 使用纯 ASGI middleware 模式"""

    def __init__(self, app, limiter: RateLimiter = None):
        self.app = app
        self.limiter = limiter or default_limiter

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # 从 scope 获取信息，避免创建 Request 对象读取 body
        headers = dict(scope.get("headers", []))
        path = scope.get("path", "")
        method = scope.get("method", "GET")

        # 跳过白名单
        if any(path.startswith(p) for p in WHITELIST_PATHS):
            await self.app(scope, receive, send)
            return

        # 跳过 multipart/form-data 请求（文件上传）
        content_type = headers.get(b"content-type", b"").decode() if b"content-type" in headers else ""
        if "multipart/form-data" in content_type:
            await self.app(scope, receive, send)
            return

        # 获取客户端 IP
        client = scope.get("client")
        client_ip = client[0] if client else "unknown"
        x_forwarded = headers.get(b"x-forwarded-for")
        if x_forwarded:
            client_ip = x_forwarded.decode().split(",")[0].strip()

        allowed, remaining = self.limiter.is_allowed(client_ip, path)

        if not allowed:
            response = JSONResponse(
                status_code=429,
                content={
                    "error": "Too Many Requests",
                    "detail": f"请求频率超限，请在 {self.limiter.window_seconds} 秒后重试",
                    "retry_after": self.limiter.window_seconds,
                },
            )
            await response(scope, receive, send)
            return

        # 创建一个自定义 send 来添加限流头
        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                # ASGI headers 是 list of [bytes, bytes]
                existing_headers = list(message.get("headers", []))
                # 添加限流头（bytes 格式）
                existing_headers.append([b"X-RateLimit-Limit", str(self.limiter.max_requests).encode()])
                existing_headers.append([b"X-RateLimit-Remaining", str(remaining).encode()])
                existing_headers.append([b"X-RateLimit-Window", str(self.limiter.window_seconds).encode()])
                message["headers"] = existing_headers
            await send(message)

        await self.app(scope, receive, send_with_headers)


def get_rate_limiter():
    """获取默认限流器实例"""
    return default_limiter
