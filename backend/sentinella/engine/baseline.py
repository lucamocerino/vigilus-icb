from __future__ import annotations
"""
Gestione baseline rolling 90 giorni.
Valori di default basati su osservazioni tipiche di GDELT per l'Italia.
"""
from datetime import datetime, timezone, timedelta
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)

# Percorso al file baseline reale (generato da seed_baseline.py)
BASELINE_FILE = Path(__file__).parent.parent.parent.parent / "data" / "seed" / "baseline_real.json"

DEFAULT_BASELINES: dict[str, dict[str, dict[str, float]]] = {
    "geopolitica": {
        "article_count":  {"mean": 80.0,  "std": 30.0},
        "negative_ratio": {"mean": 0.35,  "std": 0.12},
        "military_count": {"mean": 30.0,  "std": 15.0},
    },
    "terrorismo": {
        "article_count":  {"mean": 15.0,  "std": 8.0},
        "negative_ratio": {"mean": 0.55,  "std": 0.18},
    },
    "cyber": {
        "bulletin_count": {"mean": 8.0,   "std": 4.0},
        "critical_count": {"mean": 1.5,   "std": 1.5},
        "total_cve":      {"mean": 12.0,  "std": 8.0},
    },
    "eversione": {
        "article_count":  {"mean": 20.0,  "std": 10.0},
        "negative_ratio": {"mean": 0.40,  "std": 0.14},
    },
    "militare": {
        "total_flights":  {"mean": 8.0,   "std": 4.0},
    },
    "sociale": {
        "article_count":  {"mean": 25.0,  "std": 12.0},
        "trends_mean":    {"mean": 30.0,  "std": 20.0},
    },
}

# Carica baseline reale se esiste
_real_baselines: dict = {}

def _load_real_baselines() -> None:
    global _real_baselines
    if BASELINE_FILE.exists():
        try:
            _real_baselines = json.loads(BASELINE_FILE.read_text())
            logger.info(f"Baseline reale caricata da {BASELINE_FILE}")
        except Exception as e:
            logger.warning(f"Impossibile caricare baseline reale: {e}")

_load_real_baselines()


def get_default_baseline(dimension: str, proxy: str) -> dict[str, float]:
    """Restituisce baseline reale se disponibile, altrimenti i default statici."""
    if _real_baselines:
        real = _real_baselines.get(dimension, {}).get(proxy)
        if real:
            return real
    return DEFAULT_BASELINES.get(dimension, {}).get(proxy, {"mean": 0.0, "std": 1.0})


async def get_baseline(db, dimension: str, proxy: str, days: int = 90) -> dict[str, float]:
    """Baseline da DB (usata quando ci sono abbastanza dati storici)."""
    from sqlalchemy import select
    from sentinella.models.score import DimensionScore, ScoreSnapshot

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = (
        select(DimensionScore.raw_values)
        .join(ScoreSnapshot)
        .where(DimensionScore.dimension == dimension, ScoreSnapshot.timestamp >= cutoff)
        .order_by(ScoreSnapshot.timestamp.desc())
        .limit(days * 6)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()

    values = []
    for raw in rows:
        if raw and proxy in raw:
            try:
                values.append(float(raw[proxy]))
            except (TypeError, ValueError):
                pass

    if len(values) < 14:
        return get_default_baseline(dimension, proxy)

    import numpy as np
    return {"mean": float(np.mean(values)), "std": float(np.std(values)) or 1.0}
