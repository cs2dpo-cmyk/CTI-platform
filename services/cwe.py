"""Read the CWE snapshot: which weakness type each CVE belongs to.

CWE is a defect taxonomy, not a news taxonomy: it says "this is a command
injection", not "this story is a patch advisory". It is used here to confirm a
CVE is a weakness record and to give the assessment a precise, quotable type.

Refresh with tools/refresh_cwe.py; the file is data/cwe.json.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "data" / "cwe.json"


@lru_cache(maxsize=1)
def _payload() -> dict:
    if not PATH.exists():
        return {"generated": "", "source": "", "cves": {}}
    try:
        return json.loads(PATH.read_text(encoding="utf-8"))
    except ValueError:
        return {"generated": "", "source": "", "cves": {}}


def all_cves() -> dict[str, list[dict]]:
    return _payload().get("cves") or {}


def for_cve(cve: str) -> list[dict]:
    return list(all_cves().get(cve.upper()) or [])


def labels(cve: str) -> list[str]:
    """Short "CWE-78 OS Command Injection" strings for a UI chip."""
    out = []
    for entry in for_cve(cve):
        name = entry.get("name") or ""
        out.append(f"{entry.get('id', '')} {name}".strip())
    return out


def meta() -> dict:
    payload = _payload()
    entries = payload.get("cves") or {}
    return {
        "generated": payload.get("generated", ""),
        "source": payload.get("source", ""),
        "cves": len(entries),
        "with_cwe": sum(1 for value in entries.values() if value),
    }


def reset() -> None:
    _payload.cache_clear()
