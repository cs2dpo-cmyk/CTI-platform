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

from services.cve import extract_cves
from dataclasses import dataclass
from typing import Iterable, Sequence

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

    @property
    def title_cves(self) -> frozenset[str]:
        """Only the ids the headline itself names.

        A widely-referenced CVE (Brotli, Log4Shell) shows up in the body of many
        unrelated stories, so a body match alone must not merge two articles.
        """
        return extract_cves(self.title)


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
    """Cluster items that describe the same event.

    Clusters are **stars**: a member joins only when it is directly similar to
    the cluster's representative. Plain union-find would merge transitively
    (A~B, B~C implies A,C in one group even when A and C are unrelated), which
    on real data fused "Apple patch notes" with "PHP update" through a shared
    link. Star clustering keeps every merged pair defensible.
    """
    keys = [item.key for item in items]
    by_key = {item.key: item for item in items}
    grams = {item.key: shingles(item.title) for item in items}

    def link(left: Item, right: Item) -> str | None:
        if left.url and left.url == right.url:
            return "url"
        if left.cves and left.cves == right.cves and len(left.cves) >= 2:
            return "cve"
        if left.title_cves and right.title_cves and (left.title_cves & right.title_cves):
            return "cve"
        left_grams, right_grams = grams[left.key], grams[right.key]
        if jaccard(left_grams, right_grams) >= title_threshold:
            return "title"
        if (
            min(len(left_grams), len(right_grams)) >= MIN_SHINGLES_FOR_CONTAINMENT
            and containment(left_grams, right_grams) >= containment_threshold
        ):
            return "digest"
        return None

    neighbours: dict[int, set[int]] = {key: set() for key in keys}
    reasons: dict[tuple[int, int], str] = {}
    for index, left_key in enumerate(keys):
        for right_key in keys[index + 1 :]:
            reason = link(by_key[left_key], by_key[right_key])
            if reason:
                neighbours[left_key].add(right_key)
                neighbours[right_key].add(left_key)
                reasons[(left_key, right_key)] = reason

    assigned: set[int] = set()
    groups: list[DuplicateGroup] = []
    for key in keys:  # keys are ascending, so the representative is the oldest id
        if key in assigned:
            continue
        members = sorted(node for node in neighbours[key] if node not in assigned)
        assigned.add(key)
        assigned.update(members)
        group_reasons = {
            reasons.get((min(key, member), max(key, member)), "title") for member in members
        }
        groups.append(DuplicateGroup(keys=[key] + members, reasons=group_reasons))

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
