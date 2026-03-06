"""Tests for new feature endpoints: export, compare, regional."""
from __future__ import annotations
import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from sentinella.db import Base, get_db
from sentinella.models.score import ScoreSnapshot, DimensionScore

from fastapi import FastAPI
from sentinella.api import api_router

test_app = FastAPI()
test_app.include_router(api_router)

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(TEST_DB_URL, echo=False)
TestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestSession() as session:
        yield session

test_app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
async def setup_db():
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
async def seed_history():
    """Insert 10 days of score snapshots."""
    async with TestSession() as db:
        now = datetime.now(timezone.utc)
        for i in range(10):
            snap = ScoreSnapshot(
                timestamp=now - timedelta(days=i),
                score=30.0 + i * 3,
                level="NORMALE" if 30 + i * 3 <= 40 else "ATTENZIONE",
                color="#3b82f6",
            )
            db.add(snap)
            await db.flush()
            for dim in ["geopolitica", "terrorismo", "cyber", "eversione", "militare", "sociale"]:
                db.add(DimensionScore(
                    snapshot_id=snap.id,
                    dimension=dim,
                    score=25.0 + i * 2,
                    raw_values={"article_count": 10 + i},
                ))
        await db.commit()


class TestExportCsv:
    @pytest.mark.asyncio
    async def test_csv_empty(self, client):
        resp = await client.get("/api/export/csv?days=7")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/csv")

    @pytest.mark.asyncio
    async def test_csv_with_data(self, client, seed_history):
        resp = await client.get("/api/export/csv?days=30")
        assert resp.status_code == 200
        lines = resp.text.strip().split("\n")
        assert len(lines) >= 2  # header + data
        assert "timestamp" in lines[0]
        assert "geopolitica_score" in lines[0]

    @pytest.mark.asyncio
    async def test_csv_content_disposition(self, client, seed_history):
        resp = await client.get("/api/export/csv?days=7")
        assert "attachment" in resp.headers.get("content-disposition", "")


class TestExportReport:
    @pytest.mark.asyncio
    async def test_report_empty(self, client):
        resp = await client.get("/api/export/report")
        assert resp.status_code == 200
        assert resp.json().get("error") is not None

    @pytest.mark.asyncio
    async def test_report_with_data(self, client, seed_history):
        resp = await client.get("/api/export/report")
        assert resp.status_code == 200
        data = resp.json()
        assert "current" in data
        assert "dimensions" in data
        assert "anomalies" in data
        assert "history_7d" in data
        assert "disclaimer" in data


class TestCompare:
    @pytest.mark.asyncio
    async def test_compare_week(self, client, seed_history):
        resp = await client.get("/api/score/compare?period=week")
        assert resp.status_code == 200
        data = resp.json()
        assert "period1" in data
        assert "period2" in data
        assert "delta_score" in data
        assert "dimensions" in data

    @pytest.mark.asyncio
    async def test_compare_month(self, client, seed_history):
        resp = await client.get("/api/score/compare?period=month")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_compare_empty(self, client):
        resp = await client.get("/api/score/compare?period=week")
        assert resp.status_code == 200
        data = resp.json()
        assert data["period1"]["count"] == 0


class TestRegional:
    @pytest.mark.asyncio
    async def test_regional(self, client):
        resp = await client.get("/api/map/regional")
        assert resp.status_code == 200
        data = resp.json()
        assert "regions" in data
        assert len(data["regions"]) == 3
        assert "total_events" in data
        region_names = {r["name"] for r in data["regions"]}
        assert region_names == {"Nord", "Centro", "Sud"}
