"""Tests for sentinella.collectors.base — BaseCollector and CollectorResult."""
import pytest
from sentinella.collectors.base import BaseCollector, CollectorResult


class TestCollectorResult:
    def test_create(self):
        r = CollectorResult(source="test", data={"a": 1}, records_count=5)
        assert r.source == "test"
        assert r.data == {"a": 1}
        assert r.records_count == 5
        assert r.collected_at is not None

    def test_repr(self):
        r = CollectorResult(source="gdelt", data={}, records_count=10)
        assert "gdelt" in repr(r)
        assert "10" in repr(r)


class TestBaseCollector:
    @pytest.mark.asyncio
    async def test_safe_collect_catches_error(self):
        class BrokenCollector(BaseCollector):
            name = "broken"
            display_name = "Broken"

            async def collect(self):
                raise RuntimeError("boom")

        c = BrokenCollector()
        result = await c.safe_collect()
        assert result is None

    @pytest.mark.asyncio
    async def test_safe_collect_returns_result(self):
        class GoodCollector(BaseCollector):
            name = "good"
            display_name = "Good"

            async def collect(self):
                return CollectorResult("good", {"ok": True}, 1)

        c = GoodCollector()
        result = await c.safe_collect()
        assert result is not None
        assert result.source == "good"
