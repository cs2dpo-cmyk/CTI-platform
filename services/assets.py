"""Asset inventory: which systems exist, and whether they face the internet.

The corpus is news, so it cannot know whether a CVE touches a real system. This
module closes that gap with a small CSV inventory:

    asset_id,name,exposure,products
    vpn-01,遠端存取 VPN,public,citrix netscaler|fortinet|vpn

products is a pipe-separated keyword list. A CVE is considered present on an
asset when one of its keywords appears in the article headline that names the
CVE - the same signal a human uses when they read "Citrix NetScaler" and think
"that is our VPN box".

The inventory is a seed for the demo; a production deployment replaces the file
with an export from its CMDB. Nothing is invented per CVE: an unmatched CVE is
reported as unknown, not assumed internal.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

INVENTORY = Path(__file__).resolve().parent.parent / "data" / "assets.csv"

PUBLIC = "public"
INTERNAL = "internal"
VALID_EXPOSURE = (PUBLIC, INTERNAL)


@dataclass(frozen=True)
class Asset:
    asset_id: str
    name: str
    exposure: str
    products: tuple[str, ...]


def parse_rows(rows: list[dict]) -> list[Asset]:
    assets: list[Asset] = []
    for row in rows:
        exposure = (row.get("exposure") or "").strip().lower()
        if exposure not in VALID_EXPOSURE:
            continue
        products = tuple(
            part.strip().lower()
            for part in (row.get("products") or "").split("|")
            if part.strip()
        )
        if not products:
            continue
        assets.append(
            Asset(
                asset_id=(row.get("asset_id") or "").strip(),
                name=(row.get("name") or "").strip(),
                exposure=exposure,
                products=products,
            )
        )
    return assets


@lru_cache(maxsize=1)
def load() -> tuple[Asset, ...]:
    try:
        with INVENTORY.open(encoding="utf-8-sig", newline="") as handle:
            return tuple(parse_rows(list(csv.DictReader(handle))))
    except OSError:
        return ()


def match(titles: list[str], inventory: tuple[Asset, ...] | None = None) -> list[Asset]:
    """Assets running a product named in any of the headlines."""
    inventory = load() if inventory is None else inventory
    if not titles or not inventory:
        return []
    haystack = " ".join(titles).lower()
    return [asset for asset in inventory if any(product in haystack for product in asset.products)]


def exposure_for(
    titles: list[str], inventory: tuple[Asset, ...] | None = None
) -> tuple[str, list[Asset]]:
    """(exposure, matched assets). Any internet-facing asset wins over internal."""
    matched = match(titles, inventory)
    if not matched:
        return "unknown", []
    if any(asset.exposure == PUBLIC for asset in matched):
        return PUBLIC, matched
    return INTERNAL, matched
