"""Which CVEs also appear in Taiwan-sourced reporting?

The corpus is about 79% international, so raw volume measures the sources, not
local relevance. A CVE that a Taiwanese source also wrote about is a stronger
signal for a Taiwan-based CISO: it reached local advisories and local operations
teams. The index is small (tens of CVEs), so it is built per request from the
threats table rather than cached.
"""

from __future__ import annotations

import json
from typing import Any

TAIWAN = "taiwan"

__all__ = ["build_index", "from_db", "hits_for"]


def build_index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """cve -> {"articles", "sources", "titles"} for Taiwan-sourced rows only.

    Each row must provide cves (list[str]), region, and optionally source/title.
    """
    table: dict[str, dict[str, Any]] = {}
    for row in rows:
        if (row.get("region") or "").lower() != TAIWAN:
            continue
        for cve in row.get("cves") or []:
            key = str(cve).upper()
            if not key:
                continue
            entry = table.setdefault(key, {"articles": 0, "sources": [], "titles": []})
            entry["articles"] += 1
            source = row.get("source")
            if source and source not in entry["sources"]:
                entry["sources"].append(source)
            title = row.get("title")
            if title and len(entry["titles"]) < 3:
                entry["titles"].append(title)
    return table


def from_db(db: Any) -> dict[str, dict[str, Any]]:
    """Same index, built from the stored rows (used by the list endpoint)."""
    from sqlalchemy import select

    import database

    rows = [
        {"cves": _parse(ids), "source": source, "title": title, "region": region}
        for ids, source, title, region in db.execute(
            select(
                database.Threat.cve_ids,
                database.Threat.source,
                database.Threat.title,
                database.Threat.region,
            )
        ).all()
    ]
    return build_index(rows)


def _parse(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str) and raw:
        try:
            return json.loads(raw)
        except ValueError:
            return []
    return []


def hits_for(cves: list[str] | None, index: dict[str, dict[str, Any]]) -> int:
    """How many of these CVEs a Taiwan source also reported."""
    return sum(1 for cve in cves or [] if str(cve).upper() in index)
