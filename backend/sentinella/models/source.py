from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, Integer, String, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column
from sentinella.db import Base


class SourceStatus(Base):
    __tablename__ = "source_status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(100))
    is_healthy: Mapped[bool] = mapped_column(Boolean, default=True)
    last_success: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_attempt: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    records_last_run: Mapped[int] = mapped_column(Integer, default=0)

    def __repr__(self) -> str:
        status = "OK" if self.is_healthy else "ERR"
        return f"<SourceStatus {self.name} [{status}]>"
