"""
Collector INGV — terremoti italiani dal feed FDSNWS dell'Istituto Nazionale di Geofisica.
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone, timedelta

import httpx

from sentinella.collectors.base import BaseCollector, CollectorResult
from sentinella.collectors import cache as col_cache

logger = logging.getLogger(__name__)

INGV_API = "https://webservices.ingv.it/fdsnws/event/1/query"
CACHE_KEY = "ingv_earthquakes"
CACHE_TTL = 30 * 60  # 30 minuti


class IngvCollector(BaseCollector):
    name = "ingv"
    display_name = "INGV Terremoti"

    async def collect(self) -> CollectorResult:
        cached = col_cache.get(CACHE_KEY)
        if cached is not None:
            return CollectorResult(source=self.name, data=cached, records_count=cached.get("count", 0))

        end = datetime.now(timezone.utc)
        start = end - timedelta(days=7)

        params = {
            "starttime": start.strftime("%Y-%m-%dT%H:%M:%S"),
            "endtime": end.strftime("%Y-%m-%dT%H:%M:%S"),
            "minlat": 35.0, "maxlat": 48.0,
            "minlon": 6.0, "maxlon": 19.0,
            "minmag": 2.0,
            "format": "geojson",
            "orderby": "time",
            "limit": 100,
        }

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(INGV_API, params=params)
            if resp.status_code == 204:
                data = {"type": "FeatureCollection", "features": []}
            else:
                resp.raise_for_status()
                data = resp.json()

        features = data.get("features", [])
        earthquakes = []
        for f in features:
            props = f.get("properties", {})
            coords = f.get("geometry", {}).get("coordinates", [0, 0, 0])
            earthquakes.append({
                "time": props.get("time", ""),
                "mag": props.get("mag", 0),
                "place": props.get("place", ""),
                "depth": coords[2] if len(coords) > 2 else 0,
                "lat": coords[1] if len(coords) > 1 else 0,
                "lon": coords[0] if len(coords) > 0 else 0,
                "magType": props.get("magType", ""),
            })

        result = {
            "count": len(earthquakes),
            "max_mag": max((e["mag"] for e in earthquakes), default=0),
            "earthquakes": earthquakes,
            "geojson": data,
        }

        col_cache.set(CACHE_KEY, result, ttl_seconds=CACHE_TTL)
        return CollectorResult(source=self.name, data=result, records_count=len(earthquakes))
