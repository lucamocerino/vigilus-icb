from __future__ import annotations
"""
APScheduler — intervallo configurabile via SCHEDULER_INTERVAL_MINUTES.
Fonti lente (Google Trends, ACLED) usano cache interna con TTL proprio.
"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from sentinella.config import settings

logger = logging.getLogger(__name__)

_scheduler = AsyncIOScheduler(timezone="Europe/Rome")


async def _run_cycle() -> None:
    from sentinella.db import AsyncSessionLocal
    from sentinella.engine.score import run_score_cycle
    from sentinella.api.websocket import broadcast_score

    async with AsyncSessionLocal() as db:
        snapshot = await run_score_cycle(db)
        if snapshot:
            await broadcast_score(snapshot)


def setup_scheduler() -> AsyncIOScheduler:
    if not settings.scheduler_enabled:
        logger.info("Scheduler disabilitato via config")
        return _scheduler

    interval = settings.scheduler_interval_minutes
    _scheduler.add_job(
        _run_cycle,
        trigger=IntervalTrigger(minutes=interval),
        id="score_cycle",
        replace_existing=True,
    )
    logger.info(f"Scheduler configurato — ciclo ogni {interval} minuti")
    return _scheduler


def get_scheduler() -> AsyncIOScheduler:
    return _scheduler
