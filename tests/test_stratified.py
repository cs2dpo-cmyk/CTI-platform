import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from build_stratified import bucket, month_range, pick


def test_month_range_spans_year_boundary():
    assert month_range("2025-11", "2026-02") == ["2025-11", "2025-12", "2026-01", "2026-02"]


def test_month_range_single_month():
    assert month_range("2026-03", "2026-03") == ["2026-03"]


def test_bucket_drops_rows_without_a_parseable_date():
    items = [
        {"title": "a", "url": "u1", "date": "2026-01-05", "source": "THN"},
        {"title": "b", "url": "u2", "date": "", "source": "網管人"},
        {"title": "c", "url": "u3", "date": "01/05/2026", "source": "X"},
    ]
    grouped = bucket(items)
    assert list(grouped) == ["2026-01"]
    assert len(grouped["2026-01"]) == 1


def test_bucket_deduplicates_by_url():
    items = [
        {"title": "a", "url": "u1", "date": "2026-01-05", "source": "THN"},
        {"title": "a again", "url": "u1", "date": "2026-01-06", "source": "THN"},
    ]
    assert len(bucket(items)["2026-01"]) == 1


def test_pick_caps_each_month_and_keeps_sources_apart():
    grouped = {
        "2026-01": [
            {"date": "2026-01-09", "source": "THN", "url": "a"},
            {"date": "2026-01-08", "source": "THN", "url": "b"},
            {"date": "2026-01-07", "source": "TWCERT", "url": "c"},
            {"date": "2026-01-06", "source": "THN", "url": "d"},
        ]
    }
    chosen = pick(grouped, "THN", 2, ["2026-01"])
    assert [row["url"] for row in chosen] == ["a", "b"]   # newest first, capped at 2


def test_pick_returns_nothing_for_a_month_without_rows():
    assert pick({}, "THN", 5, ["2026-01"]) == []
