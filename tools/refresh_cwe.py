"""Collect the CWE weakness type for every CVE in the corpus.

CWE describes *what kind of defect* a vulnerability is (command injection, auth
bypass, deserialisation...). It cannot tell a patch advisory from an attack
story - it is a defect taxonomy, not a news taxonomy - but it does two useful
things: it confirms the CVE really is a weakness record, and it gives the
assessment a precise, quotable type instead of a vague category.

The names ship inside the CVE 5.x record (problemTypes[].descriptions[]), so no
separate MITRE catalogue download is needed.

    ./.venv/Scripts/python.exe tools/refresh_cwe.py
    ./.venv/Scripts/python.exe tools/refresh_cwe.py --limit 20
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DATA = ROOT / "data"
OUT = DATA / "cwe.json"
API = "https://cve.circl.lu/api/cve/"
USER_AGENT = "cti-platform/1.0 (academic research)"
PACE = 0.6
PREFIX = re.compile(r"^\s*CWE-\d+\s*[:：-]?\s*", re.IGNORECASE)


def corpus_cves() -> list[str]:
    from services import dataset

    records, _ = dataset.load_dataset()
    found: set[str] = set()
    for record in records:
        for cve in record.evidence.get("cves") or []:
            found.add(str(cve).upper())
    return sorted(found)


def cwes_from_record(record: dict) -> list[dict]:
    """[{id, name}] from a CVE 5.x record, CNA first then ADP."""
    containers = record.get("containers") or {}
    found: dict[str, str] = {}
    for container in [containers.get("cna") or {}] + list(containers.get("adp") or []):
        for problem in container.get("problemTypes") or []:
            for desc in problem.get("descriptions") or []:
                cwe = str(desc.get("cweId") or "").upper()
                if not cwe.startswith("CWE-"):
                    continue
                name = PREFIX.sub("", str(desc.get("description") or "")).strip()
                if name and cwe not in found:
                    found[cwe] = name
    return [{"id": key, "name": value} for key, value in sorted(found.items())]


def fetch(cve: str) -> list[dict] | None:
    request = urllib.request.Request(API + cve, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError):
        return None
    return cwes_from_record(payload) if isinstance(payload, dict) else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    existing: dict[str, list] = {}
    if OUT.exists():
        existing = (json.loads(OUT.read_text(encoding="utf-8")).get("cves") or {})

    targets = corpus_cves()
    todo = [cve for cve in targets if args.refresh or cve not in existing]
    if args.limit:
        todo = todo[: args.limit]
    print(f"corpus CVEs {len(targets)} | cached {len(existing)} | to fetch {len(todo)}", flush=True)

    def save() -> None:
        payload = {
            "generated": date.today().isoformat(),
            "source": "https://cve.circl.lu/api/cve (CVE.org problemTypes)",
            "cves": dict(sorted(existing.items())),
        }
        OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    found_count = 0
    for index, cve in enumerate(todo, start=1):
        cwes = fetch(cve)
        if cwes is not None:
            existing[cve] = cwes
            if cwes:
                found_count += 1
        if index % 20 == 0 or index == len(todo):
            save()
            print(f"  {index}/{len(todo)}  with CWE {found_count}", flush=True)
        time.sleep(PACE)

    save()
    with_cwe = sum(1 for value in existing.values() if value)
    print(f"-> {OUT.relative_to(ROOT)}  CVEs {len(existing)}  with CWE {with_cwe}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
