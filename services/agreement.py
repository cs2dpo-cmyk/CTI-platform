"""Inter-annotator agreement.

Two people labelling the same sheet is the only way to know whether the labels
themselves are stable; a classifier cannot be more reliable than its ground
truth. Cohen's kappa is reported because raw agreement looks high whenever one
class dominates: always guessing MALWARE agrees ~47% of the time on this corpus
while carrying no information.
"""

from __future__ import annotations

from collections import Counter


def cohen_kappa(left: list[str], right: list[str]) -> float:
    """Cohen's kappa for two equal-length label sequences."""
    if not left or len(left) != len(right):
        return 0.0
    total = len(left)
    observed = sum(1 for a, b in zip(left, right) if a == b) / total
    left_counts = Counter(left)
    right_counts = Counter(right)
    expected = sum(
        (left_counts[label] / total) * (right_counts[label] / total)
        for label in set(left) | set(right)
    )
    if expected >= 1.0:
        return 0.0
    return (observed - expected) / (1.0 - expected)


def binary_kappa(left: list[str], right: list[str], positive: str) -> float:
    """Kappa for one class treated as the positive label."""
    return cohen_kappa(
        ["1" if value == positive else "0" for value in left],
        ["1" if value == positive else "0" for value in right],
    )


def confusion(left: list[str], right: list[str], labels: list[str]) -> dict[str, dict[str, int]]:
    table = {row: {column: 0 for column in labels} for row in labels}
    for a, b in zip(left, right):
        if a in table and b in table[a]:
            table[a][b] += 1
    return table


def describe(left: list[str], right: list[str], labels: list[str]) -> dict:
    total = len(left)
    agree = sum(1 for a, b in zip(left, right) if a == b)
    return {
        "rows": total,
        "agree": agree,
        "agreement": round(agree / total, 3) if total else 0.0,
        "kappa": round(cohen_kappa(left, right), 3),
        "per_class_kappa": {
            label: round(binary_kappa(left, right, label), 3) for label in labels
        },
        "confusion": confusion(left, right, labels),
    }
