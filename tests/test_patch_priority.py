from datetime import date

from services import patch_priority


def _item(**kwargs):
    base = {"cves": ["CVE-2026-1"], "source": "THN", "published_at": date(2026, 1, 1), "cvss": 5.0}
    base.update(kwargs)
    return base


def test_kev_membership_forces_p1(monkeypatch):
    monkeypatch.setattr(patch_priority, "is_exploited", lambda cve: True)
    items = patch_priority.build([_item(cvss=2.0)], {})
    assert items[0].priority == "P1"
    assert items[0].sla == "24 小時"


def test_epss_above_threshold_is_p2(monkeypatch):
    monkeypatch.setattr(patch_priority, "is_exploited", lambda cve: False)
    items = patch_priority.build([_item(cvss=3.0)], {"CVE-2026-1": 0.42})
    assert items[0].priority == "P2"
    assert "EPSS" in items[0].reason


def test_high_cvss_is_p2_without_epss(monkeypatch):
    monkeypatch.setattr(patch_priority, "is_exploited", lambda cve: False)
    items = patch_priority.build([_item(cvss=9.8)], {})
    assert items[0].priority == "P2"


def test_low_signal_is_p3(monkeypatch):
    monkeypatch.setattr(patch_priority, "is_exploited", lambda cve: False)
    items = patch_priority.build([_item(cvss=4.0)], {"CVE-2026-1": 0.01})
    assert items[0].priority == "P3"


def test_aggregation_keeps_max_cvss_earliest_date_and_sources(monkeypatch):
    monkeypatch.setattr(patch_priority, "is_exploited", lambda cve: False)
    rows = [
        _item(source="TWCERT", published_at=date(2026, 3, 1), cvss=7.0),
        _item(source="THN", published_at=date(2026, 1, 5), cvss=9.5),
    ]
    items = patch_priority.build(rows, {})
    assert items[0].articles == 2
    assert items[0].cvss == 9.5
    assert items[0].first_seen == date(2026, 1, 5)
    assert items[0].sources == {"TWCERT", "THN"}


def test_exposed_escalates_one_level(monkeypatch):
    monkeypatch.setattr(patch_priority, "is_exploited", lambda cve: False)
    monkeypatch.setattr(patch_priority.exposure_ctx, "resolve", lambda cve, public, titles: ("public", "reported"))
    items = patch_priority.build([_item(cvss=3.0)], {"CVE-2026-1": 0.2})
    assert items[0].priority == "P1"   # base P2 -> P1
    assert "升一級" in items[0].reason


def test_internal_demotes_one_level(monkeypatch):
    monkeypatch.setattr(patch_priority, "is_exploited", lambda cve: False)
    monkeypatch.setattr(patch_priority.exposure_ctx, "resolve", lambda cve, public, titles: ("internal", "manual"))
    items = patch_priority.build([_item(cvss=3.0)], {"CVE-2026-1": 0.2})
    assert items[0].priority == "P3"   # base P2 -> P3
    assert "降一級" in items[0].reason


def test_unknown_exposure_keeps_base_band(monkeypatch):
    monkeypatch.setattr(patch_priority, "is_exploited", lambda cve: False)
    monkeypatch.setattr(patch_priority.exposure_ctx, "resolve", lambda cve, public, titles: ("unknown", "none"))
    items = patch_priority.build([_item(cvss=3.0)], {"CVE-2026-1": 0.2})
    assert items[0].priority == "P2"


def test_exposure_can_be_switched_off(monkeypatch):
    monkeypatch.setattr(patch_priority, "is_exploited", lambda cve: False)
    monkeypatch.setattr(patch_priority.exposure_ctx, "resolve", lambda cve, public, titles: ("public", "reported"))
    items = patch_priority.build([_item(cvss=3.0)], {"CVE-2026-1": 0.2}, use_exposure=False)
    assert items[0].priority == "P2"


def test_kev_never_demotes(monkeypatch):
    monkeypatch.setattr(patch_priority, "is_exploited", lambda cve: True)
    monkeypatch.setattr(patch_priority.exposure_ctx, "resolve", lambda cve, public, titles: ("internal", "manual"))
    items = patch_priority.build([_item(cvss=3.0)], {})
    assert items[0].priority == "P1"
    assert "內部資產" in items[0].reason
