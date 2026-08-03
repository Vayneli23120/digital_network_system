"""
简单内存缓存

带 TTL 的 LRU 缓存，用于缓存 Dashboard、统计查询等读多写少的数据。
"""

import time
import hashlib
import inspect
import threading
from typing import Any, Optional
from collections import OrderedDict
from loguru import logger

# 缓存 TTL 常量（供路由层使用）
_DASHBOARD_TTL = 30  # Dashboard 摘要缓存 30 秒
_TREND_TTL = 60  # 趋势数据缓存 60 秒
_DEVICE_LIST_TTL = 20  # 设备列表缓存 20 秒


class SimpleCache:
    """带 TTL 的内存缓存"""

    def __init__(self, max_size: int = 256, default_ttl: int = 60):
        self._cache: OrderedDict = OrderedDict()
        self._locks: dict = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            value, expires_at = self._cache[key]
            if time.time() > expires_at:
                # 过期，删除
                del self._cache[key]
                self._misses += 1
                return None

            # LRU: 移到末尾表示最近使用
            self._cache.move_to_end(key)
            self._hits += 1
            return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值"""
        if ttl is None:
            ttl = self._default_ttl

        expires_at = time.time() + ttl

        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self._cache[key] = (value, expires_at)
            else:
                if len(self._cache) >= self._max_size:
                    # 删除最旧的
                    self._cache.popitem(last=False)
                self._cache[key] = (value, expires_at)

    def delete(self, key: str) -> bool:
        """删除缓存值"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> int:
        """清空缓存，返回删除的数量"""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    def get_stats(self) -> dict:
        """获取缓存统计信息"""
        with self._lock:
            total = self._hits + self._misses
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(self._hits / total * 100, 1) if total > 0 else 0,
                "default_ttl": self._default_ttl,
            }

    def invalidate_prefix(self, prefix: str) -> int:
        """使匹配前缀的所有键失效"""
        with self._lock:
            keys_to_delete = [k for k in self._cache if k.startswith(prefix)]
            for k in keys_to_delete:
                del self._cache[k]
            return len(keys_to_delete)


class HybridCache(SimpleCache):
    """内存 LRU + Redis 兜底的组合缓存。

    内存层沿用 SimpleCache 的 LRU/TTL 语义；Redis 层作为可选的分布式兜底：
    - ``get``：内存 miss 时回查 Redis，命中则回填内存（保持原始 TTL）。
    - ``set``/``delete``/``clear``/``invalidate_prefix``：内存动作后级联 Redis。

    Redis 不可用或 ``config.cache.enabled=false`` 时自动降级为纯内存，
    行为与 SimpleCache 完全一致，调用方无感。
    """

    def __init__(self, max_size: int = 256, default_ttl: int = 60):
        super().__init__(max_size=max_size, default_ttl=default_ttl)
        self._redis: Optional[Any] = None

    def _redis_backend(self):
        """惰性获取 Redis 后端（单例）"""
        if self._redis is None:
            from app.shared.redis_cache import get_redis_cache
            self._redis = get_redis_cache()
        return self._redis

    def get(self, key: str) -> Optional[Any]:
        value = super().get(key)
        if value is not None:
            return value
        redis = self._redis_backend()
        if redis.available:
            remote = redis.get(key)
            if remote is not None:
                super().set(key, remote, ttl=redis.get_ttl(key))
                return remote
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        super().set(key, value, ttl=ttl)
        redis = self._redis_backend()
        if redis.available:
            redis.set(key, value, ttl=ttl)

    def delete(self, key: str) -> bool:
        removed = super().delete(key)
        redis = self._redis_backend()
        if redis.available:
            redis.delete(key)
        return removed

    def clear(self) -> int:
        count = super().clear()
        redis = self._redis_backend()
        if redis.available:
            redis.clear()
        return count

    def invalidate_prefix(self, prefix: str) -> int:
        count = super().invalidate_prefix(prefix)
        redis = self._redis_backend()
        if redis.available:
            redis.invalidate_prefix(prefix)
        return count


# 全局缓存实例（HybridCache：内存 + Redis 兜底）
cache = HybridCache(max_size=256, default_ttl=60)


def _cache_key(prefix: str, **kwargs) -> str:
    """生成确定性缓存键（完整 md5，不受 PYTHONHASHSEED 影响）"""
    raw = str(sorted(kwargs.items()))
    h = hashlib.md5(raw.encode()).hexdigest()
    return f"{prefix}:{h}"


def cached(key_prefix: str, ttl: Optional[int] = None):
    """缓存装饰器

    用法:
        @cached("dashboard", ttl=30)
        def get_dashboard_data():
            return heavy_computation()

    缓存键由签名绑定后的实参确定生成（确定性），不使用内置 hash()
    （其值受 PYTHONHASHSEED 影响且对含 repr 地址的对象不稳定）。
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            bound = inspect.signature(func).bind(*args, **kwargs)
            bound.apply_defaults()
            cache_key = _cache_key(key_prefix, **dict(bound.arguments))
            result = cache.get(cache_key)
            if result is not None:
                return result

            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl=ttl)
            return result
        return wrapper
    return decorator
