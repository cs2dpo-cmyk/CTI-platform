"""Load the research CSVs and turn them into scored, labelled threat records.

The two ``*_with_dates.csv`` files are the single source of truth: every
article's cluster, publication date and source URL come straight from the file.
Each article is classified individually by :mod:`services.classify` (the K-Means
cluster is kept for topic exploration only), and every derived number in the API
(stats, feed, decision matrix) is computed from these rows -- there are no
hard-coded counts and no simulated dates.
"""

from __future__ import annotations

import csv
import io
import json
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from services import classify

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATASET_DIR = BASE_DIR / "data"

DEFAULT_DATE_COLUMN = "published_at"


@dataclass(frozen=True)
class DatasetRecord:
    id: int
    title: str
    source: str
    region: str
    cluster: str
    category: str  # VULN | MALWARE | RESEARCH | OTHER
    evidence: dict[str, Any]  # CVSS / exploitation / exposure / CVE ids
    published_at: date
    source_url: str = ""
    date_source: str = ""

    def as_seed(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "source": self.source,
            "region": self.region,
            "cluster": self.cluster,
            "category": self.category,
            "evidence": self.evidence,
        }


_cache: dict[str, Any] = {"signature": None, "records": [], "info": {}}


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #


def dataset_dir() -> Path:
    override = os.getenv("CTI_DATASET_DIR", "").strip()
    return Path(override) if override else DEFAULT_DATASET_DIR


def _read_meta(directory: Path) -> dict[str, Any]:
    path = directory / "dataset_meta.json"
    if path.exists():
        with io.open(path, encoding="utf-8-sig") as handle:
            return json.load(handle)
    return {}


def _resolve_csv(directory: Path, value: str, default_name: str) -> Path:
    """Resolve a metadata path.

    ``"Taiwan.csv"``        → relative to the dataset directory
    ``"data/Taiwan.csv"``   → relative to the project root
    ``"/abs/Taiwan.csv"``   → used as-is
    """
    raw = (value or default_name).strip()
    path = Path(raw)
    if path.is_absolute():
        return path
    if path.parent != Path("."):
        return (BASE_DIR / path).resolve()
    return directory / path


def _csv_paths(directory: Path, meta: dict[str, Any]) -> tuple[Path, Path]:
    provenance = meta.get("provenance", {})
    taiwan = _resolve_csv(
        directory,
        meta.get("taiwan_csv") or provenance.get("taiwan_file", ""),
        "Taiwan_security_dataset_with_dates.csv",
    )
    global_ = _resolve_csv(
        directory,
        meta.get("global_csv") or provenance.get("global_file", ""),
        "Global_security_dataset_with_dates.csv",
    )
    return taiwan, global_


def corpus_signature() -> tuple:
    """mtime fingerprint of the files the corpus is parsed from."""
    directory = dataset_dir()
    meta = _read_meta(directory)
    taiwan_path, global_path = _csv_paths(directory, meta)
    return _signature([taiwan_path, global_path, directory / "dataset_meta.json"])


def _signature(paths: Iterable[Path]) -> tuple:
    stamps = []
    for path in paths:
        stamps.append((str(path), path.stat().st_mtime if path.exists() else 0))
    return tuple(stamps)


# --------------------------------------------------------------------------- #
# Parsing helpers
# --------------------------------------------------------------------------- #


def _rows_from_csv(path: Path) -> list[dict[str, str]]:
    with io.open(path, encoding="utf-8-sig", newline="") as handle:
        return [{k.strip(): (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def _parse_date(raw: str) -> date | None:
    text = (raw or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


# --------------------------------------------------------------------------- #
# Loader
# --------------------------------------------------------------------------- #


def load_dataset(*, refresh: bool = False) -> tuple[list[DatasetRecord], dict[str, Any]]:
    """Parse both CSVs into records plus provenance metadata (cached by mtime)."""
    directory = dataset_dir()
    meta = _read_meta(directory)
    taiwan_path, global_path = _csv_paths(directory, meta)

    signature = _signature([taiwan_path, global_path, directory / "dataset_meta.json"])
    if not refresh and _cache["signature"] == signature and _cache["records"]:
        return _cache["records"], _cache["info"]

    provenance = meta.get("provenance", {})
    date_column = (meta.get("date_column") or DEFAULT_DATE_COLUMN).strip()
    export_date = _parse_date(provenance.get("exported_at", "")) or date(2026, 10, 30)

    missing = [str(path) for path in (taiwan_path, global_path) if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "找不到語料 CSV：" + "、".join(missing)
            + "。請確認 dataset_meta.json 的 taiwan_csv / global_csv 路徑，"
            "或設定 CTI_DATASET_DIR 指向資料夾。"
        )

    records: list[DatasetRecord] = []
    next_id = 1
    per_region: dict[str, int] = {}
    date_sources: dict[str, int] = {}
    unknown_dates: list[str] = []

    for region, path in (("taiwan", taiwan_path), ("global", global_path)):
        rows = _rows_from_csv(path)

        for row in rows:
            title = row.get("title", "")
            if not title:
                continue
            cluster = str(row.get("cluster", "")).strip()
            text = row.get("cleaned_text", "")
            category, _reason = classify.classify(title, text)
            evidence = classify.extract_evidence(title, text)

            source = row.get("platform") or ("THN" if region == "global" else "UNKNOWN")
            published = _parse_date(row.get(date_column, ""))
            if published is None:
                # Never invent a date: fall back to the export day and say so.
                published = export_date
                date_source = "unknown"
                unknown_dates.append(title)
            else:
                date_source = (row.get("date_source") or "source").strip() or "source"

            records.append(
                DatasetRecord(
                    id=next_id,
                    title=title,
                    source=source,
                    region=region,
                    cluster=cluster,
                    category=category,
                    evidence=evidence,
                    published_at=published,
                    source_url=(row.get("source_url") or "").strip(),
                    date_source=date_source,
                )
            )
            next_id += 1
            per_region[region] = per_region.get(region, 0) + 1
            date_sources[date_source] = date_sources.get(date_source, 0) + 1

    classification = {key: 0 for key in classify.CATEGORIES}
    for record in records:
        classification[record.category] = classification.get(record.category, 0) + 1

    info = {
        "sources": [str(taiwan_path), str(global_path)],
        "source_directory": provenance.get("source_directory", str(directory)),
        "exported_at": export_date.isoformat(),
        "note": provenance.get("note", ""),
        "classification_note": meta.get("classification_note", ""),
        "classifier": meta.get("classifier", "services/classify.py"),
        "validation": meta.get("validation", {}),
        "classification": classification,
        "threats": len(records) - classification.get("OTHER", 0),
        "date_policy": meta.get("date_policy", "column"),
        "date_column": date_column,
        "date_sources": date_sources,
        "rows": per_region,
        "total": len(records),
        "unknown_dates": unknown_dates,
    }

    _cache.update(signature=signature, records=records, info=info)
    return records, info


def group_clusters(records: Iterable[DatasetRecord]) -> list[dict[str, Any]]:
    """Region × cluster tally, with the category mix inside each cluster.

    A cluster is no longer assumed to be one category: the labels come from the
    per-article classifier, so a cluster can legitimately mix (for example the
    Taiwan C1 group holds attacks, policy notes and product news).
    """
    buckets: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        key = (record.region, record.cluster)
        bucket = buckets.setdefault(
            key,
            {"region": record.region, "cluster": record.cluster, "category": record.category,
             "count": 0, "breakdown": {}},
        )
        bucket["breakdown"][record.category] = bucket["breakdown"].get(record.category, 0) + 1
        bucket["count"] += 1
    return sorted(buckets.values(), key=lambda item: (item["region"], int(item["cluster"] or 0)))
