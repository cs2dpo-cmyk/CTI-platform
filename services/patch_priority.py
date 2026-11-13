"""Turn the corpus into a patch list ordered by exploitation likelihood.

The corpus is news, not an asset inventory, so the unit of work is a CVE: every
article that names one contributes to that CVE's record (EPSS, highest CVSS
seen, how widely it was reported, who reported it).

Banding follows the published guidance rather than a hand-picked weight:

    P1  24h   listed in CISA KEV - exploitation is confirmed
    P2   7d   EPSS >= 0.10 (the usual "worth scheduling" threshold), or
              CVSS >= 9.0 when no EPSS is available
    P3  30d   everything else

EPSS is a probability, so the bands are deliberately coarse: a CVE at 0.11 and
one at 0.40 both belong on the same patch cycle.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from services.kev import is_exploited

EPSS_ACT = 0.10
CVSS_ACT = 9.0
SLA = {"P1": "24 小時", "P2": "7 天", "P3": "30 天"}
BAND_LABEL = {
    "P1": "EPSS 或 KEV 顯示已／極可能被利用",
    "P2": "利用機率中等或嚴重度極高",
    "P3": "觀測即可，納入例行更新",
}


@dataclass
class PatchItem:
    cve: str
    epss: float | None
    cvss: float | None
    exploited: bool
    articles: int = 0
    sources: set[str] = field(default_factory=set)
    first_seen: date | None = None
    priority: str = "P3"

    @property
    def sla(self) -> str:
        return SLA[self.priority]

    @property
    def reason(self) -> str:
        if self.exploited:
            return "列入 CISA KEV，已被實際利用"
        if self.epss is not None and self.epss >= EPSS_ACT:
            return f"EPSS {self.epss:.0%} ≥ {EPSS_ACT:.0%}"
        if self.cvss is not None and self.cvss >= CVSS_ACT:
            return f"CVSS {self.cvss:.1f} ≥ {CVSS_ACT:.0f}"
        if self.epss is not None:
            return f"EPSS {self.epss:.0%}，低於排程門檻"
        return "無 EPSS／CVSS 資料，僅供觀測"

    def as_dict(self) -> dict:
        return {
            "cve": self.cve,
            "priority": self.priority,
            "sla": self.sla,
            "epss": None if self.epss is None else round(self.epss, 4),
            "cvss": None if self.cvss is None else round(self.cvss, 1),
            "exploited": self.exploited,
            "articles": self.articles,
            "sources": sorted(self.sources),
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "reason": self.reason,
        }


def _band(item: PatchItem) -> str:
    if item.exploited:
        return "P1"
    if item.epss is not None and item.epss >= EPSS_ACT:
        return "P2"
    if item.cvss is not None and item.cvss >= CVSS_ACT:
        return "P2"
    return "P3"


def build(rows: list[dict], epss: dict[str, float]) -> list[PatchItem]:
    """Aggregate per-CVE records from corpus rows.

    Each row must provide: cves (list), source, published_at (date), cvss.
    """
    table: dict[str, PatchItem] = {}
    for row in rows:
        for cve in row.get("cves") or []:
            key = cve.upper()
            item = table.get(key)
            if item is None:
                item = PatchItem(cve=key, epss=epss.get(key), cvss=row.get("cvss"), exploited=is_exploited(key))
                table[key] = item
            item.articles += 1
            if row.get("source"):
                item.sources.add(row["source"])
            published = row.get("published_at")
            if published and (item.first_seen is None or published < item.first_seen):
                item.first_seen = published
            cvss = row.get("cvss")
            if cvss is not None and (item.cvss is None or cvss > item.cvss):
                item.cvss = cvss

    for item in table.values():
        item.priority = _band(item)

    order = {"P1": 0, "P2": 1, "P3": 2}
    return sorted(
        table.values(),
        key=lambda i: (order[i.priority], -(i.epss or 0.0), -(i.cvss or 0.0), i.cve),
    )


def summarize(items: list[PatchItem]) -> dict:
    counts = {"P1": 0, "P2": 0, "P3": 0}
    for item in items:
        counts[item.priority] += 1
    return {
        "cves": len(items),
        "by_priority": counts,
        "exploited": sum(1 for item in items if item.exploited),
        "bands": BAND_LABEL,
    }
