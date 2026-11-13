"""FastAPI application entrypoint for the CTI risk decision-support platform.

Run locally:  uvicorn main:app --reload
On Render:    uvicorn main:app --host 0.0.0.0 --port $PORT
"""

from __future__ import annotations

import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import false, func, or_, select
from sqlalchemy.orm import Session, load_only

import database
import schemas
from services import analytics, dataset, epss, kev, patch_priority, risk_engine, snapshots

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"),
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("cti.api")

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
VERSION = "1.0.0"


# --------------------------------------------------------------------------- #
# App lifecycle
# --------------------------------------------------------------------------- #


@asynccontextmanager
async def lifespan(app: FastAPI):
    seeded = database.init_db()
    logger.info("CTI platform ready (seeded %s records)", seeded)
    yield
    logger.info("CTI platform shutting down")


app = FastAPI(
    title="CTI 資安風險決策支援平台 API",
    description=(
        "基於 TF-IDF + K-Means 情資分析的可解釋風險評分服務。"
        "提供總覽統計、即時風險評估與 P1-P3 情資篩選。"
    ),
    version=VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
)

_origins = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "*").split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins or ["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

api = APIRouter(prefix="/api/v1", tags=["cti"])


# --------------------------------------------------------------------------- #
# Health
# --------------------------------------------------------------------------- #


@api.get("/health", response_model=schemas.HealthResponse, summary="健康檢查")
def health(db: Session = Depends(database.get_db)) -> schemas.HealthResponse:
    count = db.scalar(select(func.count()).select_from(database.Threat)) or 0
    dialect = database.engine.dialect.name
    return schemas.HealthResponse(
        status="ok",
        database=f"{dialect}://{database.engine.url.database}",
        threats=count,
        version=VERSION,
    )


# --------------------------------------------------------------------------- #
# Overview statistics
# --------------------------------------------------------------------------- #


# The dashboard payload only changes when the corpus does, so it is computed
# once and re-served until a row is added, updated or the CSVs change.
_STATS_CACHE: dict[tuple[Any, ...], schemas.StatsResponse] = {}


def _sample_breakdown(db: Session) -> dict:
    """How much of the corpus comes from the balanced sample, and what the
    natural rows say about urgency when the balanced rows are removed."""
    balanced = dataset.canonical_urls()
    rows = db.execute(
        select(database.Threat.source_url, database.Threat.priority, database.Threat.risk_score)
    ).all()
    natural = [row for row in rows if (row.source_url or "") not in balanced]
    natural_scored = [row for row in natural if row.risk_score is not None]
    return {
        "balanced_rows": len(rows) - len(natural),
        "natural_rows": len(natural),
        "natural_p1_share": round(
            sum(1 for row in natural if row.priority == "P1") / len(natural), 3
        ) if natural else None,
        "natural_avg_score": round(
            sum(row.risk_score for row in natural_scored) / len(natural_scored), 1
        ) if natural_scored else None,
    }


@api.get("/stats", response_model=schemas.StatsResponse, summary="全球 / 台灣情資統計與 Meta-Category 分布")
def stats(db: Session = Depends(database.get_db)) -> schemas.StatsResponse:
    version = database.corpus_version(db)
    if not version[0]:
        raise HTTPException(status_code=503, detail="情資資料庫尚未初始化，請稍後重試。")

    key = (version, dataset.corpus_signature())
    cached = _STATS_CACHE.get(key)
    if cached is None:
        columns = (getattr(database.Threat, name) for name in analytics.STATS_COLUMNS)
        stmt = select(database.Threat).options(load_only(*columns))
        threats = db.scalars(stmt).all()
        _, dataset_info = dataset.load_dataset()
        stats_payload = analytics.build_stats(threats, dataset_info)
        stats_payload["totals"].update(_sample_breakdown(db))
        cached = schemas.StatsResponse(
            **stats_payload,
            data_as_of=snapshots.as_of(),
            stale_days=snapshots.staleness_days(),
            snapshots=snapshots.describe(),
        )
        _STATS_CACHE.clear()
        _STATS_CACHE[key] = cached
    # generated_at describes this response, not the cached computation.
    return cached.model_copy(update={"generated_at": datetime.now(timezone.utc)})


# --------------------------------------------------------------------------- #
# Live assessment
# --------------------------------------------------------------------------- #


@api.post("/assess", response_model=schemas.AssessResponse, summary="即時風險評估與 P1-P3 處置建議")
def assess(payload: schemas.AssessRequest, db: Session = Depends(database.get_db)) -> schemas.AssessResponse:
    matched = _match_corpus(
        db, cve_id=payload.cve_id, category=payload.category, region=payload.region
    )
    epss_score = epss.score_for([payload.cve_id]) if payload.cve_id else None
    kev_hit = kev.is_exploited(payload.cve_id) if payload.cve_id else False
    result = risk_engine.assess(
        asset_type=payload.asset_type,
        threat_source=payload.threat_source,
        category=payload.category,
        region=payload.region,
        cvss=payload.cvss,
        exploit_status=payload.exploit_status,
        exposure=payload.exposure,
        controls=payload.controls,
        data_sensitivity=payload.data_sensitivity,
        region_hits=matched["region_hits"],
        epss=epss_score,
        kev=kev_hit,
    )

    # Corroboration bonus: a CVE that already appears in the intel corpus is
    # materially more actionable than a hypothetical one.
    bonus = (2.0 if payload.cve_id else 0.0) + min(6.0, 2.0 * matched["cve_hits"])
    adjustments = list(result.adjustments)
    if bonus:
        adjustments.append(
            {
                "key": "corpus_corroboration",
                "label": f"情資語料佐證（{matched['cve_hits']} 筆命中）",
                "points": round(bonus, 2),
            }
        )

    score = round(min(result.score + bonus, 99.0), 1)
    final_priority = risk_engine.priority_for(score)
    if kev_hit:
        # Confirmed exploitation outranks any numeric band.
        final_priority = "P1"
    elif payload.cvss is not None and payload.cvss >= 9.0 and payload.exploit_status == "active":
        final_priority = "P1"

    meta = risk_engine.PRIORITY_META[final_priority]
    plan = risk_engine.playbook(risk_engine.meta_of(payload.category), final_priority)
    summary = _summarise(payload, score, final_priority, matched, epss=epss_score, kev=kev_hit)

    return schemas.AssessResponse(
        assessment_id=uuid.uuid4().hex[:12],
        asset_name=payload.asset_name,
        cve_id=payload.cve_id,
        score=score,
        risk_level=risk_engine.risk_level_for(score),
        priority=final_priority,
        priority_label=meta["label"],
        headline=meta["headline"],
        criteria=meta["criteria"],
        sla_hours=meta["sla_hours"],
        owner=meta["owner"],
        confidence=result.confidence,
        factors=[factor.as_dict() for factor in result.factors],
        adjustments=adjustments,
        action_plan=[schemas.ActionStep(**step) for step in plan],
        summary=summary,
        generated_at=datetime.now(timezone.utc),
    )


def _match_corpus(db: Session, *, cve_id: str | None, category: str,
                  region: str) -> dict[str, Any]:
    """Find how many seeded intel items corroborate this assessment.

    Every lookup hits an indexed equality comparison. The CVE was previously
    matched with `upper(title) LIKE '%...%'`, which cannot use an index and
    forced a full table scan on every assessment.
    """
    threat = database.Threat
    category_hits = db.scalar(
        select(func.count()).select_from(threat).where(threat.category == category)
    ) or 0
    region_hits = db.scalar(
        select(func.count()).select_from(threat).where(threat.region == region)
    ) or 0
    cve_hits = 0
    if cve_id:
        cve_hits = db.scalar(
            select(func.count()).select_from(threat).where(
                or_(threat.cve_id == cve_id, threat.cve_ids.like(f'%"{cve_id}"%'))
            )
        ) or 0
    return {"category_hits": category_hits, "cve_hits": cve_hits, "region_hits": region_hits}


def _summarise(payload: schemas.AssessRequest, score: float, priority: str,
               matched: dict[str, Any], epss: float | None = None,
               kev: bool = False) -> str:
    asset = risk_engine.ASSET_TYPES[payload.asset_type]["label"]
    threat = risk_engine.THREAT_SOURCES[payload.threat_source]["label"]
    region = "台灣在地" if payload.region == "taiwan" else "國際來源"
    parts = [
        f"以「{asset}」面對「{threat}」進行評估，綜合風險分數 {score:.1f}，判定為 {priority}。",
        f"情資語料中有 {matched['category_hits']} 筆同類別事件",
    ]
    if payload.cve_id:
        parts.append(f"，其中 {matched['cve_hits']} 筆直接提及 {payload.cve_id}")
    parts.append(f"；在地關聯採計{region} {matched.get('region_hits', 0)} 筆語料。")
    if kev:
        parts.append("該 CVE 已列入 CISA KEV，利用事實明確。")
    elif epss is not None:
        parts.append(f"FIRST EPSS 估計未來 30 天利用機率為 {epss:.0%}。")
    return "".join(parts)


# --------------------------------------------------------------------------- #
# EPSS-driven patch priority
# --------------------------------------------------------------------------- #


@api.get("/patch-priority", response_model=schemas.PatchPriorityResponse,
         summary="修補優先級（EPSS + KEV）")
def patch_priority_list(
    priority: Literal["P1", "P2", "P3"] | None = Query(None, description="只看某個優先級"),
    exposure: bool = Query(True, description="是否依曝險上下調整一級"),
    limit: int = Query(20, ge=1, le=300),
    db: Session = Depends(database.get_db),
) -> schemas.PatchPriorityResponse:
    """CVEs ordered by exploitation likelihood, with an SLA band per CVE.

    P1 is KEV membership (exploitation confirmed), P2 is EPSS >= 0.10 or
    CVSS >= 9.0, P3 is everything else. See services/patch_priority.py.
    """
    records, _ = dataset.load_dataset()
    duplicate_ids = set(
        db.scalars(
            select(database.Threat.id).where(database.Threat.duplicate_of.is_not(None))
        ).all()
    )
    rows = [
        {
            "cves": record.evidence.get("cves") or [],
            "source": record.source,
            "published_at": record.published_at,
            "cvss": record.evidence.get("cvss"),
            "title": record.title,
            "public_facing": record.evidence.get("exposure") == "public",
        }
        for record in records
        if record.id not in duplicate_ids
    ]
    items = patch_priority.build(rows, epss.all_scores(), use_exposure=exposure)
    summary = patch_priority.summarize(items)
    if priority:
        items = [item for item in items if item.priority == priority]
    return schemas.PatchPriorityResponse(
        data_as_of=snapshots.as_of(),
        stale_days=snapshots.staleness_days(),
        snapshots=snapshots.describe(),
        total=summary["cves"],
        returned=min(len(items), limit),
        items=[schemas.PatchItemOut(**item.as_dict()) for item in items[:limit]],
        summary=summary,
    )


# --------------------------------------------------------------------------- #
# Threat list with query filters
# --------------------------------------------------------------------------- #


@api.get("/threats", response_model=schemas.ThreatListResponse, summary="情資列表（Priority / Region 篩選）")
def list_threats(
    priority: Literal["P1", "P2", "P3"] | None = Query(None, description="處置優先級"),
    region: Literal["taiwan", "global"] | None = Query(None, description="情資來源地區"),
    category: Literal["VULN", "MALWARE", "RESEARCH", "OTHER"] | None = Query(None),
    meta_category: Literal["VULN", "MALWARE", "RESEARCH", "OTHER"] | None = Query(None, include_in_schema=False),
    source: str | None = Query(None, max_length=32, description="情資來源，例如 TWCERT"),
    q: str | None = Query(None, max_length=120, description="標題關鍵字"),
    min_score: float | None = Query(None, ge=0, le=100),
    sort: Literal["risk", "date"] = Query("risk", description="排序依據"),
    dedupe: bool = Query(True, description="排除重複事件（預設開，設 false 可看全部文章）"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(database.get_db),
) -> schemas.ThreatListResponse:
    stmt = select(database.Threat)
    conditions = []
    if dedupe:
        conditions.append(database.Threat.duplicate_of.is_(None))
    if priority:
        conditions.append(database.Threat.priority == priority)
    if region:
        conditions.append(database.Threat.region == region)
    if category:
        conditions.append(database.Threat.category == category)
    if meta_category:
        conditions.append(database.Threat.meta_category == meta_category)
    if source:
        conditions.append(database.Threat.source == source)
    if q:
        needle = q.strip()
        # The trigram index answers substring search in O(log n); needles too
        # short for a trigram (e.g. "AI") keep the LIKE scan they need.
        ids = database.search_title_ids(db, needle)
        if ids is None:
            conditions.append(database.Threat.title.ilike(f"%{needle}%"))
        elif ids:
            conditions.append(database.Threat.id.in_(ids))
        else:
            conditions.append(false())
    if min_score is not None:
        conditions.append(database.Threat.risk_score >= min_score)
    if conditions:
        stmt = stmt.where(*conditions)

    total = db.scalar(
        select(func.count()).select_from(database.Threat).where(*conditions)
    ) or 0

    if sort == "date":
        stmt = stmt.order_by(database.Threat.published_at.desc(), database.Threat.risk_score.desc())
    else:
        stmt = stmt.order_by(database.Threat.risk_score.desc(), database.Threat.published_at.desc())

    rows = db.scalars(stmt.limit(limit).offset(offset)).all()
    items = [schemas.threat_to_schema(row) for row in rows]
    return schemas.ThreatListResponse(
        data_as_of=snapshots.as_of(),
        stale_days=snapshots.staleness_days(),
        snapshots=snapshots.describe(),
        total=total,
        limit=limit,
        offset=offset,
        returned=len(items),
        filters={
            "priority": priority,
            "region": region,
            "category": category,
            "meta_category": meta_category,
            "source": source,
            "q": q,
            "min_score": min_score,
            "sort": sort,
        },
        items=items,
    )


@api.get("/threats/{threat_id}", response_model=schemas.ThreatOut, summary="單筆情資明細")
def get_threat(threat_id: int, db: Session = Depends(database.get_db)) -> schemas.ThreatOut:
    row = db.get(database.Threat, threat_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="查無此情資項目")
    return schemas.threat_to_schema(row)


app.include_router(api)


# --------------------------------------------------------------------------- #
# Static dashboard
# --------------------------------------------------------------------------- #

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    # The dashboard HTML has no content hash in its URL, so browsers would
    # otherwise keep a heuristic copy. Revalidate on every load.
    return FileResponse(STATIC_DIR / "index.html", headers={"Cache-Control": "no-cache"})


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)
