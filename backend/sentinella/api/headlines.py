"""
Endpoint headlines — titoli recenti da tutte le fonti per il ticker scrollante.
Combina Mega RSS (50+ feed), GDELT, CSIRT.
"""
from __future__ import annotations
import logging
from fastapi import APIRouter

from sentinella.collectors import cache as col_cache
from sentinella.collectors.news_rss import get_geo_events
from sentinella.collectors.mega_rss import get_all_headlines as get_mega_headlines

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["headlines"])


@router.get("/headlines")
async def get_headlines() -> list[dict]:
    """Restituisce i titoli più recenti da tutte le fonti per il ticker."""
    headlines: list[dict] = []
    seen_titles: set[str] = set()

    def _add(title: str, source: str, dimension: str, url: str):
        t = title.strip()
        if t and t.lower() not in seen_titles and dimension != "non_pertinente":
            seen_titles.add(t.lower())
            headlines.append({"title": t, "source": source, "dimension": dimension, "url": url})

    # 1. Mega RSS — priorità (50+ feed)
    for h in get_mega_headlines()[:40]:
        _add(h.get("title", ""), h.get("source", "RSS"), h.get("dimension", ""), h.get("url", ""))

    # 2. GDELT — titoli dalla cache
    gdelt = col_cache.get("gdelt_data")
    if gdelt and isinstance(gdelt, dict):
        for dim, dim_data in gdelt.items():
            for article in (dim_data.get("articles") or [])[:3]:
                _add(article.get("title", ""), "GDELT", dim, article.get("url", ""))

    # 3. RSS geo-events
    for ev in get_geo_events()[:5]:
        _add(ev.get("title", ""), "RSS", ev.get("dimension", ""), ev.get("url", ""))

    # 4. CSIRT
    csirt = col_cache.get("csirt_data")
    if csirt and isinstance(csirt, dict):
        for bulletin in (csirt.get("bulletins") or [])[:5]:
            _add(bulletin.get("title", ""), "CSIRT", "cyber", "")

    return headlines[:50]
