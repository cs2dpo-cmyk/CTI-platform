#!/usr/bin/env python3
"""Build data/gold_labels.csv from a hand-labelled read of the 100 headlines.

The labels were assigned by reading each headline and deciding what a CISO
would call it, *before* any rule was written. They are keyed by (region,
cluster, position-in-cluster) so a row cannot silently drift: the script
asserts that every cluster string matches the number of rows it labels.
"""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# V = vulnerability/patch advisory, M = malware & active attack,
# R = research/governance/policy, O = other (industry/product news, not a threat)
LABELS = {
    "taiwan": {
        "0": "RMMMMMM",
        "1": "MRMMRMRMMROOOROOVOMORRMMOOO",
        "2": "VVRVVMMVRRVMMVVV",
    },
    "global": {
        "0": "VMRRVRVOMMMMRMMVVRMMVVMMMVMMVMRRMMM",
        "1": "ORVVVM",
        "2": "RMMRMRMMM",
    },
}


def read_rows(path: Path) -> list[dict[str, str]]:
    with io.open(path, encoding="utf-8-sig", newline="") as handle:
        return [{k.strip(): (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def main() -> None:
    meta = json.loads((DATA / "dataset_meta.json").read_text(encoding="utf-8"))
    files = {"taiwan": DATA / "Taiwan_security_dataset_with_dates.csv",
             "global": DATA / "Global_security_dataset_with_dates.csv"}

    out: list[dict[str, str]] = []
    for region, path in files.items():
        rows = read_rows(path)
        seen: dict[str, int] = {}
        for row in rows:
            cluster = str(row.get("cluster", "")).strip()
            key = LABELS[region][cluster]
            index = seen.get(cluster, 0)
            seen[cluster] = index + 1
            if index >= len(key):
                raise SystemExit(f"{region} C{cluster}: more rows than labels")
            out.append({
                "region": region,
                "cluster": cluster,
                "position": str(index + 1),
                "title": row["title"],
                "gold": key[index],
            })
        for cluster, count in seen.items():
            if count != len(LABELS[region][cluster]):
                raise SystemExit(f"{region} C{cluster}: {count} rows vs {len(LABELS[region][cluster])} labels")

    target = DATA / "gold_labels.csv"
    with io.open(target, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["region", "cluster", "position", "title", "gold"])
        writer.writeheader()
        writer.writerows(out)

    counts: dict[str, int] = {}
    for row in out:
        counts[row["gold"]] = counts.get(row["gold"], 0) + 1
    print(f"wrote {target} ({len(out)} rows): {counts}")


if __name__ == "__main__":
    main()
