#!/usr/bin/env python3
"""Score services/classify.py against the hand-labelled gold set.

Also reports the accuracy of the *previous* cluster -> meta-category mapping so
the improvement is measurable rather than asserted.
"""
from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from services import classify  # noqa: E402  (path is set up above)

DATA = ROOT / "data"
ORDER = ["VULN", "MALWARE", "RESEARCH", "OTHER"]
GOLD_CODE = {"V": "VULN", "M": "MALWARE", "R": "RESEARCH", "O": "OTHER"}


def read_rows(path: Path) -> list[dict[str, str]]:
    with io.open(path, encoding="utf-8-sig", newline="") as handle:
        return [{k.strip(): (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def load() -> list[dict[str, str]]:
    gold = {row["title"]: GOLD_CODE[row["gold"]] for row in read_rows(DATA / "gold_labels.csv")}
    meta = json.loads((DATA / "dataset_meta.json").read_text(encoding="utf-8"))
    mapping = meta.get("cluster_to_meta", {})
    overrides = {t.strip() for t in meta.get("research_overrides", [])}

    rows: list[dict[str, str]] = []
    for region in ("taiwan", "global"):
        path = DATA / f"{'Taiwan' if region == 'taiwan' else 'Global'}_security_dataset_with_dates.csv"
        for row in read_rows(path):
            title = row["title"]
            cluster = str(row.get("cluster", "")).strip()
            old = str(mapping.get(region, {}).get(cluster, "VULN")).upper()
            if title in overrides:
                old = "RESEARCH"
            category, reason = classify.classify(title, row.get("cleaned_text", ""))
            rows.append({
                "region": region, "cluster": cluster, "title": title,
                "gold": gold[title], "old": old, "new": category, "reason": reason,
            })
    return rows


def report(rows: list[dict[str, str]], key: str, title: str) -> None:
    correct = sum(1 for r in rows if r[key] == r["gold"])
    total = len(rows)
    print(f"\n=== {title}: {correct}/{total} = {correct / total:.1%} ===")
    print("gold\\pred " + "".join(f"{c:>9}" for c in ORDER))
    for g in ORDER:
        line = [f"{g:<9}"]
        for p in ORDER:
            line.append(f"{sum(1 for r in rows if r['gold'] == g and r[key] == p):>9}")
        print(" ".join(line))

    for category in ORDER:
        tp = sum(1 for r in rows if r["gold"] == category and r[key] == category)
        fp = sum(1 for r in rows if r["gold"] != category and r[key] == category)
        fn = sum(1 for r in rows if r["gold"] == category and r[key] != category)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        print(f"  {category:<9} P={precision:.2f} R={recall:.2f} n={tp + fn}")


def main() -> None:
    rows = load()
    report(rows, "old", "previous cluster -> meta-category mapping")
    report(rows, "new", "services/classify.py rules")
    wrong = [r for r in rows if r["new"] != r["gold"]]
    print(f"\n--- {len(wrong)} disagreements ---")
    for r in wrong:
        print(f"[{r['region'][:2]} {r['cluster']}] gold={r['gold']:<8} new={r['new']:<8} | {r['title'][:78]}")
        print(f"          reason: {r['reason']}")


if __name__ == "__main__":
    main()
