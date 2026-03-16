from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from sentinella.db import get_db
from sentinella.models.event import ClassifiedEvent

router = APIRouter(prefix="/api/events", tags=["events"])


class EventOut(BaseModel):
    id: int
    source: str
    dimension: str
    title: str
    summary: Optional[str]
    url: Optional[str]
    sentiment: Optional[float]
    event_date: datetime

    model_config = {"from_attributes": True}


@router.get("/latest", response_model=list)
async def get_latest_events(
    dimension: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list:
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    stmt = (
        select(ClassifiedEvent)
        .where(
            ClassifiedEvent.event_date >= cutoff,
            ClassifiedEvent.dimension != "non_pertinente",
        )
        .order_by(desc(ClassifiedEvent.event_date))
        .limit(limit)
    )
    if dimension:
        stmt = stmt.where(ClassifiedEvent.dimension == dimension)

    result = await db.execute(stmt)
    events = result.scalars().all()
    return [EventOut.model_validate(e).model_dump() for e in events]


@router.get("/search")
async def search_events(
    q: str = Query(description="Termine di ricerca"),
    dimension: Optional[str] = Query(default=None),
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list:
    """Ricerca full-text su titoli e summary degli eventi."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    search_term = f"%{q}%"

    from sqlalchemy import or_
    stmt = (
        select(ClassifiedEvent)
        .where(
            ClassifiedEvent.event_date >= cutoff,
            ClassifiedEvent.dimension != "non_pertinente",
            or_(
                ClassifiedEvent.title.ilike(search_term),
                ClassifiedEvent.summary.ilike(search_term),
            )
        )
        .order_by(desc(ClassifiedEvent.event_date))
        .limit(limit)
    )
    if dimension:
        stmt = stmt.where(ClassifiedEvent.dimension == dimension)

    result = await db.execute(stmt)
    events = result.scalars().all()
    return [EventOut.model_validate(e).model_dump() for e in events]
