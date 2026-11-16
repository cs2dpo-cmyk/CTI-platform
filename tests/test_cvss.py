"""The CVSS fallback must read CVE records correctly and never invent a score."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import refresh_cvss  # noqa: E402


def record(*, cna=None, adp=None):
    return {"containers": {"cna": cna or {}, "adp": adp or []}}


def test_reads_cna_v3_1():
    payload = record(cna={"metrics": [{"cvssV3_1": {"baseScore": 9.4, "version": "3.1"}}]})
    assert refresh_cvss.score_from_record(payload) == (9.4, "3.1")


def test_prefers_v3_1_over_v4():
    payload = record(cna={"metrics": [
        {"cvssV4_0": {"baseScore": 8.0, "version": "4.0"}},
        {"cvssV3_1": {"baseScore": 7.5, "version": "3.1"}},
    ]})
    assert refresh_cvss.score_from_record(payload) == (7.5, "3.1")


def test_falls_back_to_adp():
    payload = record(
        cna={"metrics": []},
        adp=[{"metrics": [{"cvssV3_1": {"baseScore": 6.1, "version": "3.1"}}]}],
    )
    assert refresh_cvss.score_from_record(payload) == (6.1, "3.1")


def test_reads_legacy_top_level_block():
    payload = {"cvss": {"baseScore": 5.0, "version": "2.0"}}
    assert refresh_cvss.score_from_record(payload) == (5.0, "2.0")


def test_ignores_out_of_range_and_missing():
    payload = record(cna={"metrics": [{"cvssV3_1": {"baseScore": 11.5}}]})
    assert refresh_cvss.score_from_record(payload) is None
    assert refresh_cvss.score_from_record({}) is None


def test_snapshot_lookup_takes_the_highest_of_several_cves(monkeypatch):
    from services import cvss

    # A path inside the repo: pytest's tmp_path lives under a temp root this
    # sandbox refuses to scan.
    tmp = ROOT / ".tmp"
    tmp.mkdir(exist_ok=True)
    path = tmp / "cvss-test.json"
    path.write_text(
        '{"generated": "2026-11-16", "source": "test", "scores": {'
        '"CVE-2020-0001": {"score": 5.0, "version": "3.1"},'
        '"CVE-2020-0002": {"score": 9.8, "version": "3.1"}}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(cvss, "PATH", path)
    cvss.reset()
    assert cvss.score_for(["CVE-2020-0001", "CVE-2020-0002"]) == 9.8
    assert cvss.score_for("CVE-2020-0002") == 9.8
    assert cvss.score_for(["CVE-1999-9999"]) is None
    cvss.reset()
