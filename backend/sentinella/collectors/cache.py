from __future__ import annotations
"""
Cache in-memory con TTL per i collector lenti (Google Trends, ACLED).
Non richiede Redis — dati mantenuti in memoria per processo.
"""
import time
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

_store: dict[str, dict] = {}


def get(key: str) -> Optional[Any]:
    entry = _store.get(key)
    if entry is None:
        return None
    if time.time() > entry["expires_at"]:
        del _store[key]
        logger.debug(f"[cache] '{key}' scaduta")
        return None
    age_min = int((time.time() - entry["created_at"]) / 60)
    logger.debug(f"[cache] HIT '{key}' (età {age_min}min, TTL {entry['ttl_sec']//60}min)")
    return entry["value"]


def set(key: str, value: Any, ttl_seconds: int) -> None:
    now = time.time()
    _store[key] = {
        "value": value,
        "created_at": now,
        "expires_at": now + ttl_seconds,
        "ttl_sec": ttl_seconds,
    }
    logger.debug(f"[cache] SET '{key}' TTL={ttl_seconds//60}min")


def invalidate(key: str) -> None:
    _store.pop(key, None)


def status() -> dict[str, dict]:
    now = time.time()
    return {
        k: {
            "age_min": int((now - v["created_at"]) / 60),
            "expires_in_min": max(0, int((v["expires_at"] - now) / 60)),
            "ttl_min": v["ttl_sec"] // 60,
        }
        for k, v in _store.items()
        if now <= v["expires_at"]
    }
