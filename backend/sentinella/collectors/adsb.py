from __future__ import annotations
"""
Collector ADS-B — Attività voli militari tramite OpenSky Network.
Monitoraggio basi militari italiane principali.
"""
from datetime import datetime, timezone
from typing import Any
import logging

import httpx

from sentinella.collectors.base import BaseCollector, CollectorResult
from sentinella.collectors import cache as col_cache
from sentinella.config import settings

CACHE_KEY = "adsb_data"
CACHE_TTL = 60 * 60  # 1 ora — OpenSky free tier: ~100 req/giorno senza auth

logger = logging.getLogger(__name__)

OPENSKY_API = "https://opensky-network.org/api"

# Bounding box approssimativa delle basi militari italiane principali
# (lat_min, lat_max, lon_min, lon_max)
MILITARY_BASES = {
    "aviano": {"lat_min": 46.00, "lat_max": 46.10, "lon_min": 12.57, "lon_max": 12.67},
    "sigonella": {"lat_min": 37.37, "lat_max": 37.47, "lon_min": 14.87, "lon_max": 14.97},
    "ghedi": {"lat_min": 45.38, "lat_max": 45.48, "lon_min": 10.22, "lon_max": 10.32},
    "amendola": {"lat_min": 41.49, "lat_max": 41.59, "lon_min": 15.67, "lon_max": 15.77},
    "trapani_birgi": {"lat_min": 37.89, "lat_max": 37.99, "lon_min": 12.47, "lon_max": 12.57},
}


class AdsbCollector(BaseCollector):
    name = "adsb"
    display_name = "ADS-B (OpenSky)"

    async def collect(self) -> CollectorResult:
        cached = col_cache.get(CACHE_KEY)
        if cached is not None:
            logger.info("[adsb] Cache HIT")
            return CollectorResult(source=self.name, data=cached,
                                   records_count=cached.get("total_flights", 0))

        now = int(datetime.now(timezone.utc).timestamp())
        auth = None
        if settings.opensky_username and settings.opensky_password:
            auth = (settings.opensky_username, settings.opensky_password)

        results = {}
        total_flights = 0

        async with httpx.AsyncClient(timeout=20) as client:
            for base_name, bbox in MILITARY_BASES.items():
                try:
                    flights = await self._get_flights_in_area(client, bbox, now, auth)
                    results[base_name] = {
                        "flight_count": len(flights),
                        "flights": flights[:10],
                    }
                    total_flights += len(flights)
                except Exception as e:
                    logger.warning(f"[adsb] Errore per {base_name}: {e}")
                    results[base_name] = {"flight_count": 0, "flights": []}

        data = {"bases": results, "total_flights": total_flights}
        col_cache.set(CACHE_KEY, data, ttl_seconds=CACHE_TTL)
        return CollectorResult(source=self.name, data=data, records_count=total_flights)

    async def _get_flights_in_area(
        self,
        client: httpx.AsyncClient,
        bbox: dict,
        timestamp: int,
        auth: tuple | None,
    ) -> list[dict[str, Any]]:
        params = {
            "lamin": bbox["lat_min"],
            "lomin": bbox["lon_min"],
            "lamax": bbox["lat_max"],
            "lomax": bbox["lon_max"],
        }

        kwargs: dict = {"params": params}
        if auth:
            kwargs["auth"] = auth

        resp = await client.get(f"{OPENSKY_API}/states/all", **kwargs)
        if resp.status_code == 429:
            logger.warning("[adsb] Rate limit OpenSky raggiunto")
            return []
        resp.raise_for_status()

        data = resp.json()
        states = data.get("states") or []

        flights = []
        for state in states:
            # state[0]=icao24, state[1]=callsign, state[8]=on_ground
            if state and len(state) > 8:
                flights.append({
                    "icao24": state[0],
                    "callsign": (state[1] or "").strip(),
                    "on_ground": state[8],
                })

        return flights
