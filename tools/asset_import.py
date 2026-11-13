"""Validate an asset inventory CSV before it replaces data/assets.csv.

Usage:
    ./.venv/Scripts/python.exe tools/asset_import.py --file my_assets.csv
    ./.venv/Scripts/python.exe tools/asset_import.py --file my_assets.csv --apply
"""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services import assets, dataset, epss, patch_priority  # noqa: E402

TARGET = ROOT / "data" / "assets.csv"
REQUIRED = ("asset_id", "name", "exposure", "products")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, required=True)
    parser.add_argument("--apply", action="store_true", help="驗證後覆蓋 data/assets.csv")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    with args.file.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [column for column in REQUIRED if column not in (reader.fieldnames or [])]
        if missing:
            print(f"缺少欄位：{', '.join(missing)}")
            return 2
        rows = list(reader)

    parsed = assets.parse_rows(rows)
    skipped = len(rows) - len(parsed)
    public = sum(1 for asset in parsed if asset.exposure == assets.PUBLIC)
    print(f"rows {len(rows)}  accepted {len(parsed)}  skipped {skipped}  public {public}  internal {len(parsed) - public}")

    records, _ = dataset.load_dataset()
    corpus_rows = [
        {
            "cves": record.evidence.get("cves") or [],
            "source": record.source,
            "published_at": record.published_at,
            "cvss": record.evidence.get("cvss"),
            "title": record.title,
            "public_facing": record.evidence.get("exposure") == "public",
        }
        for record in records
    ]
    items = patch_priority.build(corpus_rows, epss.all_scores())
    inventory_hits = sum(1 for item in items if item.exposure_source == "inventory")
    covered = sum(1 for item in items if item.exposure != "unknown")
    print(f"CVEs {len(items)}  matched by inventory {inventory_hits}  exposure known {covered} ({covered / len(items):.0%})")

    if args.apply:
        shutil.copyfile(args.file, TARGET)
        print(f"applied -> {TARGET.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
