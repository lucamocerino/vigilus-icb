"""
Endpoint data layers — GeoJSON statici per basi militari, infrastrutture critiche.
"""
from __future__ import annotations
import json
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/layers", tags=["layers"])

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "geojson"

_cache: dict[str, dict] = {}


def _load(filename: str) -> dict:
    if filename not in _cache:
        path = DATA_DIR / filename
        if not path.exists():
            raise HTTPException(404, f"Layer {filename} non trovato")
        _cache[filename] = json.loads(path.read_text())
    return _cache[filename]


@router.get("/military")
async def get_military_bases() -> dict:
    return _load("military_bases.json")


@router.get("/infrastructure")
async def get_infrastructure() -> dict:
    return _load("infrastructure.json")


@router.get("/all")
async def get_all_layers() -> dict:
    """Restituisce tutti i data layer disponibili."""
    return {
        "military": _load("military_bases.json"),
        "infrastructure": _load("infrastructure.json"),
    }
