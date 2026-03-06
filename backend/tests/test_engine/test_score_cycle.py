"""Tests for engine/score.py — run_score_cycle with mocked collectors."""
import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sentinella.db import Base
from sentinella.models.score import ScoreSnapshot, DimensionScore
from sentinella.models.source import SourceStatus
from sentinella.collectors.base import CollectorResult

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(TEST_DB_URL, echo=False)
TestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


def _make_mock_collector(name, data, records=0):
    mock = AsyncMock()
    mock.name = name
    mock.display_name = name.upper()
    mock.safe_collect = AsyncMock(return_value=CollectorResult(source=name, data=data, records_count=records))
    return mock


class TestRunScoreCycle:
    @pytest.mark.asyncio
    async def test_full_cycle_with_mocks(self):
        from sentinella.engine.score import run_score_cycle

        gdelt_data = {
            "geopolitica": {"article_count": 80, "negative_ratio": 0.35},
            "terrorismo": {"article_count": 15, "negative_ratio": 0.55},
            "cyber": {"article_count": 5, "negative_ratio": 0.30},
            "eversione": {"article_count": 20, "negative_ratio": 0.40},
            "militare": {"article_count": 20, "negative_ratio": 0.30},
            "sociale": {"article_count": 25, "negative_ratio": 0.25},
        }

        mocks = {
            "GdeltCollector": _make_mock_collector("gdelt", gdelt_data, 80),
            "NewsRssCollector": _make_mock_collector("rss", {"by_dimension": {}, "total": 0}, 0),
            "CsirtCollector": _make_mock_collector("csirt", {"bulletin_count": 5, "critical_count": 1, "total_cve": 10, "infra_affected_count": 0}, 5),
            "GoogleTrendsCollector": _make_mock_collector("trends", {"terrorismo": {"mean": 20}, "sociale": {"mean": 30}, "militare": {"mean": 15}}, 3),
            "AcledCollector": _make_mock_collector("acled", {"protests": 3, "riots": 1, "total_events": 4}, 4),
            "AdsbCollector": _make_mock_collector("adsb", {"total_flights": 5, "bases": {}}, 5),
            "MegaRssCollector": _make_mock_collector("mega_rss", {"total": 0, "headlines": []}, 0),
        }

        with patch("sentinella.collectors.GdeltCollector", return_value=mocks["GdeltCollector"]), \
             patch("sentinella.collectors.NewsRssCollector", return_value=mocks["NewsRssCollector"]), \
             patch("sentinella.collectors.CsirtCollector", return_value=mocks["CsirtCollector"]), \
             patch("sentinella.collectors.GoogleTrendsCollector", return_value=mocks["GoogleTrendsCollector"]), \
             patch("sentinella.collectors.AcledCollector", return_value=mocks["AcledCollector"]), \
             patch("sentinella.collectors.AdsbCollector", return_value=mocks["AdsbCollector"]), \
             patch("sentinella.collectors.MegaRssCollector", return_value=mocks["MegaRssCollector"]):
            async with TestSession() as db:
                snapshot = await run_score_cycle(db)

        assert snapshot is not None
        assert 0 <= snapshot.score <= 100
        assert snapshot.level in ("CALMO", "NORMALE", "ATTENZIONE", "ELEVATO", "CRITICO")
        assert snapshot.color is not None

    @pytest.mark.asyncio
    async def test_cycle_all_collectors_fail(self):
        from sentinella.engine.score import run_score_cycle

        mock = AsyncMock()
        mock.name = "broken"
        mock.display_name = "Broken"
        mock.safe_collect = AsyncMock(return_value=None)

        with patch("sentinella.collectors.GdeltCollector", return_value=mock), \
             patch("sentinella.collectors.NewsRssCollector", return_value=mock), \
             patch("sentinella.collectors.CsirtCollector", return_value=mock), \
             patch("sentinella.collectors.GoogleTrendsCollector", return_value=mock), \
             patch("sentinella.collectors.AcledCollector", return_value=mock), \
             patch("sentinella.collectors.AdsbCollector", return_value=mock), \
             patch("sentinella.collectors.MegaRssCollector", return_value=mock):
            async with TestSession() as db:
                snapshot = await run_score_cycle(db)

        # Should still produce a score even with all collectors failing
        assert snapshot is not None
        assert 0 <= snapshot.score <= 100

    @pytest.mark.asyncio
    async def test_cycle_saves_dimensions(self):
        from sentinella.engine.score import run_score_cycle
        from sqlalchemy import select

        mock = _make_mock_collector("gdelt", {
            "geopolitica": {"article_count": 50, "negative_ratio": 0.5},
            "terrorismo": {"article_count": 10, "negative_ratio": 0.5},
            "cyber": {"article_count": 5, "negative_ratio": 0.3},
            "eversione": {"article_count": 10, "negative_ratio": 0.4},
            "militare": {"article_count": 15, "negative_ratio": 0.3},
            "sociale": {"article_count": 20, "negative_ratio": 0.3},
        }, 50)
        empty_mock = _make_mock_collector("empty", {}, 0)

        with patch("sentinella.collectors.GdeltCollector", return_value=mock), \
             patch("sentinella.collectors.NewsRssCollector", return_value=empty_mock), \
             patch("sentinella.collectors.CsirtCollector", return_value=empty_mock), \
             patch("sentinella.collectors.GoogleTrendsCollector", return_value=empty_mock), \
             patch("sentinella.collectors.AcledCollector", return_value=empty_mock), \
             patch("sentinella.collectors.AdsbCollector", return_value=empty_mock), \
             patch("sentinella.collectors.MegaRssCollector", return_value=empty_mock):
            async with TestSession() as db:
                snapshot = await run_score_cycle(db)

                # Verify dimensions saved
                stmt = select(DimensionScore).where(DimensionScore.snapshot_id == snapshot.id)
                result = await db.execute(stmt)
                dims = result.scalars().all()

        assert len(dims) == 6
        dim_names = {d.dimension for d in dims}
        assert dim_names == {"geopolitica", "terrorismo", "cyber", "eversione", "militare", "sociale"}
