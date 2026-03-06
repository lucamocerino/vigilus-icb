from __future__ import annotations
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sentinella.db import get_db
from sentinella.models.score import DimensionScore, ScoreSnapshot

router = APIRouter(prefix="/api/dimension", tags=["dimensions"])

VALID_DIMENSIONS = {"geopolitica", "terrorismo", "cyber", "eversione", "militare", "sociale"}


class DimensionDetailOut(BaseModel):
    dimension: str
    score: float
    raw_values: dict
    timestamp: datetime

    model_config = {"from_attributes": True}


@router.get("/{name}", response_model=dict)
async def get_dimension(
    name: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    if name not in VALID_DIMENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Dimensione non valida. Valide: {sorted(VALID_DIMENSIONS)}",
        )

    stmt = (
        select(DimensionScore)
        .join(ScoreSnapshot)
        .where(DimensionScore.dimension == name)
        .options(selectinload(DimensionScore.snapshot))
        .order_by(desc(ScoreSnapshot.timestamp))
        .limit(1)
    )
    result = await db.execute(stmt)
    ds = result.scalar_one_or_none()

    if ds is None:
        raise HTTPException(status_code=404, detail=f"Nessun dato per dimensione '{name}'")

    return {
        "dimension": ds.dimension,
        "score": ds.score,
        "raw_values": ds.raw_values or {},
        "timestamp": ds.snapshot.timestamp,
    }


@router.get("/{name}/history", response_model=list)
async def get_dimension_history(
    name: str,
    days: int = Query(default=30, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
) -> list:
    if name not in VALID_DIMENSIONS:
        raise HTTPException(status_code=400, detail="Dimensione non valida")

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = (
        select(DimensionScore)
        .join(ScoreSnapshot)
        .where(
            DimensionScore.dimension == name,
            ScoreSnapshot.timestamp >= cutoff,
        )
        .options(selectinload(DimensionScore.snapshot))
        .order_by(ScoreSnapshot.timestamp)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()

    return [
        {
            "dimension": ds.dimension,
            "score": ds.score,
            "raw_values": ds.raw_values or {},
            "timestamp": ds.snapshot.timestamp,
        }
        for ds in rows
    ]
