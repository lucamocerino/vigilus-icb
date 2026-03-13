"""Tests for collectors: GDELT, CSIRT, ACLED, ADS-B, GoogleTrends, MegaRSS, INGV."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sentinella.collectors.gdelt import GdeltCollector, NEGATIVE_TITLE_KEYWORDS
from sentinella.collectors.csirt import CsirtCollector
from sentinella.collectors.acled import AcledCollector
from sentinella.collectors.adsb import AdsbCollector
from sentinella.collectors.google_trends import GoogleTrendsCollector
from sentinella.collectors.mega_rss import MegaRssCollector
from sentinella.collectors.ingv import IngvCollector
from sentinella.collectors import cache as col_cache
from sentinella.collectors.base import CollectorResult


class TestGdeltCollector:
    def test_aggregate_empty(self):
        c = GdeltCollector()
        result = c._aggregate_articles([])
        assert result["article_count"] == 0
        assert result["negative_ratio"] == 0.0

    def test_aggregate_with_articles(self):
        articles = [
            {"title": "Italy attack threat alert", "url": "http://a", "seendate": "", "domain": "x", "language": "en"},
            {"title": "Italy peace summit", "url": "http://b", "seendate": "", "domain": "y", "language": "en"},
            {"title": "Bomb exploded in Rome", "url": "http://c", "seendate": "", "domain": "z", "language": "en"},
        ]
        c = GdeltCollector()
        result = c._aggregate_articles(articles)
        assert result["article_count"] == 3
        assert result["negative_ratio"] > 0  # "attack" and "bomb" are negative
        assert len(result["articles"]) <= 15

    def test_aggregate_caps_at_15(self):
        articles = [{"title": f"Article {i}", "url": f"http://{i}", "seendate": "", "domain": "", "language": ""} for i in range(30)]
        c = GdeltCollector()
        result = c._aggregate_articles(articles)
        assert len(result["articles"]) == 15

    def test_negative_keywords_regex(self):
        assert NEGATIVE_TITLE_KEYWORDS.search("terror attack in Italy")
        assert NEGATIVE_TITLE_KEYWORDS.search("ransomware hack breach")
        assert NEGATIVE_TITLE_KEYWORDS.search("esplosione bomba Roma")
        assert not NEGATIVE_TITLE_KEYWORDS.search("sunny day in Florence")

    @pytest.mark.asyncio
    async def test_collect_uses_cache(self):
        col_cache._store.clear()
        col_cache.set("gdelt_data", {"geopolitica": {"article_count": 5, "negative_ratio": 0.2}}, 300)
        c = GdeltCollector()
        result = await c.collect()
        assert result.source == "gdelt"
        assert result.records_count == 5
        col_cache._store.clear()


class TestCsirtCollector:
    def test_aggregate_empty(self):
        c = CsirtCollector()
        result = c._aggregate([])
        assert result["bulletin_count"] == 0
        assert result["critical_count"] == 0

    def test_aggregate_with_bulletins(self):
        c = CsirtCollector()
        bulletins = [
            {"type": "alert", "title": "CVE-2024-1234", "severity": "critica", "severity_score": 4, "cve_count": 2, "affects_critical_infra": True},
            {"type": "bollettino", "title": "Update", "severity": "media", "severity_score": 2, "cve_count": 0, "affects_critical_infra": False},
        ]
        result = c._aggregate(bulletins)
        assert result["bulletin_count"] == 2
        assert result["alert_count"] == 1
        assert result["critical_count"] == 1
        assert result["total_cve"] == 2
        assert result["infra_affected_count"] == 1
        assert result["max_severity_score"] == 4

    @pytest.mark.asyncio
    async def test_collect_uses_cache(self):
        col_cache._store.clear()
        col_cache.set("csirt_data", {"bulletin_count": 3}, 300)
        c = CsirtCollector()
        result = await c.collect()
        assert result.records_count == 3
        col_cache._store.clear()


class TestAcledCollector:
    def test_aggregate_empty(self):
        c = AcledCollector()
        result = c._aggregate([])
        assert result["total_events"] == 0
        assert result["protests"] == 0

    def test_aggregate_with_events(self):
        c = AcledCollector()
        events = [
            {"event_type": "Protests"},
            {"event_type": "Protests"},
            {"event_type": "Riots"},
            {"event_type": "Violence against civilians"},
        ]
        result = c._aggregate(events)
        assert result["total_events"] == 4
        assert result["protests"] == 2
        assert result["riots"] == 1
        assert result["violence_civilians"] == 1

    @pytest.mark.asyncio
    async def test_no_api_key_returns_empty(self):
        from sentinella.config import settings
        orig_key, orig_email = settings.acled_api_key, settings.acled_email
        settings.acled_api_key = ""
        settings.acled_email = ""
        try:
            c = AcledCollector()
            result = await c.collect()
            assert result.records_count == 0
        finally:
            settings.acled_api_key = orig_key
            settings.acled_email = orig_email


class TestAdsbCollector:
    @pytest.mark.asyncio
    async def test_collect_uses_cache(self):
        col_cache._store.clear()
        col_cache.set("adsb_data", {"total_flights": 5, "bases": {}}, 300)
        c = AdsbCollector()
        result = await c.collect()
        assert result.records_count == 5
        col_cache._store.clear()


class TestGoogleTrendsCollector:
    @pytest.mark.asyncio
    async def test_collect_uses_cache(self):
        col_cache._store.clear()
        col_cache.set("google_trends_data", {"terrorismo": {"mean": 20}}, 300)
        c = GoogleTrendsCollector()
        result = await c.collect()
        assert result.records_count == 1
        col_cache._store.clear()


class TestMegaRssCollector:
    def test_group_by(self):
        c = MegaRssCollector()
        articles = [
            {"category": "cronaca"}, {"category": "cronaca"}, {"category": "cyber"},
        ]
        result = c._group_by(articles, "category")
        assert result["cronaca"] == 2
        assert result["cyber"] == 1

    def test_classify_keyword_override(self):
        """Verifica che SmartClassifier gestisca correttamente i casi critici."""
        from sentinella.nlp.classifier import get_classifier

        classifier = get_classifier()
        # Keyword override (alta confidenza)
        r = classifier.classify("attentato terrorismo isis", "top")
        assert r["dimension"] == "terrorismo"
        r = classifier.classify("ransomware hacker attacco", "top")
        assert r["dimension"] == "cyber"
        # Semantico o keyword — deve essere militare
        r = classifier.classify("esercitazione militare NATO nel Mediterraneo", "top")
        assert r["dimension"] == "militare"
        # Gossip/spettacolo deve essere non_pertinente
        r = classifier.classify("Mara Venier e Renato Zero al festival di Sanremo", "top")
        assert r["dimension"] == "non_pertinente"

    @pytest.mark.asyncio
    async def test_collect_uses_cache(self):
        col_cache._store.clear()
        col_cache.set("mega_rss_data", {"total": 10, "headlines": [], "by_category": {}, "by_dimension": {}, "by_source": {}}, 300)
        c = MegaRssCollector()
        result = await c.collect()
        assert result.records_count == 10
        col_cache._store.clear()


class TestIngvCollector:
    @pytest.mark.asyncio
    async def test_collect_uses_cache(self):
        col_cache._store.clear()
        col_cache.set("ingv_earthquakes", {"count": 3, "max_mag": 3.5, "earthquakes": []}, 300)
        c = IngvCollector()
        result = await c.collect()
        assert result.records_count == 3
        col_cache._store.clear()
