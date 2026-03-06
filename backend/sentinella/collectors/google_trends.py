from __future__ import annotations
"""
Collector Google Trends — cache 24h per rispettare i rate limit.
Anche con cicli rapidi, l'API viene chiamata al massimo una volta al giorno.
"""
import asyncio
from typing import Any
import logging

from sentinella.collectors.base import BaseCollector, CollectorResult
from sentinella.collectors import cache as col_cache

logger = logging.getLogger(__name__)

CACHE_KEY = "google_trends_data"
CACHE_TTL = 24 * 3600  # 24 ore

TREND_QUERIES: dict[str, list[str]] = {
    "terrorismo": ["attentato", "terrorismo Italia", "allerta terrorismo"],
    "sociale":    ["manifestazione Roma", "sciopero", "protesta"],
    "militare":   ["Aviano base", "Sigonella", "NATO Italia"],
    "geopolitica": ["guerra", "sanzioni", "crisi diplomatica"],
    "cyber":      ["attacco informatico", "hacker Italia", "ransomware"],
}


class GoogleTrendsCollector(BaseCollector):
    name = "google_trends"
    display_name = "Google Trends"

    async def collect(self) -> CollectorResult:
        cached = col_cache.get(CACHE_KEY)
        if cached is not None:
            logger.info("[google_trends] Cache HIT — dati validi, skip API call")
            return CollectorResult(source=self.name, data=cached, records_count=len(cached))

        logger.info("[google_trends] Cache MISS — chiamata API")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._fetch_trends)

        if result:
            col_cache.set(CACHE_KEY, result, ttl_seconds=CACHE_TTL)

        return CollectorResult(
            source=self.name,
            data=result,
            records_count=len(result),
        )

    def _fetch_trends(self) -> dict[str, Any]:
        try:
            from pytrends.request import TrendReq
        except ImportError:
            logger.warning("[google_trends] pytrends non installato")
            return {}

        import time
        pytrends = TrendReq(hl="it-IT", tz=60, timeout=(10, 25))
        results = {}

        for dimension, keywords in TREND_QUERIES.items():
            try:
                pytrends.build_payload(keywords, cat=0, timeframe="now 7-d", geo="IT")
                data = pytrends.interest_over_time()
                if data.empty:
                    results[dimension] = {"mean": 0, "max": 0, "keywords": {}}
                    continue

                keyword_means = {
                    kw: float(data[kw].mean())
                    for kw in keywords
                    if kw in data.columns
                }
                results[dimension] = {
                    "mean": sum(keyword_means.values()) / len(keyword_means) if keyword_means else 0,
                    "max": max(keyword_means.values()) if keyword_means else 0,
                    "keywords": keyword_means,
                }
            except Exception as e:
                logger.warning(f"[google_trends] Errore {dimension}: {e}")
                results[dimension] = {"mean": 0, "max": 0, "keywords": {}}

            time.sleep(2)  # rispetta rate limit tra query

        return results
