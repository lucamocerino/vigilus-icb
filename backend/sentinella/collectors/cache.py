from __future__ import annotations
"""
Cache in-memory con TTL per i collector lenti (Google Trends, ACLED).
Non richiede Redis — dati mantenuti in memoria per processo.
Limite massimo di entry per evitare OOM su Render free tier.
"""
import sys
import time
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

MAX_ENTRIES = 15
_store: dict[str, dict] = {}


def _estimate_size(obj: Any) -> int:
    """Stima approssimativa della dimensione in byte di un oggetto."""
    try:
        return sys.getsizeof(obj)
    except TypeError:
        return 0


def _evict_expired() -> None:
    """Rimuove tutte le entry scadute."""
    now = time.time()
    expired = [k for k, v in _store.items() if now > v["expires_at"]]
    for k in expired:
        del _store[k]
        logger.debug(f"[cache] '{k}' scaduta — rimossa")


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
    _evict_expired()
    # Se siamo al limite e la chiave è nuova, rimuovi la più vecchia
    if key not in _store and len(_store) >= MAX_ENTRIES:
        oldest_key = min(_store, key=lambda k: _store[k]["created_at"])
        del _store[oldest_key]
        logger.debug(f"[cache] Evicted '{oldest_key}' — limite {MAX_ENTRIES} entry")
    now = time.time()
    _store[key] = {
        "value": value,
        "created_at": now,
        "expires_at": now + ttl_seconds,
        "ttl_sec": ttl_seconds,
    }
    logger.debug(f"[cache] SET '{key}' TTL={ttl_seconds//60}min ({len(_store)}/{MAX_ENTRIES} entry)")


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
