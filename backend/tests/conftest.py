"""Shared fixtures for Sentinella test suite."""
from __future__ import annotations
import pytest


@pytest.fixture
def gdelt_data_normal():
    """GDELT data at baseline levels."""
    return {
        "geopolitica": {"article_count": 80, "negative_ratio": 0.35},
        "terrorismo":  {"article_count": 15, "negative_ratio": 0.55},
        "cyber":       {"article_count": 5,  "negative_ratio": 0.30},
        "eversione":   {"article_count": 20, "negative_ratio": 0.40},
        "militare":    {"article_count": 20, "negative_ratio": 0.30},
        "sociale":     {"article_count": 25, "negative_ratio": 0.25},
    }


@pytest.fixture
def gdelt_data_high():
    """GDELT data well above baseline (should produce elevated scores)."""
    return {
        "geopolitica": {"article_count": 200, "negative_ratio": 0.75},
        "terrorismo":  {"article_count": 60,  "negative_ratio": 0.90},
        "cyber":       {"article_count": 30,  "negative_ratio": 0.80},
        "eversione":   {"article_count": 80,  "negative_ratio": 0.85},
        "militare":    {"article_count": 70,  "negative_ratio": 0.70},
        "sociale":     {"article_count": 90,  "negative_ratio": 0.75},
    }


@pytest.fixture
def trends_data_normal():
    return {
        "terrorismo": {"mean": 20, "max": 40},
        "sociale":    {"mean": 30, "max": 60},
        "militare":   {"mean": 15, "max": 35},
        "geopolitica": {"mean": 25, "max": 50},
        "cyber":      {"mean": 10, "max": 25},
    }


@pytest.fixture
def csirt_data_normal():
    return {
        "bulletin_count": 8,
        "alert_count": 2,
        "critical_count": 1,
        "high_count": 3,
        "total_cve": 12,
        "infra_affected_count": 0,
        "max_severity_score": 3,
        "bulletins": [],
    }


@pytest.fixture
def acled_data_normal():
    return {
        "total_events": 5,
        "protests": 3,
        "riots": 1,
        "violence_civilians": 0,
        "battles": 0,
        "by_type": {},
    }


@pytest.fixture
def adsb_data_normal():
    return {
        "total_flights": 8,
        "bases": {},
    }


@pytest.fixture
def rss_data_normal():
    return {
        "by_dimension": {
            "geopolitica": ["art1"],
            "eversione": ["art1", "art2", "art3"],
            "sociale": ["art1", "art2"],
        },
        "total": 10,
        "geo_count": 3,
    }
