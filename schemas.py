"""Pydantic v2 request/response contracts for the public API."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Priority = Literal["P1", "P2", "P3"]
Region = Literal["taiwan", "global"]
RiskLevel = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]

CVE_PATTERN = r"^CVE-\d{4}-\d{4,7}$"


# --------------------------------------------------------------------------- #
# Threats
# --------------------------------------------------------------------------- #


class ActionStep(BaseModel):
    order: int
    title: str
    owner: str
    sla_hours: int
    detail: str


class DataProvenance(BaseModel):
    """Which data the response was computed from, and when it was captured."""

    data_as_of: str = ""
    stale_days: int | None = None
    snapshots: dict[str, Any] = Field(default_factory=dict)


class ThreatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    source: str
    region: Region
    category: str
    category_label: str
    meta_category: str
    meta_label: str
    cluster: str | None = None
    source_url: str | None = None
    risk_score: float | None = None
    risk_level: RiskLevel | None = None
    priority: Priority | None = None
    action_plan: list[ActionStep] = Field(default_factory=list)
    cve_id: str | None = None
    cve_ids: list[str] = Field(default_factory=list)
    duplicate_of: int | None = None
    published_at: date
    created_at: datetime | None = None


class PatchItemOut(BaseModel):
    cve: str
    priority: Priority
    sla: str
    epss: float | None = None
    cvss: float | None = None
    exploited: bool = False
    exposure: str = "unknown"
    exposure_label: str = ""
    assets: list[str] = Field(default_factory=list)
    articles: int = 0
    sources: list[str] = Field(default_factory=list)
    first_seen: str | None = None
    reason: str = ""


class PatchPriorityResponse(DataProvenance):
    total: int
    returned: int
    items: list[PatchItemOut] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)


class ThreatListResponse(DataProvenance):
    total: int
    limit: int
    offset: int
    returned: int
    filters: dict[str, Any]
    items: list[ThreatOut]


# --------------------------------------------------------------------------- #
# Assessment
# --------------------------------------------------------------------------- #


class AssessRequest(BaseModel):
    """Inputs collected by the interactive risk console."""

    asset_type: Literal[
        "core_datacenter", "ot_ics", "identity_idp", "cloud_infra",
        "dev_pipeline", "web_app", "endpoint",
    ] = Field("web_app", description="受評估的資產類型")
    threat_source: Literal[
        "zero_day", "ransomware", "apt", "supply_chain", "malware",
        "credential_theft", "phishing", "ddos",
    ] = Field("phishing", description="主要威脅來源")
    category: Literal["VULN", "MALWARE", "RESEARCH"] = "VULN"
    region: Region = "taiwan"
    cve_id: str | None = Field(default=None, description="CVE 編號，例如 CVE-2026-111497")
    cvss: float | None = Field(default=None, ge=0.0, le=10.0, description="CVSS 3.1 分數")
    exploit_status: Literal["active", "poc_public", "unknown", "none"] = "unknown"
    exposure: Literal["public", "partner", "internal"] = "internal"
    controls: list[Literal["edr", "mfa", "waf", "segmentation", "backup", "patch_pipeline"]] = Field(
        default_factory=list
    )
    data_sensitivity: Literal["high", "medium", "low"] = "medium"
    asset_name: str | None = Field(default=None, max_length=120)

    @field_validator("cve_id")
    @classmethod
    def _normalise_cve(cls, value: str | None) -> str | None:
        if value in (None, ""):
            return None
        candidate = value.strip().upper()
        import re

        if not re.match(CVE_PATTERN, candidate):
            raise ValueError("CVE 編號格式應為 CVE-YYYY-NNNN（例：CVE-2026-111497）")
        return candidate

    @field_validator("asset_name")
    @classmethod
    def _strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class FactorOut(BaseModel):
    key: str
    label: str
    value: str
    normalized: float
    weight: float
    points: float


class AdjustmentOut(BaseModel):
    key: str
    label: str
    points: float


class AssessResponse(BaseModel):
    assessment_id: str
    asset_name: str | None
    cve_id: str | None
    score: float
    risk_level: RiskLevel
    priority: Priority
    priority_label: str
    headline: str
    criteria: str
    sla_hours: int
    owner: str
    confidence: float
    factors: list[FactorOut]
    adjustments: list[AdjustmentOut]
    action_plan: list[ActionStep]
    summary: str
    generated_at: datetime


# --------------------------------------------------------------------------- #
# Stats / dashboard
# --------------------------------------------------------------------------- #


class RegionStat(BaseModel):
    key: str
    label: str
    count: int
    share: float
    avg_score: float
    top_category: str


class MetaCategoryStat(BaseModel):
    key: str
    label: str
    label_en: str
    count: int
    share: float
    by_region: dict[str, int]


class CategoryStat(BaseModel):
    key: str
    label: str
    count: int
    share: float
    by_region: dict[str, int]


class BucketStat(BaseModel):
    key: str
    label: str
    count: int
    share: float


class ClusterStat(BaseModel):
    """One K-Means cluster inside one region, with its mapped Meta-Category."""

    region: str
    cluster: str
    label: str
    category: str
    category_label: str
    count: int
    breakdown: dict[str, int] = Field(default_factory=dict)


class DatasetInfo(BaseModel):
    """Provenance of the CSV rows that feed every number in the dashboard."""

    sources: list[str] = Field(default_factory=list)
    source_directory: str = ""
    exported_at: str = ""
    note: str = ""
    # Per-article classification (services/classify.py) replaced the old
    # cluster -> meta-category table; the counts and the validation result are
    # served so the dashboard can state how the corpus was labelled.
    classifier: str = ""
    classification_note: str = ""
    classification: dict[str, int] = Field(default_factory=dict)
    threats: int = 0
    validation: dict[str, Any] = Field(default_factory=dict)
    mapping_note: str = ""
    date_policy: str = ""
    date_column: str = ""
    date_sources: dict[str, int] = Field(default_factory=dict)
    rows: dict[str, int] = Field(default_factory=dict)
    total: int = 0
    overrides: list[str] = Field(default_factory=list)


class TimelinePoint(BaseModel):
    # `global` is a Python keyword, so the field is aliased to keep the JSON
    # contract the dashboard expects.
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    date: str
    taiwan: int
    global_: int = Field(alias="global")
    total: int


class PriorityBucket(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    priority: Priority
    label: str
    headline: str
    sla_hours: int
    criteria: str
    owner: str
    tone: str
    count: int
    taiwan: int
    global_: int = Field(alias="global")
    avg_score: float
    top_category: dict[str, Any] | None
    sample_titles: list[str]
    action_plan: list[ActionStep]


class ModelInfo(BaseModel):
    pipeline: str
    vectorizer: str
    clustering: str
    clusters: int
    corpus: str
    balance: str
    scoring: str
    classification: str = ""
    classification_accuracy: float | None = None


class StatsResponse(DataProvenance):
    generated_at: datetime
    model: ModelInfo
    totals: dict[str, Any]
    regions: list[RegionStat]
    meta_categories: list[MetaCategoryStat]
    clusters: list[ClusterStat]
    dataset: DatasetInfo
    risk_levels: list[BucketStat]
    priorities: list[BucketStat]
    sources: list[BucketStat]
    timeline: list[TimelinePoint]
    matrix: list[PriorityBucket]
    insights: list[str]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    database: str
    threats: int
    version: str


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def threat_to_schema(threat_row: Any) -> ThreatOut:
    """Convert an ORM row (or plain mapping) into the public threat schema."""
    get = threat_row.get if isinstance(threat_row, dict) else lambda key, default=None: getattr(
        threat_row, key, default
    )
    category = get("category", "Vulnerability")
    meta = get("meta_category", "VULN")
    from services import risk_engine

    raw_ids = get("cve_ids")
    try:
        cve_ids = json.loads(raw_ids) if isinstance(raw_ids, str) and raw_ids else []
    except json.JSONDecodeError:
        cve_ids = []
    primary_cve = get("cve_id")
    if not cve_ids and primary_cve:
        cve_ids = [primary_cve]

    raw_plan = get("action_plan", "[]")
    try:
        plan = json.loads(raw_plan) if isinstance(raw_plan, str) else (raw_plan or [])
    except json.JSONDecodeError:
        plan = []
    if not plan:
        # Rows no longer store their playbook: it is a pure function of
        # (meta_category, priority), so it is derived on read instead of being
        # duplicated into every database row.
        plan = risk_engine.playbook(meta, get("priority") or "P3")

    return ThreatOut(
        id=get("id"),
        title=get("title"),
        source=get("source"),
        region=get("region"),
        category=category,
        category_label=risk_engine.CATEGORY_TAXONOMY.get(category, {}).get("label", category),
        meta_category=meta,
        meta_label=risk_engine.META_CATEGORY_META.get(meta, {}).get("label", meta),
        cluster=get("cluster"),
        source_url=get("source_url"),
        risk_score=None if get("risk_score") is None else round(float(get("risk_score")), 1),
        risk_level=get("risk_level"),
        priority=get("priority"),
        action_plan=[ActionStep(**step) for step in plan if isinstance(step, dict)],
        cve_id=primary_cve or (cve_ids[0] if cve_ids else None),
        cve_ids=cve_ids,
        duplicate_of=get("duplicate_of"),
        published_at=get("published_at"),
        created_at=get("created_at"),
    )
