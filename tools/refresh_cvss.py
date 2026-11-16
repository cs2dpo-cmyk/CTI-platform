"""Fetch CVSS base scores for corpus CVEs that no article stated.

News headlines rarely print a numeric score, so half the patch list had no
severity signal at all and fell back to EPSS alone. This tool fills only those
gaps from the CVE.org record (served by the CIRCL mirror) and records where each
number came from.

Article-derived scores are never overwritten: they are traceable to a specific
headline, while the snapshot is only a fallback for "nobody said".

    ./.venv/Scripts/python.exe tools/refresh_cvss.py                # 補齊缺的
    ./.venv/Scripts/python.exe tools/refresh_cvss.py --limit 20     # 先試 20 筆
    ./.venv/Scripts/python.exe tools/refresh_cvss.py --refresh      # 全部重抓
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DATA = ROOT / "data"
OUT = DATA / "cvss.json"
API = "https://cve.circl.lu/api/cve/"
USER_AGENT = "cti-platform/1.0 (academic research)"
PACE = 1.1  # seconds between requests; the mirror is not a bulk endpoint

# CVSS v3.1 first: it is what modern advisories publish. v2 is last resort.
VERSION_ORDER = ("cvssV3_1", "cvssV4_0", "cvssV3_0", "cvssV2_0")


def corpus_cves(*, missing_only: bool = False) -> list[str]:
    """Every CVE in the corpus, or only those no article gave a score for."""
    from services import dataset

    records, _ = dataset.load_dataset()
    found: set[str] = set()
    covered: set[str] = set()
    for record in records:
        cves = [str(cve).upper() for cve in record.evidence.get("cves") or []]
        found.update(cves)
        if record.evidence.get("cvss") is not None:
            covered.update(cves)
    return sorted(found - covered if missing_only else found)


def _score_from_metrics(metrics: object) -> tuple[float, str] | None:
    """Pick the best score out of a CVE 5.x metrics list."""
    if not isinstance(metrics, list):
        return None
    for key in VERSION_ORDER:
        for entry in metrics:
            block = entry.get(key) if isinstance(entry, dict) else None
            if not isinstance(block, dict):
                continue
            score = block.get("baseScore")
            if isinstance(score, (int, float)) and 0.0 <= float(score) <= 10.0:
                return float(score), block.get("version") or key.replace("cvssV", "").replace("_", ".")
    return None


def score_from_record(record: dict) -> tuple[float, str] | None:
    """Read the score out of a CVE 5.x record, CNA metrics first, then ADP."""
    containers = record.get("containers") or {}
    candidates = [containers.get("cna") or {}]
    candidates.extend(containers.get("adp") or [])
    for container in candidates:
        found = _score_from_metrics(container.get("metrics"))
        if found:
            return found
    # Older shapes: a flat cvss block, or a top-level metrics list.
    legacy = record.get("cvss")
    if isinstance(legacy, dict) and isinstance(legacy.get("baseScore"), (int, float)):
        return float(legacy["baseScore"]), str(legacy.get("version") or "2.0")
    return _score_from_metrics(record.get("metrics"))


def fetch(cve: str) -> tuple[float, str] | None:
    request = urllib.request.Request(API + cve, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    return score_from_record(payload)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0, help="本次最多抓幾筆（0=全部）")
    parser.add_argument("--refresh", action="store_true", help="忽略既有快照，全部重抓")
    parser.add_argument("--dry-run", action="store_true", help="只列出要抓的 CVE")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    existing: dict[str, dict] = {}
    if OUT.exists():
        payload = json.loads(OUT.read_text(encoding="utf-8"))
        existing = payload.get("scores") or {}

    targets = corpus_cves(missing_only=True)
    todo = [cve for cve in targets if args.refresh or cve not in existing]
    if args.limit:
        todo = todo[: args.limit]
    print(f"corpus CVEs {len(targets)} | cached {len(existing)} | to fetch {len(todo)}")
    if args.dry_run:
        print(" ".join(todo[:40]))
        return 0

    fetched = 0
    failed: list[str] = []

    def save() -> None:
        """Persist after every batch so a slow or aborted run is not wasted."""
        payload = {
            "generated": date.today().isoformat(),
            "source": "https://cve.circl.lu/api/cve (CVE.org records)",
            "scores": dict(sorted(existing.items())),
        }
        OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    for index, cve in enumerate(todo, start=1):
        found = fetch(cve)
        if found:
            score, version = found
            existing[cve] = {
                "score": score,
                "version": version,
                "source": "cve.org",
                "fetched": date.today().isoformat(),
            }
            fetched += 1
        else:
            failed.append(cve)
        if index % 20 == 0 or index == len(todo):
            save()
            print(f"  {index}/{len(todo)}  ok {fetched}  miss {len(failed)}", flush=True)
        time.sleep(PACE)

    save()
    print(f"-> {OUT.relative_to(ROOT)}  scores {len(existing)}  fetched {fetched}  not found {len(failed)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
