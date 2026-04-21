"""
Tests for cache service
"""

import pytest
import time
from app.services.cache import SimpleCache


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
