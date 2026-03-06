from __future__ import annotations
from pydantic_settings import BaseSettings
from typing import ClassVar


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite+aiosqlite:///./sentinella.db"
    redis_url: str = "redis://localhost:6379"

    # Anthropic
    anthropic_api_key: str = ""

    # ACLED
    acled_api_key: str = ""
    acled_email: str = ""

    # OpenSky
    opensky_username: str = ""
    opensky_password: str = ""

    # App
    debug: bool = True
    scheduler_enabled: bool = True

    # CORS — lista origini separata da virgola, default localhost per dev
    cors_origins: str = "http://localhost:3000,http://localhost:5173,http://localhost:3001"

    # Autenticazione — API key per proteggere gli endpoint (vuoto = auth disabilitata)
    api_key: str = ""

    # Rate limiting — richieste per minuto (0 = disabilitato)
    rate_limit_per_minute: int = 200

    # Sentry (opzionale)
    sentry_dsn: str = ""

    # Frequenza aggiornamento score (minuti)
    # Default 30min. Fonti lente (Trends, ACLED) usano cache indipendente.
    # Valori consigliati: 15, 30, 60, 120, 240
    scheduler_interval_minutes: int = 15

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # Score weights (devono sommare a 1.0)
    WEIGHTS: ClassVar[dict[str, float]] = {
        "geopolitica": 0.25,
        "terrorismo": 0.20,
        "cyber": 0.15,
        "eversione": 0.15,
        "militare": 0.15,
        "sociale": 0.10,
    }

    BASELINE_DAYS: ClassVar[int] = 90

    LEVELS: ClassVar[list[dict]] = [
        {"min": 0,  "max": 20,  "label": "CALMO",      "color": "#22c55e"},
        {"min": 21, "max": 40,  "label": "NORMALE",    "color": "#3b82f6"},
        {"min": 41, "max": 60,  "label": "ATTENZIONE", "color": "#eab308"},
        {"min": 61, "max": 80,  "label": "ELEVATO",    "color": "#f97316"},
        {"min": 81, "max": 100, "label": "CRITICO",    "color": "#ef4444"},
    ]

    model_config = {"env_file": ".env", "case_sensitive": False}


settings = Settings()


def get_level(score: float) -> dict:
    for level in settings.LEVELS:
        if level["min"] <= score <= level["max"]:
            return level
    return settings.LEVELS[-1]
