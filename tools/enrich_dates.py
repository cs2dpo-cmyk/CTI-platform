"""Enrich the research CSVs with real publication dates.

Sources, all authoritative and machine-readable:

* The Hacker News — Blogger JSON feed (``published`` timestamp per post).
* TWCERT/CC      — RSS feed + year listing (``<time>`` per item).
* iThome         — news listing pages (``p.post-at`` per item).

Rows that cannot be matched keep the deterministic row-order backfill used by
the platform and are marked ``estimated`` so the dashboard can disclose it.

Usage:
    python tools/enrich_dates.py                # writes *_with_dates.csv
    python tools/enrich_dates.py --report       # only print the match report
"""

from __future__ import annotations

import argparse
import csv
import html
import io
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import date, timedelta
from difflib import SequenceMatcher
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

TAIWAN_CSV = "Taiwan_security_dataset_cleaned.csv"
GLOBAL_CSV = "Global_security_dataset_cleaned.csv"
TAIWAN_OUT = "Taiwan_security_dataset_with_dates.csv"
GLOBAL_OUT = "Global_security_dataset_with_dates.csv"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

WINDOW_START = date(2026, 8, 1)
WINDOW_END = date(2026, 11, 6)
FALLBACK_ANCHOR = date(2026, 10, 30)

# Pairs of characters that appear interchangeably between feeds and the CSV.
_NORMALISE_MAP = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-"})


@dataclass
class Hit:
    published: date
    url: str
    source: str


@dataclass
class Report:
    matched: dict[str, Hit] = field(default_factory=dict)
    unmatched: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# HTTP
# --------------------------------------------------------------------------- #


def http_get(url: str, *, retries: int = 3) -> bytes:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=40) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError) as exc:  # pragma: no cover
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"failed to fetch {url}: {last}")


def _https(url: str) -> str:
    """Publishers we scrape all serve TLS; upgrade the Blogger http links."""
    if url.startswith("http://") and any(host in url for host in (
        "thehackernews.com", "twcert.org.tw", "ithome.com.tw"
    )):
        return "https://" + url[len("http://"):]
    return url


# --------------------------------------------------------------------------- #
# Title normalisation
# --------------------------------------------------------------------------- #


def normalise(title: str) -> str:
    text = html.unescape(title or "").translate(_NORMALISE_MAP)
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[\s\u3000]+", "", text)
    return text.strip().lower()


# --------------------------------------------------------------------------- #
# Collectors
# --------------------------------------------------------------------------- #


def collect_thn() -> dict[str, Hit]:
    hits: dict[str, Hit] = {}
    start = 1
    page = 0
    while True:
        url = (
            "https://thehackernews.com/feeds/posts/default?alt=json"
            f"&max-results=60&start-index={start}"
            f"&published-min={WINDOW_START.isoformat()}T00:00:00%2B05:30"
            f"&published-max={WINDOW_END.isoformat()}T00:00:00%2B05:30"
        )
        try:
            payload = json.loads(http_get(url))
        except RuntimeError as exc:
            print(f"  ! THN page {page + 1}: {exc}", file=sys.stderr)
            break
        entries = payload.get("feed", {}).get("entry", [])
        if not entries:
            break
        for entry in entries:
            title = entry.get("title", {}).get("$t", "")
            stamp = entry.get("published", {}).get("$t", "")
            link = ""
            for candidate in entry.get("link", []):
                if candidate.get("rel") == "alternate":
                    link = candidate.get("href", "")
                    break
            if not title or not stamp:
                continue
            hits.setdefault(
                normalise(title),
                Hit(published=date.fromisoformat(stamp[:10]), url=_https(link), source="thehackernews.com"),
            )
        page += 1
        start += 60
        print(f"  THN page {page}: +{len(entries)} posts (total {len(hits)})")
        if len(entries) < 60:
            break
        time.sleep(0.4)
    return hits


def collect_twcert() -> dict[str, Hit]:
    hits: dict[str, Hit] = {}
    feeds = [
        "https://www.twcert.org.tw/tw/rss-104-1.xml",
        "https://www.twcert.org.tw/tw/lp-104-1.html",
        "https://www.twcert.org.tw/tw/lp-104-1-xCat-21.html",
    ]
    for url in feeds:
        try:
            body = http_get(url).decode("utf-8", "replace")
        except RuntimeError as exc:
            print(f"  ! TWCERT {url}: {exc}", file=sys.stderr)
            continue

        for item in re.findall(r"<item>(.*?)</item>", body, re.S):
            title = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>", item, re.S) or re.search(
                r"<title>(.*?)</title>", item, re.S
            )
            stamp = re.search(r"<pubDate>(.*?)</pubDate>", item, re.S)
            link = re.search(r"<link>(.*?)</link>", item, re.S)
            if not title or not stamp:
                continue
            parsed = _parse_rss_date(stamp.group(1).strip())
            if not parsed:
                continue
            hits.setdefault(
                normalise(title.group(1)),
                Hit(published=parsed, url=(link.group(1).strip() if link else url), source="twcert.org.tw"),
            )

        for href, title, stamp in re.findall(
            r'<li><a href="([^"]+)"><span class="num">\d+</span>(.*?)<time>(\d{4}-\d{2}-\d{2})</time></a></li>',
            body,
            re.S,
        ):
            hits.setdefault(
                normalise(title),
                Hit(
                    published=date.fromisoformat(stamp),
                    url=_https("https://www.twcert.org.tw" + href),
                    source="twcert.org.tw",
                ),
            )
        time.sleep(0.3)
    print(f"  TWCERT: {len(hits)} items")
    return hits


def collect_ithome(max_pages: int = 45) -> dict[str, Hit]:
    hits: dict[str, Hit] = {}
    for page in range(1, max_pages + 1):
        url = f"https://www.ithome.com.tw/news?page={page}"
        try:
            body = http_get(url).decode("utf-8", "replace")
        except RuntimeError as exc:
            print(f"  ! iThome page {page}: {exc}", file=sys.stderr)
            break

        found = re.findall(
            r'<p class="title"><a href="([^"]+)">(.*?)</a>\s*</p>.*?<p class="post-at">\s*(\d{4}-\d{2}-\d{2})',
            body,
            re.S,
        )
        if not found:
            break
        oldest: date | None = None
        for href, title, stamp in found:
            published = date.fromisoformat(stamp)
            oldest = published if oldest is None else min(oldest, published)
            hits.setdefault(
                normalise(re.sub(r"<[^>]+>", "", title)),
                Hit(published=published, url=_https("https://www.ithome.com.tw" + href), source="ithome.com.tw"),
            )
        if page % 5 == 0 or oldest is None:
            print(f"  iThome page {page}: {len(found)} items (oldest {oldest})")
        if oldest and oldest < WINDOW_START:
            break
        time.sleep(0.3)
    print(f"  iThome: {len(hits)} items")
    return hits


def _parse_rss_date(raw: str) -> date | None:
    for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%d"):
        try:
            from datetime import datetime

            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    match = re.search(r"(\d{1,2})\s+(\w{3})\s+(\d{4})", raw)
    if match:
        from datetime import datetime

        try:
            return datetime.strptime(" ".join(match.groups()), "%d %b %Y").date()
        except ValueError:
            return None
    return None


# --------------------------------------------------------------------------- #
# Matching
# --------------------------------------------------------------------------- #


def match(title: str, pool: dict[str, Hit]) -> tuple[Hit | None, float]:
    key = normalise(title)
    if key in pool:
        return pool[key], 1.0

    # Feeds occasionally trim the trailing clause; accept a very close variant.
    best: tuple[Hit | None, float] = (None, 0.0)
    for candidate, hit in pool.items():
        if abs(len(candidate) - len(key)) > 25:
            continue
        score = SequenceMatcher(None, key, candidate).ratio()
        if score > best[1]:
            best = (hit, score)
    if best[1] >= 0.94:
        return best[0], best[1]
    return None, best[1]


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with io.open(path, encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = [{key: (value or "") for key, value in row.items()} for row in reader]
        return list(reader.fieldnames or []), rows


def enrich(
    filename: str,
    pool: dict[str, Hit],
    anchor: date,
    *,
    report_only: bool,
) -> Report:
    path = DATA_DIR / filename
    fields, rows = read_csv(path)
    report = Report()
    output: list[dict[str, str]] = []

    for index, row in enumerate(rows):
        hit, score = match(row.get("title", ""), pool)
        estimated = anchor - timedelta(days=index)
        if hit:
            published = hit.published
            source = hit.source
            note = "" if score >= 0.999 else f"標題近似比對 {score:.2f}"
            url = hit.url
            report.matched[row["title"]] = hit
        else:
            published = estimated
            source = "estimated"
            note = "來源未收錄，依擷取順序推估"
            url = ""
            report.unmatched.append(row["title"])

        output.append(
            {
                **row,
                "published_at": published.isoformat(),
                "date_source": source,
                "source_url": url,
                "date_note": note,
            }
        )

    out_fields = fields + ["published_at", "date_source", "source_url", "date_note"]
    dates = [row["published_at"] for row in output]
    matched = len(report.matched)
    estimated = len(report.unmatched)

    print(f"\n[{filename}]")
    print(f"  rows          : {len(rows)}")
    print(f"  real dates    : {matched}  ({matched / max(len(rows), 1) * 100:.0f}%)")
    print(f"  estimated     : {estimated}")
    if dates:
        print(f"  span          : {min(dates)} → {max(dates)}")
    sources: dict[str, int] = {}
    for row in output:
        sources[row["date_source"]] = sources.get(row["date_source"], 0) + 1
    print(f"  by source     : {sources}")

    if report_only:
        return report

    out_path = DATA_DIR / filename.replace("_cleaned.csv", "_with_dates.csv")
    with io.open(out_path, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=out_fields)
        writer.writeheader()
        writer.writerows(output)
    print(f"  written       : {out_path.name} ({out_path.stat().st_size:,} bytes)")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="store_true", help="只輸出比對報告，不寫檔")
    args = parser.parse_args()

    print("Collecting publication dates…")
    pools: dict[str, dict[str, Hit]] = {}
    print("[The Hacker News]")
    pools.update(collect_thn())
    print("[TWCERT/CC]")
    twcert = collect_twcert()
    print("[iThome]")
    ithome = collect_ithome()

    taiwan_pool = {**twcert, **ithome}
    print(f"  taiwan pool: {len(taiwan_pool)} items")

    global_report = enrich(GLOBAL_CSV, pools, FALLBACK_ANCHOR, report_only=args.report)
    taiwan_report = enrich(TAIWAN_CSV, taiwan_pool, FALLBACK_ANCHOR, report_only=args.report)

    total_unmatched = len(global_report.unmatched) + len(taiwan_report.unmatched)
    if total_unmatched:
        print(f"\nUnmatched titles ({total_unmatched}):")
        for title in (global_report.unmatched + taiwan_report.unmatched)[:20]:
            print("  -", title[:90])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
