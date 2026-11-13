"""CVE identifier extraction that survives the corpus cleaning step.

tools/build_corpus.py tokenises article text with jieba before writing the CSV,
which turns CVE-2025-5777 into "cve 2025 5777". A strict regex then finds almost
nothing, even though every article names its CVE.

Two patterns are therefore accepted and normalised to CVE-YYYY-NNNN:

    strict   CVE-2025-5777
    spaced   cve 2025 5777 / cve-2025 5777 / CVE_2025_5777

The tolerant form is deliberately narrow (a year plus a 4-7 digit id) so that
ordinary prose such as "cve 2025 report" is not treated as an identifier.
"""

from __future__ import annotations

import re

STRICT_PATTERN = re.compile(r"CVE-\d{4}-\d{4,7}", re.IGNORECASE)
SPACED_PATTERN = re.compile(r"\bCVE[\s\-_]*(\d{4})[\s\-_]+(\d{4,7})\b", re.IGNORECASE)


def extract_cves(*texts: str | None) -> frozenset[str]:
    """Return every CVE id found in the given texts, upper-cased and deduped."""
    found: set[str] = set()
    for text in texts:
        if not text:
            continue
        for match in STRICT_PATTERN.finditer(text):
            found.add(match.group(0).upper())
        for match in SPACED_PATTERN.finditer(text):
            found.add(f"CVE-{match.group(1)}-{match.group(2)}")
    return frozenset(found)


def extract_cve_list(*texts: str | None) -> list[str]:
    """Sorted list form, convenient for JSON storage."""
    return sorted(extract_cves(*texts))


def extract_cve(*texts: str | None) -> str | None:
    """The first id, or None. Kept for the single-column call sites."""
    ids = extract_cve_list(*texts)
    return ids[0] if ids else None
