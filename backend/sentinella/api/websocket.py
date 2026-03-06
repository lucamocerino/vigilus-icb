from __future__ import annotations
"""
WebSocket endpoint per push aggiornamenti score in tempo reale.
"""
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from sentinella.models.score import ScoreSnapshot

router = APIRouter()
logger = logging.getLogger(__name__)

_connections: set[WebSocket] = set()


@router.websocket("/ws/score")
async def ws_score(websocket: WebSocket) -> None:
    await websocket.accept()
    _connections.add(websocket)
    logger.info(f"WebSocket connesso. Connessioni attive: {len(_connections)}")

    try:
        while True:
            # Mantieni la connessione aperta, inviamo dati via broadcast_score
            await websocket.receive_text()
    except WebSocketDisconnect:
        _connections.discard(websocket)
        logger.info(f"WebSocket disconnesso. Connessioni attive: {len(_connections)}")


async def broadcast_score(snapshot: ScoreSnapshot) -> None:
    """Invia il nuovo score a tutti i client connessi."""
    if not _connections:
        return

    payload = json.dumps({
        "type": "score_update",
        "data": {
            "score": snapshot.score,
            "level": snapshot.level,
            "color": snapshot.color,
            "timestamp": snapshot.timestamp.isoformat(),
            "dimensions": {
                d.dimension: d.score
                for d in (snapshot.dimensions or [])
            },
        },
    })

    dead: set[WebSocket] = set()
    for ws in list(_connections):
        try:
            await ws.send_text(payload)
        except Exception:
            dead.add(ws)

    _connections.difference_update(dead)
