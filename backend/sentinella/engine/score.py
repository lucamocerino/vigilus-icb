from __future__ import annotations
"""
Score Engine — orchestra tutti i collector e calcola lo score sintetico finale.
"""
from datetime import datetime, timezone
import gc
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from sentinella.config import settings, get_level
from sentinella.engine.dimensions import (
    calc_geopolitica,
    calc_terrorismo,
    calc_cyber,
    calc_eversione,
    calc_militare,
    calc_sociale,
)
from sentinella.models.score import ScoreSnapshot, DimensionScore
from sentinella.models.source import SourceStatus

logger = logging.getLogger(__name__)


async def run_score_cycle(db: AsyncSession) -> ScoreSnapshot | None:
    """
    Esegue un ciclo completo:
    1. Raccoglie dati da tutti i collector
    2. Calcola i 6 sotto-indici
    3. Calcola lo score sintetico
    4. Salva snapshot su DB
    """
    from sentinella.collectors import (
        GdeltCollector, NewsRssCollector, CsirtCollector,
        GoogleTrendsCollector, AcledCollector, AdsbCollector,
        MegaRssCollector,
    )

    logger.info("Avvio ciclo score...")

    # 1. Raccogli dati
    collectors = {
        "gdelt": GdeltCollector(),
        "rss": NewsRssCollector(),
        "csirt": CsirtCollector(),
        "trends": GoogleTrendsCollector(),
        "acled": AcledCollector(),
        "adsb": AdsbCollector(),
        "mega_rss": MegaRssCollector(),
    }

    # Esecuzione sequenziale per contenere il picco di memoria (Render free = 512MB)
    collected: dict[str, Any] = {}
    for name, collector in collectors.items():
        try:
            result = await collector.safe_collect()
            if result is None:
                logger.warning(f"Collector {name} fallito")
                collected[name] = {}
            else:
                collected[name] = result.data
                await _update_source_status(db, name, success=True, records=result.records_count)
        except Exception:
            logger.warning(f"Collector {name} fallito", exc_info=True)
            collected[name] = {}
        gc.collect()

    # Persist headline events from mega_rss into DB
    mega_rss_data = collected.get("mega_rss", {})
    if mega_rss_data.get("headlines"):
        await _persist_headlines(db, mega_rss_data["headlines"])

    # 2. Calcola sotto-indici
    gdelt = collected.get("gdelt", {})
    csirt = collected.get("csirt", {})
    trends = collected.get("trends", {})
    acled = collected.get("acled", {})
    adsb = collected.get("adsb", {})
    rss = collected.get("rss", {})

    dim_scores: dict[str, tuple[float, dict]] = {
        "geopolitica": calc_geopolitica(gdelt),
        "terrorismo": calc_terrorismo(gdelt, trends),
        "cyber": calc_cyber(csirt, gdelt),
        "eversione": calc_eversione(gdelt, acled, rss),
        "militare": calc_militare(adsb, gdelt, trends),
        "sociale": calc_sociale(gdelt, trends, acled),
    }

    # 3. Score sintetico (media pesata)
    w = settings.WEIGHTS
    final_score = sum(
        dim_scores[dim][0] * w[dim]
        for dim in dim_scores
    )
    final_score = round(max(0.0, min(100.0, final_score)), 2)
    level = get_level(final_score)

    logger.info(
        f"Score calcolato: {final_score:.1f} [{level['label']}] — "
        + " | ".join(f"{d}={s:.1f}" for d, (s, _) in dim_scores.items())
    )

    # 4. Salva su DB
    snapshot = ScoreSnapshot(
        timestamp=datetime.now(timezone.utc),
        score=final_score,
        level=level["label"],
        color=level["color"],
    )
    db.add(snapshot)
    await db.flush()

    for dim, (score_val, raw_values) in dim_scores.items():
        ds = DimensionScore(
            snapshot_id=snapshot.id,
            dimension=dim,
            score=score_val,
            raw_values=raw_values,
        )
        db.add(ds)

    await db.commit()
    await db.refresh(snapshot)

    logger.info(f"Snapshot {snapshot.id} salvato.")
    return snapshot


async def _update_source_status(
    db: AsyncSession,
    name: str,
    success: bool,
    records: int = 0,
    error: str | None = None,
) -> None:
    from sqlalchemy import select
    from sentinella.collectors import ALL_COLLECTORS

    display_names = {c.name: c.display_name for c in ALL_COLLECTORS}

    stmt = select(SourceStatus).where(SourceStatus.name == name)
    result = await db.execute(stmt)
    source = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if source is None:
        source = SourceStatus(
            name=name,
            display_name=display_names.get(name, name),
        )
        db.add(source)

    source.last_attempt = now
    source.is_healthy = success
    if success:
        source.last_success = now
        source.records_last_run = records
        source.last_error = None
    else:
        source.last_error = error

    await db.flush()


async def _persist_headlines(db: AsyncSession, headlines: list[dict]) -> None:
    """Save RSS headlines as ClassifiedEvent for full-text search history."""
    from sentinella.models.event import ClassifiedEvent
    from sqlalchemy import select
    from datetime import timedelta

    try:
        now = datetime.now(timezone.utc)

        # Get existing URLs to avoid duplicates
        recent_cutoff = now - timedelta(days=1)
        stmt = select(ClassifiedEvent.url).where(ClassifiedEvent.event_date >= recent_cutoff)
        result = await db.execute(stmt)
        existing_urls = {r[0] for r in result.all() if r[0]}

        count = 0
        for h in headlines[:200]:
            url = h.get("url", "")
            if url and url in existing_urls:
                continue
            if not h.get("title"):
                continue
            if h.get("dimension") == "non_pertinente":
                continue

            event = ClassifiedEvent(
                source=h.get("source", "rss")[:30],
                dimension=h.get("dimension", "geopolitica")[:30],
                title=h.get("title", "")[:500],
                summary=h.get("summary", "")[:1000] if h.get("summary") else None,
                url=url[:1000] if url else None,
                relevance=1.0,
                event_date=now,
                classified_at=now,
            )
            db.add(event)
            existing_urls.add(url)
            count += 1

        if count:
            await db.flush()
            logger.info(f"Persistiti {count} eventi headline in DB")
    except Exception as e:
        logger.error(f"Errore durante persist headlines: {e}", exc_info=True)
