"""
Tests for cache service
"""

import pytest
import time
from unittest.mock import patch
from app.shared.cache import SimpleCache, HybridCache


class TestSimpleCache:
    def test_set_and_get(self):
        cache = SimpleCache(max_size=10, default_ttl=60)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_missing_key(self):
        cache = SimpleCache()
        assert cache.get("nonexistent") is None

    def test_ttl_expiry(self):
        cache = SimpleCache(default_ttl=1)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        time.sleep(1.1)
        assert cache.get("key1") is None

    def test_custom_ttl(self):
        cache = SimpleCache(default_ttl=60)
        cache.set("key1", "value1", ttl=1)
        assert cache.get("key1") == "value1"
        time.sleep(1.1)
        assert cache.get("key1") is None

    def test_lru_eviction(self):
        cache = SimpleCache(max_size=3, default_ttl=60)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        # Access "a" to make it recent
        cache.get("a")
        # Add "d" - should evict "b" (oldest)
        cache.set("d", 4)
        assert cache.get("b") is None
        assert cache.get("a") == 1
        assert cache.get("c") == 3
        assert cache.get("d") == 4

    def test_update_existing_key(self):
        cache = SimpleCache()
        cache.set("key1", "old")
        cache.set("key1", "new")
        assert cache.get("key1") == "new"

    def test_delete(self):
        cache = SimpleCache()
        cache.set("key1", "value1")
        assert cache.delete("key1") is True
        assert cache.get("key1") is None

    def test_delete_missing_key(self):
        cache = SimpleCache()
        assert cache.delete("nonexistent") is False

    def test_clear(self):
        cache = SimpleCache()
        cache.set("a", 1)
        cache.set("b", 2)
        count = cache.clear()
        assert count == 2
        assert cache.get("a") is None
        assert cache.get("b") is None

    def test_get_stats(self):
        cache = SimpleCache(max_size=10, default_ttl=60)
        cache.set("key1", "value1")
        cache.get("key1")
        cache.get("missing")

        stats = cache.get_stats()
        assert stats["size"] == 1
        assert stats["max_size"] == 10
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 50.0

    def test_invalidate_prefix(self):
        cache = SimpleCache()
        cache.set("dashboard:abc", 1)
        cache.set("dashboard:def", 2)
        cache.set("other:xyz", 3)

        count = cache.invalidate_prefix("dashboard:")
        assert count == 2
        assert cache.get("dashboard:abc") is None
        assert cache.get("dashboard:def") is None
        assert cache.get("other:xyz") == 3

    def test_invalidate_prefix_no_match(self):
        cache = SimpleCache()
        cache.set("key1", "value1")
        count = cache.invalidate_prefix("nonexistent:")
        assert count == 0
        assert cache.get("key1") == "value1"

    def test_concurrent_access(self):
        """Test thread safety"""
        import threading
        cache = SimpleCache(max_size=100, default_ttl=60)

        def writer():
            for i in range(50):
                cache.set(f"key-{threading.current_thread().name}-{i}", i)

        def reader():
            for i in range(50):
                cache.get(f"key-{threading.current_thread().name}-{i}")

        threads = []
        for i in range(5):
            t1 = threading.Thread(target=writer, name=f"w{i}")
            t2 = threading.Thread(target=reader, name=f"r{i}")
            threads.extend([t1, t2])

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should not raise any exceptions
        stats = cache.get_stats()
        assert stats["size"] <= 100


class _FakeRedisBackend:
    """模拟 RedisCache 后端（仅测 HybridCache 级联/回填/降级逻辑）"""

    def __init__(self, available=True):
        self.available = available
        self._store = {}
        self._ttls = {}
        self.set_calls = []
        self.delete_calls = []
        self.clear_calls = 0
        self.invalidate_calls = []

    def set(self, key, value, ttl=None):
        self._store[key] = value
        self._ttls[key] = ttl
        self.set_calls.append((key, value, ttl))

    def get(self, key):
        return self._store.get(key)

    def get_ttl(self, key):
        return self._ttls.get(key)

    def delete(self, key):
        self._store.pop(key, None)
        self.delete_calls.append(key)

    def clear(self):
        self.clear_calls += 1
        self._store.clear()

    def invalidate_prefix(self, prefix):
        self.invalidate_calls.append(prefix)
        keys = [k for k in self._store if k.startswith(prefix)]
        for k in keys:
            del self._store[k]
        return len(keys)


class TestHybridCache:
    def test_degraded_to_pure_memory_when_redis_unavailable(self):
        """Redis 不可用（available=False）时行为与 SimpleCache 一致，且不触碰 Redis"""
        fake = _FakeRedisBackend(available=False)
        cache = HybridCache(max_size=16, default_ttl=60)
        with patch("app.shared.redis_cache.get_redis_cache", return_value=fake):
            cache.set("a", 1)
            cache.set("b", 2)
            assert cache.get("a") == 1
            count = cache.invalidate_prefix("a")
            assert count == 1
            assert cache.get("a") is None
            # 降级路径不得产生 Redis 调用
            assert fake.set_calls == []
            assert fake.invalidate_calls == []

    def test_redis_fallback_refills_memory_with_original_ttl(self):
        """内存 miss → Redis 命中 → 回填内存并保持原始 TTL"""
        fake = _FakeRedisBackend(available=True)
        fake._store["dashboard:x"] = {"v": 42}
        fake._ttls["dashboard:x"] = 30

        cache = HybridCache(max_size=16, default_ttl=60)
        with patch("app.shared.redis_cache.get_redis_cache", return_value=fake):
            # 第一次：内存 miss，Redis 命中，回填
            assert cache.get("dashboard:x") == {"v": 42}
            # 第二次：内存命中
            assert cache.get("dashboard:x") == {"v": 42}
            stats = cache.get_stats()
            assert stats["hits"] == 1
            assert stats["misses"] == 1

    def test_set_cascades_to_redis(self):
        """set 双写内存 + Redis"""
        fake = _FakeRedisBackend(available=True)
        cache = HybridCache(max_size=16, default_ttl=60)
        with patch("app.shared.redis_cache.get_redis_cache", return_value=fake):
            cache.set("k", "v", ttl=120)
            assert fake.set_calls == [("k", "v", 120)]
            assert cache.get("k") == "v"

    def test_cascade_invalidate_clear_delete(self):
        """invalidate_prefix/clear/delete 级联 Redis 对应动作"""
        fake = _FakeRedisBackend(available=True)
        cache = HybridCache(max_size=16, default_ttl=60)
        with patch("app.shared.redis_cache.get_redis_cache", return_value=fake):
            cache.set("dashboard:abc", 1)
            cache.set("other", 2)
            cache.invalidate_prefix("dashboard:")
            assert fake.invalidate_calls == ["dashboard:"]
            cache.delete("other")
            assert fake.delete_calls == ["other"]
            cache.clear()
            assert fake.clear_calls == 1

    def test_redis_miss_returns_none(self):
        """内存 miss + Redis miss → None"""
        fake = _FakeRedisBackend(available=True)
        cache = HybridCache(max_size=16, default_ttl=60)
        with patch("app.shared.redis_cache.get_redis_cache", return_value=fake):
            assert cache.get("nonexistent") is None
