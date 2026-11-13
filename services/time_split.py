"""Temporal splits for backtesting.

A random split answers "does the model fit this corpus". A time split answers
"does it still work on data from a later period", which is the question a
deployed tool faces. The corpus is far from uniform in time (two months hold
three quarters of the rows), so the cutoff is chosen from the data rather than
hard-coded, and every window reports its own size.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date
from typing import Iterable, Sequence


@dataclass
class Window:
    name: str
    rows: list
    start: date | None = None
    end: date | None = None

    @property
    def size(self) -> int:
        return len(self.rows)


def split(records: Sequence, cutoff: date) -> tuple[Window, Window]:
    """Rows published before the cutoff form development; the rest is test."""
    train = [row for row in records if row.published_at < cutoff]
    test = [row for row in records if row.published_at >= cutoff]
    return (
        Window("development", train, _first(train), _last(train)),
        Window("test", test, _first(test), _last(test)),
    )


def _first(rows: Iterable) -> date | None:
    dates = [row.published_at for row in rows]
    return min(dates) if dates else None


def _last(rows: Iterable) -> date | None:
    dates = [row.published_at for row in rows]
    return max(dates) if dates else None


def monthly_counts(records: Sequence) -> dict[str, int]:
    counter = Counter(row.published_at.strftime("%Y-%m") for row in records)
    return dict(sorted(counter.items()))


def suggest_cutoff(
    records: Sequence, *, min_test: int = 60, min_train: int = 40
) -> date | None:
    """The earliest cutoff that still leaves min_test rows in the test window.

    Choosing the latest possible cutoff would shrink the test window to a
    handful of rows and make every number noise; this walks forward until the
    test window is large enough, and returns None when no cutoff can satisfy
    both minimums.
    """
    dates = sorted({row.published_at for row in records})
    for cutoff in dates:
        test = sum(1 for row in records if row.published_at >= cutoff)
        train = len(records) - test
        if test >= min_test and train >= min_train:
            return cutoff
    return None


def describe(window: Window) -> dict:
    return {
        "name": window.name,
        "rows": window.size,
        "start": window.start.isoformat() if window.start else None,
        "end": window.end.isoformat() if window.end else None,
    }
