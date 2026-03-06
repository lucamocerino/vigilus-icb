from fastapi import APIRouter
from sentinella.config import settings

router = APIRouter(prefix="/api/methodology", tags=["methodology"])


@router.get("")
async def get_methodology() -> dict:
    return {
        "description": "Indice composito data-driven basato su proxy pubblici",
        "dimensions": [
            {
                "name": dim,
                "weight": weight,
                "description": _descriptions[dim],
                "sources": _sources[dim],
            }
            for dim, weight in settings.WEIGHTS.items()
        ],
        "normalization": "Z-score vs baseline rolling 90 giorni, mappato su scala 0-100",
        "update_frequency": "Ogni 4 ore (02:00, 06:00, 10:00, 14:00, 18:00, 22:00 CET)",
        "disclaimer": (
            "NON e' un livello di allerta ufficiale. "
            "Riflette anomalie statistiche nei dati pubblici, non una valutazione di intelligence."
        ),
    }


_descriptions = {
    "geopolitica": "Tensione internazionale con impatto sull'Italia (GDELT Goldstein Scale, tone)",
    "terrorismo": "Rischio terroristico diretto e indiretto (GDELT, Google Trends, RSS)",
    "cyber": "Attacchi informatici a infrastrutture italiane (CSIRT Italia, bollettini ACN)",
    "eversione": "Estremismo interno e proteste (GDELT, ACLED, RSS)",
    "militare": "Movimenti militari anomali (ADS-B OpenSky, Google Trends)",
    "sociale": "Tensione sociale e manifestazioni (Google Trends, GDELT, ACLED)",
}

_sources = {
    "geopolitica": ["GDELT", "ACLED"],
    "terrorismo": ["GDELT", "Google Trends", "RSS"],
    "cyber": ["CSIRT Italia", "ACN", "GDELT"],
    "eversione": ["GDELT", "ACLED", "RSS"],
    "militare": ["OpenSky Network", "Google Trends", "GDELT"],
    "sociale": ["Google Trends", "GDELT", "ACLED"],
}
