"""Build a re-labelling sheet for the disputed rows.

After the guide gained an explicit rule table for the contested article types,
the disputed rows are re-annotated from scratch. The sheet deliberately omits
both the earlier labels and the model's answer: the point is to test whether the
clarified rules converge, not to revisit the old argument.

    ./.venv/Scripts/python.exe tools/make_relabel.py --round 2
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FIELDS = ["id", "title", "source", "region", "label", "notes"]


def read(path: Path) -> list[dict[str, str]]:
    with io.open(path, encoding="utf-8-sig", newline="") as handle:
        return [{k.strip(): (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--round", type=int, default=2)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    suffix = "" if args.round == 1 else "2"
    disputes = read(DATA / f"holdout{suffix}_disputes.csv")
    labels = {row["id"]: row for row in read(DATA / f"holdout{suffix}_labels.csv")}

    target = DATA / f"relabel{suffix}_labels.csv"
    if target.exists() and not args.force:
        print(f"{target.relative_to(ROOT)} 已存在（{len(read(target))} 列），要重建請加 --force")
        return 0

    rows = []
    for dispute in disputes:
        source = labels.get(dispute["id"], {})
        rows.append({
            "id": dispute["id"],
            "title": dispute["title"],
            "source": source.get("source", ""),
            "region": source.get("region", ""),
            "label": "",
            "notes": "",
        })

    for path in (target, target.with_name(target.stem + "_b.csv")):
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)

    print(f"disputed rows {len(rows)}")
    print(f"-> {target.relative_to(ROOT)} 與 {target.stem}_b.csv（兩個獨立標註者）")
    print("欄位刻意不含舊標籤與模型答案，避免被前一次的結論錨定。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
