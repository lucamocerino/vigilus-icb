from __future__ import annotations
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sentinella.db import get_db
from sentinella.models.source import SourceStatus

router = APIRouter(prefix="/api/sources", tags=["sources"])


class SourceOut(BaseModel):
    name: str
    display_name: str
    is_healthy: bool
    last_success: Optional[datetime]
    last_attempt: Optional[datetime]
    last_error: Optional[str]
    records_last_run: int

    model_config = {"from_attributes": True}


@router.get("/status", response_model=list)
async def get_sources_status(db: AsyncSession = Depends(get_db)) -> list:
    result = await db.execute(select(SourceStatus).order_by(SourceStatus.name))
    sources = result.scalars().all()
    return [SourceOut.model_validate(s).model_dump() for s in sources]
