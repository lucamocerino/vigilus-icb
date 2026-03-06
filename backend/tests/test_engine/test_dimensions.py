"""Tests for sentinella.engine.dimensions — 6 dimension calculators."""
from sentinella.engine.dimensions import (
    calc_geopolitica,
    calc_terrorismo,
    calc_cyber,
    calc_eversione,
    calc_militare,
    calc_sociale,
)


class TestCalcGeopolitica:
    def test_returns_tuple(self, gdelt_data_normal):
        score, raw = calc_geopolitica(gdelt_data_normal)
        assert isinstance(score, float)
        assert isinstance(raw, dict)

    def test_score_in_range(self, gdelt_data_normal):
        score, _ = calc_geopolitica(gdelt_data_normal)
        assert 0.0 <= score <= 100.0

    def test_raw_has_expected_keys(self, gdelt_data_normal):
        _, raw = calc_geopolitica(gdelt_data_normal)
        assert "article_count" in raw
        assert "negative_ratio" in raw
        assert "military_count" in raw

    def test_high_data_produces_higher_score(self, gdelt_data_normal, gdelt_data_high):
        score_normal, _ = calc_geopolitica(gdelt_data_normal)
        score_high, _ = calc_geopolitica(gdelt_data_high)
        assert score_high > score_normal

    def test_empty_data_returns_valid(self):
        score, raw = calc_geopolitica({})
        assert 0.0 <= score <= 100.0


class TestCalcTerrorismo:
    def test_returns_tuple(self, gdelt_data_normal, trends_data_normal):
        score, raw = calc_terrorismo(gdelt_data_normal, trends_data_normal)
        assert isinstance(score, float)
        assert isinstance(raw, dict)

    def test_score_in_range(self, gdelt_data_normal, trends_data_normal):
        score, _ = calc_terrorismo(gdelt_data_normal, trends_data_normal)
        assert 0.0 <= score <= 100.0

    def test_raw_has_expected_keys(self, gdelt_data_normal, trends_data_normal):
        _, raw = calc_terrorismo(gdelt_data_normal, trends_data_normal)
        assert "article_count" in raw
        assert "negative_ratio" in raw
        assert "trends_mean" in raw

    def test_empty_data_returns_valid(self):
        score, _ = calc_terrorismo({}, {})
        assert 0.0 <= score <= 100.0


class TestCalcCyber:
    def test_returns_tuple(self, csirt_data_normal, gdelt_data_normal):
        score, raw = calc_cyber(csirt_data_normal, gdelt_data_normal)
        assert isinstance(score, float)
        assert isinstance(raw, dict)

    def test_score_in_range(self, csirt_data_normal, gdelt_data_normal):
        score, _ = calc_cyber(csirt_data_normal, gdelt_data_normal)
        assert 0.0 <= score <= 100.0

    def test_raw_has_expected_keys(self, csirt_data_normal, gdelt_data_normal):
        _, raw = calc_cyber(csirt_data_normal, gdelt_data_normal)
        assert "bulletin_count" in raw
        assert "critical_count" in raw
        assert "total_cve" in raw

    def test_high_critical_raises_score(self, gdelt_data_normal):
        low = {"bulletin_count": 2, "critical_count": 0, "total_cve": 2, "infra_affected_count": 0}
        high = {"bulletin_count": 20, "critical_count": 10, "total_cve": 40, "infra_affected_count": 5}
        score_low, _ = calc_cyber(low, gdelt_data_normal)
        score_high, _ = calc_cyber(high, gdelt_data_normal)
        assert score_high > score_low


class TestCalcEversione:
    def test_returns_tuple(self, gdelt_data_normal, acled_data_normal, rss_data_normal):
        score, raw = calc_eversione(gdelt_data_normal, acled_data_normal, rss_data_normal)
        assert isinstance(score, float)
        assert isinstance(raw, dict)

    def test_score_in_range(self, gdelt_data_normal, acled_data_normal, rss_data_normal):
        score, _ = calc_eversione(gdelt_data_normal, acled_data_normal, rss_data_normal)
        assert 0.0 <= score <= 100.0

    def test_empty_data_returns_valid(self):
        score, _ = calc_eversione({}, {}, {})
        assert 0.0 <= score <= 100.0


class TestCalcMilitare:
    def test_returns_tuple(self, adsb_data_normal, gdelt_data_normal, trends_data_normal):
        score, raw = calc_militare(adsb_data_normal, gdelt_data_normal, trends_data_normal)
        assert isinstance(score, float)
        assert isinstance(raw, dict)

    def test_score_in_range(self, adsb_data_normal, gdelt_data_normal, trends_data_normal):
        score, _ = calc_militare(adsb_data_normal, gdelt_data_normal, trends_data_normal)
        assert 0.0 <= score <= 100.0

    def test_raw_has_expected_keys(self, adsb_data_normal, gdelt_data_normal, trends_data_normal):
        _, raw = calc_militare(adsb_data_normal, gdelt_data_normal, trends_data_normal)
        assert "total_flights" in raw
        assert "gdelt_articles" in raw
        assert "trends_mean" in raw


class TestCalcSociale:
    def test_returns_tuple(self, gdelt_data_normal, trends_data_normal, acled_data_normal):
        score, raw = calc_sociale(gdelt_data_normal, trends_data_normal, acled_data_normal)
        assert isinstance(score, float)
        assert isinstance(raw, dict)

    def test_score_in_range(self, gdelt_data_normal, trends_data_normal, acled_data_normal):
        score, _ = calc_sociale(gdelt_data_normal, trends_data_normal, acled_data_normal)
        assert 0.0 <= score <= 100.0

    def test_empty_data_returns_valid(self):
        score, _ = calc_sociale({}, {}, {})
        assert 0.0 <= score <= 100.0
