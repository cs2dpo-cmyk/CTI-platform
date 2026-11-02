"""Load the research CSVs and turn them into scored, labelled threat records.

The two ``*_security_dataset_cleaned.csv`` files are the single source of truth:
every article's cluster id comes from the file, the cluster is mapped to a
Meta-Category through ``data/dataset_meta.json``, and every derived number in the
API (stats, feed, decision matrix) is computed from these rows — there are no
hard-coded counts anywhere.

The export does not carry publication dates, so dates are backfilled from the
row order (newest first) anchored at the export date. ``date_policy`` in the
metadata documents this; set it to ``"none"`` to disable backfilling.
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATASET_DIR = BASE_DIR / "data"

VALID_META = ("VULN", "MALWARE", "RESEARCH")

# Titles that read like a critical advisory get a HIGH hint; the rest MEDIUM.
_SEVERE = re.compile(
    r"critical|zero[- ]day|0-day|actively exploited|remote code|arbitrary code|\brce\b"
    r"|滿分|在野|遠端程式碼|任意程式碼|緊急|重大|rce|exploited in the wild",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class DatasetRecord:
    id: int
    title: str
    source: str
    region: str
    cluster: str
    category: str  # VULN | MALWARE | RESEARCH
    risk_hint: str  # HIGH | MEDIUM | LOW
    published_at: date

    def as_seed(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "source": self.source,
            "region": self.region,
            "cluster": self.cluster,
            "category": self.category,
            "risk_hint": self.risk_hint,
        }


_cache: dict[str, Any] = {"signature": None, "records": [], "info": {}}


def dataset_dir() -> Path:
    override = os.getenv("CTI_DATASET_DIR", "").strip()
    return Path(override) if override else DEFAULT_DATASET_DIR


def _read_meta(directory: Path) -> dict[str, Any]:
    path = directory / "dataset_meta.json"
    if path.exists():
        with io.open(path, encoding="utf-8-sig") as handle:
            return json.load(handle)
    return {}


def _signature(directory: Path, meta: dict[str, Any]) -> tuple:
    names = [meta.get("provenance", {}).get("taiwan_file", "Taiwan_security_dataset_cleaned.csv"),
             meta.get("provenance", {}).get("global_file", "Global_security_dataset_cleaned.csv")]
    stamps = []
    for name in names:
        path = directory / name
        stamps.append((name, path.stat().st_mtime if path.exists() else 0))
    return tuple(stamps)


def _risk_hint(title: str, meta_category: str) -> str:
    if meta_category == "RESEARCH":
        return "LOW"
    return "HIGH" if _SEVERE.search(title) else "MEDIUM"


def _rows_from_csv(path: Path) -> list[dict[str, str]]:
    with io.open(path, encoding="utf-8-sig", newline="") as handle:
        return [{k.strip(): (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def load_dataset(*, refresh: bool = False) -> tuple[list[DatasetRecord], dict[str, Any]]:
    """Parse both CSVs into records plus provenance metadata (cached by mtime)."""
    directory = dataset_dir()
    meta = _read_meta(directory)
    signature = _signature(directory, meta)
    if not refresh and _cache["signature"] == signature and _cache["records"]:
        return _cache["records"], _cache["info"]

    provenance = meta.get("provenance", {})
    mapping = meta.get("cluster_to_meta", {})
    overrides = {title.strip() for title in meta.get("research_overrides", []) if title.strip()}
    date_policy = meta.get("date_policy", "row_order_backfill")
    export_date = date.fromisoformat(provenance.get("exported_at", "2026-10-30"))

    files = [
        ("taiwan", provenance.get("taiwan_file", "Taiwan_security_dataset_cleaned.csv")),
        ("global", provenance.get("global_file", "Global_security_dataset_cleaned.csv")),
    ]

    records: list[DatasetRecord] = []
    next_id = 1
    per_region: dict[str, int] = {}
    missing: list[str] = []

    for region, filename in files:
        path = directory / filename
        if not path.exists():
            missing.append(str(path))
            continue

        rows = _rows_from_csv(path)
        region_map = {str(key): str(value).upper() for key, value in mapping.get(region, {}).items()}

        for index, row in enumerate(rows):
            title = row.get("title", "")
            if not title:
                continue
            cluster = str(row.get("cluster", "")).strip()
            category = region_map.get(cluster, "VULN")
            if category not in VALID_META:
                category = "VULN"
            if title in overrides:
                category = "RESEARCH"

            source = row.get("platform") or ("THN" if region == "global" else "UNKNOWN")
            published = (
                export_date - timedelta(days=index)
                if date_policy == "row_order_backfill"
                else export_date
            )

            records.append(
                DatasetRecord(
                    id=next_id,
                    title=title,
                    source=source,
                    region=region,
                    cluster=cluster,
                    category=category,
                    risk_hint=_risk_hint(title, category),
                    published_at=published,
                )
            )
            next_id += 1
            per_region[region] = per_region.get(region, 0) + 1

    if missing:
        raise FileNotFoundError(
            "找不到語料 CSV：" + "、".join(missing)
            + "。請將 Taiwan/Global_security_dataset_cleaned.csv 放到 data/，"
            "或設定 CTI_DATASET_DIR 指向原始資料夾。"
        )

    info = {
        "sources": [str(directory / filename) for _, filename in files],
        "source_directory": provenance.get("source_directory", str(directory)),
        "exported_at": export_date.isoformat(),
        "note": provenance.get("note", ""),
        "mapping_note": meta.get("mapping_note", ""),
        "cluster_to_meta": mapping,
        "date_policy": date_policy,
        "rows": per_region,
        "total": len(records),
        "overrides": sorted(overrides),
    }

    _cache.update(signature=signature, records=records, info=info)
    return records, info


def group_clusters(records: Iterable[DatasetRecord]) -> list[dict[str, Any]]:
    """Region × cluster tally with the Meta-Category each cluster maps to."""
    buckets: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        key = (record.region, record.cluster)
        bucket = buckets.setdefault(
            key,
            {"region": record.region, "cluster": record.cluster, "category": record.category, "count": 0},
        )
        bucket["count"] += 1
    return sorted(buckets.values(), key=lambda item: (item["region"], int(item["cluster"] or 0)))
