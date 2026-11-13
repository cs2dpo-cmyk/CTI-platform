"""Score services/classify.py on the held-out annotation sheet.

Unlike tools/eval_classifier.py (which measures the same 100 rows the rules were
tuned on), this only counts rows that were never used during development. Run it
after filling data/holdout_labels.csv.

    ./.venv/Scripts/python.exe tools/eval_holdout.py
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services import classify  # noqa: E402

LABELS = ["VULN", "MALWARE", "RESEARCH", "OTHER"]
SHEET = ROOT / "data" / "holdout_labels.csv"



def read_labels(path: Path) -> list[dict[str, str]]:
    with io.open(path, encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return [row for row in rows if (row.get("label") or "").strip()]


def per_class(gold: list[str], predicted: list[str]) -> dict[str, dict[str, float]]:
    result = {}
    for label in LABELS:
        tp = sum(1 for g, p in zip(gold, predicted) if g == label and p == label)
        fp = sum(1 for g, p in zip(gold, predicted) if g != label and p == label)
        fn = sum(1 for g, p in zip(gold, predicted) if g == label and p != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        result[label] = {
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1, 3),
            "support": sum(1 for g in gold if g == label),
        }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sheet", type=Path, default=SHEET)
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    sheet = args.sheet.resolve()
    rows = read_labels(sheet)
    if not rows:
        print(f"{sheet.relative_to(ROOT)} 還沒有任何標註。")
        print("請依 docs/annotation-guide.md 填入 label 欄（VULN / MALWARE / RESEARCH / OTHER）後再執行。")
        return 0

    gold = [row["label"].strip().upper() for row in rows]
    predicted = [classify.classify(row["title"])[0] for row in rows]
    correct = sum(1 for g, p in zip(gold, predicted) if g == p)
    accuracy = correct / len(rows)

    majority_label = Counter(gold).most_common(1)[0][0]
    majority_accuracy = sum(1 for g in gold if g == majority_label) / len(rows)

    report = {
        "rows": len(rows),
        "accuracy": round(accuracy, 3),
        "correct": correct,
        "majority_baseline": {"label": majority_label, "accuracy": round(majority_accuracy, 3)},
        "per_class": per_class(gold, predicted),
        "confusion": {
            g: {p: sum(1 for x, y in zip(gold, predicted) if x == g and y == p) for p in LABELS}
            for g in LABELS
        },
    }
    report_path = sheet.with_name(sheet.stem + "_report.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"held-out rows {len(rows)}")
    print(f"accuracy {correct}/{len(rows)} = {accuracy:.1%}")
    print(f"majority baseline ({majority_label}) = {majority_accuracy:.1%}")
    print(f"lift {accuracy - majority_accuracy:+.1%}")
    print(f"{'class':<10}{'prec':>7}{'rec':>7}{'f1':>7}{'n':>5}")
    for label in LABELS:
        stats = report["per_class"][label]
        print(f"{label:<10}{stats['precision']:>7.2f}{stats['recall']:>7.2f}{stats['f1']:>7.2f}{stats['support']:>5}")
    print(f"\n-> {report_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
