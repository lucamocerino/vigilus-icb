from __future__ import annotations
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sentinella.db import get_db
from sentinella.models.score import ScoreSnapshot
from sentinella.config import settings
from sentinella.engine.baseline import get_default_baseline
from sentinella.models.source import SourceStatus

router = APIRouter(prefix="/api/score", tags=["score"])


@router.get("/current")
async def get_current_score(db: AsyncSession = Depends(get_db)) -> dict:
    # Prendi gli ultimi 2 snapshot per calcolare il trend
    stmt = (
        select(ScoreSnapshot)
        .options(selectinload(ScoreSnapshot.dimensions))
        .order_by(desc(ScoreSnapshot.timestamp))
        .limit(2)
    )
    result = await db.execute(stmt)
    snapshots = result.scalars().all()

    if not snapshots:
        raise HTTPException(status_code=404, detail="Nessuno score disponibile")

    current = snapshots[0]
    previous = snapshots[1] if len(snapshots) > 1 else None

    prev_map = {d.dimension: d.score for d in previous.dimensions} if previous else {}

    # Confidence: quante fonti hanno avuto successo nell'ultimo ciclo
    src_result = await db.execute(select(SourceStatus))
    sources = src_result.scalars().all()
    sources_ok = sum(1 for s in sources if s.is_healthy)
    sources_total = len(sources)

    return {
        "id": current.id,
        "timestamp": current.timestamp,
        "score": current.score,
        "level": current.level,
        "color": current.color,
        "previous_score": previous.score if previous else None,
        "score_trend": round(current.score - previous.score, 2) if previous else 0,
        "sources_ok": sources_ok,
        "sources_total": sources_total,
        "dimensions": [
            {
                "dimension": d.dimension,
                "score": d.score,
                "raw_values": d.raw_values or {},
                "trend": round(d.score - prev_map.get(d.dimension, d.score), 2),
            }
            for d in current.dimensions
        ],
    }


@router.get("/history")
async def get_score_history(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> list:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = (
        select(ScoreSnapshot)
        .where(ScoreSnapshot.timestamp >= cutoff)
        .order_by(ScoreSnapshot.timestamp)
    )
    result = await db.execute(stmt)
    snapshots = result.scalars().all()

    return [
        {
            "timestamp": s.timestamp,
            "score": s.score,
            "level": s.level,
            "color": s.color,
        }
        for s in snapshots
    ]


@router.get("/anomalies")
async def get_anomalies(db: AsyncSession = Depends(get_db)) -> list:
    """Restituisce i proxy che superano 1.5 deviazioni standard dalla baseline."""
    stmt = (
        select(ScoreSnapshot)
        .options(selectinload(ScoreSnapshot.dimensions))
        .order_by(desc(ScoreSnapshot.timestamp))
        .limit(1)
    )
    result = await db.execute(stmt)
    snapshot = result.scalar_one_or_none()

    if not snapshot:
        return []

    anomalies = []
    for dim_score in snapshot.dimensions:

        raw = dim_score.raw_values or {}

        for proxy, value in raw.items():
            b = get_default_baseline(dim_score.dimension, proxy)
            if b["std"] == 0 and b["mean"] == 0:
                continue
            mean, std = b["mean"], b["std"]
            if std == 0:
                continue
            try:
                z = (float(value) - mean) / std
            except (TypeError, ValueError):
                continue

            if abs(z) >= 1.5:
                anomalies.append({
                    "dimension": dim_score.dimension,
                    "proxy": proxy,
                    "value": round(float(value), 3),
                    "mean": mean,
                    "std": std,
                    "z_score": round(z, 2),
                    "direction": "alto" if z > 0 else "basso",
                    "dimension_score": dim_score.score,
                })

    anomalies.sort(key=lambda x: abs(x["z_score"]), reverse=True)
    return anomalies


@router.post("/trigger", summary="Forza aggiornamento manuale (solo dev)")
async def trigger_score(db: AsyncSession = Depends(get_db)) -> dict:
    if not settings.debug:
        raise HTTPException(status_code=403, detail="Solo in modalità debug")

    from sentinella.engine.score import run_score_cycle
    snapshot = await run_score_cycle(db)

    if snapshot is None:
        raise HTTPException(status_code=500, detail="Ciclo score fallito")

    return {"id": snapshot.id, "score": snapshot.score, "level": snapshot.level}


@router.post("/cleanup", summary="Riclassifica eventi con bassa confidence")
async def cleanup_events(db: AsyncSession = Depends(get_db)) -> dict:
    """Riclassifica gli eventi salvati con il vecchio fallback e rimuove i non pertinenti."""
    from sentinella.nlp.classifier import get_classifier
    from sentinella.models.event import ClassifiedEvent
    from sqlalchemy import delete

    classifier = get_classifier()

    # Prendi tutti gli eventi degli ultimi 7 giorni
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    stmt = select(ClassifiedEvent).where(ClassifiedEvent.event_date >= cutoff)
    result = await db.execute(stmt)
    events = result.scalars().all()

    reclassified = 0
    deleted = 0
    for event in events:
        text = (event.title or "") + " " + (event.summary or "")
        r = classifier.classify(text.strip())
        new_dim = r["dimension"]

        if new_dim == "non_pertinente":
            await db.delete(event)
            deleted += 1
        elif new_dim != event.dimension:
            event.dimension = new_dim
            reclassified += 1

    await db.commit()
    return {
        "total_checked": len(events),
        "reclassified": reclassified,
        "deleted_non_pertinente": deleted,
    }
