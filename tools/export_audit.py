#!/usr/bin/env python3
"""Export the per-article classification and score as an audit CSV.

This is the artifact the research notebook plots from, so the paper's numbers
and the dashboard's numbers cannot drift apart: both read the same file.
"""
from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from services import classify, dataset, risk_engine  # noqa: E402

DATA = ROOT / "data"
FIELDS = [
    "region", "source", "cluster", "meta_category", "reason",
    "cves", "cvss", "exploit", "exposure", "risk_score", "priority", "title", "gold",
]


def load_gold() -> dict[str, str]:
    path = DATA / "gold_labels.csv"
    if not path.exists():
        return {}
    code = {"V": "VULN", "M": "MALWARE", "R": "RESEARCH", "O": "OTHER"}
    with io.open(path, encoding="utf-8-sig", newline="") as handle:
        return {row["title"]: code.get(row["gold"], "") for row in csv.DictReader(handle)}


def main() -> None:
    records, info = dataset.load_dataset(refresh=True)
    gold = load_gold()

    rows = []
    for record in records:
        result = risk_engine.score_seed_record(record.as_seed())
        _category, reason = classify.classify(record.title, "")
        evidence = record.evidence
        rows.append({
            "region": record.region,
            "source": record.source,
            "cluster": record.cluster,
            "meta_category": record.category,
            "reason": reason,
            "cves": ",".join(evidence.get("cves") or []),
            "cvss": "" if evidence.get("cvss") is None else evidence["cvss"],
            "exploit": evidence.get("exploit", ""),
            "exposure": evidence.get("exposure", ""),
            "risk_score": "" if result is None else result.score,
            "priority": "" if result is None else result.priority,
            "title": record.title,
            "gold": gold.get(record.title, ""),
        })

    target = DATA / "classification_audit.csv"
    with io.open(target, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["meta_category"]] = counts.get(row["meta_category"], 0) + 1
    agree = sum(1 for row in rows if row["gold"] and row["gold"] == row["meta_category"])
    graded = sum(1 for row in rows if row["gold"])
    print(f"wrote {target} ({len(rows)} rows)")
    print("classification:", counts)
    print(f"agreement with gold: {agree}/{graded} = {agree / graded:.1%}" if graded else "no gold labels")


if __name__ == "__main__":
    main()
