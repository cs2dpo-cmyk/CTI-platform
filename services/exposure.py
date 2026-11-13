"""Exposure context for a CVE, inferred from what the corpus actually says.

A vulnerability's urgency depends on whether the affected system can be reached
from the internet. The corpus has no asset inventory, so exposure is inferred
from two signals, in order:

    reported   an article about the CVE describes it as internet-facing
    inferred   the CVE's headline names an edge product (Citrix, Fortinet,
               Exchange, firewall, gateway, ...)
    unknown    neither signal fired

A deployment can pin the answer per CVE in data/exposure_overrides.json, which
is how an asset owner would feed real context in until a proper inventory is
connected.
"""

from __future__ import annotations

import json
import re

from services import assets
from functools import lru_cache
from pathlib import Path

OVERRIDES = Path(__file__).resolve().parent.parent / "data" / "exposure_overrides.json"

PUBLIC = "public"
INTERNAL = "internal"
UNKNOWN = "unknown"

SOURCE_LABELS = {
    "manual": "人工指定",
    "inventory": "資產清單",
    "reported": "情資描述對外",
    "inferred": "產品推斷對外",
    "none": "未取得曝險資訊",
}

# Edge products whose presence in a headline is a strong internet-facing signal.
EDGE_PATTERN = re.compile(
    r"netscaler|citrix|fortinet|fortigate|fortios|sonicwall|palo alto|pan-os|"
    r"exchange server|exchange|vpn|firewall|gateway|edge|reverse proxy|"
    r"防火牆|閘道|對外|邊界|路由器|網頁伺服器",
    re.IGNORECASE,
)


@lru_cache(maxsize=1)
def _overrides() -> dict[str, str]:
    try:
        payload = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {
        key.upper(): value
        for key, value in payload.items()
        if value in (PUBLIC, INTERNAL, UNKNOWN)
    }


def override_for(cve: str) -> str | None:
    return _overrides().get(cve.upper())


def mentions_edge_product(title: str) -> bool:
    return bool(EDGE_PATTERN.search(title or ""))


def resolve_detail(
    cve: str,
    article_public: bool,
    titles: list[str],
) -> tuple[str, str, list]:
    """Return (exposure, source, matched assets) for one CVE.

    The inventory outranks article wording: "our VPN box runs Citrix" is a fact,
    while "the vendor says internet-facing" is only a hint about the product.
    """
    manual = override_for(cve)
    if manual:
        return manual, "manual", []

    inventory_exposure, matched = assets.exposure_for(titles)
    if inventory_exposure != UNKNOWN:
        return inventory_exposure, "inventory", matched

    if article_public:
        return PUBLIC, "reported", []
    if any(mentions_edge_product(title) for title in titles):
        return PUBLIC, "inferred", []
    return UNKNOWN, "none", []


def resolve(cve: str, article_public: bool, titles: list[str]) -> tuple[str, str]:
    exposure, source, _ = resolve_detail(cve, article_public, titles)
    return exposure, source
