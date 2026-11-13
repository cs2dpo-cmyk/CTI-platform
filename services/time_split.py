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
    records: Sequence,
    *,
    min_test: int = 60,
    min_train: int = 40,
    labelled: dict[str, str] | None = None,
    min_train_labelled: int = 30,
    min_test_labelled: int = 30,
) -> date | None:
    """Earliest cutoff that leaves enough rows - and labels - on both sides.

    A cutoff that grows the test window but empties the development window is
    useless: the accuracy column would read "n/a". When a label map is supplied,
    both windows must also carry enough labelled rows to be measured.
    """
    dates = sorted({row.published_at for row in records})

    def labelled_count(rows: list) -> int:
        if not labelled:
            return len(rows)
        return sum(1 for row in rows if labelled.get(getattr(row, "title", "")))

    for cutoff in dates:
        train = [row for row in records if row.published_at < cutoff]
        test = [row for row in records if row.published_at >= cutoff]
        if len(test) < min_test or len(train) < min_train:
            continue
        if labelled and (
            labelled_count(train) < min_train_labelled
            or labelled_count(test) < min_test_labelled
        ):
            continue
        return cutoff
    return None


def describe(window: Window) -> dict:
    return {
        "name": window.name,
        "rows": window.size,
        "start": window.start.isoformat() if window.start else None,
        "end": window.end.isoformat() if window.end else None,
    }
