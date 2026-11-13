"""Write the EPSS-driven patch list.

Usage:
    ./.venv/Scripts/python.exe tools/patch_report.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services import dataset, epss, patch_priority  # noqa: E402

OUTPUT = ROOT / "data" / "patch_priority.csv"


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    records, _ = dataset.load_dataset()
    rows = [
        {
            "cves": record.evidence.get("cves") or [],
            "source": record.source,
            "published_at": record.published_at,
            "cvss": record.evidence.get("cvss"),
        }
        for record in records
    ]
    items = patch_priority.build(rows, epss.all_scores())
    summary = patch_priority.summarize(items)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(items[0].as_dict().keys()))
        writer.writeheader()
        for item in items:
            writer.writerow(item.as_dict())

    print(f"CVEs {summary['cves']}  exploited {summary['exploited']}  {summary['by_priority']}")
    print(f"{'CVE':<18}{'P':>3} {'EPSS':>6} {'CVSS':>5} {'ART':>4}  reason")
    for item in items[:20]:
        print(
            f"{item.cve:<18}{item.priority:>3} "
            f"{(item.epss or 0):>6.2f} {(item.cvss or 0):>5.1f} {item.articles:>4}  {item.reason}"
        )
    print(f"\n-> {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
