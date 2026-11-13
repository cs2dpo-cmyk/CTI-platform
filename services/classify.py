"""Deterministic, auditable classification of one intelligence item.

Why rules instead of the K-Means cluster label?

The clusters are *vocabulary* groups fitted per region. They are useful for
exploring what a corpus talks about, but a cluster is not a risk category: in
this corpus the international C0 group (35 items, mapped to VULN) contains 18
breach/attack stories, and the Taiwan C1 group (27 items, mapped to MALWARE)
contains 10 product or earnings announcements. Mapping a whole cluster to one
meta-category therefore mislabels whole blocks of rows, and because the risk
score is derived from the category, a mislabel becomes a wrong P1.

These rules are ordered and each one is explainable. They are evaluated against
data/gold_labels.csv (100 hand-labelled headlines) by tools/eval_classifier.py.
"""

from __future__ import annotations

import re
from typing import Any

from services.cve import extract_cves

CATEGORIES = ("VULN", "MALWARE", "RESEARCH", "OTHER")
LABELS = {
    "VULN": "系統漏洞與修補對策",
    "MALWARE": "惡意威脅與主動攻擊",
    "RESEARCH": "前瞻研究與平台治理",
    "OTHER": "產業與產品動態",
}

_CVSS = re.compile(r"CVSS[^0-9]{0,12}(\d{1,2}(?:\.\d)?)", re.IGNORECASE)

# --- vocabulary groups ------------------------------------------------------
# Each pattern is a whole word/phrase where the language allows it, so that
# "patch" does not fire inside "dispatch".
_VULN = re.compile(
    r"漏洞|修補|安全性更新|安全更新|重大更新|緊急更新|補丁|"
    r"\bvulnerabilit\w*|\bflaws?\b|\bpatches?\b|\bpatched\b|\bpatching\b|"
    r"\bfixes?\b|\bfixed\b|\badvisor(?:y|ies)\b|\bCVE-\d{4}-\d{4,7}\b|"
    r"\bRCE\b|remote code execution|arbitrary code execution|code execution|"
    r"\bzero[- ]day\b|\b0-day\b|\bCVSS\b",
    re.IGNORECASE,
)

_ATTACK = re.compile(
    r"勒索|惡意|釣魚|竊取|竊走|入侵|遭駭|被駭|外洩|後門|木馬|殭屍|"
    r"駭客|攻擊|掃描|滲透|"
    r"\bmalware\b|\bransomware\b|\bphishing\b|\bbreach(?:es|ed)?\b|"
    r"\bhack(?:ed|s|ing|er|ers)\b|\battack(?:s|ed|ers?|ing)?\b|"
    r"\bexploit(?:s|ed|ing|ation)?\b|\bbackdoor\b|\btrojan\b|\bspyware\b|"
    r"\bstealer\b|\bscam(?:s)?\b|\bhijack(?:ed|s)?\b|\bcompromis(?:e|ed)\b|"
    r"\bst(?:olen|eal)\b|\bleak(?:s|ed)?\b|\bminers?\b|\binfect(?:ed|s)?\b",
    re.IGNORECASE,
)

_ACTOR = re.compile(
    r"駭客|攻擊者|犯罪集團|勒索軟體組織|"
    r"\bhackers?\b|\battackers?\b|\bthreat actors?\b|\bcybercriminals?\b|"
    r"\bAPT\d*\b|Lazarus|Volt Typhoon|ShinyHunters|UAT-\d+|China-Linked|"
    r"\bgroup\b|\bgang\b",
    re.IGNORECASE,
)

_PATCH_VERB = re.compile(
    r"修補|安全性更新|安全更新|緊急更新|重大更新|更新|公告|\bpatch(?:es|ed)?\b|\bfix(?:es|ed)?\b|\bupdate[sd]?\b|"
    r"\badvisor(?:y|ies)\b|\bbackports?\b|\breleases?\b",
    re.IGNORECASE,
)

# Chinese incident phrasing is explicit that something already happened,
# unlike the word "exploited" inside a vendor advisory headline.
_INCIDENT = re.compile(r"遭到利用|遭利用|在野|已遭|被利用", re.IGNORECASE)

_RESEARCH = re.compile(
    r"研究|調查|報告|分析|治理|法規|政策|合規|標準|指引|指南|規範|白皮書|座談|提出|制裁|模式|"
    r"\bwebinar\b|\bsurvey\b|\bstudy\b|\breport\b|\bresearch(?:ers?)?\b|"
    r"\banalysis\b|\bbenchmark\w*\b|\bbounty\b|\bsanction\w*\b|"
    r"\bseiz(?:e|ed|ure)\b|\bFBI\b|\bEuropol\b|\bgovernance\b|\bpolicy\b|"
    r"\bregulat\w+\b|\bcompliance\b|\bguideline\w*\b|\bframework\b|"
    r"\bweekly recap\b|\bthreatsday\b|\bopinion\b|\bcareers?\b",
    re.IGNORECASE,
)

_BREACH = re.compile(
    r"竊取|竊走|外洩|入侵|遭駭|被駭|breach|hacked|compromised|stolen|leaked|"
    r"credential|takeover|hijack",
    re.IGNORECASE,
)

# Product / industry vocabulary only counts when the item carries no security
# vocabulary at all, which is what separates "MacBook launch" from "Apple fixes
# an exploited flaw".
_PRODUCT = re.compile(
    r"營收|財報|季度|獲利|成長|售價|定價|推出|發表|釋出|上市|布局|採用|併購|收購|"
    r"大腦|語音|影像|模型|生態|夥伴|訂閱|用戶|功能|版本|工具|原型|介面|業者|應用|"
    r"\bearnings\b|\brevenue\b|\bquarter\b|\bprofit\b|\blaunch(?:es|ed)?\b|"
    r"\bunveil(?:s|ed)?\b|\bintroduc(?:es|ed)\b|\bpartnership\b|\bacquir(?:es|ed)\b|"
    r"\binstalls?\b|\bapp store\b|\bmodel\b|\bfeature\b|\brollout\b|\bpreview\b",
    re.IGNORECASE,
)

_SECURITY = re.compile(
    r"漏洞|修補|攻擊|惡意|竊|駭|入侵|勒索|釣魚|防護|資安|安全|"
    r"\bsecurity\b|\bvulnerab\w+\b|\bthreat\b|\bmalware\b|\bransomware\b|"
    r"\bexploit\w*\b|\bbreach\b|\bhack\w*\b|\bphishing\b|\bpatch\w*\b",
    re.IGNORECASE,
)


def _hits(pattern: re.Pattern[str], text: str) -> int:
    return len({match.group(0).lower() for match in pattern.finditer(text)})


def extract_evidence(title: str, text: str = "") -> dict[str, Any]:
    """Pull the machine-checkable facts a risk score is allowed to depend on."""
    body = f"{title} {text}"
    cves = sorted(extract_cves(body))
    cvss_match = _CVSS.search(body)
    cvss = float(cvss_match.group(1)) if cvss_match else None
    if cvss is not None and not 0.0 <= cvss <= 10.0:
        cvss = None

    active = bool(re.search(
        r"actively exploited|exploited in the wild|in the wild|已遭利用|遭到利用|"
        r"積極利用|在野|攻擊者已|已有攻擊|active exploitation",
        body, re.IGNORECASE))
    poc = bool(re.search(r"proof[- ]of[- ]concept|PoC|概念驗證|exploit code|利用程式碼",
                         body, re.IGNORECASE))
    public = bool(re.search(r"internet[- ]exposed|public[- ]facing|對外|公開網際網路|掃描",
                            body, re.IGNORECASE))
    # Wording that justifies a high severity even when no CVSS number is quoted.
    critical = bool(re.search(
        r"\bcritical\b|zero[- ]day|0-day|\bRCE\b|remote code|arbitrary code|"
        r"actively exploited|exploited in the wild|"
        r"滿分|重大|緊急|在野|已遭利用|積極利用|嚴重",
        body, re.IGNORECASE))

    return {
        "cves": cves,
        "cvss": cvss,
        "exploit": "active" if active else ("poc_public" if poc else "unknown"),
        "exposure": "public" if public else "internal",
        "critical_wording": critical,
    }


def classify(title: str, text: str = "") -> tuple[str, str]:
    """Return (category, reason). Ordered rules; first match wins."""
    body = f"{title} {text}"

    vuln = _hits(_VULN, body)
    attack = _hits(_ATTACK, body)
    research = _hits(_RESEARCH, body)
    product = _hits(_PRODUCT, body)
    actor = bool(_ACTOR.search(body))
    breach = bool(_BREACH.search(body))
    patch = bool(_PATCH_VERB.search(body))
    incident = bool(_INCIDENT.search(body))

    # 1. Nothing that reads like security work: keep it out of the threat funnel.
    if not (vuln or attack or actor or patch or breach or incident):
        return ("OTHER", "no security vocabulary; product/industry signal") if product \
            else ("RESEARCH", "governance note without a concrete event")

    # 2. "Already exploited" describes an incident, not an advisory.
    if incident:
        return "MALWARE", "exploitation reported as an event"

    # 3. A named actor plus attack or breach evidence.
    if actor and (breach or attack):
        return "MALWARE", "named actor with attack/breach evidence"

    # 4. Two or more independent attack terms and no patch action.
    if attack >= 2 and not patch:
        return "MALWARE", "attack vocabulary"

    # 5. Governance and research notes. Runs after the attack checks so a
    #    write-up *about* an attack is still classified as an attack.
    if research and not actor:
        return "RESEARCH", "governance/research vocabulary"

    # 6. Vendor advisories: a patch/fix action with no attacker.
    if patch and not actor:
        return "VULN", "patch/advisory action"

    # 7. Reported compromise without a patch action.
    if breach:
        return "MALWARE", "breach reported without a patch action"

    # 8. Flaw write-ups.
    if vuln:
        return "VULN", "CVE/flaw/patch vocabulary"

    # 9. Remaining attack content.
    if attack:
        return "MALWARE", "attack vocabulary"

    if research:
        return "RESEARCH", "research vocabulary"
    return "OTHER", "no threat evidence"


def audit_row(title: str, text: str = "") -> dict[str, Any]:
    """Classification plus the signals behind it, for the audit CSV."""
    body = f"{title} {text}"
    category, reason = classify(title, text)
    evidence = extract_evidence(title, text)
    return {
        "category": category,
        "reason": reason,
        "vuln_hits": _hits(_VULN, body),
        "attack_hits": _hits(_ATTACK, body),
        "research_hits": _hits(_RESEARCH, body),
        "product_hits": _hits(_PRODUCT, body),
        "actor": bool(_ACTOR.search(body)),
        "breach": bool(_BREACH.search(body)),
        "patch": bool(_PATCH_VERB.search(body)),
        **evidence,
    }
