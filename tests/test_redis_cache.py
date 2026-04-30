"""
Tests for Redis cache service (without requiring actual Redis server)
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from app.shared.redis_cache import RedisCache, get_redis_cache


class TestRedisCacheUnavailable:
    def test_not_available_without_redis(self):
        with patch("app.shared.redis_cache.REDIS_AVAILABLE", False):
            cache = RedisCache()
            assert cache.available is False

    def test_get_returns_none_when_unavailable(self):
        cache = RedisCache()
        cache._client = None
        assert cache.get("any_key") is None

    def test_set_returns_false_when_unavailable(self):
        cache = RedisCache()
        cache._client = None
        assert cache.set("key", "value") is False

    def test_delete_returns_false_when_unavailable(self):
        cache = RedisCache()
        cache._client = None
        assert cache.delete("key") is False

    def test_clear_returns_zero_when_unavailable(self):
        cache = RedisCache()
        cache._client = None
        assert cache.clear() == 0


class TestRedisCacheWithMock:
    @pytest.fixture
    def mock_redis(self):
        client = MagicMock()
        client.ping.return_value = True
        client.get.return_value = None
        client.setex.return_value = True
        client.keys.return_value = []
        client.delete.return_value = 0
        client.info.return_value = {"used_memory_human": "1.00M", "connected_clients": 1}
        return client

    def test_available_with_connected_client(self, mock_redis):
        cache = RedisCache()
        cache._client = mock_redis
        assert cache.available is True

    def test_set_and_get_json(self, mock_redis):
        cache = RedisCache()
        cache._client = mock_redis

        mock_redis.get.return_value = '{"name": "test", "count": 42}'
        cache.set("my_key", {"name": "test", "count": 42})

        result = cache.get("my_key")
        assert result == {"name": "test", "count": 42}

    def test_set_with_custom_ttl(self, mock_redis):
        cache = RedisCache(default_ttl=60)
        cache._client = mock_redis

        cache.set("key", "value", ttl=120)
        mock_redis.setex.assert_called_once()

    def test_delete_key(self, mock_redis):
        cache = RedisCache()
        cache._client = mock_redis

        cache.delete("my_key")
        mock_redis.delete.assert_called_once_with("my_key")

    def test_invalidate_prefix(self, mock_redis):
        cache = RedisCache()
        cache._client = mock_redis
        mock_redis.keys.return_value = ["dashboard:abc", "dashboard:def"]

        count = cache.invalidate_prefix("dashboard:")
        assert count == 0  # mock returns 0
        mock_redis.keys.assert_called_once_with("dashboard:*")

    def test_get_stats(self, mock_redis):
        cache = RedisCache()
        cache._client = mock_redis

        stats = cache.get_stats()
        assert stats["available"] is True
        assert "used_memory_human" in stats


class TestGetRedisCache:
    def test_singleton_returns_same_instance(self):
        import app.shared.redis_cache as rc_module
        rc_module._redis_cache = None

        with patch("app.shared.redis_cache.RedisCache") as MockRedis:
            MockRedis.return_value = MagicMock(available=False)
            s1 = get_redis_cache()
            s2 = get_redis_cache()
            assert s1 is s2

        rc_module._redis_cache = None
