from services import assets, exposure


def _asset(asset_id: str, exposure: str, products: str) -> assets.Asset:
    return assets.Asset(
        asset_id=asset_id,
        name=asset_id,
        exposure=exposure,
        products=tuple(part.strip().lower() for part in products.split("|")),
    )


def test_parse_rows_skips_bad_exposure_and_empty_products():
    rows = [
        {"asset_id": "a1", "name": "A", "exposure": "public", "products": "nginx|php"},
        {"asset_id": "a2", "name": "B", "exposure": "dmz", "products": "nginx"},
        {"asset_id": "a3", "name": "C", "exposure": "internal", "products": ""},
    ]
    parsed = assets.parse_rows(rows)
    assert [asset.asset_id for asset in parsed] == ["a1"]


def test_match_is_case_insensitive_and_cross_language():
    inventory = (_asset("vpn-01", "public", "citrix netscaler|vpn"),)
    matched = assets.match(["Citrix NetScaler 漏洞遭利用"], inventory)
    assert [asset.asset_id for asset in matched] == ["vpn-01"]


def test_public_asset_wins_over_internal():
    inventory = (
        _asset("web-01", "public", "php"),
        _asset("dev-01", "internal", "php"),
    )
    exposure_value, matched = assets.exposure_for(["PHP 修補公告"], inventory)
    assert exposure_value == "public"
    assert len(matched) == 2


def test_inventory_beats_article_wording_in_resolution(monkeypatch):
    inventory = (_asset("wsus-01", "internal", "wsus"),)
    monkeypatch.setattr(exposure.assets, "load", lambda: inventory)
    value, source, matched = exposure.resolve_detail("CVE-2026-1", True, ["WSUS 更新"])
    assert (value, source) == ("internal", "inventory")
    assert [asset.asset_id for asset in matched] == ["wsus-01"]


def test_manual_override_beats_inventory(monkeypatch):
    inventory = (_asset("wsus-01", "internal", "wsus"),)
    monkeypatch.setattr(exposure.assets, "load", lambda: inventory)
    monkeypatch.setattr(exposure, "_overrides", lambda: {"CVE-2026-1": "public"})
    value, source, _ = exposure.resolve_detail("CVE-2026-1", False, ["WSUS 更新"])
    assert (value, source) == ("public", "manual")
