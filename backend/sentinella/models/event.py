from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlalchemy import Float, DateTime, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from sentinella.db import Base


class RawEvent(Base):
    __tablename__ = "raw_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(30), index=True)
    external_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    event_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    raw_data: Mapped[dict] = mapped_column(JSON)

    def __repr__(self) -> str:
        return f"<RawEvent {self.source} {self.event_date}>"


class ClassifiedEvent(Base):
    __tablename__ = "classified_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    raw_event_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(30), index=True)
    dimension: Mapped[str] = mapped_column(String(30), index=True)
    title: Mapped[str] = mapped_column(String(500))
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    sentiment: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    relevance: Mapped[float] = mapped_column(Float, default=1.0)
    event_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    classified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:
        return f"<ClassifiedEvent {self.dimension} {self.title[:50]}>"
