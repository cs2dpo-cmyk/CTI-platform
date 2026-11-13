"""Build the held-out annotation sheet from the rows that have no gold label.

The 100 existing labels were used while tuning the rules, so they cannot double
as a test set. The other half of the corpus has never been labelled; this tool
turns it into a sheet two people can annotate independently.

Predictions are deliberately NOT written to the sheet: seeing the model's answer
while labelling turns the test back into a self-fulfilling measurement.

Usage:
    ./.venv/Scripts/python.exe tools/make_holdout.py
    ./.venv/Scripts/python.exe tools/make_holdout.py --force   # overwrite labels
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DATA = ROOT / "data"
SHEET = DATA / "holdout_labels.csv"
MANIFEST = DATA / "holdout_manifest.json"
CORPUS = {
    "taiwan": DATA / "Taiwan_security_dataset_with_dates.csv",
    "global": DATA / "Global_security_dataset_with_dates.csv",
}


def read_rows(path: Path) -> list[dict[str, str]]:
    with io.open(path, encoding="utf-8-sig", newline="") as handle:
        return [{k.strip(): (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="覆蓋已存在的標註表")
    parser.add_argument("--limit", type=int, default=100, help="最多抽幾筆")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if SHEET.exists() and not args.force:
        existing = read_rows(SHEET)
        filled = sum(1 for row in existing if row.get("label"))
        print(f"{SHEET.relative_to(ROOT)} 已存在：{len(existing)} 列，已標 {filled} 列")
        print("要重建請加 --force（會覆蓋已填的標註）")
        return 0

    gold_titles = {row["title"] for row in read_rows(DATA / "gold_labels.csv")}
    candidates: list[dict[str, str]] = []
    for region, path in CORPUS.items():
        for row in read_rows(path):
            title = row.get("title", "")
            if not title or title in gold_titles:
                continue
            candidates.append({
                "title": title,
                "source": row.get("platform", ""),
                "region": region,
            })

    candidates.sort(key=lambda row: (row["region"], row["source"], row["title"]))
    selected = candidates[: args.limit]

    with SHEET.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "title", "source", "region", "label", "notes"])
        writer.writeheader()
        for index, row in enumerate(selected, start=1):
            writer.writerow({
                "id": f"H{index:03d}",
                "title": row["title"],
                "source": row["source"],
                "region": row["region"],
                "label": "",
                "notes": "",
            })

    manifest = {
        "generated": date.today().isoformat(),
        "sheet": SHEET.name,
        "rows": len(selected),
        "pool": len(candidates),
        "gold_rows_reserved": len(gold_titles),
        "categories": ["VULN", "MALWARE", "RESEARCH", "OTHER"],
        "by_source": {
            source: sum(1 for row in selected if row["source"] == source)
            for source in sorted({row["source"] for row in selected})
        },
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"pool {len(candidates)}  selected {len(selected)}  gold reserved {len(gold_titles)}")
    print(f"by source {manifest['by_source']}")
    print(f"-> {SHEET.relative_to(ROOT)}（label 欄留空）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
