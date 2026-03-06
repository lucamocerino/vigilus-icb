"""Edge-case tests for API endpoints — error handling, boundaries, empty data."""
import pytest
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from sentinella.db import Base, get_db
from sentinella.models.score import ScoreSnapshot, DimensionScore
from sentinella.models.event import ClassifiedEvent

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
async def seed_events():
    async with TestSession() as db:
        for i in range(5):
            db.add(ClassifiedEvent(
                source="test",
                dimension=["geopolitica", "cyber", "terrorismo", "sociale", "militare"][i % 5],
                title=f"Evento test {i} Roma terrorismo cyber attacco",
                summary=f"Descrizione evento {i}",
                url=f"http://test/{i}",
                relevance=1.0,
                event_date=datetime.now(timezone.utc),
                classified_at=datetime.now(timezone.utc),
            ))
        await db.commit()


class TestEventSearchEdgeCases:
    @pytest.mark.asyncio
    async def test_search_empty_query(self, client):
        resp = await client.get("/api/events/search?q=")
        # FastAPI validates required params
        assert resp.status_code in (200, 422)

    @pytest.mark.asyncio
    async def test_search_no_results(self, client, seed_events):
        resp = await client.get("/api/events/search?q=zzzznonexistent")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_search_finds_match(self, client, seed_events):
        resp = await client.get("/api/events/search?q=terrorismo")
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) > 0
        assert any("terrorismo" in e["title"].lower() for e in results)

    @pytest.mark.asyncio
    async def test_search_with_dimension_filter(self, client, seed_events):
        resp = await client.get("/api/events/search?q=Evento&dimension=cyber")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_search_respects_limit(self, client, seed_events):
        resp = await client.get("/api/events/search?q=Evento&limit=2")
        assert resp.status_code == 200
        assert len(resp.json()) <= 2

    @pytest.mark.asyncio
    async def test_search_special_chars(self, client):
        resp = await client.get("/api/events/search?q=%25DROP%20TABLE")
        assert resp.status_code == 200  # Should not crash


class TestCompareEdgeCases:
    @pytest.mark.asyncio
    async def test_compare_invalid_period(self, client):
        resp = await client.get("/api/score/compare?period=invalid")
        assert resp.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_compare_custom_missing_dates(self, client):
        resp = await client.get("/api/score/compare?period=custom")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_compare_week_empty_db(self, client):
        resp = await client.get("/api/score/compare?period=week")
        assert resp.status_code == 200
        data = resp.json()
        assert data["period1"]["count"] == 0


class TestDigestEdgeCases:
    @pytest.mark.asyncio
    async def test_digest_empty_db(self, client):
        resp = await client.get("/api/digest/daily")
        assert resp.status_code == 200
        data = resp.json()
        assert data["score"]["current"] is None

    @pytest.mark.asyncio
    async def test_digest_with_score(self, client):
        async with TestSession() as db:
            snap = ScoreSnapshot(timestamp=datetime.now(timezone.utc), score=45.0, level="ATTENZIONE", color="#eab308")
            db.add(snap)
            await db.flush()
            for dim in ["geopolitica", "terrorismo", "cyber", "eversione", "militare", "sociale"]:
                db.add(DimensionScore(snapshot_id=snap.id, dimension=dim, score=40.0, raw_values={"article_count": 10}))
            await db.commit()

        resp = await client.get("/api/digest/daily")
        assert resp.status_code == 200
        data = resp.json()
        assert data["score"]["current"] == 45.0
        assert "summary" in data


class TestOsintEdgeCases:
    @pytest.mark.asyncio
    async def test_earthquakes_endpoint(self, client):
        resp = await client.get("/api/earthquakes")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_flights_empty(self, client):
        resp = await client.get("/api/flights")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_predictions(self, client):
        resp = await client.get("/api/predictions")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "probability" in data[0]

    @pytest.mark.asyncio
    async def test_outages(self, client):
        resp = await client.get("/api/outages")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert all("service" in s for s in data)

    @pytest.mark.asyncio
    async def test_hotspots_empty(self, client):
        resp = await client.get("/api/hotspots")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_region_valid(self, client, seed_events):
        resp = await client.get("/api/region/lazio")
        assert resp.status_code == 200
        data = resp.json()
        assert data["region"] == "lazio"
        assert "cities" in data

    @pytest.mark.asyncio
    async def test_region_invalid(self, client):
        resp = await client.get("/api/region/mordor")
        assert resp.status_code == 200
        assert "error" in resp.json()

    @pytest.mark.asyncio
    async def test_region_case_insensitive(self, client):
        resp = await client.get("/api/region/LOMBARDIA")
        assert resp.status_code == 200
        assert resp.json().get("region") == "LOMBARDIA" or "error" not in resp.json()


class TestLayersEdgeCases:
    @pytest.mark.asyncio
    async def test_military_layers(self, client):
        resp = await client.get("/api/layers/military")
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) > 0

    @pytest.mark.asyncio
    async def test_infrastructure_layers(self, client):
        resp = await client.get("/api/layers/infrastructure")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_all_layers(self, client):
        resp = await client.get("/api/layers/all")
        assert resp.status_code == 200
        data = resp.json()
        assert "military" in data
        assert "infrastructure" in data


class TestCorrelationEdgeCases:
    @pytest.mark.asyncio
    async def test_correlations_empty(self, client):
        resp = await client.get("/api/score/correlations?hours=24")
        assert resp.status_code == 200
        data = resp.json()
        assert data["snapshots_analyzed"] == 0

    @pytest.mark.asyncio
    async def test_convergence_empty(self, client):
        resp = await client.get("/api/map/convergence")
        assert resp.status_code == 200


class TestTrendingEdgeCases:
    @pytest.mark.asyncio
    async def test_trending_empty(self, client):
        resp = await client.get("/api/trending")
        assert resp.status_code == 200
        data = resp.json()
        assert "keywords" in data
        assert "total_headlines" in data

    @pytest.mark.asyncio
    async def test_headlines_endpoint(self, client):
        resp = await client.get("/api/headlines")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
