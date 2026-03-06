"""Tests for auth and rate limiting middleware."""
from __future__ import annotations
import os
import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

from sentinella.middleware.auth import ApiKeyMiddleware
from sentinella.middleware.rate_limit import RateLimitMiddleware


def _make_app(api_key: str = "", rpm: int = 0) -> FastAPI:
    """Create a minimal FastAPI app with middleware for testing."""
    app = FastAPI()

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/api/score/current")
    async def score():
        return {"score": 42}

    @app.get("/api/methodology")
    async def methodology():
        return {"info": "public"}

    # Middleware order matters — auth first, then rate limit
    app.add_middleware(ApiKeyMiddleware)
    if rpm > 0:
        app.add_middleware(RateLimitMiddleware, requests_per_minute=rpm)

    return app


class TestApiKeyMiddleware:
    @pytest.mark.asyncio
    async def test_no_key_configured_allows_all(self):
        """When API_KEY is empty, all requests pass through."""
        from sentinella.config import settings
        original = settings.api_key
        settings.api_key = ""
        try:
            app = _make_app()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get("/api/score/current")
                assert resp.status_code == 200
        finally:
            settings.api_key = original

    @pytest.mark.asyncio
    async def test_valid_key_allows_request(self):
        from sentinella.config import settings
        original = settings.api_key
        settings.api_key = "test-secret-key"
        try:
            app = _make_app(api_key="test-secret-key")
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get(
                    "/api/score/current",
                    headers={"X-API-Key": "test-secret-key"},
                )
                assert resp.status_code == 200
        finally:
            settings.api_key = original

    @pytest.mark.asyncio
    async def test_invalid_key_returns_401(self):
        from sentinella.config import settings
        original = settings.api_key
        settings.api_key = "correct-key"
        try:
            app = _make_app(api_key="correct-key")
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get(
                    "/api/score/current",
                    headers={"X-API-Key": "wrong-key"},
                )
                assert resp.status_code == 401
        finally:
            settings.api_key = original

    @pytest.mark.asyncio
    async def test_missing_key_returns_401(self):
        from sentinella.config import settings
        original = settings.api_key
        settings.api_key = "required-key"
        try:
            app = _make_app(api_key="required-key")
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get("/api/score/current")
                assert resp.status_code == 401
        finally:
            settings.api_key = original

    @pytest.mark.asyncio
    async def test_public_paths_bypass_auth(self):
        from sentinella.config import settings
        original = settings.api_key
        settings.api_key = "secret"
        try:
            app = _make_app(api_key="secret")
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                # /health è pubblico
                resp = await c.get("/health")
                assert resp.status_code == 200

                # /api/methodology è pubblico
                resp = await c.get("/api/methodology")
                assert resp.status_code == 200
        finally:
            settings.api_key = original


class TestRateLimitMiddleware:
    @pytest.mark.asyncio
    async def test_under_limit_passes(self):
        app = _make_app(rpm=10)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            for _ in range(5):
                resp = await c.get("/health")
                assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_over_limit_returns_429(self):
        app = _make_app(rpm=3)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            for _ in range(3):
                await c.get("/health")
            resp = await c.get("/health")
            assert resp.status_code == 429
            assert "Retry-After" in resp.headers

    @pytest.mark.asyncio
    async def test_disabled_when_zero(self):
        app = _make_app(rpm=0)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            for _ in range(100):
                resp = await c.get("/health")
                assert resp.status_code == 200
