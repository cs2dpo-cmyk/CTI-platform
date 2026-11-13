"""Retune the corpus risk weights against CISA KEV, and test whether EPSS helps.

The product scores a corpus row with a fixed weighted sum (severity, exploit,
exposure, CVE corroboration). Those weights were chosen by hand. This script
asks two questions with proper cross-validation, using KEV as the label:

   1. Is there a weighting (or a small model) that separates KEV from non-KEV
      better than the hand-tuned one and better than a plain CVSS sort?
   2. Does adding EPSS - the exploit-prediction score - improve it?

Everything is stdlib-only, so the numbers are reproducible on a machine with no
scientific Python installed.

Usage:
    ./.venv/Scripts/python.exe tools/tune_weights.py --kev .tmp/kev.json --epss .tmp/epss.json
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services import dataset, risk_engine  # noqa: E402

FEATURES = ("severity", "exploit", "exposure", "corroboration")
CURRENT_WEIGHTS = {"severity": 0.50, "exploit": 0.30, "exposure": 0.12, "corroboration": 0.08}
REPORT_PATH = ROOT / "data" / "tuning_report.json"


def load_kev(path: Path) -> set[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {item["cveID"].upper() for item in payload["vulnerabilities"]}


def load_epss(path: Path) -> dict[str, float]:
    return {k.upper(): float(v) for k, v in json.loads(path.read_text(encoding="utf-8")).items()}


def build_rows(kev: set[str], epss: dict[str, float]) -> list[dict]:
    records, _ = dataset.load_dataset()
    rows = []
    for record in records:
        result = risk_engine.score_seed_record(record.as_seed())
        if result is None:
            continue
        cves = record.evidence.get("cves") or []
        if not cves:
            continue
        values = {factor.key: factor.normalized for factor in result.factors}
        rows.append(
            {
                "title": record.title,
                "score": result.score,
                "features": [values.get(key, 0.0) for key in FEATURES],  # exploit == EPSS when known
                "epss": max((epss.get(cve.upper(), 0.0) for cve in cves), default=0.0),
                "label": any(cve.upper() in kev for cve in cves),
            }
        )
    return rows


def auc(scores: list[float], labels: list[bool]) -> float:
    positives = [s for s, y in zip(scores, labels) if y]
    negatives = [s for s, y in zip(scores, labels) if not y]
    if not positives or not negatives:
        return float("nan")
    wins = 0.0
    for p in positives:
        for n in negatives:
            if p > n:
                wins += 1
            elif p == n:
                wins += 0.5
    return wins / (len(positives) * len(negatives))


def weighted(features: list[float], weights: list[float]) -> float:
    return sum(w * x for w, x in zip(weights, features))


def stratified_folds(labels: list[bool], k: int, rng: random.Random) -> list[list[int]]:
    pos = [i for i, y in enumerate(labels) if y]
    neg = [i for i, y in enumerate(labels) if not y]
    rng.shuffle(pos)
    rng.shuffle(neg)
    folds = [[] for _ in range(k)]
    for group in (pos, neg):
        for index, item in enumerate(group):
            folds[index % k].append(item)
    return folds


def fit_logistic(
    matrix: list[list[float]], labels: list[bool], iterations: int = 900, lr: float = 0.25, l2: float = 1e-3
) -> tuple[list[float], list[float]]:
    n = len(matrix[0])
    mean = [sum(row[j] for row in matrix) / len(matrix) for j in range(n)]
    std = []
    for j in range(n):
        var = sum((row[j] - mean[j]) ** 2 for row in matrix) / len(matrix)
        std.append(math.sqrt(var) or 1.0)
    normalized = [[(row[j] - mean[j]) / std[j] for j in range(n)] for row in matrix]

    weights = [0.0] * n
    bias = 0.0
    for _ in range(iterations):
        grad = [0.0] * n
        grad_bias = 0.0
        for row, label in zip(normalized, labels):
            z = bias + sum(w * x for w, x in zip(weights, row))
            pred = 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, z))))
            error = pred - (1.0 if label else 0.0)
            for j in range(n):
                grad[j] += error * row[j]
            grad_bias += error
        scale = 1.0 / len(normalized)
        for j in range(n):
            weights[j] -= lr * (grad[j] * scale + l2 * weights[j])
        bias -= lr * grad_bias * scale
    return weights, mean, std


def predict_logistic(row: list[float], weights: list[float], mean: list[float], std: list[float]) -> float:
    z = sum(w * ((x - m) / s) for w, x, m, s in zip(weights, row, mean, std))
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, z))))


def search_weights(
    matrix: list[list[float]], labels: list[bool], rng: random.Random, samples: int = 4000
) -> list[float]:
    best, best_auc = None, -1.0
    n = len(matrix[0])
    for _ in range(samples):
        raw = [rng.expovariate(1.0) for _ in range(n)]
        total = sum(raw) or 1.0
        weights = [value / total for value in raw]
        score = auc([weighted(row, weights) for row in matrix], labels)
        if score > best_auc:
            best, best_auc = weights, score
    return best or [1.0 / n] * n


def cross_validate(rows: list[dict], repeats: int = 10, folds: int = 5, seed: int = 7) -> dict:
    labels = [row["label"] for row in rows]
    rng = random.Random(seed)
    results = {
        "baseline": [], "cvss": [], "epss_only": [], "logistic": [], "logistic_epss": [],
        "weights": [], "weights_epss": [],
    }
    current = [CURRENT_WEIGHTS[key] for key in FEATURES]

    for _ in range(repeats):
        for test_idx in stratified_folds(labels, folds, rng):
            train_idx = [i for i in range(len(rows)) if i not in test_idx]
            train = [rows[i] for i in train_idx]
            test = [rows[i] for i in test_idx]
            test_labels = [row["label"] for row in test]

            results["baseline"].append(
                auc([weighted(row["features"], current) for row in test], test_labels)
            )
            results["cvss"].append(
                auc([row["features"][0] for row in test], test_labels)  # severity ~ cvss/10
            )
            results["epss_only"].append(auc([row["epss"] for row in test], test_labels))

            train_matrix = [row["features"] for row in train]
            train_epss = [row["features"] + [row["epss"]] for row in train]
            train_labels = [row["label"] for row in train]

            w, m, s = fit_logistic(train_matrix, train_labels)
            results["logistic"].append(
                auc([predict_logistic(row["features"], w, m, s) for row in test], test_labels)
            )
            w2, m2, s2 = fit_logistic(train_epss, train_labels)
            results["logistic_epss"].append(
                auc([predict_logistic(row["features"] + [row["epss"]], w2, m2, s2) for row in test], test_labels)
            )

            fitted = search_weights(train_matrix, train_labels, random.Random(seed))
            results["weights"].append(
                auc([weighted(row["features"], fitted) for row in test], test_labels)
            )
            fitted_epss = search_weights(
                [row["features"] + [row["epss"]] for row in train], train_labels, random.Random(seed + 1)
            )
            results["weights_epss"].append(
                auc([weighted(row["features"] + [row["epss"]], fitted_epss) for row in test], test_labels)
            )
    return results


def statistics_stdev(values: list[float]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    return math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))


def summarize(values: list[float]) -> dict:
    values = [v for v in values if not math.isnan(v)]
    if not values:
        return {"mean": None, "std": None}
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / len(values)
    return {"mean": round(mean, 3), "std": round(math.sqrt(var), 3), "n": len(values)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kev", type=Path, required=True)
    parser.add_argument("--epss", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=10)
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    kev = load_kev(args.kev)
    epss = load_epss(args.epss)
    rows = build_rows(kev, epss)
    positives = sum(1 for row in rows if row["label"])

    raw = cross_validate(rows, repeats=args.repeats)
    report = {
        "rows": len(rows),
        "positives": positives,
        "base_rate": round(positives / len(rows), 3),
        "cv": {name: summarize(values) for name, values in raw.items()},
    }

    # Weights fitted on everything, for a human-readable proposal.
    matrix = [row["features"] for row in rows]
    labels = [row["label"] for row in rows]
    fitted = search_weights(matrix, labels, random.Random(11))
    fitted_epss = search_weights([row["features"] + [row["epss"]] for row in rows], labels, random.Random(12))
    report["proposed_weights"] = dict(zip(FEATURES, [round(w, 3) for w in fitted]))
    report["proposed_weights_with_epss"] = dict(zip(list(FEATURES) + ["epss"], [round(w, 3) for w in fitted_epss]))
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"rows {len(rows)}  positives {positives}  base rate {report['base_rate']:.2f}")
    print(f"epss coverage: {sum(1 for row in rows if row['epss'] > 0)}/{len(rows)}")
    print(f"{'model':<16}{'mean AUC':>10}{'std':>8}")
    for name, stats in report["cv"].items():
        print(f"{name:<16}{stats['mean']:>10.3f}{stats['std']:>8.3f}")
    print()
    print("feature std:", {key: round(statistics_stdev([row["features"][i] for row in rows]), 3)
                          for i, key in enumerate(FEATURES)})
    print("weights fitted on all rows:", report["proposed_weights"])
    print("with epss:", report["proposed_weights_with_epss"])
    print(f"\nreport -> {REPORT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
