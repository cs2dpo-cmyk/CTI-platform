"""EPSS lookup (Exploit Prediction Scoring System, FIRST).

EPSS estimates the probability that a CVE is exploited in the next 30 days. The
snapshot in data/epss.json was taken on 2026-11-13; refresh it by re-fetching

    https://api.first.org/data/v1/epss?cve=CVE-...,CVE-...

The score is used as the "exploit maturity" input when the article names a CVE,
because the wording-based heuristic ("已遭利用") says nothing about the CVEs the
article merely lists.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

SNAPSHOT = Path(__file__).resolve().parent.parent / "data" / "epss.json"


@lru_cache(maxsize=1)
def _scores() -> dict[str, float]:
    try:
        return {
            key.upper(): float(value)
            for key, value in json.loads(SNAPSHOT.read_text(encoding="utf-8")).items()
        }
    except (OSError, ValueError):
        return {}


def score_for(cves: list[str] | tuple[str, ...] | None) -> float | None:
    """Highest EPSS among the given CVEs, or None when none is scored.

    The maximum is deliberate: if any id in the article is likely to be
    exploited, the article is worth attention.
    """
    if not cves:
        return None
    values = [_scores().get(cve.upper()) for cve in cves]
    known = [value for value in values if value is not None]
    return max(known) if known else None
