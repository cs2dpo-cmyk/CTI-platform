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


def test_ignores_non_cwe_entries():
    payload = record(cna={"problemTypes": [{"descriptions": [{"cweId": "NVD-CWE-Other", "description": "Other"}]}]})
    assert refresh_cwe.cwes_from_record(payload) == []
    assert refresh_cwe.cwes_from_record({}) == []
