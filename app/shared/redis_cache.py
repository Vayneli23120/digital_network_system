"""
Redis 缓存服务

提供基于 Redis 的缓存层，支持 TTL、JSON 序列化、缓存穿透保护。
作为 app/shared/cache.py 内存缓存的补充，用于多进程/分布式部署场景。
"""

import json
from typing import Any, Optional
from loguru import logger

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class RedisCache:
    """Redis 缓存服务"""

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0,
                 password: str = "", default_ttl: int = 60, enabled: bool = True):
        self.default_ttl = default_ttl
        self._client: Optional[redis.Redis] = None

        if not enabled:
            # config.cache.enabled=false 时不建连，HybridCache 自动降级纯内存
            logger.info("Redis 数据缓存未启用（config.cache.enabled=false）")
            return

        if not REDIS_AVAILABLE:
            logger.warning("Redis 未安装，缓存服务不可用")
            return

        try:
            self._client = redis.Redis(
                host=host, port=port, db=db,
                password=password if password else None,
                decode_responses=True,
                socket_connect_timeout=5,
            )
            self._client.ping()
            logger.info(f"Redis 缓存已连接 {host}:{port}/{db}")
        except Exception as e:
            logger.warning(f"Redis 连接失败，缓存服务不可用: {e}")
            self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if not self.available:
            return None
        try:
            raw = self._client.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as e:
            logger.warning(f"Redis GET 失败 {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        if not self.available:
            return False
        try:
            raw = json.dumps(value, default=str)
            expire = ttl or self.default_ttl
            self._client.setex(key, expire, raw)
            return True
        except Exception as e:
            logger.warning(f"Redis SET 失败 {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """删除缓存"""
        if not self.available:
            return False
        try:
            self._client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Redis DELETE 失败 {key}: {e}")
            return False

    def get_ttl(self, key: str) -> Optional[int]:
        """查询键剩余存活秒数（供内存层回填保持原始 TTL，已过期/不存在返回 None）"""
        if not self.available:
            return None
        try:
            ttl = self._client.ttl(key)
            return ttl if ttl and ttl > 0 else None
        except Exception as e:
            logger.warning(f"Redis TTL 查询失败 {key}: {e}")
            return None

    def incr(self, key: str, ttl: Optional[int] = None) -> Optional[int]:
        """原子自增，首次自增时设置 TTL（nx）。返回当前计数，失败返回 None。"""
        if not self.available:
            return None
        try:
            pipe = self._client.pipeline()
            pipe.incr(key)
            if ttl:
                pipe.expire(key, ttl, nx=True)
            results = pipe.execute()
            return results[0]
        except Exception as e:
            logger.warning(f"Redis INCR 失败 {key}: {e}")
            return None

    def invalidate_prefix(self, prefix: str) -> int:
        """清除匹配前缀的所有键"""
        if not self.available:
            return 0
        try:
            keys = self._client.keys(f"{prefix}*")
            if keys:
                return self._client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Redis 批量删除失败 {prefix}: {e}")
            return 0

    def clear(self) -> int:
        """清空当前 DB 的所有缓存"""
        if not self.available:
            return 0
        try:
            return self._client.flushdb()
        except Exception as e:
            logger.warning(f"Redis FLUSHDB 失败: {e}")
            return 0

    def get_stats(self) -> dict:
        """获取 Redis 缓存统计"""
        if not self.available:
            return {"available": False}
        try:
            info = self._client.info("memory")
            return {
                "available": True,
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "connected_clients": self._client.info("clients").get("connected_clients", 0),
            }
        except Exception as e:
            return {"available": False, "error": str(e)}


# 全局缓存实例
_redis_cache: Optional[RedisCache] = None


def get_redis_cache() -> RedisCache:
    """获取 Redis 缓存实例（尊重 config.cache.enabled：False 时不建连）"""
    global _redis_cache
    if _redis_cache is None:
        from app.shared.config import get_config
        config = get_config()
        cc = config.cache
        _redis_cache = RedisCache(
            host=cc.host,
            port=cc.port,
            db=cc.db,
            password=cc.password,
            default_ttl=cc.default_ttl,
            enabled=cc.enabled,
        )
    return _redis_cache
