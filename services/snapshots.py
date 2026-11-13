"""Provenance for every data snapshot the API depends on.

Numbers that move without explanation are worse than no numbers: a reviewer has
to be able to ask "as of when?" and get an answer from the API itself. Each
snapshot file records when it was produced; data/snapshots.json records where it
came from. Entry counts are computed from the files, never stored, so they
cannot drift.
"""

from __future__ import annotations

import json
from datetime import date
from functools import lru_cache
from pathlib import Path

REGISTRY = Path(__file__).resolve().parent.parent / "data" / "snapshots.json"


@lru_cache(maxsize=1)
def _registry() -> dict:
    try:
        return json.loads(REGISTRY.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _entries(name: str) -> int | None:
    from services import assets, epss, kev

    if name == "epss":
        return len(epss.all_scores())
    if name == "kev":
        return kev.snapshot_size()
    if name == "assets":
        return len(assets.load())
    return None


def describe() -> dict:
    """{name: {generated, source, entries}} for every registered snapshot."""
    out: dict[str, dict] = {}
    for name, meta in _registry().items():
        out[name] = {
            "generated": meta.get("generated"),
            "source": meta.get("source"),
            "entries": _entries(name),
        }
    return out


def as_of() -> str:
    """The oldest snapshot date: the point in time the whole response is valid.

    Using the oldest (not the newest) is deliberate - a KEV list from last week
    makes the answer no fresher than that, whatever EPSS says.
    """
    dates = [meta.get("generated") for meta in _registry().values() if meta.get("generated")]
    if not dates:
        return date.today().isoformat()
    return min(dates)


def staleness_days() -> int | None:
    try:
        oldest = date.fromisoformat(as_of())
    except ValueError:
        return None
    return (date.today() - oldest).days
