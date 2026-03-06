"""
Geographic convergence — rileva zone dove 3+ dimensioni si sovrappongono.
Binning spaziale 1°×1°.
"""
from __future__ import annotations
import logging
from collections import defaultdict
from fastapi import APIRouter

from sentinella.collectors.news_rss import get_geo_events

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/map", tags=["map"])


@router.get("/convergence")
async def get_convergence() -> dict:
    """Rileva zone dove eventi di 3+ dimensioni diverse si sovrappongono."""
    events = get_geo_events()
    if not events:
        return {"zones": [], "total_events": 0}

    # Bin events into 1°×1° grid cells
    grid: dict[tuple[int, int], dict] = defaultdict(lambda: {
        "dimensions": set(),
        "events": [],
        "count": 0,
    })

    for ev in events:
        lat = int(ev.get("lat", 0))
        lon = int(ev.get("lon", 0))
        cell = grid[(lat, lon)]
        cell["dimensions"].add(ev.get("dimension", ""))
        cell["count"] += 1
        if len(cell["events"]) < 5:
            cell["events"].append({
                "title": ev.get("title", ""),
                "dimension": ev.get("dimension", ""),
                "location": ev.get("location", ""),
            })

    # Filter cells with 2+ dimensions
    zones = []
    for (lat, lon), cell in grid.items():
        dim_count = len(cell["dimensions"])
        if dim_count >= 2:
            zones.append({
                "lat": lat + 0.5,
                "lon": lon + 0.5,
                "dimension_count": dim_count,
                "dimensions": list(cell["dimensions"]),
                "event_count": cell["count"],
                "events": cell["events"],
                "severity": "alta" if dim_count >= 3 else "media",
            })

    zones.sort(key=lambda z: z["dimension_count"], reverse=True)

    return {
        "zones": zones,
        "total_events": len(events),
        "convergence_count": len(zones),
    }
