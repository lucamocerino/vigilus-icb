"""
Cross-stream correlation — rileva spike simultanei su 2+ dimensioni.
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sentinella.db import get_db
from sentinella.models.score import ScoreSnapshot

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/score", tags=["score"])

DIMENSIONS = ["geopolitica", "terrorismo", "cyber", "eversione", "militare", "sociale"]


@router.get("/correlations")
async def get_correlations(
    hours: int = Query(default=24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Rileva dimensioni che salgono/scendono insieme (correlazione temporale)."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    stmt = (
        select(ScoreSnapshot)
        .options(selectinload(ScoreSnapshot.dimensions))
        .where(ScoreSnapshot.timestamp >= cutoff)
        .order_by(ScoreSnapshot.timestamp)
    )
    result = await db.execute(stmt)
    snapshots = result.scalars().all()

    if len(snapshots) < 2:
        return {"correlations": [], "alerts": [], "snapshots_analyzed": len(snapshots)}

    # Build time series per dimension
    series: dict[str, list[float]] = {d: [] for d in DIMENSIONS}
    for snap in snapshots:
        dim_map = {ds.dimension: ds.score for ds in snap.dimensions}
        for d in DIMENSIONS:
            series[d].append(dim_map.get(d, 0))

    # Compute pairwise correlation
    correlations = []
    for i, d1 in enumerate(DIMENSIONS):
        for d2 in DIMENSIONS[i + 1:]:
            r = _pearson(series[d1], series[d2])
            if abs(r) >= 0.6:
                correlations.append({
                    "dim1": d1,
                    "dim2": d2,
                    "correlation": round(r, 3),
                    "direction": "positiva" if r > 0 else "inversa",
                    "strength": "forte" if abs(r) >= 0.8 else "moderata",
                })

    correlations.sort(key=lambda x: abs(x["correlation"]), reverse=True)

    # Detect simultaneous spikes (both dimensions above their baseline in latest snapshot)
    alerts = []
    if snapshots:
        latest = snapshots[-1]
        prev = snapshots[-2] if len(snapshots) >= 2 else None
        dim_latest = {ds.dimension: ds.score for ds in latest.dimensions}
        dim_prev = {ds.dimension: ds.score for ds in prev.dimensions} if prev else {}

        spiking = []
        for d in DIMENSIONS:
            curr = dim_latest.get(d, 0)
            prev_val = dim_prev.get(d, curr)
            if curr > 60 and curr - prev_val > 5:
                spiking.append({"dimension": d, "score": curr, "delta": round(curr - prev_val, 1)})

        if len(spiking) >= 2:
            alerts.append({
                "type": "multi_spike",
                "message": f"{len(spiking)} dimensioni in spike simultaneo",
                "dimensions": spiking,
                "severity": "alta" if len(spiking) >= 3 else "media",
            })

    return {
        "correlations": correlations,
        "alerts": alerts,
        "snapshots_analyzed": len(snapshots),
        "period_hours": hours,
    }


def _pearson(x: list[float], y: list[float]) -> float:
    n = len(x)
    if n < 2:
        return 0.0
    mx = sum(x) / n
    my = sum(y) / n
    cov = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    sx = sum((xi - mx) ** 2 for xi in x) ** 0.5
    sy = sum((yi - my) ** 2 for yi in y) ** 0.5
    if sx == 0 or sy == 0:
        return 0.0
    return cov / (sx * sy)
