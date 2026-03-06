from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any
import logging

logger = logging.getLogger(__name__)


class CollectorResult:
    def __init__(self, source: str, data: dict[str, Any], records_count: int = 0):
        self.source = source
        self.data = data
        self.records_count = records_count
        self.collected_at = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        return f"<CollectorResult {self.source} records={self.records_count}>"


class BaseCollector(ABC):
    name: str = ""
    display_name: str = ""

    @abstractmethod
    async def collect(self) -> CollectorResult:
        """Raccoglie dati dalla fonte e restituisce un CollectorResult."""
        ...

    async def safe_collect(self) -> CollectorResult | None:
        """Wrapper con error handling per uso dallo scheduler."""
        try:
            result = await self.collect()
            logger.info(f"[{self.name}] Raccolti {result.records_count} record")
            return result
        except Exception as e:
            logger.error(f"[{self.name}] Errore durante la raccolta: {e}", exc_info=True)
            return None
