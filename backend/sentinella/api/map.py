from __future__ import annotations
from fastapi import APIRouter

router = APIRouter(prefix="/api/map", tags=["map"])


@router.get("/events")
async def get_map_events() -> list:
    """Restituisce gli articoli RSS geo-taggati con coordinate per la mappa."""
    from sentinella.collectors.news_rss import get_geo_events
    return get_geo_events()
