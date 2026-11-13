"""Near-duplicate detection for threat-intel items.

Two items are the same *event* when a responder would only open one ticket for
them. That is coarser than string equality: the same CVE is routinely covered by
TWCERT (Chinese) and The Hacker News (English) with unrelated titles, and the
same story is re-published with a tweaked headline.

Matching is therefore tiered:

    url      identical source_url
    cve      identical non-empty CVE set
    title    character 3-gram Jaccard >= threshold

Only stdlib is used so the module can run inside the ingest worker too.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable, Sequence

CVE_PATTERN = re.compile(r"CVE-\d{4}-\d{4,7}", re.IGNORECASE)

DEFAULT_TITLE_THRESHOLD = 0.82
# A digest post ("daily roundup") contains another headline verbatim: Jaccard
# punishes the length gap, containment does not.
DEFAULT_CONTAINMENT = 0.88
MIN_SHINGLES_FOR_CONTAINMENT = 12
SHINGLE_SIZE = 3


@dataclass(frozen=True)
class Item:
    """The minimum a record needs to take part in duplicate detection."""

    key: int
    title: str
    source: str = ""
    url: str = ""
    cve_text: str = ""  # extra text the CVE regex may scan (e.g. summary)

    @property
    def cves(self) -> frozenset[str]:
        return extract_cves(self.title, self.cve_text)


def extract_cves(*texts: str | None) -> frozenset[str]:
    """Return the normalised (upper-case) CVE ids found in the given texts."""
    found: set[str] = set()
    for text in texts:
        if not text:
            continue
        found.update(match.upper() for match in CVE_PATTERN.findall(text))
    return frozenset(found)


def normalize_title(title: str) -> str:
    """Lower-case, NFKC-fold and strip punctuation/whitespace.

    Chinese and English titles both survive this, which keeps one similarity
    metric usable across the mixed corpus.
    """
    if not title:
        return ""
    text = unicodedata.normalize("NFKC", title).lower()
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[\s\W_]+", "", text)
    return text


def shingles(text: str, size: int = SHINGLE_SIZE) -> set[str]:
    normalized = normalize_title(text)
    if not normalized:
        return set()
    if len(normalized) <= size:
        return {normalized}
    return {normalized[i : i + size] for i in range(len(normalized) - size + 1)}


def jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    intersection = len(left & right)
    if not intersection:
        return 0.0
    return intersection / len(left | right)


def containment(left: set[str], right: set[str]) -> float:
    """Overlap relative to the smaller set (catches digests and reposts)."""
    if not left or not right:
        return 0.0
    return len(left & right) / min(len(left), len(right))


def title_similarity(left: str, right: str) -> float:
    return jaccard(shingles(left), shingles(right))


def title_containment(left: str, right: str) -> float:
    return containment(shingles(left), shingles(right))


def _find(parent: dict[int, int], key: int) -> int:
    root = key
    while parent[root] != root:
        root = parent[root]
    while parent[key] != root:
        parent[key], key = root, parent[key]
    return root


def _union(parent: dict[int, int], left: int, right: int) -> None:
    left_root, right_root = _find(parent, left), _find(parent, right)
    if left_root != right_root:
        parent[right_root] = left_root


@dataclass
class DuplicateGroup:
    keys: list[int]
    reasons: set[str]

    @property
    def size(self) -> int:
        return len(self.keys)


def group_duplicates(
    items: Sequence[Item],
    title_threshold: float = DEFAULT_TITLE_THRESHOLD,
    containment_threshold: float = DEFAULT_CONTAINMENT,
) -> list[DuplicateGroup]:
    """Cluster items that describe the same event. O(n^2), fine up to ~10k."""
    parent = {item.key: item.key for item in items}
    reasons: dict[int, set[str]] = {item.key: set() for item in items}
    shingle_cache = {item.key: shingles(item.title) for item in items}

    for i, left in enumerate(items):
        for right in items[i + 1 :]:
            reason = None
            if left.url and left.url == right.url:
                reason = "url"
            elif left.cves and left.cves == right.cves:
                reason = "cve"
            else:
                left_grams = shingle_cache[left.key]
                right_grams = shingle_cache[right.key]
                if jaccard(left_grams, right_grams) >= title_threshold:
                    reason = "title"
                elif (
                    min(len(left_grams), len(right_grams)) >= MIN_SHINGLES_FOR_CONTAINMENT
                    and containment(left_grams, right_grams) >= containment_threshold
                ):
                    reason = "digest"
            if reason:
                _union(parent, left.key, right.key)
                reasons[left.key].add(reason)
                reasons[right.key].add(reason)

    buckets: dict[int, list[int]] = {}
    for item in items:
        buckets.setdefault(_find(parent, item.key), []).append(item.key)

    groups: list[DuplicateGroup] = []
    for keys in buckets.values():
        merged_reasons: set[str] = set()
        for key in keys:
            merged_reasons |= reasons[key]
        groups.append(DuplicateGroup(keys=sorted(keys), reasons=merged_reasons))
    groups.sort(key=lambda group: (-group.size, group.keys[0]))
    return groups


def similarity_sensitivity(
    items: Sequence[Item], thresholds: Iterable[float] = (0.70, 0.75, 0.80, 0.85, 0.90)
) -> dict[float, int]:
    """How many groups each threshold would produce. Used to pick a value."""
    return {
        threshold: len(group_duplicates(items, title_threshold=threshold))
        for threshold in thresholds
    }
