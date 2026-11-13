"""Turn the scraped historical rows into loader-compatible CSVs.

The app reads data/*_security_dataset_with_dates.csv. This imports the stratified
history into the same shape, dropping any article whose URL already exists so the
canonical 200-row sample is never duplicated.

    ./.venv/Scripts/python.exe tools/import_expanded.py
"""

from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SOURCE = DATA / "expanded" / "historical.csv"
TARGETS = {
    "taiwan": DATA / "Taiwan_expanded_dataset_with_dates.csv",
    "global": DATA / "Global_expanded_dataset_with_dates.csv",
}
FIELDS = ["platform", "title", "cleaned_text", "cluster", "published_at", "date_source", "source_url", "date_note"]
TAIWAN_SOURCES = {"TWCERT", "iThome", "網管人"}


def read(path: Path) -> list[dict[str, str]]:
    with io.open(path, encoding="utf-8-sig", newline="") as handle:
        return [{k.strip(): (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    existing_urls = set()
    for name in ("Taiwan_security_dataset_with_dates.csv", "Global_security_dataset_with_dates.csv"):
        existing_urls.update(row["source_url"] for row in read(DATA / name) if row.get("source_url"))

    rows = read(SOURCE)
    kept: dict[str, list[dict[str, str]]] = {"taiwan": [], "global": []}
    skipped = 0
    for row in rows:
        url = row.get("url", "")
        if not url or url in existing_urls:
            skipped += 1
            continue
        region = "taiwan" if row.get("source") in TAIWAN_SOURCES else "global"
        kept[region].append({
            "platform": row.get("source", ""),
            "title": row.get("title", ""),
            "cleaned_text": "",
            "cluster": "3",   # not part of the K-Means run; kept in its own bucket
            "published_at": row.get("date", ""),
            "date_source": "scraped",
            "source_url": url,
            "date_note": "",
        })
        existing_urls.add(url)

    for region, path in TARGETS.items():
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(sorted(kept[region], key=lambda row: row["published_at"]))

    print(f"source {len(rows)} | skipped {skipped} (duplicate url) | taiwan {len(kept['taiwan'])} | global {len(kept['global'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
