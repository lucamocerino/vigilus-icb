"""
Daily digest — riepilogo automatico delle ultime 24 ore.
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sentinella.db import get_db
from sentinella.models.score import ScoreSnapshot
from sentinella.models.event import ClassifiedEvent
from sentinella.engine.baseline import get_default_baseline

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/digest", tags=["digest"])

DIMENSIONS = ["geopolitica", "terrorismo", "cyber", "eversione", "militare", "sociale"]


@router.get("/daily")
async def get_daily_digest(db: AsyncSession = Depends(get_db)) -> dict:
    """Genera riepilogo delle ultime 24 ore."""
    now = datetime.now(timezone.utc)
    cutoff_24h = now - timedelta(hours=24)

    # Latest and 24h-ago snapshots
    stmt_latest = (
        select(ScoreSnapshot)
        .options(selectinload(ScoreSnapshot.dimensions))
        .order_by(desc(ScoreSnapshot.timestamp))
        .limit(1)
    )
    latest = (await db.execute(stmt_latest)).scalar_one_or_none()

    stmt_24h = (
        select(ScoreSnapshot)
        .options(selectinload(ScoreSnapshot.dimensions))
        .where(ScoreSnapshot.timestamp <= cutoff_24h)
        .order_by(desc(ScoreSnapshot.timestamp))
        .limit(1)
    )
    ago_24h = (await db.execute(stmt_24h)).scalar_one_or_none()

    # Score delta
    score_now = latest.score if latest else None
    score_24h = ago_24h.score if ago_24h else None
    delta = round(score_now - score_24h, 2) if score_now is not None and score_24h is not None else None

    # Dimension deltas
    dim_now = {ds.dimension: ds.score for ds in latest.dimensions} if latest else {}
    dim_24h = {ds.dimension: ds.score for ds in ago_24h.dimensions} if ago_24h else {}
    dim_changes = []
    for d in DIMENSIONS:
        curr = dim_now.get(d)
        prev = dim_24h.get(d)
        if curr is not None:
            dim_changes.append({
                "dimension": d,
                "score": round(curr, 1),
                "delta": round(curr - prev, 1) if prev is not None else None,
                "direction": (
                    "peggiorato" if prev is not None and curr - prev > 3
                    else "migliorato" if prev is not None and curr - prev < -3
                    else "stabile"
                ),
            })
    dim_changes.sort(key=lambda x: abs(x.get("delta") or 0), reverse=True)

    # Top events in last 24h
    stmt_events = (
        select(ClassifiedEvent)
        .where(ClassifiedEvent.event_date >= cutoff_24h)
        .order_by(desc(ClassifiedEvent.event_date))
        .limit(20)
    )
    events_result = await db.execute(stmt_events)
    recent_events = events_result.scalars().all()

    # Event counts by dimension
    stmt_counts = (
        select(ClassifiedEvent.dimension, func.count(ClassifiedEvent.id))
        .where(ClassifiedEvent.event_date >= cutoff_24h)
        .group_by(ClassifiedEvent.dimension)
    )
    count_result = await db.execute(stmt_counts)
    event_counts = {row[0]: row[1] for row in count_result.all()}

    # Anomalies
    anomalies = []
    if latest:
        for ds in latest.dimensions:
            raw = ds.raw_values or {}
            for proxy, value in raw.items():
                b = get_default_baseline(ds.dimension, proxy)
                if b["std"] == 0:
                    continue
                try:
                    z = (float(value) - b["mean"]) / b["std"]
                except (TypeError, ValueError):
                    continue
                if abs(z) >= 2.0:
                    anomalies.append({
                        "dimension": ds.dimension,
                        "proxy": proxy,
                        "z_score": round(z, 2),
                        "direction": "alto" if z > 0 else "basso",
                    })
    anomalies.sort(key=lambda x: abs(x["z_score"]), reverse=True)

    return {
        "generated_at": now.isoformat(),
        "period": "24h",
        "score": {
            "current": score_now,
            "previous": score_24h,
            "delta": delta,
            "level": latest.level if latest else None,
            "direction": (
                "peggiorato" if delta and delta > 3
                else "migliorato" if delta and delta < -3
                else "stabile"
            ),
        },
        "dimensions": dim_changes,
        "events": {
            "total": sum(event_counts.values()),
            "by_dimension": event_counts,
            "top": [
                {"title": e.title, "dimension": e.dimension, "source": e.source}
                for e in recent_events[:10]
            ],
        },
        "anomalies": anomalies[:5],
        "summary": _generate_text_summary(score_now, delta, dim_changes, anomalies, event_counts),
    }


def _generate_text_summary(score, delta, dims, anomalies, event_counts) -> str:
    """Genera un riepilogo testuale del digest."""
    parts = []

    if score is not None:
        parts.append(f"Score attuale: {score:.1f}/100.")

    if delta is not None:
        if delta > 3:
            parts.append(f"In peggioramento ({delta:+.1f} nelle ultime 24h).")
        elif delta < -3:
            parts.append(f"In miglioramento ({delta:+.1f} nelle ultime 24h).")
        else:
            parts.append("Situazione stabile nelle ultime 24h.")

    changed = [d for d in dims if d.get("delta") and abs(d["delta"]) > 3]
    if changed:
        parts.append("Variazioni significative: " + ", ".join(
            f"{d['dimension']} {d['delta']:+.1f}" for d in changed[:3]
        ) + ".")

    if anomalies:
        parts.append(f"{len(anomalies)} anomalie rilevate (z-score > 2σ).")

    total_events = sum(event_counts.values())
    if total_events:
        parts.append(f"{total_events} eventi raccolti nelle ultime 24h.")

    return " ".join(parts) if parts else "Nessun dato disponibile per il digest."
