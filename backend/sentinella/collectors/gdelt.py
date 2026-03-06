from __future__ import annotations
"""
Collector GDELT — API DOC 2.0.

Limitazioni reali riscontrate:
- Rate limit: 1 req / 6 secondi (HTTP 429 altrimenti)
- `artlist` non restituisce campo `tone` — usiamo negatività da titolo
- Richieste sempre sequenziali, non parallele
- Cache 1h per non sprecare quota nel ciclo frequente
"""
import asyncio
import time
import re
from datetime import datetime, timezone, timedelta
from typing import Any
import logging

import httpx

from sentinella.collectors.base import BaseCollector, CollectorResult
from sentinella.collectors import cache as col_cache

logger = logging.getLogger(__name__)

GDELT_DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"
CACHE_KEY     = "gdelt_data"
CACHE_TTL     = 60 * 60  # 1 ora
REQUEST_DELAY = 7         # secondi tra richieste (rate limit = ~1/5s, usiamo 7 per sicurezza)
MAX_RETRIES   = 2

# Query semplificate — NO sourcelang:, NO operatori complessi
QUERIES: dict[str, str] = {
    "geopolitica": "Italy security",
    "terrorismo":  "Italy terror",
    "eversione":   "Italy protest",
    "sociale":     "Italy strike",
    "cyber":       "Italy cyber",
    "militare":    "Italy military",
}

# Keyword negative per ricavare un indice di negatività dai titoli
NEGATIVE_TITLE_KEYWORDS = re.compile(
    r'\b(attack|attacco|threat|minaccia|crisis|crisi|emergency|emergenza|'
    r'terror|bomb|explosion|esplosione|alert|allarme|warning|danger|pericolo|'
    r'riot|rivolta|violence|violenza|hack|breach|ransomware|war|guerra)\b',
    re.IGNORECASE
)


class GdeltCollector(BaseCollector):
    name = "gdelt"
    display_name = "GDELT Project"

    async def collect(self) -> CollectorResult:
        cached = col_cache.get(CACHE_KEY)
        if cached is not None:
            logger.info("[gdelt] Cache HIT — skip API call")
            return CollectorResult(source=self.name, data=cached,
                                   records_count=sum(v.get("article_count", 0) for v in cached.values()))

        logger.info("[gdelt] Cache MISS — avvio raccolta sequenziale")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._fetch_all_sync)

        # Only cache if we got actual data — avoid poisoning cache with empty results
        if result and any(v.get("article_count", 0) > 0 for v in result.values()):
            col_cache.set(CACHE_KEY, result, ttl_seconds=CACHE_TTL)

        total = sum(v.get("article_count", 0) for v in result.values())
        return CollectorResult(source=self.name, data=result, records_count=total)

    def _fetch_all_sync(self) -> dict[str, Any]:
        """Fetch sequenziale con delay tra richieste."""
        end   = datetime.now(timezone.utc)
        start = end - timedelta(days=7)
        base_params = {
            "mode":          "artlist",
            "maxrecords":    "250",
            "format":        "json",
            "startdatetime": start.strftime("%Y%m%d%H%M%S"),
            "enddatetime":   end.strftime("%Y%m%d%H%M%S"),
            "sort":          "DateDesc",
        }

        results: dict[str, Any] = {}
        first = True

        for dim, query in QUERIES.items():
            if not first:
                time.sleep(REQUEST_DELAY)
            first = False

            articles = self._fetch_with_retry(query, base_params)
            results[dim] = self._aggregate_articles(articles)
            logger.info(f"[gdelt] {dim}: {results[dim]['article_count']} articoli")

        return results

    def _fetch_with_retry(self, query: str, base_params: dict) -> list[dict]:
        for attempt in range(MAX_RETRIES + 1):
            try:
                r = httpx.get(
                    GDELT_DOC_API,
                    params={"query": query, **base_params},
                    timeout=20,
                )
                if r.status_code == 429:
                    wait = 10 * (attempt + 1)
                    logger.warning(f"[gdelt] 429 rate limit — attendo {wait}s (attempt {attempt+1})")
                    time.sleep(wait)
                    continue
                if r.status_code != 200 or not r.text.strip():
                    logger.warning(f"[gdelt] Risposta inattesa: {r.status_code}")
                    return []
                # GDELT returns rate-limit message as plain text with HTTP 200
                text = r.text.strip()
                if not text.startswith("{"):
                    logger.warning(f"[gdelt] Risposta non-JSON (rate limit?): {text[:80]}")
                    time.sleep(10 * (attempt + 1))
                    continue
                data = r.json()
                return data.get("articles") or []
            except Exception as e:
                logger.warning(f"[gdelt] Errore fetch (attempt {attempt+1}): {e}")
                time.sleep(5)

        return []

    def _aggregate_articles(self, articles: list[dict]) -> dict[str, Any]:
        if not articles:
            return {"article_count": 0, "negative_ratio": 0.0, "articles": []}

        negative = sum(
            1 for a in articles
            if NEGATIVE_TITLE_KEYWORDS.search(a.get("title", ""))
        )

        return {
            "article_count":  len(articles),
            "negative_ratio": round(negative / len(articles), 3),
            "articles": [
                {
                    "title":     a.get("title", ""),
                    "url":       a.get("url", ""),
                    "seendate":  a.get("seendate", ""),
                    "domain":    a.get("domain", ""),
                    "language":  a.get("language", ""),
                }
                for a in articles[:15]
            ],
        }
