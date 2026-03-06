from __future__ import annotations
"""
Collector CSIRT Italia — struttura reale verificata: selettore `.card`.
Formato card: "Alert/Bollettino - GG/MM/AA HH:MM Titolo testo..."
"""
import re
from typing import Any
import logging

import httpx
from bs4 import BeautifulSoup

from sentinella.collectors.base import BaseCollector, CollectorResult
from sentinella.collectors import cache as col_cache

logger = logging.getLogger(__name__)

CSIRT_URL = "https://www.csirt.gov.it/contenuti/bollettini"
CACHE_KEY  = "csirt_data"
CACHE_TTL  = 30 * 60  # 30 minuti

SEVERITY_MAP = {"critica": 4, "alta": 3, "media": 2, "bassa": 1}

CRITICAL_INFRA = re.compile(
    r'\b(pubblica.amministrazione|PA|energia|trasporti|sanit[àa]|'
    r'ospedale|ferrovie|aeroporto|porto|teleco|banche?|finanziar)\b',
    re.IGNORECASE
)


class CsirtCollector(BaseCollector):
    name = "csirt"
    display_name = "CSIRT Italia (ACN)"

    async def collect(self) -> CollectorResult:
        cached = col_cache.get(CACHE_KEY)
        if cached is not None:
            logger.info("[csirt] Cache HIT")
            return CollectorResult(source=self.name, data=cached,
                                   records_count=cached.get("bulletin_count", 0))

        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(CSIRT_URL, headers={
                "User-Agent": "Mozilla/5.0 VIGILUS/0.1 (OSINT research)"
            })
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        bulletins = self._parse_cards(soup)
        data = self._aggregate(bulletins)

        col_cache.set(CACHE_KEY, data, ttl_seconds=CACHE_TTL)

        return CollectorResult(source=self.name, data=data, records_count=len(bulletins))

    def _parse_cards(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        bulletins = []
        cards = soup.select(".card")

        for card in cards[:60]:
            text = card.get_text(" ", strip=True)
            if not text:
                continue

            # Tipo: Alert o Bollettino
            tipo = "alert" if text.lower().startswith("alert") else "bollettino"

            # Estrai titolo: dopo il separatore " - data -" o simile
            # Formato: "Alert - 06/03/26 08:44 Titolo..."
            parts = re.split(r'\d{2}/\d{2}/\d{2}\s+\d{2}:\d{2}', text, maxsplit=1)
            title = parts[1].strip()[:200] if len(parts) > 1 else text[:200]

            text_lower = text.lower()
            severity = "sconosciuta"
            for kw in SEVERITY_MAP:
                if f'"{kw}"' in text_lower or f"gravità \"{kw}\"" in text_lower or f" {kw}" in text_lower:
                    severity = kw
                    break

            cve_count = len(re.findall(r"cve-\d{4}-\d+", text, re.IGNORECASE))
            affects_infra = bool(CRITICAL_INFRA.search(text))

            bulletins.append({
                "type":            tipo,
                "title":           title,
                "severity":        severity,
                "severity_score":  SEVERITY_MAP.get(severity, 0),
                "cve_count":       cve_count,
                "affects_critical_infra": affects_infra,
            })

        return bulletins

    def _aggregate(self, bulletins: list[dict]) -> dict[str, Any]:
        if not bulletins:
            return {
                "bulletin_count": 0, "alert_count": 0,
                "critical_count": 0, "high_count": 0,
                "total_cve": 0, "infra_affected_count": 0,
                "max_severity_score": 0,
            }
        return {
            "bulletin_count":      len(bulletins),
            "alert_count":         sum(1 for b in bulletins if b["type"] == "alert"),
            "critical_count":      sum(1 for b in bulletins if b["severity"] == "critica"),
            "high_count":          sum(1 for b in bulletins if b["severity"] == "alta"),
            "total_cve":           sum(b["cve_count"] for b in bulletins),
            "infra_affected_count": sum(1 for b in bulletins if b["affects_critical_infra"]),
            "max_severity_score":  max(b["severity_score"] for b in bulletins),
            "bulletins":           bulletins[:10],
        }
