from datetime import date

from services import snapshots


def test_registry_describes_every_snapshot():
    described = snapshots.describe()
    assert {"epss", "kev", "assets"} <= set(described)
    for name, meta in described.items():
        assert meta["generated"], name
        assert meta["source"], name
        assert meta["entries"] and meta["entries"] > 0, name


def test_as_of_is_the_oldest_snapshot_date():
    described = snapshots.describe()
    oldest = min(meta["generated"] for meta in described.values())
    assert snapshots.as_of() == oldest


def test_staleness_is_not_negative():
    days = snapshots.staleness_days()
    assert days is not None and days >= 0


def test_as_of_is_a_real_date():
    date.fromisoformat(snapshots.as_of())
