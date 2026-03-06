from __future__ import annotations
from datetime import datetime
from sqlalchemy import Float, DateTime, Integer, String, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sentinella.db import Base


class ScoreSnapshot(Base):
    __tablename__ = "scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    score: Mapped[float] = mapped_column(Float)
    level: Mapped[str] = mapped_column(String(20))
    color: Mapped[str] = mapped_column(String(10))

    dimensions: Mapped[list["DimensionScore"]] = relationship(
        back_populates="snapshot", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ScoreSnapshot {self.timestamp} score={self.score:.1f} level={self.level}>"


class DimensionScore(Base):
    __tablename__ = "dimension_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("scores.id"), index=True)
    dimension: Mapped[str] = mapped_column(String(30), index=True)
    score: Mapped[float] = mapped_column(Float)
    raw_values: Mapped[dict] = mapped_column(JSON, default=dict)
    z_scores: Mapped[dict] = mapped_column(JSON, default=dict)

    snapshot: Mapped["ScoreSnapshot"] = relationship(back_populates="dimensions")

    def __repr__(self) -> str:
        return f"<DimensionScore {self.dimension}={self.score:.1f}>"
