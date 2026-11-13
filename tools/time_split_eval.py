"""Backtest classification and ranking on a later time window.

    ./.venv/Scripts/python.exe tools/time_split_eval.py
    ./.venv/Scripts/python.exe tools/time_split_eval.py --cutoff 2026-10-01

Reports, per window: labelled rows, classification accuracy, and - for rows that
name a CVE - KEV hit rate, precision@10 and AUC of the ranking.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services import classify, dataset, risk_engine, time_split  # noqa: E402
from services.kev import is_exploited  # noqa: E402

DATA = ROOT / "data"
REPORT = DATA / "time_split_report.json"
GOLD_CODE = {"V": "VULN", "M": "MALWARE", "R": "RESEARCH", "O": "OTHER"}


def read_rows(path: Path) -> list[dict[str, str]]:
    with io.open(path, encoding="utf-8-sig", newline="") as handle:
        return [{k.strip(): (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def load_labels() -> dict[str, str]:
    labels: dict[str, str] = {}
    for row in read_rows(DATA / "gold_labels.csv"):
        labels[row["title"]] = GOLD_CODE.get(row["gold"], "")
    for row in read_rows(DATA / "holdout_labels.csv"):
        if row.get("label"):
            labels[row["title"]] = row["label"].upper()
    return labels


def auc(scored: list[tuple[float, bool]]) -> float:
    positives = [s for s, y in scored if y]
    negatives = [s for s, y in scored if not y]
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


def evaluate(rows: list, labels: dict[str, str]) -> dict:
    labelled = [row for row in rows if labels.get(row.title)]
    correct = sum(1 for row in labelled if classify.classify(row.title)[0] == labels[row.title])

    scored = []
    for row in rows:
        result = risk_engine.score_seed_record(row.as_seed())
        cves = row.evidence.get("cves") or []
        if result is None or not cves:
            continue
        scored.append(
            {
                "score": result.score,
                "kev": any(is_exploited(cve) for cve in cves),
            }
        )

    ranked = sorted(scored, key=lambda item: -item["score"])
    kev_hits = sum(1 for item in scored if item["kev"])
    return {
        "rows": len(rows),
        "labelled": len(labelled),
        "accuracy": round(correct / len(labelled), 3) if labelled else None,
        "cve_rows": len(scored),
        "kev_rows": kev_hits,
        "base_rate": round(kev_hits / len(scored), 3) if scored else None,
        "precision_at_10": round(sum(1 for i in ranked[:10] if i["kev"]) / min(10, len(ranked)), 3)
        if ranked else None,
        "auc": auc([(item["score"], item["kev"]) for item in scored]) if scored else None,
        "categories": dict(Counter(classify.classify(row.title)[0] for row in rows)),
        "months": time_split.monthly_counts(rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cutoff", type=str, default=None, help="YYYY-MM-DD")
    parser.add_argument("--min-test", type=int, default=60)
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    records, _ = dataset.load_dataset()
    if args.cutoff:
        cutoff = date.fromisoformat(args.cutoff)
    else:
        cutoff = time_split.suggest_cutoff(records, min_test=args.min_test)
        if cutoff is None:
            print("沒有可用的切點（訓練或測試窗口會太小）")
            return 2

    development, test = time_split.split(records, cutoff)
    labels = load_labels()
    dev_report = evaluate(development.rows, labels)
    test_report = evaluate(test.rows, labels)

    report = {
        "cutoff": cutoff.isoformat(),
        "development": time_split.describe(development) | dev_report,
        "test": time_split.describe(test) | test_report,
        "note": (
            "EPSS 與 KEV 都是 2026-11 的快照：分類退化可以直接比較，"
            "但『當時的利用機率』無法還原，排序分數屬於現況回測。"
        ),
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"cutoff {cutoff}  (development < cutoff <= test)")
    print(f"{'':<14}{'rows':>6}{'labelled':>10}{'accuracy':>10}{'cve':>6}{'kev':>6}{'P@10':>7}{'AUC':>7}")
    for name, stats in (("development", report["development"]), ("test", report["test"])):
        acc = "n/a" if stats["accuracy"] is None else f"{stats['accuracy']:.2f}"
        p10 = "n/a" if stats["precision_at_10"] is None else f"{stats['precision_at_10']:.2f}"
        auc_value = "n/a" if stats["auc"] is None else f"{stats['auc']:.2f}"
        print(
            f"{name:<14}{stats['rows']:>6}{stats['labelled']:>10}{acc:>10}"
            f"{stats['cve_rows']:>6}{stats['kev_rows']:>6}{p10:>7}{auc_value:>7}"
        )
    print(f"\n-> {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
