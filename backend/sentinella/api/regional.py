"""
Endpoint mappa regionale — aggrega eventi per macro-regione italiana.
"""
from __future__ import annotations
import logging
from fastapi import APIRouter

from sentinella.collectors.news_rss import get_geo_events

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/map", tags=["map"])

# Mapping città/regioni → macro-regione
_MACRO_REGIONS: dict[str, str] = {
    # Nord
    "milano": "Nord", "torino": "Nord", "genova": "Nord", "venezia": "Nord",
    "bologna": "Nord", "firenze": "Nord", "verona": "Nord", "trieste": "Nord",
    "padova": "Nord", "modena": "Nord", "reggio emilia": "Nord", "trento": "Nord",
    "bolzano": "Nord", "pisa": "Nord", "lombardia": "Nord", "veneto": "Nord",
    "piemonte": "Nord", "emilia-romagna": "Nord", "liguria": "Nord",
    "trentino": "Nord", "friuli": "Nord", "toscana": "Nord",
    # Centro
    "roma": "Centro", "napoli": "Centro", "ancona": "Centro",
    "lazio": "Centro", "marche": "Centro", "abruzzo": "Centro",
    "umbria": "Centro", "molise": "Centro", "campania": "Centro",
    # Sud
    "bari": "Sud", "palermo": "Sud", "catania": "Sud", "cagliari": "Sud",
    "salerno": "Sud", "foggia": "Sud", "sassari": "Sud",
    "reggio calabria": "Sud", "puglia": "Sud", "calabria": "Sud",
    "sicilia": "Sud", "sardegna": "Sud", "basilicata": "Sud",
}

# Centroidi per visualizzazione
_REGION_CENTERS = {
    "Nord":   {"lat": 45.4, "lon": 10.9},
    "Centro": {"lat": 42.0, "lon": 12.8},
    "Sud":    {"lat": 39.5, "lon": 15.5},
}


@router.get("/regional")
async def get_regional_data() -> dict:
    """Aggrega eventi geo-taggati per macro-regione (Nord/Centro/Sud)."""
    events = get_geo_events()

    regions: dict[str, dict] = {
        name: {
            "name": name,
            "center": center,
            "event_count": 0,
            "by_dimension": {},
            "recent_events": [],
        }
        for name, center in _REGION_CENTERS.items()
    }

    for event in events:
        location = event.get("location", "").lower().strip()
        macro = _MACRO_REGIONS.get(location)
        if not macro:
            continue

        region = regions[macro]
        region["event_count"] += 1

        dim = event.get("dimension", "geopolitica")
        region["by_dimension"][dim] = region["by_dimension"].get(dim, 0) + 1

        if len(region["recent_events"]) < 5:
            region["recent_events"].append({
                "title": event.get("title", ""),
                "dimension": dim,
                "location": event.get("location", ""),
            })

    # Calcola intensità relativa (0-100) per colore choropleth
    max_events = max((r["event_count"] for r in regions.values()), default=1) or 1
    for region in regions.values():
        region["intensity"] = round((region["event_count"] / max_events) * 100, 1)

    return {
        "regions": list(regions.values()),
        "total_events": len(events),
        "coverage": sum(1 for r in regions.values() if r["event_count"] > 0),
    }
