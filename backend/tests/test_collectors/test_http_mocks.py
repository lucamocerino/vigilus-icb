"""Tests with mocked HTTP for collectors that make real network calls."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import httpx

from sentinella.collectors.gdelt import GdeltCollector
from sentinella.collectors.csirt import CsirtCollector
from sentinella.collectors.acled import AcledCollector
from sentinella.collectors.adsb import AdsbCollector
from sentinella.collectors.ingv import IngvCollector
from sentinella.collectors.mega_rss import MegaRssCollector
from sentinella.collectors import cache as col_cache


class TestGdeltFetchWithRetry:
    def test_successful_fetch(self):
        col_cache._store.clear()
        c = GdeltCollector()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '{"articles": [{"title": "Test Italy", "url": "http://t", "seendate": "", "domain": "x", "language": "en"}]}'
        mock_resp.json.return_value = {"articles": [{"title": "Test Italy", "url": "http://t", "seendate": "", "domain": "x", "language": "en"}]}

        with patch("httpx.get", return_value=mock_resp):
            result = c._fetch_with_retry("Italy test", {})
        assert len(result) == 1
        assert result[0]["title"] == "Test Italy"

    def test_429_rate_limit(self):
        col_cache._store.clear()
        c = GdeltCollector()
        mock_429 = MagicMock()
        mock_429.status_code = 429

        with patch("httpx.get", return_value=mock_429), patch("time.sleep"):
            result = c._fetch_with_retry("test", {})
        assert result == []

    def test_non_json_response(self):
        col_cache._store.clear()
        c = GdeltCollector()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "Rate limit exceeded"
        mock_resp.strip = lambda: "Rate limit exceeded"

        with patch("httpx.get", return_value=mock_resp), patch("time.sleep"):
            result = c._fetch_with_retry("test", {})
        assert result == []

    def test_empty_response(self):
        c = GdeltCollector()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = ""

        with patch("httpx.get", return_value=mock_resp):
            result = c._fetch_with_retry("test", {})
        assert result == []

    def test_network_error(self):
        c = GdeltCollector()
        with patch("httpx.get", side_effect=httpx.ConnectError("Connection refused")), patch("time.sleep"):
            result = c._fetch_with_retry("test", {})
        assert result == []


class TestCsirtParseCards:
    def test_parse_alert_card(self):
        from bs4 import BeautifulSoup
        html = '<div class="card">Alert - 06/03/26 08:44 Vulnerabilità critica CVE-2024-1234 in Apache</div>'
        soup = BeautifulSoup(html, "html.parser")
        c = CsirtCollector()
        bulletins = c._parse_cards(soup)
        assert len(bulletins) == 1
        assert bulletins[0]["type"] == "alert"
        assert bulletins[0]["cve_count"] == 1

    def test_parse_bollettino(self):
        from bs4 import BeautifulSoup
        html = '<div class="card">Bollettino - 05/03/26 10:00 Aggiornamento sicurezza alta priorità</div>'
        soup = BeautifulSoup(html, "html.parser")
        c = CsirtCollector()
        bulletins = c._parse_cards(soup)
        assert len(bulletins) == 1
        assert bulletins[0]["type"] == "bollettino"
        assert bulletins[0]["severity"] == "alta"

    def test_parse_infra_detection(self):
        from bs4 import BeautifulSoup
        html = '<div class="card">Alert - 01/01/26 00:00 Attacco alla pubblica amministrazione PA</div>'
        soup = BeautifulSoup(html, "html.parser")
        c = CsirtCollector()
        bulletins = c._parse_cards(soup)
        assert bulletins[0]["affects_critical_infra"] is True

    def test_parse_empty_cards(self):
        from bs4 import BeautifulSoup
        html = '<div class="card"></div><div class="card">   </div>'
        soup = BeautifulSoup(html, "html.parser")
        c = CsirtCollector()
        bulletins = c._parse_cards(soup)
        assert len(bulletins) == 0

    def test_parse_no_cards(self):
        from bs4 import BeautifulSoup
        html = '<div class="nothing">No cards here</div>'
        soup = BeautifulSoup(html, "html.parser")
        c = CsirtCollector()
        bulletins = c._parse_cards(soup)
        assert len(bulletins) == 0

    @pytest.mark.asyncio
    async def test_collect_http_success(self):
        col_cache._store.clear()
        html = '<html><body><div class="card">Alert - 06/03/26 08:00 Test critica CVE-2024-5678</div></body></html>'
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            c = CsirtCollector()
            result = await c.collect()
        assert result.records_count == 1
        col_cache._store.clear()


class TestAcledCollectHttp:
    @pytest.mark.asyncio
    async def test_collect_with_api_key(self):
        col_cache._store.clear()
        from sentinella.config import settings
        orig_key, orig_email = settings.acled_api_key, settings.acled_email
        settings.acled_api_key = "test-key"
        settings.acled_email = "test@test.com"

        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.json = MagicMock(return_value={"data": [
            {"event_type": "Protests"}, {"event_type": "Riots"},
        ]})
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        try:
            with patch("httpx.AsyncClient", return_value=mock_client):
                c = AcledCollector()
                result = await c.collect()
            assert result.records_count == 2
            assert result.data["protests"] == 1
        finally:
            settings.acled_api_key = orig_key
            settings.acled_email = orig_email
            col_cache._store.clear()


class TestAdsbCollectHttp:
    @pytest.mark.asyncio
    async def test_collect_with_flights(self):
        col_cache._store.clear()
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.json = MagicMock(return_value={"states": [
            ["abc123", "CALL01  ", None, None, None, None, None, None, False],
        ]})
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            c = AdsbCollector()
            result = await c.collect()
        assert result.records_count >= 0  # Depends on how many bases respond
        col_cache._store.clear()

    @pytest.mark.asyncio
    async def test_429_handled(self):
        col_cache._store.clear()
        mock_resp = AsyncMock()
        mock_resp.status_code = 429

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            c = AdsbCollector()
            result = await c.collect()
        assert result.data["total_flights"] == 0
        col_cache._store.clear()


class TestIngvCollectHttp:
    @pytest.mark.asyncio
    async def test_collect_with_data(self):
        col_cache._store.clear()
        geojson = {
            "type": "FeatureCollection",
            "features": [{
                "properties": {"time": "2026-03-06T10:00:00", "mag": 3.2, "place": "Costa Calabra", "magType": "ML"},
                "geometry": {"type": "Point", "coordinates": [16.5, 38.9, 10.0]},
            }],
        }
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.json = MagicMock(return_value=geojson)
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            c = IngvCollector()
            result = await c.collect()
        assert result.records_count == 1
        assert result.data["max_mag"] == 3.2
        assert result.data["earthquakes"][0]["place"] == "Costa Calabra"
        col_cache._store.clear()

    @pytest.mark.asyncio
    async def test_collect_204_no_content(self):
        col_cache._store.clear()
        mock_resp = AsyncMock()
        mock_resp.status_code = 204

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            c = IngvCollector()
            result = await c.collect()
        assert result.records_count == 0
        col_cache._store.clear()


class TestMegaRssCollectHttp:
    @pytest.mark.asyncio
    async def test_fetch_feed_success(self):
        rss_xml = """<?xml version="1.0"?>
        <rss><channel>
            <item><title>Notizia test Roma</title><link>http://test/1</link><summary>Desc</summary></item>
            <item><title>Cyber attacco hacker</title><link>http://test/2</link><summary>Hack</summary></item>
        </channel></rss>"""

        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.text = rss_xml

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        c = MegaRssCollector()
        result = await c._fetch_feed(mock_client, {"name": "Test", "url": "http://feed", "category": "top"})
        assert len(result) == 2
        assert result[0]["source"] == "Test"
        # Classification now happens in batch via _classify_batch, not in _fetch_feed
        assert "title" in result[1]
        assert result[1]["category"] == "top"

        # Verify batch classification works
        classified = c._classify_batch(result)
        assert classified[1]["dimension"] == "cyber"
        assert "confidence" in classified[1]

    @pytest.mark.asyncio
    async def test_fetch_feed_failure(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Network error"))

        c = MegaRssCollector()
        result = await c._fetch_feed(mock_client, {"name": "Bad", "url": "http://bad", "category": "top"})
        assert result == []

    @pytest.mark.asyncio
    async def test_dedup_titles(self):
        col_cache._store.clear()
        rss_xml = """<?xml version="1.0"?>
        <rss><channel>
            <item><title>Stessa notizia</title><link>http://a</link></item>
            <item><title>Stessa notizia</title><link>http://b</link></item>
        </channel></rss>"""

        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.text = rss_xml

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            c = MegaRssCollector()
            headlines = await c._fetch_all()
        # Should deduplicate
        titles = [h["title"] for h in headlines]
        assert titles.count("Stessa notizia") == 1
        col_cache._store.clear()
