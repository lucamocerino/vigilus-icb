from __future__ import annotations
from contextlib import asynccontextmanager
import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from sentinella.config import settings
from sentinella.db import init_db
from sentinella.scheduler import setup_scheduler
from sentinella.api import api_router
from sentinella.api.websocket import router as ws_router
from sentinella.middleware.auth import ApiKeyMiddleware
from sentinella.middleware.rate_limit import RateLimitMiddleware

import json as _json

class _JsonFormatter(logging.Formatter):
    def format(self, record):
        return _json.dumps({
            "ts": self.formatTime(record), "level": record.levelname,
            "logger": record.name, "msg": record.getMessage(),
        })

if settings.debug:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
else:
    handler = logging.StreamHandler()
    handler.setFormatter(_JsonFormatter())
    logging.basicConfig(level=logging.WARNING, handlers=[handler])

logger = logging.getLogger(__name__)

# ── Sentry (opzionale) ──
try:
    import sentry_sdk
    if settings.sentry_dsn:
        sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1)
        logger.info("Sentry inizializzato")
except ImportError:
    pass

# ── Prometheus metrics ──
try:
    from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
    REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
    REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency', ['endpoint'])
    PROMETHEUS_ENABLED = True
except ImportError:
    PROMETHEUS_ENABLED = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Avvio VIGILUS...")
    await init_db()
    logger.info("Database inizializzato")

    scheduler = setup_scheduler()
    scheduler.start()
    logger.info("Scheduler avviato")

    yield

    scheduler.shutdown(wait=False)
    logger.info("Scheduler fermato")


app = FastAPI(
    title="VIGILUS — Italy Crisis Board API",
    description="Real-time OSINT intelligence dashboard for Italy's national security",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# CORS — origini da variabile d'ambiente
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Autenticazione API key (attiva solo se API_KEY è configurato)
app.add_middleware(ApiKeyMiddleware)

# Rate limiting (attivo solo se rate_limit_per_minute > 0)
app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.rate_limit_per_minute)

app.include_router(api_router)
app.include_router(ws_router)


# Security headers middleware
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if not settings.debug:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# Prometheus metrics middleware
if PROMETHEUS_ENABLED:
    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start
        endpoint = request.url.path
        REQUEST_COUNT.labels(request.method, endpoint, response.status_code).inc()
        REQUEST_LATENCY.labels(endpoint).observe(duration)
        return response


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "vigilus-icb"}


if PROMETHEUS_ENABLED:
    from starlette.responses import Response as StarletteResponse

    @app.get("/metrics")
    async def metrics():
        return StarletteResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)
