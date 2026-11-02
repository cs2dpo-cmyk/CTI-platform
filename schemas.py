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
    risk_score: float
    risk_level: RiskLevel
    priority: Priority
    action_plan: list[ActionStep] = Field(default_factory=list)
    published_at: date
    created_at: datetime | None = None


class ThreatListResponse(BaseModel):
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
    category: Literal["Vulnerability", "Malware", "SupplyChain", "Research"] = "Vulnerability"
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
    noise_reduction: float
    corpus: str
    balance: str
    scoring: str


class StatsResponse(BaseModel):
    generated_at: datetime
    model: ModelInfo
    totals: dict[str, Any]
    regions: list[RegionStat]
    meta_categories: list[MetaCategoryStat]
    categories: list[CategoryStat]
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

    raw_plan = get("action_plan", "[]")
    try:
        plan = json.loads(raw_plan) if isinstance(raw_plan, str) else (raw_plan or [])
    except json.JSONDecodeError:
        plan = []

    return ThreatOut(
        id=get("id"),
        title=get("title"),
        source=get("source"),
        region=get("region"),
        category=category,
        category_label=risk_engine.CATEGORY_TAXONOMY.get(category, {}).get("label", category),
        meta_category=meta,
        meta_label=risk_engine.META_CATEGORY_META.get(meta, {}).get("label", meta),
        risk_score=round(float(get("risk_score") or 0.0), 1),
        risk_level=get("risk_level", "MEDIUM"),
        priority=get("priority", "P3"),
        action_plan=[ActionStep(**step) for step in plan if isinstance(step, dict)],
        published_at=get("published_at"),
        created_at=get("created_at"),
    )
