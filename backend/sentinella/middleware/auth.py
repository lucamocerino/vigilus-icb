"""
Middleware di autenticazione via API key.
Se API_KEY è configurato in .env, protegge tutti gli endpoint tranne quelli pubblici.
Se API_KEY è vuoto, l'auth è disabilitata (modalità sviluppo).
"""
from __future__ import annotations
import logging
from fastapi import Request
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from sentinella.config import settings

logger = logging.getLogger(__name__)

PUBLIC_PATHS = {
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/methodology",
}

PUBLIC_PREFIXES = (
    "/ws/",
)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class ApiKeyMiddleware(BaseHTTPMiddleware):
    """Verifica X-API-Key header se API_KEY è configurato."""

    async def dispatch(self, request: Request, call_next):
        if not settings.api_key:
            return await call_next(request)

        path = request.url.path

        if path in PUBLIC_PATHS or path.startswith(PUBLIC_PREFIXES):
            return await call_next(request)

        key = request.headers.get("X-API-Key", "")
        if key != settings.api_key:
            logger.warning(f"Richiesta non autorizzata: {request.method} {path}")
            return JSONResponse(
                status_code=401,
                content={"detail": "API key mancante o non valida"},
            )

        return await call_next(request)
