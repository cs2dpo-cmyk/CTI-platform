"""CISA KEV lookup (Known Exploited Vulnerabilities).

The snapshot in data/kev_ids.json was taken from
https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json
on 2026-11-10. A KEV entry is the strongest available statement that a
vulnerability is being exploited, so patch priority treats it as "act now".
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

SNAPSHOT = Path(__file__).resolve().parent.parent / "data" / "kev_ids.json"
FULL = Path(__file__).resolve().parent.parent / "data" / "kev_full.json"


@lru_cache(maxsize=1)
def _ids() -> frozenset[str]:
    try:
        payload = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        return frozenset(item.upper() for item in payload.get("ids", []))
    except (OSError, ValueError):
        return frozenset()


def is_exploited(cve: str) -> bool:
    return cve.upper() in _ids()


def snapshot_size() -> int:
    return len(_ids())


@lru_cache(maxsize=1)
def full() -> dict[str, dict]:
    """Every KEV entry with its metadata (added date, ransomware use, vendor).

    kev_ids.json is enough for "is this exploited"; this richer snapshot exists
    so the gap view can say what the corpus never saw and when it was added.
    """
    try:
        payload = json.loads(FULL.read_text(encoding="utf-8"))
        return payload.get("vulnerabilities") or {}
    except (OSError, ValueError):
        return {}


def ransomware_use(cve: str) -> str:
    return (full().get(cve.upper()) or {}).get("ransomware", "Unknown")
