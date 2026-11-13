"""Compare the balanced sample with the natural corpus on the same metrics.

The canonical 200 rows were sampled 50:50 on purpose; the 588 scraped rows
follow the real publishing ratio (about 80:20 global:taiwan). Running the same
statistics over both shows which conclusions are artefacts of sampling and which
survive, which is a stronger statement than "our sample is skewed".

    ./.venv/Scripts/python.exe tools/dataset_comparison.py
"""

from __future__ import annotations

import csv
import io
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = DATA / "dataset_comparison.json"
CATEGORIES = ["MALWARE", "VULN", "RESEARCH", "OTHER"]


def read_urls(name: str) -> set[str]:
    path = DATA / name
    if not path.exists():
        return set()
    with io.open(path, encoding="utf-8-sig", newline="") as handle:
        return {row.get("source_url", "").strip() for row in csv.DictReader(handle)}


def profile(rows: list[dict]) -> dict:
    total = len(rows) or 1
    scored = [row for row in rows if row["risk_score"] is not None]
    months = Counter(row["month"] for row in rows)
    return {
        "rows": len(rows),
        "regions": {key: sum(1 for row in rows if row["region"] == key) for key in ("taiwan", "global")},
        "sources": dict(Counter(row["source"] for row in rows)),
        "meta": {
            key: {
                "count": sum(1 for row in rows if row["meta"] == key),
                "share": round(sum(1 for row in rows if row["meta"] == key) / total, 3),
            }
            for key in CATEGORIES
        },
        "avg_score": round(sum(row["risk_score"] for row in scored) / len(scored), 1) if scored else None,
        "priorities": {
            key: {
                "count": sum(1 for row in rows if row["priority"] == key),
                "share": round(sum(1 for row in rows if row["priority"] == key) / total, 3),
            }
            for key in ("P1", "P2", "P3")
        },
        "months": len(months),
        "first_month": min(months) if months else None,
        "last_month": max(months) if months else None,
        "thin_months": sum(1 for count in months.values() if count < 5),
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    balanced_urls = read_urls("Taiwan_security_dataset_with_dates.csv") | read_urls(
        "Global_security_dataset_with_dates.csv"
    )

    connection = sqlite3.connect(f"file:{DATA / 'cti.db'}?mode=ro", uri=True)
    try:
        rows = [
            {
                "url": url or "",
                "region": region,
                "source": source,
                "meta": meta,
                "risk_score": score,
                "priority": priority,
                "month": (published or "")[:7],
            }
            for url, region, source, meta, score, priority, published in connection.execute(
                "select source_url, region, source, meta_category, risk_score, priority, published_at from threats"
            )
        ]
    finally:
        connection.close()

    balanced = [row for row in rows if row["url"] in balanced_urls]
    natural = [row for row in rows if row["url"] not in balanced_urls]

    report = {
        "balanced_sample": profile(balanced),
        "natural_corpus": profile(natural),
        "combined": profile(rows),
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    header = f"{'metric':<26}{'balanced':>12}{'natural':>12}{'combined':>12}"
    print(header)
    for key, label in (
        ("rows", "rows"),
        ("months", "months covered"),
        ("avg_score", "average score"),
    ):
        values = [report[name][key] for name in ("balanced_sample", "natural_corpus", "combined")]
        print(f"{label:<26}" + "".join(f"{str(v):>12}" for v in values))
    for key in ("taiwan", "global"):
        values = [report[name]["regions"][key] for name in ("balanced_sample", "natural_corpus", "combined")]
        print(f"{'region ' + key:<26}" + "".join(f"{v:>12}" for v in values))
    for key in CATEGORIES:
        values = [f"{report[n]['meta'][key]['share']:.0%}" for n in ("balanced_sample", "natural_corpus", "combined")]
        print(f"{'meta ' + key:<26}" + "".join(f"{v:>12}" for v in values))
    for key in ("P1", "P2", "P3"):
        values = [f"{report[n]['priorities'][key]['share']:.0%}" for n in ("balanced_sample", "natural_corpus", "combined")]
        print(f"{'priority ' + key:<26}" + "".join(f"{v:>12}" for v in values))
    print(f"\n-> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
