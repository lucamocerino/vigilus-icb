"""
Export endpoints — CSV e PDF per report e dati storici.
"""
from __future__ import annotations
import csv
import io
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sentinella.db import get_db
from sentinella.models.score import ScoreSnapshot
from sentinella.config import settings
from sentinella.engine.baseline import get_default_baseline

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/export", tags=["export"])

DIMENSIONS = list(settings.WEIGHTS.keys())


@router.get("/csv")
async def export_csv(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Esporta storico score + dimensioni in formato CSV."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = (
        select(ScoreSnapshot)
        .options(selectinload(ScoreSnapshot.dimensions))
        .where(ScoreSnapshot.timestamp >= cutoff)
        .order_by(ScoreSnapshot.timestamp)
    )
    result = await db.execute(stmt)
    snapshots = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    header = ["timestamp", "score", "level"] + [f"{d}_score" for d in DIMENSIONS]
    writer.writerow(header)

    for snap in snapshots:
        dim_map = {d.dimension: d.score for d in snap.dimensions}
        row = [
            snap.timestamp.isoformat() if snap.timestamp else "",
            round(snap.score, 2),
            snap.level,
        ] + [round(dim_map.get(d, 0), 2) for d in DIMENSIONS]
        writer.writerow(row)

    output.seek(0)
    filename = f"sentinella_export_{days}d_{datetime.now().strftime('%Y%m%d')}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/report")
async def export_report(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Genera report JSON strutturato (usabile dal frontend per PDF client-side)."""
    # Ultimo snapshot
    stmt = (
        select(ScoreSnapshot)
        .options(selectinload(ScoreSnapshot.dimensions))
        .order_by(desc(ScoreSnapshot.timestamp))
        .limit(2)
    )
    result = await db.execute(stmt)
    snapshots = result.scalars().all()

    if not snapshots:
        return {"error": "Nessun dato disponibile"}

    current = snapshots[0]
    previous = snapshots[1] if len(snapshots) > 1 else None
    prev_map = {d.dimension: d.score for d in previous.dimensions} if previous else {}

    # Anomalie
    anomalies = []
    for dim_score in current.dimensions:
        raw = dim_score.raw_values or {}
        for proxy, value in raw.items():
            b = get_default_baseline(dim_score.dimension, proxy)
            if b["std"] == 0:
                continue
            try:
                z = (float(value) - b["mean"]) / b["std"]
            except (TypeError, ValueError):
                continue
            if abs(z) >= 1.5:
                anomalies.append({
                    "dimension": dim_score.dimension,
                    "proxy": proxy,
                    "value": round(float(value), 3),
                    "z_score": round(z, 2),
                    "direction": "alto" if z > 0 else "basso",
                })

    # Storico 7 giorni
    cutoff_7d = datetime.now(timezone.utc) - timedelta(days=7)
    stmt_history = (
        select(ScoreSnapshot)
        .where(ScoreSnapshot.timestamp >= cutoff_7d)
        .order_by(ScoreSnapshot.timestamp)
    )
    result_h = await db.execute(stmt_history)
    history = result_h.scalars().all()

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "title": "Sentinella Italia — Report Situazione",
        "current": {
            "timestamp": current.timestamp.isoformat() if current.timestamp else None,
            "score": round(current.score, 2),
            "level": current.level,
            "color": current.color,
            "trend": round(current.score - previous.score, 2) if previous else 0,
        },
        "dimensions": [
            {
                "name": d.dimension,
                "score": round(d.score, 2),
                "weight": settings.WEIGHTS.get(d.dimension, 0),
                "trend": round(d.score - prev_map.get(d.dimension, d.score), 2),
                "raw_values": d.raw_values or {},
            }
            for d in current.dimensions
        ],
        "anomalies": sorted(anomalies, key=lambda x: abs(x["z_score"]), reverse=True),
        "history_7d": [
            {
                "timestamp": s.timestamp.isoformat() if s.timestamp else None,
                "score": round(s.score, 2),
                "level": s.level,
            }
            for s in history
        ],
        "disclaimer": (
            "Questo report è generato automaticamente da Sentinella Italia. "
            "NON è un livello di allerta ufficiale. Aggrega anomalie statistiche "
            "su proxy pubblici."
        ),
    }
