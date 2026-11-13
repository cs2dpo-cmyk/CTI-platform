"""List every row where the two annotators or the classifier disagree.

Usage:
    ./.venv/Scripts/python.exe tools/make_disputes.py

Writes data/holdout_disputes.csv with A, B, the classifier's answer and an
empty "final" column for adjudication.
"""

from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services import classify  # noqa: E402

DATA = ROOT / "data"
OUT = DATA / "holdout_disputes.csv"


def read(path: Path) -> dict[str, dict[str, str]]:
    with io.open(path, encoding="utf-8-sig", newline="") as handle:
        return {row["id"]: row for row in csv.DictReader(handle)}


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--round", type=int, default=1, choices=[1, 2])
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    suffix = "2" if args.round == 2 else ""
    first = read(DATA / f"holdout{suffix}_labels.csv")
    second = read(DATA / f"holdout{suffix}_labels_b.csv")

    rows = []
    for key, row in first.items():
        a = (row.get("label") or "").strip().upper()
        b = (second.get(key) or {}).get("label", "").strip().upper()
        predicted = classify.classify(row["title"])[0]
        if a == b == predicted:
            continue
        rows.append({
            "id": key,
            "title": row["title"],
            "A": a,
            "B": b,
            "model": predicted,
            "A_eq_B": "yes" if a == b else "no",
            "final": "",
            "notes": "",
        })

    rows.sort(key=lambda row: (row["A_eq_B"], row["id"]))
    out = DATA / (f"holdout{suffix}_disputes.csv")
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["id", "title", "A", "B", "model", "A_eq_B", "final", "notes"]
        )
        writer.writeheader()
        writer.writerows(rows)

    both_agree = sum(1 for row in rows if row["A_eq_B"] == "yes")
    print(f"disputes {len(rows)}  (A=B but model differs: {both_agree}, A!=B: {len(rows) - both_agree})")
    print(f"-> {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
