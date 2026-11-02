"""SQLite engine, session factory and idempotent seeding."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from models import Base, Threat
from services import dataset, risk_engine

logger = logging.getLogger("cti.database")

BASE_DIR = Path(__file__).resolve().parent

# Render injects DATABASE_URL for managed databases; the PoC falls back to a
# local SQLite file so `uvicorn main:app` works with zero configuration.
DEFAULT_SQLITE_PATH = BASE_DIR / "data" / "cti.db"
DATABASE_URL = os.getenv("DATABASE_URL", "").strip() or f"sqlite:///{DEFAULT_SQLITE_PATH}"

_is_sqlite = DATABASE_URL.startswith("sqlite")

if _is_sqlite:
    # Make sure the directory that will hold the SQLite file exists (a Render
    # disk path, a fresh checkout, etc.) — create_engine does not create it.
    from sqlalchemy.engine import make_url

    _db_file = make_url(DATABASE_URL).database
    if _db_file and _db_file != ":memory:":
        Path(_db_file).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency that yields a scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(*, seed: bool = True) -> int:
    """Create tables and seed the corpus from the research CSVs when empty."""
    Base.metadata.create_all(bind=engine)
    if not seed:
        return 0

    with SessionLocal() as db:
        existing = db.scalar(select(func.count()).select_from(Threat)) or 0
        if existing:
            logger.info("Database already holds %s threats; skipping seed", existing)
            return 0

        records, info = dataset.load_dataset(refresh=True)
        for record in records:
            result = risk_engine.score_seed_record(record.as_seed())
            db.add(
                Threat(
                    id=record.id,
                    title=record.title,
                    source=record.source,
                    region=record.region,
                    category=record.category,
                    meta_category=risk_engine.meta_of(record.category),
                    cluster=record.cluster,
                    risk_score=result.score,
                    risk_level=result.risk_level,
                    priority=result.priority,
                    action_plan=json.dumps(result.action_plan, ensure_ascii=False),
                    published_at=record.published_at,
                )
            )
        db.commit()
        logger.info(
            "Seeded %s threats from %s", len(records), ", ".join(info.get("sources", []))
        )
        return len(records)


if __name__ == "__main__":  # pragma: no cover - manual bootstrap helper
    logging.basicConfig(level=logging.INFO)
    print("seeded:", init_db())
