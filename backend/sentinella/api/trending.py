"""
Endpoint trending keywords — spike detection su parole chiave dai titoli.
"""
from __future__ import annotations
import logging
from fastapi import APIRouter

from sentinella.engine.trending import update_trending
from sentinella.collectors.mega_rss import get_all_headlines

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["trending"])


@router.get("/trending")
async def get_trending() -> dict:
    """Restituisce le keyword in trend con z-score e spike detection."""
    headlines = get_all_headlines()
    trending = update_trending(headlines)

    return {
        "keywords": trending,
        "total_headlines": len(headlines),
        "spike_count": sum(1 for t in trending if t["direction"] == "spike"),
        "rising_count": sum(1 for t in trending if t["direction"] == "rising"),
    }
