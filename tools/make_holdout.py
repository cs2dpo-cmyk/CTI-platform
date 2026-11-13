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


def stratified_sample(pool: list[dict[str, str]], limit: int) -> list[dict[str, str]]:
    """Proportional by source, then round-robin across months.

    Proportional keeps the sheet representative; round-robin across months stops
    the sample from collapsing onto the two busiest months.
    """
    from collections import defaultdict

    by_source: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in pool:
        by_source[row["source"]].append(row)
    total = len(pool) or 1

    selected: list[dict[str, str]] = []
    for source, rows in sorted(by_source.items()):
        quota = max(1, round(limit * len(rows) / total))
        by_month: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in sorted(rows, key=lambda item: item["title"]):
            by_month[row.get("month", "")].append(row)
        months = sorted(by_month)
        picked = 0
        index = 0
        while picked < quota and months:
            month = months[index % len(months)]
            if by_month[month]:
                selected.append(by_month[month].pop())
                picked += 1
            index += 1
            if index > quota * len(months) + len(months):
                break
    return selected[:limit]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="覆蓋已存在的標註表")
    parser.add_argument("--limit", type=int, default=100, help="最多抽幾筆")
    parser.add_argument("--round", type=int, default=1, choices=[1, 2],
                        help="1=原始語料未標註的一半；2=擴充語料（排除所有已標註）")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    target_name = "holdout2_labels.csv" if args.round == 2 else "holdout_labels.csv"
    target = DATA / target_name
    if target.exists() and not args.force:
        existing = read_rows(target)
        filled = sum(1 for row in existing if row.get("label"))
        print(f"{target.relative_to(ROOT)} 已存在：{len(existing)} 列，已標 {filled} 列")
        print("要重建請加 --force（會覆蓋已填的標註）")
        return 0

    labelled_titles = {row["title"] for row in read_rows(DATA / "gold_labels.csv")}
    for name in ("holdout_labels.csv", "holdout_labels_b.csv"):
        path = DATA / name
        if path.exists():
            labelled_titles.update(row["title"] for row in read_rows(path))

    if args.round == 2:
        pool: list[dict[str, str]] = []
        for region, name in (
            ("taiwan", "Taiwan_expanded_dataset_with_dates.csv"),
            ("global", "Global_expanded_dataset_with_dates.csv"),
        ):
            path = DATA / name
            if not path.exists():
                continue
            for row in read_rows(path):
                title = row.get("title", "")
                if not title or title in labelled_titles:
                    continue
                pool.append({
                    "title": title,
                    "source": row.get("platform", ""),
                    "region": region,
                    "month": row.get("published_at", "")[:7],
                })
        selected = stratified_sample(pool, args.limit)
        pool_size = len(pool)
        prefix = "H2"
        sheet_name, manifest_name = "holdout2_labels.csv", "holdout2_manifest.json"
    else:
        candidates: list[dict[str, str]] = []
        for region, path in CORPUS.items():
            for row in read_rows(path):
                title = row.get("title", "")
                if not title or title in labelled_titles:
                    continue
                candidates.append({
                    "title": title,
                    "source": row.get("platform", ""),
                    "region": region,
                })
        candidates.sort(key=lambda row: (row["region"], row["source"], row["title"]))
        selected = candidates[: args.limit]
        pool_size = len(candidates)
        prefix = "H"
        sheet_name, manifest_name = "holdout_labels.csv", "holdout_manifest.json"

    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "title", "source", "region", "label", "notes"])
        writer.writeheader()
        for index, row in enumerate(selected, start=1):
            writer.writerow({
                "id": f"{prefix}{index:03d}",
                "title": row["title"],
                "source": row["source"],
                "region": row["region"],
                "label": "",
                "notes": "",
            })

    manifest = {
        "generated": date.today().isoformat(),
        "sheet": sheet_name,
        "rows": len(selected),
        "pool": pool_size,
        "labelled_rows_reserved": len(labelled_titles),
        "categories": ["VULN", "MALWARE", "RESEARCH", "OTHER"],
        "by_source": {
            source: sum(1 for row in selected if row["source"] == source)
            for source in sorted({row["source"] for row in selected})
        },
    }
    (DATA / manifest_name).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"pool {pool_size}  selected {len(selected)}  labels reserved {len(labelled_titles)}")
    print(f"by source {manifest['by_source']}")
    print(f"-> {target.relative_to(ROOT)}（label 欄留空）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
