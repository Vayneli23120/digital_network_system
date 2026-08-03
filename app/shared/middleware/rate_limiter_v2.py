"""优化的API限流中间件

分层限流策略：
- GET 请求：较宽松（读取操作）
- POST/PUT/DELETE：较严格（写入操作）
- 认证端点：严格限制（防止暴力破解）

Redis 化（批次三 3.4-5）：
- RateLimiter 支持可选 Redis 后端（固定窗口 INCR/EXPIRE），多 worker 共享额度；
- Redis 不可用或 config.cache.enabled=false 时自动降级纯内存滑动窗口，行为不变。
"""

import time
from collections import defaultdict
from typing import Dict, Optional, Tuple

from fastapi import Request
from starlette.responses import JSONResponse


class RateLimiter:
    """限流器 - 支持 Redis 固定窗口（多 worker 共享）+ 内存滑动窗口降级"""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60, key_prefix: str = "rl"):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # Redis 键前缀，区分 get/write/auth 三套限流额度
        self.key_prefix = key_prefix
        # 内存滑动窗口降级路径 {identity: [(timestamp, path), ...]}
        self._requests: Dict[str, list] = defaultdict(list)
        # 客户端最后清理时间，防止内存无限增长
        self._last_cleanup: Dict[str, float] = defaultdict(float)
        self._cleanup_interval = 300  # 5分钟清理一次
        self._redis: Optional[object] = None

    def _redis_backend(self):
        """惰性获取 Redis 后端（单例）"""
        if self._redis is None:
            from app.shared.redis_cache import get_redis_cache
            self._redis = get_redis_cache()
        return self._redis

    def _cleanup(self, identity: str, now: float):
        """清理过期的请求记录 - 优化版"""
        cutoff = now - self.window_seconds
        # 只保留窗口内的请求
        self._requests[identity] = [
            (ts, path) for ts, path in self._requests[identity]
            if ts > cutoff
        ]
        # 如果清理后为空，删除该IP记录
        if not self._requests[identity]:
            del self._requests[identity]
            if identity in self._last_cleanup:
                del self._last_cleanup[identity]

    def _redis_window_key(self, identity: str, now: float) -> str:
        """固定窗口 Redis 键：rl:{prefix}:{identity}:{窗口号}"""
        window_id = int(now // self.window_seconds)
        return f"{self.key_prefix}:{identity}:{window_id}"

    def _redis_is_allowed(self, identity: str) -> Optional[Tuple[bool, int, int]]:
        """Redis 固定窗口限流，失败返回 None 触发内存降级"""
        backend = self._redis_backend()
        if not backend.available:
            return None
        try:
            now = time.time()
            key = self._redis_window_key(identity, now)
            # INCR 原子自增，首次自增时设置窗口 TTL（nx）
            count = backend.incr(key, ttl=self.window_seconds)
            if count is None:
                return None
            remaining = max(0, self.max_requests - count)
            if count <= self.max_requests:
                return True, remaining, 0
            # 超限：重试时间 = 当前窗口剩余秒数
            retry_after = backend.get_ttl(key) or self.window_seconds
            return False, 0, int(retry_after)
        except Exception:
            return None

    def is_allowed(self, identity: str, path: str) -> Tuple[bool, int, int]:
        """检查请求是否允许

        Args:
            identity: 限流主体（IP 或用户 ID）
            path: 请求路径

        Returns:
            (是否允许, 剩余请求数, 重试时间)
        """
        # Redis 优先（多 worker 共享），失败自动降级内存
        redis_result = self._redis_is_allowed(identity)
        if redis_result is not None:
            return redis_result

        now = time.time()
        self._cleanup(identity, now)

        requests_in_window = len(self._requests[identity])
        remaining = max(0, self.max_requests - requests_in_window)
        retry_after = 0

        if requests_in_window >= self.max_requests:
            # 计算最早过期的时间
            if self._requests[identity]:
                oldest = min(ts for ts, _ in self._requests[identity])
                retry_after = int(oldest + self.window_seconds - now) + 1
            return False, 0, retry_after

        self._requests[identity].append((now, path))
        return True, remaining - 1, 0

    def get_status(self, identity: str) -> Dict:
        """获取客户端限流状态（形状与 v1 一致）"""
        backend = self._redis_backend()
        if backend.available:
            try:
                now = time.time()
                key = self._redis_window_key(identity, now)
                count = backend.get(key)
                requests_in_window = count if isinstance(count, int) else 0
                return {
                    "client_ip": identity,
                    "requests_in_window": requests_in_window,
                    "max_requests": self.max_requests,
                    "window_seconds": self.window_seconds,
                    "remaining": max(0, self.max_requests - requests_in_window),
                }
            except Exception:
                pass  # Redis 查询失败走内存路径

        now = time.time()
        self._cleanup(identity, now)
        return {
            "client_ip": identity,
            "requests_in_window": len(self._requests[identity]),
            "max_requests": self.max_requests,
            "window_seconds": self.window_seconds,
            "remaining": max(0, self.max_requests - len(self._requests[identity])),
        }


# 分层限流配置 - 放宽限制以适应正常高频使用
# key_prefix 区分 Redis 中的三套独立额度（多 worker 共享互不干扰）
GET_LIMITER = RateLimiter(max_requests=200, window_seconds=60, key_prefix="rl:get")      # GET: 200/分钟
WRITE_LIMITER = RateLimiter(max_requests=60, window_seconds=60, key_prefix="rl:write")   # 写入: 60/分钟
AUTH_LIMITER = RateLimiter(max_requests=15, window_seconds=60, key_prefix="rl:auth")     # 认证: 15/分钟

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
    "/api/dashboard",           # 仪表板聚合数据
    "/api/dashboard/summary",   # 仪表板摘要
    "/api/devices",             # 设备列表
    "/api/faults",              # 故障列表
    "/api/notifications",       # 通知
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

        # 优先按用户限流（auth 中间件已写入 scope["state"]["user_id"]，切片二启用）
        user_id = None
        scope_state = scope.get("state")
        if scope_state:
            user_id = scope_state.get("user_id")

        if user_id is not None:
            identity = str(user_id)
        else:
            # 获取客户端 IP
            client = scope.get("client")
            identity = client[0] if client else "unknown"
            x_forwarded = headers.get(b"x-forwarded-for")
            if x_forwarded:
                identity = x_forwarded.decode().split(",")[0].strip()

        # 选择限流器
        limiter = self.get_limiter(method, path)
        allowed, remaining, retry_after = limiter.is_allowed(identity, path)

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
