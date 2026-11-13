"""SQLAlchemy ORM models for the CTI decision-support PoC."""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Float, Integer, String, Text, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Declarative base shared by every model."""


class Threat(Base):
    """One normalised threat-intelligence event."""

    __tablename__ = "threats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    meta_category: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    # NULL for rows classified as OTHER (industry news): they are corpus
    # members but not threats, so they carry no score or disposition.
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    risk_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    priority: Mapped[str | None] = mapped_column(String(4), nullable=True, index=True)
    cluster: Mapped[str | None] = mapped_column(String(8), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    action_plan: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    cve_id: Mapped[str | None] = mapped_column(String(24), nullable=True, index=True)
    # Every id the article names, as a JSON array. cve_id stays as the primary
    # (first) one so existing lookups and the assessment form keep working.
    cve_ids: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    # Points at the canonical row when this article is a copy (digest post or a
    # re-publication). Nothing is deleted: the API can hide duplicates on demand.
    duplicate_of: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    published_at: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (Index("ix_threats_priority_region", "priority", "region"),)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Threat id={self.id} priority={self.priority} score={self.risk_score}>"
