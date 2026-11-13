"""Report inter-annotator agreement between two filled annotation sheets.

    ./.venv/Scripts/python.exe tools/label_agreement.py \
        --a data/holdout_labels.csv --b data/holdout_labels_b.csv

Both files are expected to use the same id column and one of VULN / MALWARE /
RESEARCH / OTHER in the label column.
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services import agreement  # noqa: E402

LABELS = ["VULN", "MALWARE", "RESEARCH", "OTHER"]


def read_labels(path: Path) -> dict[str, str]:
    with io.open(path, encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return {
        row["id"].strip(): (row.get("label") or "").strip().upper()
        for row in rows
        if (row.get("label") or "").strip()
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--a", type=Path, required=True)
    parser.add_argument("--b", type=Path, required=True)
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    first = read_labels(args.a)
    second = read_labels(args.b)
    shared = sorted(set(first) & set(second))
    if not shared:
        print("兩份檔案沒有共同的已標註 id")
        return 2

    left = [first[key] for key in shared]
    right = [second[key] for key in shared]
    stats = agreement.describe(left, right, LABELS)

    print(f"共同已標註 {stats['rows']} 列（A {len(first)} / B {len(second)}）")
    print(f"一致 {stats['agree']} 列，同意率 {stats['agreement']:.1%}")
    print(f"Cohen's kappa {stats['kappa']:.3f}")
    print("各類別 kappa:", stats["per_class_kappa"])
    print("\n混淆矩陣（列=A，欄=B）:")
    header = "        " + "".join(f"{label:>9}" for label in LABELS)
    print(header)
    for label in LABELS:
        row = "".join(f"{stats['confusion'][label][other]:>9}" for other in LABELS)
        print(f"{label:>8}{row}")

    disagreements = [(key, first[key], second[key]) for key in shared if first[key] != second[key]]
    if disagreements:
        print(f"\n不一致 {len(disagreements)} 列（前 10）:")
        for key, a, b in disagreements[:10]:
            print(f"  {key}: A={a} B={b}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
