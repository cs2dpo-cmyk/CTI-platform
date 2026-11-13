"""Simulate a fifth class for digests (weekly recaps, bulletins, roundups).

Nothing is changed in the product; this answers one question: if those articles
had their own class, would the annotators stop disagreeing?

The simulation maps any title that reads like a roundup to DIGEST, for both
annotators and for the classifier (a post-hoc rule), then recomputes agreement
and accuracy. It reports how much of the disagreement the class absorbs, which
is the only honest way to read the inflated kappa.
"""

from __future__ import annotations

import csv
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services import agreement, classify  # noqa: E402

DATA = ROOT / "data"
DIGEST = re.compile(
    r"weekly recap|threatsday|bulletin|top threats|recap|roundup|this week|"
    r"週報|摘要|彙整|一週|本周|本週",
    re.IGNORECASE,
)
CLASSES = ["VULN", "MALWARE", "RESEARCH", "OTHER", "DIGEST"]


def read(path: Path) -> list[dict[str, str]]:
    with io.open(path, encoding="utf-8-sig", newline="") as handle:
        return [{k.strip(): (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def as_digest(title: str, label: str, target: str = "DIGEST") -> str:
    return target if DIGEST.search(title or "") else label


def score(rows: list[dict], labels: dict[str, str], target: str | None) -> dict:
    gold = [as_digest(row["title"], labels[row["id"]], target) if target else labels[row["id"]] for row in rows]
    pred = []
    for row in rows:
        if target and DIGEST.search(row["title"]):
            pred.append(target)
        else:
            pred.append(classify.classify(row["title"])[0])
    correct = sum(1 for g, p in zip(gold, pred) if g == p)
    return {"accuracy": round(correct / len(rows), 3), "correct": correct, "rows": len(rows)}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    a = {r["id"]: r["label"].strip().upper() for r in read(DATA / "holdout2_labels_round1.csv")}
    b = {r["id"]: r["label"].strip().upper() for r in read(DATA / "holdout2_labels_b.csv")}
    titles = {r["id"]: r["title"] for r in read(DATA / "holdout2_labels.csv")}
    ids = sorted(set(a) & set(b))
    rows = [{"id": key, "title": titles.get(key, "")} for key in ids]

    raw_disputes = [key for key in ids if a[key] != b[key]]
    digest_rows = [key for key in ids if DIGEST.search(titles.get(key, ""))]

    report = {
        "rows": len(ids),
        "digest_rows": len(digest_rows),
        "raw_disputes": len(raw_disputes),
        "raw_disputes_on_digest_rows": sum(1 for key in raw_disputes if key in digest_rows),
        "four_class": {
            "kappa": round(agreement.cohen_kappa([a[k] for k in ids], [b[k] for k in ids]), 3),
            "annotator_a": score(rows, a, None),
            "annotator_b": score(rows, b, None),
        },
        "five_class": {
            "kappa": round(
                agreement.cohen_kappa(
                    [as_digest(titles.get(k, ""), a[k], "DIGEST") for k in ids],
                    [as_digest(titles.get(k, ""), b[k], "DIGEST") for k in ids],
                ),
                3,
            ),
            "annotator_a": score(rows, a, "DIGEST"),
            "annotator_b": score(rows, b, "DIGEST"),
        },
        "digest_as_other": {
            "kappa": round(
                agreement.cohen_kappa(
                    [as_digest(titles.get(k, ""), a[k], "OTHER") for k in ids],
                    [as_digest(titles.get(k, ""), b[k], "OTHER") for k in ids],
                ),
                3,
            ),
            "annotator_a": score(rows, a, "OTHER"),
            "annotator_b": score(rows, b, "OTHER"),
        },
    }
    (DATA / "digest_class_simulation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
