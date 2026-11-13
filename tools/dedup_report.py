"""Measure how many of the stored threats are actually distinct events.

Usage:
    ./.venv/Scripts/python.exe tools/dedup_report.py
    ./.venv/Scripts/python.exe tools/dedup_report.py --threshold 0.85

Writes data/dedup_report.json and prints a summary.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.dedup import (  # noqa: E402
    DEFAULT_TITLE_THRESHOLD,
    Item,
    group_duplicates,
    similarity_sensitivity,
)

DB_PATH = ROOT / "data" / "cti.db"
REPORT_PATH = ROOT / "data" / "dedup_report.json"


def load_items(db_path: Path) -> list[Item]:
    connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            "SELECT id, title, source, source_url, action_plan FROM threats"
        ).fetchall()
    finally:
        connection.close()
    return [
        Item(
            key=row[0],
            title=row[1] or "",
            source=row[2] or "",
            url=row[3] or "",
            cve_text=row[4] or "",
        )
        for row in rows
    ]


def build_report(items: list[Item], threshold: float) -> dict:
    groups = group_duplicates(items, title_threshold=threshold)
    by_key = {item.key: item for item in items}

    redundant = sum(group.size - 1 for group in groups)
    duplicates = [group for group in groups if group.size > 1]

    # Which source contributes the extra copies?
    redundant_by_source: Counter[str] = Counter()
    for group in duplicates:
        members = [by_key[key] for key in group.keys]
        # Keep the earliest item as the canonical one, count the rest.
        members.sort(key=lambda item: item.key)
        for extra in members[1:]:
            redundant_by_source[extra.source or "?"] += 1

    cross_source = []
    for group in duplicates:
        sources = {by_key[key].source for key in group.keys}
        if len(sources) > 1:
            cross_source.append(
                {
                    "sources": sorted(sources),
                    "reasons": sorted(group.reasons),
                    "titles": [by_key[key].title for key in group.keys],
                }
            )

    biggest = []
    for group in duplicates[:15]:
        biggest.append(
            {
                "size": group.size,
                "reasons": sorted(group.reasons),
                "sources": sorted({by_key[key].source for key in group.keys}),
                "titles": [by_key[key].title for key in group.keys],
            }
        )

    return {
        "threshold": threshold,
        "totals": {
            "items": len(items),
            "distinct_events": len(groups),
            "duplicate_groups": len(duplicates),
            "redundant_items": redundant,
            "reduction_pct": round(100 * redundant / len(items), 1) if items else 0.0,
            "largest_group": max((group.size for group in groups), default=0),
        },
        "redundant_by_source": dict(redundant_by_source),
        "cross_source_groups": len(cross_source),
        "cross_source_examples": cross_source[:10],
        "biggest_groups": biggest,
        "sensitivity": {str(k): v for k, v in similarity_sensitivity(items).items()},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--threshold", type=float, default=DEFAULT_TITLE_THRESHOLD)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    items = load_items(args.db)
    report = build_report(items, args.threshold)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    totals = report["totals"]
    print(f"items            {totals['items']}")
    print(f"distinct events  {totals['distinct_events']}")
    print(f"redundant copies {totals['redundant_items']} ({totals['reduction_pct']}%)")
    print(f"duplicate groups {totals['duplicate_groups']}  (largest {totals['largest_group']})")
    print(f"by source        {report['redundant_by_source']}")
    print(f"cross-source     {report['cross_source_groups']}")
    print(f"sensitivity      {report['sensitivity']}")
    if report["cross_source_examples"]:
        print("\ncross-source examples:")
        for example in report["cross_source_examples"][:5]:
            print(f"  [{'+'.join(example['sources'])}] {' / '.join(example['reasons'])}")
            for title in example["titles"]:
                print(f"    - {title[:90]}")
    print(f"\nreport -> {REPORT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
