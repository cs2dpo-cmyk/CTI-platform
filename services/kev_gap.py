"""KEV entries inside the corpus window that no article reported.

The patch list can only rank what the news mentioned, and news covers about 11%
of the KEV entries added while the corpus was collected. Hiding that gap is
worse than the gap itself, so this module lists what was missed: every KEV entry
added inside the corpus window that no article named, with its EPSS score, CVSS
and ransomware flag.

Nothing here changes the patch list; it is the honest "what you did not see"
companion view.
"""

from __future__ import annotations

from functools import lru_cache

from services import cvss, dataset, epss, kev, patch_priority


@lru_cache(maxsize=1)
def _corpus_cves() -> frozenset[str]:
    records, _ = dataset.load_dataset()
    found: set[str] = set()
    for record in records:
        for cve in record.evidence.get("cves") or []:
            found.add(str(cve).upper())
    return frozenset(found)


@lru_cache(maxsize=1)
def window() -> tuple[str, str]:
    """The corpus date span, so the gap is measured on a fair interval."""
    records, _ = dataset.load_dataset()
    days = [record.published_at for record in records if record.published_at]
    if not days:
        return ("", "")
    return (min(days).isoformat(), max(days).isoformat())


def build() -> dict:
    start, end = window()
    corpus = _corpus_cves()
    scores = epss.all_scores()
    severity = cvss.all_scores()
    details = kev.full()

    in_window = {
        cve: meta
        for cve, meta in details.items()
        if start <= str(meta.get("added", "")) <= end
    }
    covered = sorted(set(in_window) & corpus)

    items = []
    for cve, meta in in_window.items():
        if cve in corpus:
            continue
        band = patch_priority.base_band(True, scores.get(cve), severity.get(cve))
        items.append(
            {
                "cve": cve,
                "priority": band,
                "sla": patch_priority.SLA[band],
                "added": meta.get("added") or None,
                "ransomware": meta.get("ransomware") == "Known",
                "vendor": meta.get("vendor") or "",
                "product": meta.get("product") or "",
                "name": meta.get("name") or "",
                "epss": None if cve not in scores else round(scores[cve], 4),
                "cvss": None if cve not in severity else round(severity[cve], 1),
            }
        )
    # Ransomware-linked first: those are the ones a defender cannot defer.
    items.sort(key=lambda item: (not item["ransomware"], -(item["epss"] or 0.0), item["cve"]))

    return {
        "window_start": start,
        "window_end": end,
        "kev_total": len(details),
        "kev_in_window": len(in_window),
        "covered": len(covered),
        "covered_cves": covered,
        "uncovered": len(items),
        "ransomware": sum(1 for item in items if item["ransomware"]),
        "items": items,
    }


def uncovered_cves() -> list[str]:
    """Just the CVEs, for the CVSS backfill tool."""
    return [item["cve"] for item in build()["items"]]
