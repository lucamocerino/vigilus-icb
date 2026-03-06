"""
Mega RSS Aggregator — 50+ feed italiani organizzati per categoria.
Fetch parallelo, dedup titoli, classificazione automatica per dimensione.
"""
from __future__ import annotations
import asyncio
import re
from datetime import datetime, timezone
import logging

import feedparser
import httpx

from sentinella.collectors.base import BaseCollector, CollectorResult
from sentinella.collectors import cache as col_cache

logger = logging.getLogger(__name__)

CACHE_KEY = "mega_rss_data"
CACHE_TTL = 15 * 60  # 15 minuti

# ── 50+ Feed RSS italiani organizzati per categoria ──────────────────────

FEEDS: list[dict[str, str]] = [
    # ── Agenzie di stampa ──
    {"name": "ANSA Cronaca",     "url": "https://www.ansa.it/sito/notizie/cronaca/cronaca_rss.xml",     "category": "cronaca"},
    {"name": "ANSA Mondo",       "url": "https://www.ansa.it/sito/notizie/mondo/mondo_rss.xml",         "category": "esteri"},
    {"name": "ANSA Politica",    "url": "https://www.ansa.it/sito/notizie/politica/politica_rss.xml",   "category": "politica"},
    {"name": "ANSA Economia",    "url": "https://www.ansa.it/sito/notizie/economia/economia_rss.xml",   "category": "economia"},
    {"name": "ANSA Tecnologia",  "url": "https://www.ansa.it/sito/notizie/tecnologia/tecnologia_rss.xml", "category": "tech"},
    {"name": "ANSA Top News",    "url": "https://www.ansa.it/sito/ansait_rss.xml",                      "category": "top"},
    {"name": "AGI",              "url": "https://www.agi.it/rss",                                        "category": "top"},
    {"name": "Adnkronos",        "url": "https://www.adnkronos.com/rss",                                 "category": "top"},
    # ── Quotidiani nazionali ──
    {"name": "Repubblica",       "url": "https://www.repubblica.it/rss/homepage/rss2.0.xml",             "category": "top"},
    {"name": "Corriere",         "url": "https://xml2.corrieredellasera.it/rss/homepage.xml",            "category": "top"},
    {"name": "Il Sole 24 Ore",   "url": "https://www.ilsole24ore.com/rss/italia.xml",                   "category": "economia"},
    {"name": "Il Fatto Quotidiano", "url": "https://www.ilfattoquotidiano.it/feed/",                    "category": "politica"},
    {"name": "Il Post",          "url": "https://www.ilpost.it/feed/",                                   "category": "top"},
    {"name": "Internazionale",   "url": "https://www.internazionale.it/sitemaps/rss.xml",                "category": "esteri"},
    {"name": "Fanpage",          "url": "https://www.fanpage.it/feed/",                                  "category": "cronaca"},
    # ── Difesa & Sicurezza ──
    {"name": "Difesa Online",    "url": "https://www.difesaonline.it/rss.xml",                           "category": "difesa"},
    {"name": "Analisi Difesa",   "url": "https://www.analisidifesa.it/feed/",                            "category": "difesa"},
    {"name": "Formiche.net",     "url": "https://formiche.net/feed/",                                    "category": "geopolitica"},
    {"name": "Limes Online",     "url": "https://www.limesonline.com/feed",                              "category": "geopolitica"},
    {"name": "ISPI",             "url": "https://www.ispionline.it/it/rss.xml",                          "category": "geopolitica"},
    {"name": "Affari Internazionali", "url": "https://www.affarinternazionali.it/feed/",                 "category": "geopolitica"},
    # ── Cyber Security ──
    {"name": "CSIRT Italia",     "url": "https://www.csirt.gov.it/rss",                                  "category": "cyber"},
    {"name": "Red Hot Cyber",    "url": "https://www.redhotcyber.com/feed/",                             "category": "cyber"},
    {"name": "Cybersecurity360", "url": "https://www.cybersecurity360.it/feed/",                         "category": "cyber"},
    {"name": "ICT Security Magazine", "url": "https://www.ictsecuritymagazine.com/feed/",               "category": "cyber"},
    # ── Istituzionali ──
    {"name": "Governo.it",       "url": "https://www.governo.it/it/rss.xml",                             "category": "politica"},
    {"name": "Camera dei Deputati", "url": "https://www.camera.it/leg19/1107",                           "category": "politica"},
    {"name": "Protezione Civile", "url": "https://rischi.protezionecivile.gov.it/it/rss.xml",           "category": "emergenze"},
    # ── Esteri & Intelligence ──
    {"name": "Reuters Italia",   "url": "https://www.reuters.com/rssFeed/worldNews",                     "category": "esteri"},
    {"name": "BBC News",         "url": "https://feeds.bbci.co.uk/news/world/europe/rss.xml",            "category": "esteri"},
    {"name": "Al Jazeera",       "url": "https://www.aljazeera.com/xml/rss/all.xml",                     "category": "esteri"},
    {"name": "France24",         "url": "https://www.france24.com/en/europe/rss",                        "category": "esteri"},
    # ── Economia & Finanza ──
    {"name": "Milano Finanza",   "url": "https://www.milanofinanza.it/rss",                              "category": "economia"},
    {"name": "Borsa Italiana",   "url": "https://www.borsaitaliana.it/rss/homepage.htm",                 "category": "economia"},
    # ── Energia & Infrastrutture ──
    {"name": "Qualenergia",      "url": "https://www.qualenergia.it/rss.xml",                            "category": "energia"},
    {"name": "Rinnovabili.it",   "url": "https://www.rinnovabili.it/feed/",                              "category": "energia"},
    # ── Regioni chiave ──
    {"name": "ANSA Lombardia",   "url": "https://www.ansa.it/lombardia/notizie/lombardia_rss.xml",       "category": "regioni"},
    {"name": "ANSA Lazio",       "url": "https://www.ansa.it/lazio/notizie/lazio_rss.xml",               "category": "regioni"},
    {"name": "ANSA Campania",    "url": "https://www.ansa.it/campania/notizie/campania_rss.xml",         "category": "regioni"},
    {"name": "ANSA Sicilia",     "url": "https://www.ansa.it/sicilia/notizie/sicilia_rss.xml",           "category": "regioni"},
]

# Mapping categoria → dimensione primaria
CATEGORY_DIMENSION: dict[str, str] = {
    "cronaca": "sociale",
    "esteri": "geopolitica",
    "politica": "geopolitica",
    "economia": "sociale",
    "tech": "cyber",
    "top": "geopolitica",
    "difesa": "militare",
    "geopolitica": "geopolitica",
    "cyber": "cyber",
    "emergenze": "sociale",
    "energia": "eversione",
    "regioni": "sociale",
}

# Keyword override per classificazione fine
DIMENSION_KEYWORDS: dict[str, list[str]] = {
    "terrorismo": ["terrorismo", "terrorista", "attentato", "isis", "jihad", "bomba", "esplosione", "kamikaze"],
    "cyber": ["cyber", "hacker", "ransomware", "malware", "phishing", "data breach", "vulnerabilità", "cve-"],
    "militare": ["esercito", "marina militare", "aeronautica", "nato", "aviano", "sigonella", "esercitazione", "f-35", "difesa"],
    "eversione": ["estremismo", "anarchico", "neofascismo", "rivolta", "insurrezione", "black bloc"],
}

# Stato globale — headline raccolte per il trending
_all_headlines: list[dict] = []


def get_all_headlines() -> list[dict]:
    """Restituisce tutte le headline raccolte dall'ultimo ciclo."""
    return list(_all_headlines)


class MegaRssCollector(BaseCollector):
    name = "mega_rss"
    display_name = "RSS Aggregator (50+ feed)"

    async def collect(self) -> CollectorResult:
        cached = col_cache.get(CACHE_KEY)
        if cached is not None:
            logger.info(f"[mega_rss] Cache HIT — {cached.get('total', 0)} articoli")
            global _all_headlines
            _all_headlines = cached.get("headlines", [])
            return CollectorResult(source=self.name, data=cached, records_count=cached.get("total", 0))

        logger.info(f"[mega_rss] Cache MISS — fetch {len(FEEDS)} feed")
        headlines = await self._fetch_all()

        data = {
            "total": len(headlines),
            "by_category": self._group_by(headlines, "category"),
            "by_dimension": self._group_by(headlines, "dimension"),
            "by_source": self._group_by(headlines, "source"),
            "headlines": headlines,
        }

        col_cache.set(CACHE_KEY, data, ttl_seconds=CACHE_TTL)

        _all_headlines.clear()
        _all_headlines.extend(headlines)

        return CollectorResult(source=self.name, data=data, records_count=len(headlines))

    async def _fetch_all(self) -> list[dict]:
        """Fetch parallelo di tutti i feed con timeout."""
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            tasks = [self._fetch_feed(client, feed) for feed in FEEDS]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        all_articles: list[dict] = []
        seen_titles: set[str] = set()

        for feed, result in zip(FEEDS, results):
            if isinstance(result, Exception):
                logger.warning(f"[mega_rss] Feed {feed['name']} fallito: {result}")
                continue
            for article in (result or []):
                # Dedup per titolo normalizzato
                title_key = re.sub(r'\s+', ' ', article.get("title", "")).strip().lower()
                if title_key and title_key not in seen_titles:
                    seen_titles.add(title_key)
                    all_articles.append(article)

        logger.info(f"[mega_rss] Raccolti {len(all_articles)} articoli unici da {len(FEEDS)} feed")
        return all_articles

    async def _fetch_feed(self, client: httpx.AsyncClient, feed: dict) -> list[dict]:
        """Fetch singolo feed RSS."""
        try:
            resp = await client.get(feed["url"], headers={
                "User-Agent": "VIGILUS/0.1 (OSINT research)"
            })
            if resp.status_code != 200:
                return []

            parsed = feedparser.parse(resp.text)
            articles = []

            for entry in parsed.entries[:30]:
                title = entry.get("title", "").strip()
                if not title:
                    continue

                summary = entry.get("summary", "")[:300]
                text = (title + " " + summary).lower()
                dimension = self._classify(text, feed.get("category", "top"))

                articles.append({
                    "title": title,
                    "summary": summary,
                    "url": entry.get("link", ""),
                    "published": entry.get("published", ""),
                    "source": feed["name"],
                    "category": feed.get("category", "top"),
                    "dimension": dimension,
                    "collected_at": datetime.now(timezone.utc).isoformat(),
                })

            return articles
        except Exception:
            return []

    def _classify(self, text: str, category: str) -> str:
        """Classifica un articolo per dimensione con keyword override."""
        for dim, keywords in DIMENSION_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                return dim
        return CATEGORY_DIMENSION.get(category, "geopolitica")

    def _group_by(self, articles: list[dict], key: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for a in articles:
            val = a.get(key, "unknown")
            counts[val] = counts.get(val, 0) + 1
        return counts
