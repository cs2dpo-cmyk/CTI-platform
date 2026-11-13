"""Merge the re-labelled disputed rows back into the main sheet.

Refuses to run until every disputed row has a valid label, so a half-filled
sheet cannot silently overwrite good data. The previous sheet is backed up.

    ./.venv/Scripts/python.exe tools/apply_relabel.py --round 2
"""

from __future__ import annotations

import argparse
import csv
import io
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
LABELS = {"VULN", "MALWARE", "RESEARCH", "OTHER"}


def read(path: Path) -> list[dict[str, str]]:
    with io.open(path, encoding="utf-8-sig", newline="") as handle:
        return [{k.strip(): (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--round", type=int, default=2)
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    suffix = "" if args.round == 1 else "2"
    source = DATA / f"relabel{suffix}_labels.csv"
    target = DATA / f"holdout{suffix}_labels.csv"
    if not source.exists():
        print(f"找不到 {source.relative_to(ROOT)}，請先執行 tools/make_relabel.py")
        return 2

    relabelled = read(source)
    invalid = [row["id"] for row in relabelled if row["label"].upper() not in LABELS]
    if invalid:
        print(f"還有 {len(invalid)} 列沒有有效標籤：{', '.join(invalid[:10])} …")
        return 2

    shutil.copyfile(target, target.with_name(target.stem + "_pre_relabel.csv"))
    updates = {row["id"]: row for row in relabelled}

    rows = read(target)
    changed = 0
    for row in rows:
        update = updates.get(row["id"])
        if not update:
            continue
        if row["label"] != update["label"].upper():
            changed += 1
        row["label"] = update["label"].upper()
        row["notes"] = "relabel: " + (update.get("notes") or "")

    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "title", "source", "region", "label", "notes"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"merged {len(relabelled)} rows | changed {changed} | backup -> {target.stem}_pre_relabel.csv")
    print("下一步：tools/eval_round2.py 與 tools/make_eval_doc.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
