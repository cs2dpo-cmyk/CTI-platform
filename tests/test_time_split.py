from datetime import date
from types import SimpleNamespace

from services import time_split


def _row(day: str):
    return SimpleNamespace(published_at=date.fromisoformat(day))


def test_split_puts_cutoff_day_in_the_test_window():
    rows = [_row("2026-01-01"), _row("2026-06-15"), _row("2026-07-01")]
    development, test = time_split.split(rows, date(2026, 7, 1))
    assert development.size == 2
    assert test.size == 1
    assert development.start == date(2026, 1, 1)
    assert test.end == date(2026, 7, 1)


def test_windows_never_overlap():
    rows = [_row(f"2026-0{m}-01") for m in range(1, 10)]
    development, test = time_split.split(rows, date(2026, 5, 1))
    overlap = {id(row) for row in development.rows} & {id(row) for row in test.rows}
    assert not overlap
    assert development.size + test.size == len(rows)


def test_suggest_cutoff_respects_both_minimums():
    rows = [_row("2026-01-01")] * 5 + [_row("2026-09-01")] * 60
    cutoff = time_split.suggest_cutoff(rows, min_test=50, min_train=5)
    # 2026-01-01 would leave the development window empty, so the earliest
    # valid cutoff is the September batch.
    assert cutoff == date(2026, 9, 1)


def test_suggest_cutoff_returns_none_when_impossible():
    rows = [_row("2026-01-01")] * 5
    assert time_split.suggest_cutoff(rows, min_test=50, min_train=5) is None


def test_monthly_counts_are_sorted():
    rows = [_row("2026-03-01"), _row("2026-01-01"), _row("2026-03-20")]
    assert time_split.monthly_counts(rows) == {"2026-01": 1, "2026-03": 2}
