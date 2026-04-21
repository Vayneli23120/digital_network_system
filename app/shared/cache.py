"""
简单内存缓存

带 TTL 的 LRU 缓存，用于缓存 Dashboard、统计查询等读多写少的数据。
"""

import time
import hashlib
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


# 全局缓存实例
cache = SimpleCache(max_size=256, default_ttl=60)


def _cache_key(prefix: str, **kwargs) -> str:
    """生成缓存键"""
    raw = str(sorted(kwargs.items()))
    h = hashlib.md5(raw.encode()).hexdigest()[:8]
    return f"{prefix}:{h}"


def cached(key_prefix: str, ttl: Optional[int] = None):
    """缓存装饰器

    用法:
        @cached("dashboard", ttl=30)
        def get_dashboard_data():
            return heavy_computation()
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{key_prefix}:{hash(str(args) + str(sorted(kwargs.items())))}"
            result = cache.get(cache_key)
            if result is not None:
                return result

            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl=ttl)
            return result
        return wrapper
    return decorator
