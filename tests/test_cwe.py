"""CWE extraction must read the CVE record without inventing an id."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import refresh_cwe  # noqa: E402


def record(*, cna=None, adp=None):
    return {"containers": {"cna": cna or {}, "adp": adp or []}}


def test_reads_cna_problem_types():
    payload = record(cna={"problemTypes": [{"descriptions": [
        {"cweId": "CWE-78", "description": "CWE-78: Improper Neutralization of Special Elements used in an OS Command"}
    ]}]})
    assert refresh_cwe.cwes_from_record(payload) == [
        {"id": "CWE-78", "name": "Improper Neutralization of Special Elements used in an OS Command"}
    ]


def test_falls_back_to_adp_and_dedupes():
    payload = record(
        cna={"problemTypes": [{"descriptions": [{"cweId": "CWE-20", "description": "CWE-20 Improper Input Validation"}]}]},
        adp=[{"problemTypes": [{"descriptions": [{"cweId": "CWE-20", "description": "CWE-20 Improper Input Validation"}]}]}],
    )
    assert refresh_cwe.cwes_from_record(payload) == [
        {"id": "CWE-20", "name": "Improper Input Validation"}
    ]


def test_family_mapping_for_known_cves():
    from services import cwe

    # CWE-77 command injection / CWE-119 memory buffer: fixed by the snapshot.
    assert cwe.family("CVE-2024-3400") == "RCE"
    assert cwe.family("CVE-2023-4966") == "MEMORY"
    assert cwe.family("CVE-1999-99999") == "UNKNOWN"
    assert cwe.family_label("RCE") == "遠端執行"


def test_ignores_non_cwe_entries():
    payload = record(cna={"problemTypes": [{"descriptions": [{"cweId": "NVD-CWE-Other", "description": "Other"}]}]})
    assert refresh_cwe.cwes_from_record(payload) == []
    assert refresh_cwe.cwes_from_record({}) == []
