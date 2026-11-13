"""Does the risk ranking put already-exploited vulnerabilities first?

CISA's KEV catalog is the ground truth: a vulnerability is either confirmed
exploited in the wild or it is not. The corpus only carries that label for rows
whose text names a CVE id, so the comparison is restricted to those rows.

Three rankings are compared on the same rows:

    model   risk_score from services.risk_engine (the product's ranking)
    cvss    the CVSS number quoted in the article (None -> 0)
    random  the base rate, which is what a ranking that adds nothing achieves

Usage:
    ./.venv/Scripts/python.exe tools/kev_precision.py --kev .tmp/kev.json
"""

from __future__ import annotations

import argparse
import json
import random
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DB_PATH = ROOT / "data" / "cti.db"
REPORT_PATH = ROOT / "data" / "kev_report.json"
KS = (5, 10, 20, 50)


def load_kev(path: Path) -> set[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {item["cveID"].upper() for item in payload["vulnerabilities"]}


def load_rows(db_path: Path) -> list[dict]:
    connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            "SELECT id, title, risk_score, priority, cve_ids, duplicate_of "
            "FROM threats WHERE risk_score IS NOT NULL"
        ).fetchall()
    finally:
        connection.close()
    result = []
    for row in rows:
        ids = json.loads(row[4]) if row[4] else []
        result.append(
            {
                "id": row[0],
                "title": row[1],
                "score": row[2],
                "priority": row[3],
                "cves": ids,
                "duplicate_of": row[5],
            }
        )
    return result


def load_cvss() -> dict[str, float]:
    """CVSS quoted in each article, keyed by title."""
    from services import dataset

    records, _ = dataset.load_dataset()
    result = {}
    for record in records:
        value = (record.evidence or {}).get("cvss")
        if value is not None:
            result[record.title] = float(value)
    return result


def auc(scored: list[dict], key: str) -> float:
    """Probability that a KEV row outranks a non-KEV row (ties count 0.5)."""
    positives = [row[key] for row in scored if row["kev"]]
    negatives = [row[key] for row in scored if not row["kev"]]
    if not positives or not negatives:
        return float("nan")
    wins = 0.0
    for high in positives:
        for low in negatives:
            if high > low:
                wins += 1
            elif high == low:
                wins += 0.5
    return round(wins / (len(positives) * len(negatives)), 3)


def precision_at(ranked: list[dict], k: int) -> float:
    if not ranked:
        return 0.0
    hits = sum(1 for row in ranked[:k] if row["kev"])
    return hits / min(k, len(ranked))


def random_baseline(rows: list[dict], k: int, trials: int = 500) -> float:
    hits = 0.0
    for _ in range(trials):
        sample = random.sample(rows, min(k, len(rows)))
        hits += sum(1 for row in sample if row["kev"]) / min(k, len(rows))
    return hits / trials


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--kev", type=Path, required=True)
    parser.add_argument("--include-duplicates", action="store_true")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    kev = load_kev(args.kev)
    rows = load_rows(args.db)
    if not args.include_duplicates:
        rows = [row for row in rows if not row["duplicate_of"]]
    for row in rows:
        row["kev"] = [cve for cve in row["cves"] if cve.upper() in kev]

    labelled = [row for row in rows if row["cves"]]
    base_rate = sum(1 for row in labelled if row["kev"]) / len(labelled)

    cvss = load_cvss()
    for row in labelled:
        row["cvss"] = cvss.get(row["title"], 0.0)

    rankings = {
        "model": sorted(labelled, key=lambda row: -row["score"]),
        "cvss": sorted(labelled, key=lambda row: -row["cvss"]),
    }

    report = {
        "kev_size": len(kev),
        "rows_scored": len(rows),
        "rows_with_cve": len(labelled),
        "rows_kev": sum(1 for row in labelled if row["kev"]),
        "base_rate": round(base_rate, 3),
        "precision": {},
        "random": {str(k): round(random_baseline(labelled, k), 3) for k in KS},
        "p1": {
            "count": sum(1 for row in labelled if row["priority"] == "P1"),
            "kev": sum(1 for row in labelled if row["priority"] == "P1" and row["kev"]),
        },
    }
    report["auc"] = {
        "model": auc(labelled, "score"),
        "cvss": auc(labelled, "cvss"),
    }
    for name, ranked in rankings.items():
        report["precision"][name] = {str(k): round(precision_at(ranked, k), 3) for k in KS}

    # Recall: of the KEV rows, how many does P1/P2 capture?
    kev_rows = [row for row in labelled if row["kev"]]
    p1 = sum(1 for row in kev_rows if row["priority"] == "P1")
    p12 = sum(1 for row in kev_rows if row["priority"] in ("P1", "P2"))
    report["recall"] = {
        "p1": round(p1 / len(kev_rows), 3),
        "p1_p2": round(p12 / len(kev_rows), 3),
    }

    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"KEV catalog            {report['kev_size']}")
    print(f"scored rows            {report['rows_scored']}")
    print(f"rows naming a CVE      {report['rows_with_cve']}")
    print(f"rows matching KEV      {report['rows_kev']}  (base rate {report['base_rate']:.2f})")
    print()
    header = f"{'k':>4} {'model':>7} {'cvss':>7} {'random':>7}"
    print(header)
    for k in KS:
        print(
            f"{k:>4} {report['precision']['model'][str(k)]:>7.2f} "
            f"{report['precision']['cvss'][str(k)]:>7.2f} {report['random'][str(k)]:>7.2f}"
        )
    print()
    print(f"AUC model {report['auc']['model']:.3f}  cvss {report['auc']['cvss']:.3f}")
    print(f"P1 rows {report['p1']['count']}  of which KEV {report['p1']['kev']}")
    print(f"recall  P1 {report['recall']['p1']:.2f}  P1+P2 {report['recall']['p1_p2']:.2f}")
    print(f"\nreport -> {REPORT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
