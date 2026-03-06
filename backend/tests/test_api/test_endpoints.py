"""Tests for FastAPI API endpoints (integration tests with test DB)."""
from __future__ import annotations
import pytest
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from sentinella.db import Base, get_db
from sentinella.models.score import ScoreSnapshot, DimensionScore
from sentinella.models.source import SourceStatus
from sentinella.config import get_level

# Create a test app without lifespan (no scheduler)
from fastapi import FastAPI
from sentinella.api import api_router

test_app = FastAPI()
test_app.include_router(api_router)

# In-memory SQLite for tests
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(TEST_DB_URL, echo=False)
TestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestSession() as session:
        yield session

test_app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
async def setup_db():
    """Create tables before each test, drop after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def seed_score():
    """Insert a score snapshot with dimensions."""
    async with TestSession() as db:
        snapshot = ScoreSnapshot(
            timestamp=datetime.now(timezone.utc),
            score=42.5,
            level="ATTENZIONE",
            color="#eab308",
        )
        db.add(snapshot)
        await db.flush()

        for dim, weight in [
            ("geopolitica", 55.0), ("terrorismo", 40.0), ("cyber", 35.0),
            ("eversione", 30.0), ("militare", 50.0), ("sociale", 25.0),
        ]:
            db.add(DimensionScore(
                snapshot_id=snapshot.id,
                dimension=dim,
                score=weight,
                raw_values={"article_count": 80, "negative_ratio": 0.35},
            ))

        db.add(SourceStatus(
            name="gdelt", display_name="GDELT Project",
            is_healthy=True, records_last_run=80,
        ))
        db.add(SourceStatus(
            name="csirt", display_name="CSIRT Italia",
            is_healthy=True, records_last_run=10,
        ))
        await db.commit()
        return snapshot


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_methodology(self, client):
        resp = await client.get("/api/methodology")
        assert resp.status_code == 200
        data = resp.json()
        assert "dimensions" in data
        assert len(data["dimensions"]) == 6
        assert "disclaimer" in data


class TestScoreEndpoints:
    @pytest.mark.asyncio
    async def test_current_no_data_returns_404(self, client):
        resp = await client.get("/api/score/current")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_current_with_data(self, client, seed_score):
        resp = await client.get("/api/score/current")
        assert resp.status_code == 200
        data = resp.json()
        assert data["score"] == 42.5
        assert data["level"] == "ATTENZIONE"
        assert len(data["dimensions"]) == 6
        assert "sources_ok" in data

    @pytest.mark.asyncio
    async def test_history_empty(self, client):
        resp = await client.get("/api/score/history?days=7")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_history_with_data(self, client, seed_score):
        resp = await client.get("/api/score/history?days=7")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["score"] == 42.5

    @pytest.mark.asyncio
    async def test_anomalies_empty(self, client):
        resp = await client.get("/api/score/anomalies")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_anomalies_with_data(self, client, seed_score):
        resp = await client.get("/api/score/anomalies")
        assert resp.status_code == 200
        # May or may not have anomalies depending on baseline


class TestSourcesEndpoint:
    @pytest.mark.asyncio
    async def test_sources_status(self, client, seed_score):
        resp = await client.get("/api/sources/status")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 2


class TestCacheEndpoint:
    @pytest.mark.asyncio
    async def test_cache_status(self, client):
        resp = await client.get("/api/cache/status")
        assert resp.status_code == 200


class TestMapEndpoint:
    @pytest.mark.asyncio
    async def test_map_events(self, client):
        resp = await client.get("/api/map/events")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
