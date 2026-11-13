"""Build a month-stratified corpus for temporal analysis.

Sources with a deep archive (THN, TWCERT) supply the historical window; the
sources whose archive is shallow (iThome, 網管人) only supply the operational
window, because that is all they expose. Quotas are per month, not per source:
the month is the unit that keeps the time axis honest.

    ./.venv/Scripts/python.exe tools/build_stratified.py --dry-run
    ./.venv/Scripts/python.exe tools/build_stratified.py
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))



OUT = ROOT / "data" / "expanded"
THN_FEED = "https://thehackernews.com/feeds/posts/default?alt=json&max-results=150&start-index={index}"
THN_PAGE = 150
NETADMIN = "https://www.netadmin.com.tw/category/%e6%a5%ad%e7%95%8c%e5%8b%95%e6%85%8b/page/{page}/"


def collect_thn_archive(until: str, max_calls: int = 60) -> list[dict[str, str]]:
    """Walk the Blogger feed backwards until the month bucket is old enough."""
    from build_corpus import fetch

    items: list[dict[str, str]] = []
    for call in range(max_calls):
        index = 1 + call * THN_PAGE
        try:
            feed = json.loads(fetch(THN_FEED.format(index=index)))
        except Exception as error:
            print(f"  THN start-index {index} failed: {error}")
            break
        entries = feed.get("feed", {}).get("entry", [])
        if not entries:
            break
        oldest = ""
        for entry in entries:
            link = next((l["href"] for l in entry.get("link", []) if l.get("rel") == "alternate"), "")
            title = entry.get("title", {}).get("$t", "").strip()
            stamp = entry.get("published", {}).get("$t", "")[:10]
            if not (title and stamp):
                continue
            oldest = stamp
            items.append({
                "title": title,
                "url": link.replace("http://thehackernews.com", "https://thehackernews.com"),
                "date": stamp,
                "source": "THN",
                "lang": "en",
            })
        print(f"  THN start-index {index}: {len(entries)} entries, oldest {oldest}", flush=True)
        if oldest and oldest < until:
            break
        time.sleep(0.5)
    return items


def collect_netadmin(max_pages: int = 5) -> list[dict[str, str]]:
    """Only a few pages are exposed; enough for the operational window.

    Article URLs are numeric (/3474/), so the date has to come from the
    surrounding block rather than the link itself.
    """
    from bs4 import BeautifulSoup

    from build_corpus import fetch

    items: list[dict[str, str]] = []
    seen: set[str] = set()
    for page in range(1, max_pages + 1):
        try:
            html = fetch(NETADMIN.format(page=page))
        except Exception as error:
            print(f"  netadmin page {page} failed: {error}", flush=True)
            continue
        soup = BeautifulSoup(html, "html.parser")
        for anchor in soup.find_all("a", href=True):
            match = re.match(r"^https://www\.netadmin\.com\.tw/(\d+)/$", anchor["href"])
            if not match:
                continue
            title = anchor.get_text(" ", strip=True)
            if len(title) < 6 or anchor["href"] in seen:
                continue
            block = anchor.find_parent(["div", "li", "article", "section"]) or anchor
            found = re.search(r"20\d{2}-\d{2}-\d{2}", block.get_text(" ", strip=True))
            if not found:
                continue
            seen.add(anchor["href"])
            items.append({
                "title": title,
                "url": anchor["href"],
                "date": found.group(0),
                "source": "網管人",
                "lang": "zh",
            })
        time.sleep(0.8)
    return items


def bucket(items: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    seen: set[str] = set()
    for item in items:
        day = (item.get("date") or "").strip()
        if not re.match(r"\d{4}-\d{2}-\d{2}", day):
            continue
        if item["url"] in seen:
            continue
        seen.add(item["url"])
        grouped[day[:7]].append(item)
    return grouped


def pick(grouped: dict[str, list[dict]], source: str, per_month: int, months: list[str]) -> list[dict]:
    chosen = []
    for month in months:
        rows = [row for row in grouped.get(month, []) if row["source"] == source]
        rows.sort(key=lambda row: row["date"], reverse=True)
        chosen.extend(rows[:per_month])
    return chosen


def month_range(start: str, end: str) -> list[str]:
    year, month = int(start[:4]), int(start[5:7])
    out = []
    while f"{year:04d}-{month:02d}" <= end:
        out.append(f"{year:04d}-{month:02d}")
        month += 1
        if month > 12:
            year, month = year + 1, 1
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2024-01")
    parser.add_argument("--end", default="2026-11")
    parser.add_argument("--per-month", type=int, default=20)
    parser.add_argument("--thn-per-month", type=int, default=15)
    parser.add_argument("--twcert-per-month", type=int, default=5)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    months = month_range(args.start, args.end)
    print(f"months {len(months)} ({months[0]} .. {months[-1]})", flush=True)

    print("collecting THN archive ...", flush=True)
    thn = collect_thn_archive(until=f"{args.start}-01")
    print(f"  THN total {len(thn)}")

    print("collecting TWCERT blocks ...", flush=True)
    from build_corpus import collect_twcert
    twcert = collect_twcert(pages=40)
    print(f"  TWCERT total {len(twcert)}")

    print("collecting iThome ...", flush=True)
    from build_corpus import collect_ithome
    ithome = collect_ithome(limit=400, max_pages=50)
    print(f"  iThome total {len(ithome)}")

    print("collecting 網管人 ...", flush=True)
    netadmin = collect_netadmin(max_pages=5)
    print(f"  網管人 total {len(netadmin)}")

    grouped = bucket(thn + twcert + ithome + netadmin)
    historical = pick(grouped, "THN", args.thn_per_month, months) + pick(
        grouped, "TWCERT", args.twcert_per_month, months
    )

    recent = months[-3:]
    operational = []
    for source in ("THN", "TWCERT", "iThome", "網管人"):
        operational.extend(pick(grouped, source, 17, recent))

    manifest = {
        "generated": time.strftime("%Y-%m-%d"),
        "months": len(months),
        "historical_rows": len(historical),
        "operational_rows": len(operational),
        "operational_months": recent,
        "sources": {
            "THN": len(thn), "TWCERT": len(twcert),
            "iThome": len(ithome), "網管人": len(netadmin),
        },
        "quotas": {
            "historical_per_month": {"THN": args.thn_per_month, "TWCERT": args.twcert_per_month},
            "operational_per_source": 17,
        },
    }
    print(json.dumps(manifest, ensure_ascii=False, indent=2))

    if args.dry_run:
        return 0

    OUT.mkdir(parents=True, exist_ok=True)
    for name, rows in (("historical.csv", historical), ("operational.csv", operational)):
        with (OUT / name).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["title", "url", "date", "source", "lang"])
            writer.writeheader()
            writer.writerows(rows)
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"-> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
