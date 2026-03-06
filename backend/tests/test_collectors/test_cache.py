"""Tests for sentinella.collectors.cache — in-memory cache."""
import time
from sentinella.collectors import cache


class TestCache:
    def setup_method(self):
        """Reset cache state before each test."""
        cache._store.clear()

    def test_set_and_get(self):
        cache.set("key1", {"data": 42}, ttl_seconds=300)
        result = cache.get("key1")
        assert result == {"data": 42}

    def test_get_missing_key_returns_none(self):
        assert cache.get("nonexistent") is None

    def test_expired_key_returns_none(self):
        cache.set("temp", "value", ttl_seconds=0)
        time.sleep(0.01)
        assert cache.get("temp") is None

    def test_invalidate(self):
        cache.set("key2", "value", ttl_seconds=300)
        cache.invalidate("key2")
        assert cache.get("key2") is None

    def test_invalidate_nonexistent_no_error(self):
        cache.invalidate("nope")  # should not raise

    def test_status_returns_active_entries(self):
        cache.set("active", "v", ttl_seconds=3600)
        s = cache.status()
        assert "active" in s
        assert s["active"]["ttl_min"] == 60

    def test_status_excludes_expired(self):
        cache.set("expired", "v", ttl_seconds=0)
        time.sleep(0.01)
        s = cache.status()
        assert "expired" not in s

    def test_overwrite_key(self):
        cache.set("key", "old", ttl_seconds=300)
        cache.set("key", "new", ttl_seconds=600)
        assert cache.get("key") == "new"
