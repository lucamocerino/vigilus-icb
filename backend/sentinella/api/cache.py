from __future__ import annotations
from fastapi import APIRouter
from sentinella.collectors import cache as col_cache

router = APIRouter(prefix="/api/cache", tags=["cache"])


@router.get("/status")
async def get_cache_status() -> dict:
    """Mostra lo stato delle cache dei collector lenti."""
    return {
        "entries": col_cache.status(),
        "description": {
            "google_trends_data": "Cache Google Trends (TTL 24h)",
            "acled_data": "Cache ACLED (TTL 7 giorni)",
        },
    }


@router.delete("/invalidate/{key}")
async def invalidate_cache(key: str) -> dict:
    """Forza il refresh di una cache specifica al prossimo ciclo."""
    col_cache.invalidate(key)
    return {"invalidated": key}
