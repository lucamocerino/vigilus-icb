from __future__ import annotations
"""
Collector ACLED — cache 7 giorni (aggiornamento settimanale).
"""
from datetime import datetime, timezone, timedelta
from typing import Any
import logging

import httpx

from sentinella.collectors.base import BaseCollector, CollectorResult
from sentinella.collectors import cache as col_cache
from sentinella.config import settings

logger = logging.getLogger(__name__)

ACLED_API_URL = "https://api.acleddata.com/acled/read"
CACHE_KEY = "acled_data"
CACHE_TTL = 7 * 24 * 3600  # 7 giorni


class AcledCollector(BaseCollector):
    name = "acled"
    display_name = "ACLED"

    async def collect(self) -> CollectorResult:
        if not settings.acled_api_key or not settings.acled_email:
            logger.warning("[acled] API key non configurata — skip")
            return CollectorResult(source=self.name, data={}, records_count=0)

        cached = col_cache.get(CACHE_KEY)
        if cached is not None:
            logger.info("[acled] Cache HIT — dati settimanali validi")
            return CollectorResult(source=self.name, data=cached, records_count=cached.get("total_events", 0))

        logger.info("[acled] Cache MISS — chiamata API")
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=30)

        params = {
            "key": settings.acled_api_key,
            "email": settings.acled_email,
            "country": "Italy",
            "event_date": f"{start.strftime('%Y-%m-%d')}|{end.strftime('%Y-%m-%d')}",
            "event_date_where": "BETWEEN",
            "limit": 500,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(ACLED_API_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        events = data.get("data", []) or []
        aggregated = self._aggregate(events)

        col_cache.set(CACHE_KEY, aggregated, ttl_seconds=CACHE_TTL)

        return CollectorResult(source=self.name, data=aggregated, records_count=len(events))

    def _aggregate(self, events: list[dict]) -> dict[str, Any]:
        event_types: dict[str, int] = {}
        for e in events:
            etype = e.get("event_type", "unknown")
            event_types[etype] = event_types.get(etype, 0) + 1

        return {
            "total_events": len(events),
            "by_type": event_types,
            "protests": event_types.get("Protests", 0),
            "riots": event_types.get("Riots", 0),
            "violence_civilians": event_types.get("Violence against civilians", 0),
            "battles": event_types.get("Battles", 0),
        }
