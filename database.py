"""SQLite engine, session factory and idempotent seeding."""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine, event, func, select, text, update
from sqlalchemy.exc import OperationalError
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

if _is_sqlite:

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _connection_record):
        """WAL keeps the read-only dashboard responsive while a writer commits."""
        cursor = dbapi_connection.cursor()
        try:
            # A read-only or network-backed file can refuse WAL; that must not
            # take the whole app down, so each pragma is best-effort.
            for pragma in ("PRAGMA journal_mode=WAL", "PRAGMA synchronous=NORMAL"):
                try:
                    cursor.execute(pragma)
                except Exception:  # pragma: no cover - depends on the filesystem
                    logger.warning("SQLite rejected %s; keeping the default mode", pragma)
            cursor.execute("PRAGMA busy_timeout=5000")
        finally:
            cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

# CVE ids were only ever written into the free-text title, which forced every
# corroboration lookup into a full-table LIKE scan. Capture them once at seed
# time into the indexed column instead.
CVE_PATTERN = re.compile(r"CVE-\d{4}-\d{4,7}", re.IGNORECASE)


def extract_cve(title: str) -> str | None:
    """Return the first normalised CVE id mentioned in a title, if any."""
    match = CVE_PATTERN.search(title or "")
    return match.group(0).upper() if match else None


def corpus_version(db: Session) -> tuple[int, str, int]:
    """Cheap fingerprint of the stored corpus, used as a cache key.

    One aggregate query, no row materialisation: anything that re-seeds or
    appends rows changes the tuple.
    """
    row = db.execute(
        select(func.count(Threat.id), func.max(Threat.created_at), func.max(Threat.id))
    ).one()
    return (int(row[0] or 0), str(row[1] or ""), int(row[2] or 0))


def get_db() -> Iterator[Session]:
    """FastAPI dependency that yields a scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(*, seed: bool = True) -> int:
    """Create tables, seed the corpus when empty, and apply idempotent upgrades."""
    Base.metadata.create_all(bind=engine)
    _ensure_indexes()
    seeded = _seed_corpus() if seed else 0
    with SessionLocal() as db:
        upgraded = _upgrade_rows(db)
    # Built after seeding so the index sees the rows it has to cover.
    _ensure_fts()
    if upgraded:
        _vacuum()
    return seeded


def _seed_corpus() -> int:
    with SessionLocal() as db:
        existing = db.scalar(select(func.count()).select_from(Threat)) or 0
        if existing:
            logger.info("Database already holds %s threats; skipping seed", existing)
            return 0

        records, info = dataset.load_dataset(refresh=True)
        for record in records:
            result = risk_engine.score_seed_record(record.as_seed())
            cves = record.evidence.get("cves") or []
            db.add(
                Threat(
                    id=record.id,
                    title=record.title,
                    source=record.source,
                    region=record.region,
                    category=record.category,
                    meta_category=risk_engine.meta_of(record.category),
                    cluster=record.cluster,
                    source_url=record.source_url or None,
                    # OTHER rows are corpus members, not threats: no score, no
                    # priority, no playbook.
                    risk_score=result.score if result else None,
                    risk_level=result.risk_level if result else None,
                    priority=result.priority if result else None,
                    # The playbook is derived from (meta_category, priority) at
                    # read time; storing it per row duplicated ~35 KB in 100 rows.
                    cve_id=cves[0] if cves else extract_cve(record.title),
                    published_at=record.published_at,
                )
            )
        db.commit()
        logger.info(
            "Seeded %s threats from %s", len(records), ", ".join(info.get("sources", []))
        )
        return len(records)


def _ensure_indexes() -> None:
    """``create_all`` never adds an index to a table that already exists."""
    for table in Base.metadata.tables.values():
        for index in table.indexes:
            index.create(bind=engine, checkfirst=True)


def _upgrade_rows(db: Session) -> int:
    """Backfill indexed CVE ids and drop playbooks that are pure duplication.

    Returns the number of rows touched so the caller knows whether a VACUUM is
    worth the file rewrite.
    """
    changed = 0

    for row in db.execute(select(Threat.id, Threat.title).where(Threat.cve_id.is_(None))).all():
        cve = extract_cve(row.title)
        if cve:
            db.execute(update(Threat).where(Threat.id == row.id).values(cve_id=cve))
            changed += 1

    for row in db.execute(
        select(Threat.id, Threat.meta_category, Threat.priority, Threat.action_plan)
    ).all():
        if not row.action_plan or row.action_plan == "[]" or not row.priority:
            continue
        derived = risk_engine.playbook(risk_engine.meta_of(row.meta_category), row.priority)
        try:
            stored = json.loads(row.action_plan)
        except json.JSONDecodeError:
            continue
        if stored == derived:
            db.execute(update(Threat).where(Threat.id == row.id).values(action_plan="[]"))
            changed += 1

    if changed:
        db.commit()
        logger.info("Upgraded %s rows (cve_id backfill / playbook de-duplication)", changed)
    return changed


# --------------------------------------------------------------------------- #
# Title search index (FTS5 trigram)
# --------------------------------------------------------------------------- #

# A trigram token is three characters, so shorter needles cannot be answered by
# the index. Callers fall back to LIKE for those, which keeps "AI" working.
MIN_TRIGRAM_CHARS = 3

# A very broad needle (thousands of hits) would become an IN (...) list that can
# exceed SQLite's bound-parameter limit, so wide results fall back to LIKE too.
MAX_INDEXED_IDS = 20_000

# The index is a plain standalone FTS5 table rather than an external-content
# table with sync triggers. This API never mutates a threat row outside the
# seed / upgrade path, and a trigger whose delete command targets a missing
# index entry makes FTS5 raise "database disk image is malformed". Rebuilding
# from the source table is simpler to reason about and cannot desync.
_FTS_TABLE_DDL = (
    "CREATE VIRTUAL TABLE IF NOT EXISTS threats_fts "
    "USING fts5(title, tokenize='trigram')"
)

_fts_ready = False


def _ensure_fts() -> bool:
    """(Re)build the trigram index whenever it does not match the threat rows."""
    global _fts_ready
    if not _is_sqlite:
        _fts_ready = False
        return False
    try:
        with engine.begin() as conn:
            # Older builds used an external-content index plus sync triggers.
            for trigger in ("threats_fts_ai", "threats_fts_ad", "threats_fts_au"):
                conn.exec_driver_sql(f"DROP TRIGGER IF EXISTS {trigger}")
            existing = conn.exec_driver_sql(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='threats_fts'"
            ).first()
            if existing and "content=" in (existing[0] or ""):
                conn.exec_driver_sql("DROP TABLE threats_fts")
                existing = None

            conn.exec_driver_sql(_FTS_TABLE_DDL)
            indexed = conn.exec_driver_sql("SELECT count(*) FROM threats_fts").scalar() or 0
            stored = conn.exec_driver_sql("SELECT count(*) FROM threats").scalar() or 0
            if indexed != stored:
                conn.exec_driver_sql("DELETE FROM threats_fts")
                conn.exec_driver_sql(
                    "INSERT INTO threats_fts(rowid, title) SELECT id, title FROM threats"
                )
        _fts_ready = True
    except Exception:  # pragma: no cover - depends on the SQLite build
        _fts_ready = False
        logger.warning(
            "FTS5 trigram index unavailable; title search falls back to LIKE",
            exc_info=True,
        )
    return _fts_ready


def search_title_ids(db: Session, query: str) -> list[int] | None:
    """Row ids whose title contains the query, answered by the trigram index.

    Returns None when the index cannot answer this query (FTS5 missing or the
    needle is shorter than one trigram) so the caller can use LIKE instead.
    """
    needle = (query or "").strip()
    if not _fts_ready or len(needle) < MIN_TRIGRAM_CHARS:
        return None
    phrase = '"' + needle.replace('"', '""') + '"'
    try:
        ids = list(
            db.execute(
                text("SELECT rowid FROM threats_fts WHERE threats_fts MATCH :phrase"),
                {"phrase": phrase},
            ).scalars()
        )
    except OperationalError:  # pragma: no cover - malformed MATCH expression
        return None
    return ids if len(ids) <= MAX_INDEXED_IDS else None


def _vacuum() -> None:
    """Reclaim the pages freed by the de-duplication pass."""
    if not _is_sqlite:
        return
    try:
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.exec_driver_sql("VACUUM")
    except Exception:  # pragma: no cover - opportunistic space reclaim
        logger.warning("VACUUM failed; the database file keeps its allocated size", exc_info=True)


if __name__ == "__main__":  # pragma: no cover - manual bootstrap helper
    logging.basicConfig(level=logging.INFO)
    print("seeded:", init_db())
