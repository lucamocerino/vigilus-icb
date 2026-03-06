from __future__ import annotations
"""
Endpoint /api/score/narrative — genera un testo descrittivo via Claude AI.
Cache 30 minuti per non sprecare quota API ad ogni render.
"""
import time
import logging
from fastapi import APIRouter, Depends
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sentinella.db import get_db
from sentinella.models.score import ScoreSnapshot
from sentinella.config import settings

router = APIRouter(prefix="/api/score", tags=["narrative"])
logger = logging.getLogger(__name__)

# Cache in-memory: (testo, timestamp)
_cache: dict[str, object] = {"text": None, "ts": 0.0, "snapshot_id": None}
CACHE_TTL = 30 * 60  # 30 minuti


async def _build_context(db: AsyncSession) -> dict | None:
    """Raccoglie i dati recenti per comporre il prompt."""
    stmt = (
        select(ScoreSnapshot)
        .options(selectinload(ScoreSnapshot.dimensions))
        .order_by(desc(ScoreSnapshot.timestamp))
        .limit(2)
    )
    result = await db.execute(stmt)
    snapshots = result.scalars().all()
    if not snapshots:
        return None

    current = snapshots[0]
    previous = snapshots[1] if len(snapshots) > 1 else None
    prev_map = {d.dimension: d.score for d in previous.dimensions} if previous else {}

    dims = []
    for d in sorted(current.dimensions, key=lambda x: x.score, reverse=True):
        trend = round(d.score - prev_map.get(d.dimension, d.score), 1)
        dims.append({
            "name": d.dimension,
            "score": round(d.score, 1),
            "trend": trend,
            "raw": d.raw_values or {},
        })

    # Anomalie (proxy > 1.5σ)
    from sentinella.engine.baseline import DEFAULT_BASELINES
    anomalies = []
    for d in current.dimensions:
        baselines = DEFAULT_BASELINES.get(d.dimension, {})
        for proxy, value in (d.raw_values or {}).items():
            if proxy not in baselines:
                continue
            b = baselines[proxy]
            std = b["std"]
            if std == 0:
                continue
            try:
                z = (float(value) - b["mean"]) / std
            except (TypeError, ValueError):
                continue
            if abs(z) >= 1.5:
                anomalies.append(f"{d.dimension}/{proxy}: z={z:+.1f} (valore={value}, media={b['mean']})")

    # Articoli RSS recenti
    from sentinella.collectors.news_rss import get_geo_events
    rss_titles = [e["title"] for e in get_geo_events()[:8]]

    # Ultimo bollettino CSIRT
    from sentinella.collectors import cache as col_cache
    csirt = col_cache.get("csirt_data") or {}
    bulletins = (csirt.get("bulletins") or [])[:3]

    return {
        "snapshot_id": current.id,
        "score": round(current.score, 1),
        "level": current.level,
        "score_trend": round(current.score - previous.score, 1) if previous else 0,
        "dimensions": dims,
        "anomalies": anomalies,
        "rss_titles": rss_titles,
        "csirt_bulletins": bulletins,
    }


def _build_prompt(ctx: dict) -> str:
    dim_lines = "\n".join(
        f"  - {d['name']}: {d['score']}/100 (trend {d['trend']:+.1f})"
        for d in ctx["dimensions"]
    )
    anomaly_lines = "\n".join(f"  - {a}" for a in ctx["anomalies"]) if ctx["anomalies"] else "  Nessuna anomalia rilevante."
    rss_lines = "\n".join(f"  - {t}" for t in ctx["rss_titles"]) if ctx["rss_titles"] else "  Nessun articolo recente."
    csirt_lines = "\n".join(f"  - {b}" for b in ctx["csirt_bulletins"]) if ctx["csirt_bulletins"] else "  Nessun bollettino recente."

    return f"""Sei l'analista di Sentinella Italia, un sistema OSINT open source che monitora la sicurezza nazionale italiana attraverso proxy pubblici (GDELT, CSIRT, Google Trends, RSS ANSA, ADS-B).

Dati attuali:
- Score globale: {ctx['score']}/100 — livello {ctx['level']} (variazione rispetto al ciclo precedente: {ctx['score_trend']:+.1f} punti)

Score per dimensione:
{dim_lines}

Anomalie statistiche rilevate (>1.5σ dalla media 90 giorni):
{anomaly_lines}

Titoli recenti da RSS ANSA geo-localizzati:
{rss_lines}

Ultimi bollettini CSIRT Italia:
{csirt_lines}

Scrivi una lettura della situazione in italiano, 3-4 frasi, tono analitico e neutro. Sii specifico sui dati: cita le dimensioni anomale, le tendenze, i segnali concreti. NON usare formule generiche. Ricorda sempre che si tratta di proxy statistici pubblici, non di intelligence classificata. Concludi con una frase sul livello di affidabilità dei dati attuali."""


async def _call_claude(prompt: str) -> str:
    """Chiama Claude API in modo sincrono nel thread pool."""
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _call_claude_sync, prompt)


def _call_claude_sync(prompt: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


@router.get("/narrative")
async def get_narrative(db: AsyncSession = Depends(get_db)) -> dict:
    """
    Restituisce un testo descrittivo generato da Claude sulla situazione attuale.
    Cached 30 minuti. Richiede ANTHROPIC_API_KEY in .env.
    """
    ctx = await _build_context(db)
    if not ctx:
        return {"text": None, "cached": False, "error": "Nessun dato disponibile"}

    # Usa cache se il testo è dello stesso snapshot e non scaduto
    now = time.time()
    if (
        _cache["text"]
        and _cache["snapshot_id"] == ctx["snapshot_id"]
        and (now - float(_cache["ts"])) < CACHE_TTL
    ):
        return {"text": _cache["text"], "cached": True, "level": ctx["level"], "score": ctx["score"]}

    if not settings.anthropic_api_key:
        return {
            "text": None,
            "cached": False,
            "error": "ANTHROPIC_API_KEY non configurata. Aggiungila in backend/.env",
        }

    try:
        prompt = _build_prompt(ctx)
        text = await _call_claude(prompt)
        _cache["text"] = text
        _cache["ts"] = now
        _cache["snapshot_id"] = ctx["snapshot_id"]
        logger.info(f"[narrative] Generato per snapshot {ctx['snapshot_id']}")
        return {"text": text, "cached": False, "level": ctx["level"], "score": ctx["score"]}
    except Exception as e:
        logger.error(f"[narrative] Errore Claude API: {e}")
        return {"text": None, "cached": False, "error": str(e)}
