"""
Confronto tra due periodi temporali — medie, delta, trend per ogni dimensione.
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sentinella.db import get_db
from sentinella.models.score import ScoreSnapshot
from sentinella.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/score", tags=["score"])

DIMENSIONS = list(settings.WEIGHTS.keys())


@router.get("/compare")
async def compare_periods(
    period: str = Query(
        default="week",
        description="Tipo di confronto: week (questa vs scorsa), month, quarter",
        pattern="^(week|month|quarter|custom)$",
    ),
    # Usati solo con period=custom
    p1_start: str = Query(default=None, description="Inizio periodo 1 (ISO date, es. 2025-01-01)"),
    p1_end: str = Query(default=None, description="Fine periodo 1"),
    p2_start: str = Query(default=None, description="Inizio periodo 2"),
    p2_end: str = Query(default=None, description="Fine periodo 2"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Confronta medie score tra due periodi."""
    now = datetime.now(timezone.utc)

    if period == "week":
        p1_s = now - timedelta(days=7)
        p1_e = now
        p2_s = now - timedelta(days=14)
        p2_e = now - timedelta(days=7)
        label1, label2 = "Questa settimana", "Settimana precedente"
    elif period == "month":
        p1_s = now - timedelta(days=30)
        p1_e = now
        p2_s = now - timedelta(days=60)
        p2_e = now - timedelta(days=30)
        label1, label2 = "Ultimi 30 giorni", "30 giorni precedenti"
    elif period == "quarter":
        p1_s = now - timedelta(days=90)
        p1_e = now
        p2_s = now - timedelta(days=180)
        p2_e = now - timedelta(days=90)
        label1, label2 = "Ultimo trimestre", "Trimestre precedente"
    else:
        # Custom
        try:
            p1_s = datetime.fromisoformat(p1_start).replace(tzinfo=timezone.utc)
            p1_e = datetime.fromisoformat(p1_end).replace(tzinfo=timezone.utc)
            p2_s = datetime.fromisoformat(p2_start).replace(tzinfo=timezone.utc)
            p2_e = datetime.fromisoformat(p2_end).replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            raise HTTPException(400, "Date non valide. Formato ISO: 2025-01-01")
        label1 = f"{p1_start} → {p1_end}"
        label2 = f"{p2_start} → {p2_end}"

    async def _period_stats(start: datetime, end: datetime) -> dict:
        """Calcola statistiche per un periodo."""
        stmt = (
            select(ScoreSnapshot)
            .options(selectinload(ScoreSnapshot.dimensions))
            .where(ScoreSnapshot.timestamp >= start, ScoreSnapshot.timestamp <= end)
            .order_by(ScoreSnapshot.timestamp)
        )
        result = await db.execute(stmt)
        snapshots = result.scalars().all()

        if not snapshots:
            return {"count": 0, "avg_score": None, "min_score": None, "max_score": None, "dimensions": {}}

        scores = [s.score for s in snapshots]
        dim_scores: dict[str, list[float]] = {d: [] for d in DIMENSIONS}

        for snap in snapshots:
            for ds in snap.dimensions:
                if ds.dimension in dim_scores:
                    dim_scores[ds.dimension].append(ds.score)

        return {
            "count": len(snapshots),
            "avg_score": round(sum(scores) / len(scores), 2),
            "min_score": round(min(scores), 2),
            "max_score": round(max(scores), 2),
            "dimensions": {
                dim: {
                    "avg": round(sum(vals) / len(vals), 2) if vals else None,
                    "min": round(min(vals), 2) if vals else None,
                    "max": round(max(vals), 2) if vals else None,
                }
                for dim, vals in dim_scores.items()
            },
        }

    stats1 = await _period_stats(p1_s, p1_e)
    stats2 = await _period_stats(p2_s, p2_e)

    # Calcola delta
    delta_score = None
    if stats1["avg_score"] is not None and stats2["avg_score"] is not None:
        delta_score = round(stats1["avg_score"] - stats2["avg_score"], 2)

    dim_deltas = {}
    for dim in DIMENSIONS:
        d1 = stats1["dimensions"].get(dim, {}).get("avg")
        d2 = stats2["dimensions"].get(dim, {}).get("avg")
        dim_deltas[dim] = {
            "period1_avg": d1,
            "period2_avg": d2,
            "delta": round(d1 - d2, 2) if d1 is not None and d2 is not None else None,
            "direction": (
                "stabile" if d1 is None or d2 is None
                else "peggiorato" if d1 > d2 + 2
                else "migliorato" if d1 < d2 - 2
                else "stabile"
            ),
        }

    return {
        "period1": {"label": label1, "start": p1_s.isoformat(), "end": p1_e.isoformat(), **stats1},
        "period2": {"label": label2, "start": p2_s.isoformat(), "end": p2_e.isoformat(), **stats2},
        "delta_score": delta_score,
        "delta_direction": (
            "stabile" if delta_score is None
            else "peggiorato" if delta_score > 2
            else "migliorato" if delta_score < -2
            else "stabile"
        ),
        "dimensions": dim_deltas,
    }
