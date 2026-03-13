from __future__ import annotations
"""
Collector RSS — Feed ANSA con classificazione keyword + spaCy NER per geo-tagging.
"""
import asyncio
from datetime import datetime, timezone
from typing import Any, Optional
import logging

import feedparser
import httpx

from sentinella.collectors.base import BaseCollector, CollectorResult

logger = logging.getLogger(__name__)

RSS_FEEDS = [
    {"name": "ANSA Cronaca",  "url": "https://www.ansa.it/sito/notizie/cronaca/cronaca_rss.xml"},
    {"name": "ANSA Mondo",    "url": "https://www.ansa.it/sito/notizie/mondo/mondo_rss.xml"},
    {"name": "ANSA Politica", "url": "https://www.ansa.it/sito/notizie/politica/politica_rss.xml"},
]

DIMENSION_KEYWORDS: dict[str, list[str]] = {
    "terrorismo": [
        "terrorismo", "terrorista", "attentato", "isis", "jihad", "allerta",
        "minaccia", "bomba", "esplosione", "attacco armato",
    ],
    "cyber": [
        "cyber", "hacker", "ransomware", "data breach", "attacco informatico",
        "csirt", "acn", "infrastruttura critica", "malware", "phishing",
    ],
    "geopolitica": [
        "nato", "ue", "unione europea", "diplomazia", "sanzioni", "trattato",
        "conflitto", "ucraina", "medio oriente", "russia", "cina",
    ],
    "eversione": [
        "estremismo", "estrema destra", "estrema sinistra", "neofascismo",
        "anarchico", "insurrezione", "sovversivo", "rivolta",
    ],
    "militare": [
        "esercito", "marina", "aeronautica", "carabinieri", "esercitazione",
        "nato", "aviano", "sigonella", "forze armate", "difesa",
    ],
    "sociale": [
        "sciopero", "manifestazione", "protesta", "tensione sociale",
        "disordini", "piazza", "scontri", "polizia",
    ],
}

ITALIAN_GEO: dict[str, tuple[float, float]] = {
    "roma": (41.9028, 12.4964), "rome": (41.9028, 12.4964),
    "milano": (45.4642, 9.1900), "milan": (45.4642, 9.1900),
    "napoli": (40.8518, 14.2681), "naples": (40.8518, 14.2681),
    "torino": (45.0703, 7.6869), "turin": (45.0703, 7.6869),
    "palermo": (38.1157, 13.3615),
    "genova": (44.4056, 8.9463), "genoa": (44.4056, 8.9463),
    "bologna": (44.4949, 11.3426),
    "firenze": (43.7696, 11.2558), "florence": (43.7696, 11.2558),
    "venezia": (45.4408, 12.3155), "venice": (45.4408, 12.3155),
    "bari": (41.1171, 16.8719),
    "catania": (37.5079, 15.0830),
    "verona": (45.4384, 10.9916),
    "trieste": (45.6495, 13.7768),
    "taranto": (40.4764, 17.2297),
    "brescia": (45.5416, 10.2118),
    "bergamo": (45.6983, 9.6773),
    "perugia": (43.1107, 12.3908),
    "cagliari": (39.2238, 9.1217),
    "lecce": (40.3516, 18.1750),
    "salerno": (40.6824, 14.7681),
    "foggia": (41.4621, 15.5441),
    "sassari": (40.7259, 8.5556),
    "pisa": (43.7228, 10.4017),
    "trento": (46.0748, 11.1217),
    "bolzano": (46.4983, 11.3548),
    "ancona": (43.6158, 13.5189),
    "reggio calabria": (38.1096, 15.6472),
    "reggio emilia": (44.6989, 10.6296),
    "padova": (45.4064, 11.8768),
    "modena": (44.6471, 10.9252),
    "lombardia": (45.5845, 9.9350),
    "sicilia": (37.6000, 14.0154),
    "sardegna": (40.1208, 9.0129),
    "puglia": (41.1250, 16.8719),
    "calabria": (38.9098, 16.5872),
    "toscana": (43.7711, 11.2486),
    "veneto": (45.4972, 11.9952),
    "piemonte": (45.0526, 7.5154),
    "campania": (40.8359, 14.2488),
    "lazio": (41.9028, 12.4964),
    "emilia-romagna": (44.4949, 11.3426),
    "liguria": (44.3106, 8.4679),
    "marche": (43.3619, 13.5167),
    "abruzzo": (42.1875, 13.7501),
    "umbria": (42.9379, 12.6218),
    "trentino": (46.0748, 11.1217),
    "friuli": (46.0747, 13.2346),
    "basilicata": (40.5000, 15.9000),
    "molise": (41.5603, 14.6608),
    "italia": (41.8719, 12.5674),
}

_geo_events: list[dict] = []


def get_geo_events() -> list[dict]:
    return list(_geo_events)


_nlp: Optional[Any] = None


def _get_nlp() -> Optional[Any]:
    global _nlp
    if _nlp is None:
        try:
            import spacy
            _nlp = spacy.load("it_core_news_sm", disable=["parser", "senter"])
            logger.info("[rss] spaCy it_core_news_sm caricato")
        except Exception as e:
            logger.warning(f"[rss] spaCy non disponibile: {e}")
            _nlp = False
    return _nlp if _nlp is not False else None


def _extract_locations(text: str) -> list[dict]:
    nlp = _get_nlp()
    if nlp is None:
        return []
    try:
        doc = nlp(text[:500])
        found, seen = [], set()
        for ent in doc.ents:
            if ent.label_ in ("GPE", "LOC"):
                key = ent.text.lower().strip()
                if key in ITALIAN_GEO and key not in seen:
                    lat, lon = ITALIAN_GEO[key]
                    found.append({"name": ent.text, "lat": lat, "lon": lon})
                    seen.add(key)
        return found
    except Exception:
        return []


class NewsRssCollector(BaseCollector):
    name = "rss"
    display_name = "RSS News (ANSA)"

    async def collect(self) -> CollectorResult:
        all_articles: list[dict] = []

        async with httpx.AsyncClient(timeout=15) as client:
            tasks = [self._fetch_feed(client, feed) for feed in RSS_FEEDS]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        for res in results:
            if isinstance(res, Exception):
                logger.warning(f"[rss] Errore feed: {res}")
            else:
                all_articles.extend(res)

        classified = self._classify_articles(all_articles)
        geo = self._extract_geo_events(all_articles, classified)

        global _geo_events
        _geo_events = geo
        logger.info(f"[rss] {sum(len(v) for v in classified.values())} articoli classificati, {len(geo)} geo-taggati")

        total = sum(len(v) for v in classified.values())
        return CollectorResult(
            source=self.name,
            data={"by_dimension": classified, "total": total, "geo_count": len(geo)},
            records_count=total,
        )

    async def _fetch_feed(self, client: httpx.AsyncClient, feed: dict) -> list[dict]:
        resp = await client.get(feed["url"])
        resp.raise_for_status()
        parsed = feedparser.parse(resp.text)
        return [
            {
                "title":     entry.get("title", ""),
                "summary":   entry.get("summary", ""),
                "link":      entry.get("link", ""),
                "published": entry.get("published", ""),
                "source":    feed["name"],
            }
            for entry in parsed.entries
        ]

    def _classify_articles(self, articles: list[dict]) -> dict[str, list[dict]]:
        from sentinella.nlp.classifier import get_classifier, DIMENSIONS

        classified: dict[str, list[dict]] = {dim: [] for dim in DIMENSIONS}
        classifier = get_classifier()
        texts = [
            (a.get("title", "") + " " + a.get("summary", ""))
            for a in articles
        ]
        results = classifier.classify_batch(texts)

        for article, result in zip(articles, results):
            dim = result["dimension"]
            article["confidence"] = result["confidence"]
            article["classification_method"] = result["method"]
            classified[dim].append(article)

        return classified

    def _extract_geo_events(
        self, articles: list[dict], classified: dict[str, list[dict]]
    ) -> list[dict]:
        article_dim: dict[str, str] = {}
        for dim, arts in classified.items():
            for a in arts:
                article_dim[a.get("link", "")] = dim

        geo_events = []
        now = datetime.now(timezone.utc).isoformat()

        for article in articles:
            text = article.get("title", "") + " " + article.get("summary", "")
            locations = _extract_locations(text)
            if not locations:
                continue
            dim = article_dim.get(article.get("link", ""), "geopolitica")
            geo_events.append({
                "title":     article.get("title", ""),
                "url":       article.get("link", ""),
                "dimension": dim,
                "lat":       locations[0]["lat"],
                "lon":       locations[0]["lon"],
                "location":  locations[0]["name"],
                "collected": now,
            })

        return geo_events
