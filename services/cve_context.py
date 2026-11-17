"""Look up what the corpus and the snapshots say about one CVE.

The assessment form asks for a category (VULN vs MALWARE), and the two are easy
to confuse: the same CVE can appear in a "patch this" advisory and in an "attack
campaign" story. This module answers "what does the corpus call this CVE?" so the
form can pre-select it and say why, instead of asking the user to guess.
"""

from __future__ import annotations

import re
from collections import Counter
from functools import lru_cache

from services import cvss, dataset, epss, kev

CVE_PATTERN = re.compile(r"^CVE-\d{4}-\d{4,7}$")
CATEGORY_LABELS = {
    "VULN": "系統漏洞與修補對策",
    "MALWARE": "惡意威脅與主動攻擊",
    "RESEARCH": "前瞻研究與平台治理",
    "OTHER": "產業與產品動態",
}


@lru_cache(maxsize=1)
def _index() -> dict[str, dict]:
    """cve -> {categories: Counter, titles: list, first_seen: str}."""
    records, _ = dataset.load_dataset()
    table: dict[str, dict] = {}
    for record in records:
        for cve in record.evidence.get("cves") or []:
            key = str(cve).upper()
            entry = table.setdefault(
                key, {"categories": Counter(), "titles": [], "first_seen": None}
            )
            entry["categories"][record.category] += 1
            if record.title and len(entry["titles"]) < 3:
                entry["titles"].append(record.title)
            seen = record.published_at.isoformat() if record.published_at else None
            if seen and (entry["first_seen"] is None or seen < entry["first_seen"]):
                entry["first_seen"] = seen
    return table


def normalise(cve: str) -> str | None:
    candidate = (cve or "").strip().upper()
    return candidate if CVE_PATTERN.match(candidate) else None


def lookup(cve: str) -> dict | None:
    """Everything known about a CVE; None when the format is wrong."""
    key = normalise(cve)
    if key is None:
        return None

    entry = _index().get(key)
    counts = dict(entry["categories"]) if entry else {}
    articles = sum(counts.values())

    if articles:
        # Majority wins; a tie falls back to VULN because a CVE is a
        # vulnerability record and that is the safer default for a patch queue.
        ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0] != "VULN"))
        suggested = ordered[0][0]
        top = ordered[0]
        reason = (
            f"語料中 {articles} 篇提到此 CVE，其中 {top[1]} 篇屬「{CATEGORY_LABELS.get(suggested, suggested)}」"
        )
        if len(counts) > 1:
            others = "、".join(
                f"{CATEGORY_LABELS.get(k, k)} {v} 篇" for k, v in ordered[1:3]
            )
            reason += f"；另有 {others}，屬混合報導"
    else:
        suggested = "VULN"
        reason = "語料未收錄此 CVE；CVE 屬漏洞編號，預設為系統漏洞類"

    return {
        "cve": key,
        "in_corpus": bool(entry),
        "articles": articles,
        "categories": counts,
        "suggested_category": suggested,
        "reason": reason,
        "kev": kev.is_exploited(key),
        "epss": epss.score_for([key]),
        "cvss": cvss.score_for([key]),
        "first_seen": entry["first_seen"] if entry else None,
        "titles": entry["titles"] if entry else [],
    }
