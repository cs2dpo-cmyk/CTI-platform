"""Write the EPSS + exposure patch list, and show what exposure changes.

Usage:
    ./.venv/Scripts/python.exe tools/patch_report.py            # with exposure
    ./.venv/Scripts/python.exe tools/patch_report.py --compare  # before/after
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services import dataset, epss, patch_priority  # noqa: E402

OUTPUT = ROOT / "data" / "patch_priority.csv"


def load_rows() -> list[dict]:
    records, _ = dataset.load_dataset()
    return [
        {
            "cves": record.evidence.get("cves") or [],
            "source": record.source,
            "published_at": record.published_at,
            "cvss": record.evidence.get("cvss"),
            "title": record.title,
            "public_facing": record.evidence.get("exposure") == "public",
        }
        for record in records
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compare", action="store_true", help="只印有無曝險的差異")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    rows = load_rows()
    scores = epss.all_scores()
    items = patch_priority.build(rows, scores, use_exposure=True)
    baseline = {item.cve: item.priority for item in patch_priority.build(rows, scores, use_exposure=False)}
    summary = patch_priority.summarize(items)

    print(f"CVEs {summary['cves']}  exploited {summary['exploited']}  exposed {summary['exposed']}")
    print(f"bands {summary['by_priority']}  exposure sources {summary['exposure_sources']}")

    if args.compare:
        moves = Counter(
            (baseline[item.cve], item.priority) for item in items if baseline[item.cve] != item.priority
        )
        print("\nband changes (without exposure -> with exposure):")
        for (before, after), count in sorted(moves.items()):
            print(f"  {before} -> {after}: {count}")
        unchanged = sum(1 for item in items if baseline[item.cve] == item.priority)
        print(f"  unchanged: {unchanged}")
        return 0

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(items[0].as_dict().keys()))
        writer.writeheader()
        for item in items:
            writer.writerow(item.as_dict())

    print(f"{'CVE':<18}{'P':>3} {'EPSS':>6} {'CVSS':>5} {'曝險':>8} {'ART':>4}  reason")
    for item in items[:20]:
        print(
            f"{item.cve:<18}{item.priority:>3} {(item.epss or 0):>6.2f} {(item.cvss or 0):>5.1f} "
            f"{item.exposure:>8} {item.articles:>4}  {item.reason}"
        )
    print(f"\n-> {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
