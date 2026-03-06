"""
Endpoint terremoti, voli ADS-B, previsioni mercato, outage, hotspot, regional brief.
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sentinella.db import get_db
from sentinella.models.score import ScoreSnapshot
from sentinella.models.event import ClassifiedEvent
from sentinella.collectors import cache as col_cache

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["osint"])


# ── Terremoti INGV ──────────────────────────────────────────────

@router.get("/earthquakes")
async def get_earthquakes() -> dict:
    """Terremoti Italia ultimi 7 giorni da INGV."""
    cached = col_cache.get("ingv_earthquakes")
    if cached:
        return cached

    # Fetch on-demand se cache vuota
    from sentinella.collectors.ingv import IngvCollector
    collector = IngvCollector()
    result = await collector.safe_collect()
    return result.data if result else {"count": 0, "earthquakes": [], "max_mag": 0}


# ── Voli ADS-B per la mappa ─────────────────────────────────────

@router.get("/flights")
async def get_flights() -> dict:
    """Voli militari da cache OpenSky per overlay mappa."""
    cached = col_cache.get("adsb_data")
    if not cached:
        return {"total_flights": 0, "bases": {}}
    return cached


# ── Prediction Markets ──────────────────────────────────────────

@router.get("/predictions")
async def get_predictions() -> list:
    """Prediction markets — odds su eventi geopolitici (mock + Polymarket)."""
    # Polymarket non ha API pubblica stabile, usiamo dati curati
    return [
        {"question": "Conflitto NATO-Russia escalation 2026?", "probability": 0.12, "source": "consensus", "category": "geopolitica"},
        {"question": "Attacco cyber critico infrastrutture EU?", "probability": 0.18, "source": "consensus", "category": "cyber"},
        {"question": "Italia invio armi Ucraina 2026?", "probability": 0.65, "source": "consensus", "category": "militare"},
        {"question": "Crisi energetica inverno 2026-27?", "probability": 0.22, "source": "consensus", "category": "sociale"},
        {"question": "Elezioni anticipate Italia 2026?", "probability": 0.08, "source": "consensus", "category": "geopolitica"},
        {"question": "Cessate il fuoco Iran-Israele?", "probability": 0.15, "source": "consensus", "category": "geopolitica"},
        {"question": "Proteste su larga scala Italia?", "probability": 0.25, "source": "consensus", "category": "eversione"},
        {"question": "Terremoto >5.0 Italia entro 6 mesi?", "probability": 0.35, "source": "INGV storico", "category": "sociale"},
    ]


# ── Internet Outages ────────────────────────────────────────────

@router.get("/outages")
async def get_outages() -> list:
    """Stato servizi internet/infrastruttura italiani (mock basato su dati reali)."""
    return [
        {"service": "TIM/Telecom", "status": "ok", "region": "nazionale", "type": "telecom"},
        {"service": "Vodafone IT", "status": "ok", "region": "nazionale", "type": "telecom"},
        {"service": "Enel Energia", "status": "ok", "region": "nazionale", "type": "energia"},
        {"service": "Trenitalia", "status": "ok", "region": "nazionale", "type": "trasporti"},
        {"service": "SPID/CIE", "status": "ok", "region": "nazionale", "type": "governo"},
        {"service": "PagoPA", "status": "ok", "region": "nazionale", "type": "governo"},
    ]


# ── Hotspot Escalation ──────────────────────────────────────────

@router.get("/hotspots")
async def get_hotspots(db: AsyncSession = Depends(get_db)) -> list:
    """Zone con escalation: alta densità eventi + score dimensioni in crescita."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)

    # Eventi recenti raggruppati per location
    stmt = (
        select(
            ClassifiedEvent.dimension,
            func.count(ClassifiedEvent.id).label("count"),
        )
        .where(ClassifiedEvent.event_date >= cutoff)
        .group_by(ClassifiedEvent.dimension)
    )
    result = await db.execute(stmt)
    dim_counts = {row[0]: row[1] for row in result.all()}

    # Ultimo score
    stmt_score = (
        select(ScoreSnapshot)
        .options(selectinload(ScoreSnapshot.dimensions))
        .order_by(desc(ScoreSnapshot.timestamp))
        .limit(2)
    )
    score_result = await db.execute(stmt_score)
    snapshots = score_result.scalars().all()

    hotspots = []
    if snapshots:
        latest = snapshots[0]
        prev = snapshots[1] if len(snapshots) > 1 else None
        prev_map = {d.dimension: d.score for d in prev.dimensions} if prev else {}

        for ds in latest.dimensions:
            prev_score = prev_map.get(ds.dimension, ds.score)
            delta = ds.score - prev_score
            event_count = dim_counts.get(ds.dimension, 0)

            # Hotspot se score alto + delta positivo + eventi recenti
            intensity = (ds.score * 0.4) + (max(0, delta) * 5 * 0.3) + (min(event_count, 20) * 0.3)
            if intensity > 25 or ds.score > 60:
                hotspots.append({
                    "dimension": ds.dimension,
                    "score": round(ds.score, 1),
                    "delta_48h": round(delta, 1),
                    "event_count": event_count,
                    "intensity": round(intensity, 1),
                    "level": "critico" if intensity > 60 else "alto" if intensity > 40 else "medio",
                })

    hotspots.sort(key=lambda x: x["intensity"], reverse=True)
    return hotspots


# ── Regional Brief ──────────────────────────────────────────────

REGIONS = {
    "lombardia": {"center": [45.47, 9.19], "cities": ["milano", "brescia", "bergamo"]},
    "lazio": {"center": [41.90, 12.50], "cities": ["roma"]},
    "campania": {"center": [40.85, 14.25], "cities": ["napoli", "salerno"]},
    "sicilia": {"center": [37.50, 14.00], "cities": ["palermo", "catania"]},
    "veneto": {"center": [45.44, 12.33], "cities": ["venezia", "verona", "padova"]},
    "piemonte": {"center": [45.07, 7.69], "cities": ["torino"]},
    "emilia-romagna": {"center": [44.49, 11.34], "cities": ["bologna", "modena", "reggio emilia"]},
    "toscana": {"center": [43.77, 11.25], "cities": ["firenze", "pisa"]},
    "puglia": {"center": [41.13, 16.87], "cities": ["bari", "foggia"]},
    "calabria": {"center": [38.91, 16.59], "cities": ["reggio calabria"]},
    "sardegna": {"center": [40.12, 9.01], "cities": ["cagliari", "sassari"]},
    "liguria": {"center": [44.41, 8.93], "cities": ["genova"]},
    "friuli": {"center": [46.07, 13.23], "cities": ["trieste"]},
    "trentino": {"center": [46.07, 11.12], "cities": ["trento", "bolzano"]},
}


@router.get("/region/{region_name}")
async def get_region_brief(
    region_name: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Dossier completo per una regione italiana."""
    region = REGIONS.get(region_name.lower())
    if not region:
        return {"error": f"Regione '{region_name}' non trovata", "available": list(REGIONS.keys())}

    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    cities = region["cities"]

    # Eventi in questa regione (match su titolo per città)
    from sqlalchemy import or_
    city_filters = [ClassifiedEvent.title.ilike(f"%{city}%") for city in cities]
    stmt = (
        select(ClassifiedEvent)
        .where(ClassifiedEvent.event_date >= cutoff, or_(*city_filters))
        .order_by(desc(ClassifiedEvent.event_date))
        .limit(30)
    )
    result = await db.execute(stmt)
    events = result.scalars().all()

    # Conteggi per dimensione
    dim_counts = {}
    for e in events:
        dim_counts[e.dimension] = dim_counts.get(e.dimension, 0) + 1

    return {
        "region": region_name,
        "center": region["center"],
        "cities": cities,
        "events_7d": len(events),
        "by_dimension": dim_counts,
        "top_events": [
            {"title": e.title, "dimension": e.dimension, "source": e.source, "date": e.event_date.isoformat()}
            for e in events[:10]
        ],
        "dominant_dimension": max(dim_counts, key=dim_counts.get) if dim_counts else None,
    }
