"""Turn the corpus into a patch list ordered by exploitation and exposure.

The corpus is news, not an asset inventory, so the unit of work is a CVE: every
article that names one contributes to that CVE's record (EPSS, highest CVSS
seen, how widely it was reported, who reported it, whether it is internet-facing).

The band starts from published guidance and exposure shifts it one step:

    base  P1  CISA KEV (exploitation confirmed)
          P2  EPSS >= 0.10 or CVSS >= 9.0
          P3  everything else

    shift +1  an article or the product name says the system is internet-facing
          -1  the CVE is pinned to an internal asset in exposure_overrides.json
           0  no exposure signal (the common case in a news corpus)

KEV never shifts down: a confirmed-exploited vulnerability is patched now even
on an internal host. An absence of exposure data is not treated as "internal" -
the reason string says which it is, so a reviewer can tell the difference.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from services import exposure as exposure_ctx
from services.kev import is_exploited

EPSS_SCHEDULE = 0.10
EPSS_ACT = 0.50
CVSS_SCHEDULE = 9.0
SLA = {"P1": "24 小時", "P2": "7 天", "P3": "30 天"}


@dataclass
class PatchItem:
    cve: str
    epss: float | None
    cvss: float | None
    exploited: bool
    exposure: str = exposure_ctx.UNKNOWN
    exposure_source: str = "none"
    articles: int = 0
    sources: set[str] = field(default_factory=set)
    first_seen: date | None = None
    priority: str = "P3"

    @property
    def sla(self) -> str:
        return SLA[self.priority]

    @property
    def exposed(self) -> bool:
        return self.exposure == exposure_ctx.PUBLIC

    @property
    def reason(self) -> str:
        epss_txt = "—" if self.epss is None else f"{self.epss:.0%}"
        if self.exploited:
            base = "列入 CISA KEV，已被實際利用"
            if self.exposure == exposure_ctx.INTERNAL:
                return base + "（內部資產仍須 24 小時內處理）"
            return base
        signal = (
            f"EPSS {epss_txt} ≥ 10%"
            if (self.epss or 0) >= EPSS_SCHEDULE
            else f"CVSS {self.cvss:.1f} ≥ 9.0"
            if (self.cvss or 0) >= CVSS_SCHEDULE
            else f"EPSS {epss_txt}，低於排程門檻"
        )
        if self.exposed:
            return f"{signal}；對外曝險（{exposure_ctx.SOURCE_LABELS[self.exposure_source]}）→ 升一級"
        if self.exposure == exposure_ctx.INTERNAL:
            return f"{signal}；內網資產（人工指定）→ 降一級"
        return f"{signal}；未取得曝險資訊，維持原級"

    def as_dict(self) -> dict:
        return {
            "cve": self.cve,
            "priority": self.priority,
            "sla": self.sla,
            "epss": None if self.epss is None else round(self.epss, 4),
            "cvss": None if self.cvss is None else round(self.cvss, 1),
            "exploited": self.exploited,
            "exposure": self.exposure,
            "exposure_label": exposure_ctx.SOURCE_LABELS[self.exposure_source],
            "articles": self.articles,
            "sources": sorted(self.sources),
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "reason": self.reason,
        }


def _base_band(item: PatchItem) -> str:
    if item.exploited:
        return "P1"
    epss = item.epss or 0.0
    cvss = item.cvss or 0.0
    return "P2" if (epss >= EPSS_SCHEDULE or cvss >= CVSS_SCHEDULE) else "P3"


def _band(item: PatchItem, use_exposure: bool) -> str:
    base = _base_band(item)
    if not use_exposure or base == "P1":
        return base
    if item.exposed:
        return "P1" if base == "P2" else "P2"
    if item.exposure == exposure_ctx.INTERNAL:
        return "P3"
    return base


def build(rows: list[dict], epss: dict[str, float], use_exposure: bool = True) -> list[PatchItem]:
    """Aggregate per-CVE records from corpus rows.

    Each row must provide: cves, source, published_at, cvss, title, and
    public_facing (whether the article described the system as reachable).
    """
    table: dict[str, PatchItem] = {}
    titles: dict[str, list[str]] = {}
    public: dict[str, bool] = {}

    for row in rows:
        for cve in row.get("cves") or []:
            key = cve.upper()
            item = table.get(key)
            if item is None:
                item = PatchItem(
                    cve=key,
                    epss=epss.get(key),
                    cvss=row.get("cvss"),
                    exploited=is_exploited(key),
                )
                table[key] = item
                titles[key] = []
                public[key] = False
            item.articles += 1
            if row.get("source"):
                item.sources.add(row["source"])
            published = row.get("published_at")
            if published and (item.first_seen is None or published < item.first_seen):
                item.first_seen = published
            cvss = row.get("cvss")
            if cvss is not None and (item.cvss is None or cvss > item.cvss):
                item.cvss = cvss
            title = row.get("title") or ""
            if title:
                titles[key].append(title)
            if row.get("public_facing"):
                public[key] = True

    for key, item in table.items():
        item.exposure, item.exposure_source = exposure_ctx.resolve(
            key, public[key], titles[key]
        )
        item.priority = _band(item, use_exposure)

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
        "exposed": sum(1 for item in items if item.exposed),
        "exposure_sources": {
            source: sum(1 for item in items if item.exposure_source == source)
            for source in ("manual", "reported", "inferred", "none")
        },
    }
