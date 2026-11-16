"""Read the CVSS snapshot: scores for CVEs no article put a number on.

The snapshot exists because news copy often says "critical" without the score.
It is a fallback, never an override: a score the article stated wins, because it
can be traced back to that headline.

Refresh with tools/refresh_cvss.py; the file is data/cvss.json.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
PATH = DATA / "cvss.json"


@lru_cache(maxsize=1)
def _payload() -> dict:
    if not PATH.exists():
        return {"generated": "", "source": "", "scores": {}}
    try:
        return json.loads(PATH.read_text(encoding="utf-8"))
    except ValueError:
        return {"generated": "", "source": "", "scores": {}}


def all_scores() -> dict[str, float]:
    return {cve: float(entry["score"]) for cve, entry in (_payload().get("scores") or {}).items()}


def score_for(cves: list[str] | str | None) -> float | None:
    """Highest score among these CVEs, or None when the snapshot has nothing."""
    if not cves:
        return None
    keys = [cves] if isinstance(cves, str) else list(cves)
    scores = all_scores()
    values = [scores[key.upper()] for key in keys if key.upper() in scores]
    return max(values) if values else None


def version_for(cve: str) -> str | None:
    entry = (_payload().get("scores") or {}).get(cve.upper())
    return entry.get("version") if entry else None


def meta() -> dict:
    payload = _payload()
    return {
        "generated": payload.get("generated", ""),
        "source": payload.get("source", ""),
        "count": len(payload.get("scores") or {}),
    }


def reset() -> None:
    """Drop the cache (tests change the file)."""
    _payload.cache_clear()
