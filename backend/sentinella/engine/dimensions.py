from __future__ import annotations
"""
Calcolo dei 6 sotto-indici dimensionali dai dati grezzi dei collector.
GDELT fornisce: article_count, negative_ratio (da titoli, non `tone`)
"""
from typing import Any
import logging

from sentinella.engine.normalizer import normalize_proxy, aggregate_proxies
from sentinella.engine.baseline import get_default_baseline

logger = logging.getLogger(__name__)


def _b(dimension: str, proxy: str) -> dict[str, float]:
    return get_default_baseline(dimension, proxy)


def calc_geopolitica(gdelt_data: dict[str, Any]) -> tuple[float, dict]:
    geo = gdelt_data.get("geopolitica", {})
    mil = gdelt_data.get("militare", {})

    raw = {
        "article_count":    geo.get("article_count", 0),
        "negative_ratio":   geo.get("negative_ratio", 0.0),
        "military_count":   mil.get("article_count", 0),
    }

    proxies = {
        "article_count":  normalize_proxy(raw["article_count"],  **_b("geopolitica", "article_count")),
        "negative_ratio": normalize_proxy(raw["negative_ratio"], **_b("geopolitica", "negative_ratio")),
        "military_count": normalize_proxy(raw["military_count"], **_b("geopolitica", "military_count")),
    }
    return aggregate_proxies(proxies, {"article_count": 0.35, "negative_ratio": 0.45, "military_count": 0.20}), raw


def calc_terrorismo(gdelt_data: dict[str, Any], trends_data: dict[str, Any]) -> tuple[float, dict]:
    terror = gdelt_data.get("terrorismo", {})

    raw = {
        "article_count":  terror.get("article_count", 0),
        "negative_ratio": terror.get("negative_ratio", 0.0),
        "trends_mean":    trends_data.get("terrorismo", {}).get("mean", 0),
    }

    proxies = {
        "article_count":  normalize_proxy(raw["article_count"],  **_b("terrorismo", "article_count")),
        "negative_ratio": normalize_proxy(raw["negative_ratio"], **_b("terrorismo", "negative_ratio")),
        "trends":         normalize_proxy(raw["trends_mean"],    mean=20.0, std=15.0),
    }
    return aggregate_proxies(proxies, {"article_count": 0.40, "negative_ratio": 0.40, "trends": 0.20}), raw


def calc_cyber(csirt_data: dict[str, Any], gdelt_data: dict[str, Any]) -> tuple[float, dict]:
    raw = {
        "bulletin_count":      csirt_data.get("bulletin_count", 0),
        "critical_count":      csirt_data.get("critical_count", 0),
        "total_cve":           csirt_data.get("total_cve", 0),
        "infra_affected":      csirt_data.get("infra_affected_count", 0),
        "gdelt_cyber_count":   gdelt_data.get("cyber", {}).get("article_count", 0),
    }

    proxies = {
        "bulletins": normalize_proxy(raw["bulletin_count"],    **_b("cyber", "bulletin_count")),
        "critical":  normalize_proxy(raw["critical_count"],    **_b("cyber", "critical_count")),
        "cve":       normalize_proxy(raw["total_cve"],         **_b("cyber", "total_cve")),
        "gdelt":     normalize_proxy(raw["gdelt_cyber_count"], mean=5.0, std=4.0),
    }
    return aggregate_proxies(proxies, {"bulletins": 0.25, "critical": 0.45, "cve": 0.15, "gdelt": 0.15}), raw


def calc_eversione(
    gdelt_data: dict[str, Any],
    acled_data: dict[str, Any],
    rss_data: dict[str, Any],
) -> tuple[float, dict]:
    ev = gdelt_data.get("eversione", {})

    raw = {
        "gdelt_articles":  ev.get("article_count", 0),
        "negative_ratio":  ev.get("negative_ratio", 0.0),
        "acled_protests":  acled_data.get("protests", 0),
        "acled_riots":     acled_data.get("riots", 0),
        "rss_articles":    len(rss_data.get("by_dimension", {}).get("eversione", [])),
    }

    proxies = {
        "gdelt":     normalize_proxy(raw["gdelt_articles"],                   **_b("eversione", "article_count")),
        "negative":  normalize_proxy(raw["negative_ratio"],                   **_b("eversione", "negative_ratio")),
        "acled":     normalize_proxy(raw["acled_protests"] + raw["acled_riots"] * 2, mean=5.0, std=4.0),
        "rss":       normalize_proxy(raw["rss_articles"],                     mean=3.0, std=3.0),
    }
    return aggregate_proxies(proxies, {"gdelt": 0.35, "negative": 0.25, "acled": 0.30, "rss": 0.10}), raw


def calc_militare(
    adsb_data: dict[str, Any],
    gdelt_data: dict[str, Any],
    trends_data: dict[str, Any],
) -> tuple[float, dict]:
    raw = {
        "total_flights":   adsb_data.get("total_flights", 0),
        "gdelt_articles":  gdelt_data.get("militare", {}).get("article_count", 0),
        "trends_mean":     trends_data.get("militare", {}).get("mean", 0),
    }

    proxies = {
        "flights": normalize_proxy(raw["total_flights"],  **_b("militare", "total_flights")),
        "gdelt":   normalize_proxy(raw["gdelt_articles"], mean=20.0, std=10.0),
        "trends":  normalize_proxy(raw["trends_mean"],    mean=15.0, std=12.0),
    }
    return aggregate_proxies(proxies, {"flights": 0.50, "gdelt": 0.30, "trends": 0.20}), raw


def calc_sociale(
    gdelt_data: dict[str, Any],
    trends_data: dict[str, Any],
    acled_data: dict[str, Any],
) -> tuple[float, dict]:
    soc = gdelt_data.get("sociale", {})

    raw = {
        "gdelt_articles":  soc.get("article_count", 0),
        "negative_ratio":  soc.get("negative_ratio", 0.0),
        "trends_mean":     trends_data.get("sociale", {}).get("mean", 0),
        "acled_protests":  acled_data.get("protests", 0),
    }

    proxies = {
        "gdelt":   normalize_proxy(raw["gdelt_articles"], **_b("sociale", "article_count")),
        "trends":  normalize_proxy(raw["trends_mean"],    **_b("sociale", "trends_mean")),
        "acled":   normalize_proxy(raw["acled_protests"], mean=3.0, std=3.0),
    }
    return aggregate_proxies(proxies, {"gdelt": 0.40, "trends": 0.40, "acled": 0.20}), raw
