"""API contract tests for the CTI decision-support platform.

The corpus is loaded from the two research CSVs, so the expected numbers below
are the CSV cluster tallies (TW 7/27/16, GL 35/6/9) mapped through
``data/dataset_meta.json``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TEST_DB = ROOT / "data" / "test_cti.db"
TEST_DB.parent.mkdir(parents=True, exist_ok=True)
if TEST_DB.exists():
    TEST_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"

import database  # noqa: E402
import main  # noqa: E402


@pytest.fixture(scope="module")
def client():
    database.init_db()
    with TestClient(main.app) as test_client:
        yield test_client


# --------------------------------------------------------------------------- #
# Health & overview
# --------------------------------------------------------------------------- #


def test_health_reports_seeded_corpus(client: TestClient):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["threats"] == 100


def test_stats_returns_balanced_corpus(client: TestClient):
    body = client.get("/api/v1/stats").json()
    assert body["totals"]["threats"] == 100
    assert body["totals"]["taiwan"] == 50
    assert body["totals"]["global"] == 50
    assert len(body["meta_categories"]) == 3
    assert sum(item["count"] for item in body["meta_categories"]) == 100
    assert abs(sum(item["share"] for item in body["meta_categories"]) - 1.0) < 1e-6


def test_stats_meta_category_region_split_is_consistent(client: TestClient):
    body = client.get("/api/v1/stats").json()
    for meta in body["meta_categories"]:
        assert meta["by_region"]["taiwan"] + meta["by_region"]["global"] == meta["count"]
    for region in body["regions"]:
        assert region["count"] == 50


def test_decision_matrix_covers_three_priorities(client: TestClient):
    body = client.get("/api/v1/stats").json()
    matrix = body["matrix"]
    assert [row["priority"] for row in matrix] == ["P1", "P2", "P3"]
    assert sum(row["count"] for row in matrix) == 100
    for row in matrix:
        assert row["action_plan"], "每個優先級都必須有處置建議"


# --------------------------------------------------------------------------- #
# CSV-driven dataset
# --------------------------------------------------------------------------- #


def test_cluster_tallies_match_the_csv_files(client: TestClient):
    body = client.get("/api/v1/stats").json()
    counts = {(row["region"], row["cluster"]): row["count"] for row in body["clusters"]}
    assert counts == {
        ("taiwan", "0"): 7,
        ("taiwan", "1"): 27,
        ("taiwan", "2"): 16,
        ("global", "0"): 35,
        ("global", "1"): 6,
        ("global", "2"): 9,
    }


def test_meta_categories_follow_the_cluster_mapping(client: TestClient):
    body = client.get("/api/v1/stats").json()
    by_key = {item["key"]: item["by_region"] for item in body["meta_categories"]}
    # taiwan: C0 + C1 -> MALWARE (34), C2 -> VULN (16)
    # global: C0 + C1 -> VULN (41), C2 -> MALWARE (9)
    assert by_key["VULN"] == {"taiwan": 16, "global": 41}
    assert by_key["MALWARE"] == {"taiwan": 34, "global": 9}
    assert by_key["RESEARCH"] == {"taiwan": 0, "global": 0}


def test_every_cluster_maps_to_a_known_category(client: TestClient):
    body = client.get("/api/v1/stats").json()
    categories = {row["category"] for row in body["clusters"]}
    assert categories <= {"VULN", "MALWARE", "RESEARCH"}
    for row in body["clusters"]:
        assert row["category_label"], "每個叢集都要有可讀的分類名稱"


def test_dataset_provenance_is_reported(client: TestClient):
    body = client.get("/api/v1/stats").json()
    info = body["dataset"]
    assert info["rows"] == {"taiwan": 50, "global": 50}
    assert info["total"] == 100
    assert info["exported_at"] == "2026-10-30"
    assert any("Taiwan_security_dataset_cleaned.csv" in source for source in info["sources"])
    assert info["date_policy"] == "row_order_backfill"


# --------------------------------------------------------------------------- #
# Assessment
# --------------------------------------------------------------------------- #


def test_assess_critical_inputs_return_p1(client: TestClient):
    response = client.post(
        "/api/v1/assess",
        json={
            "asset_type": "core_datacenter",
            "threat_source": "ransomware",
            "category": "MALWARE",
            "region": "taiwan",
            "cvss": 9.8,
            "exploit_status": "active",
            "exposure": "public",
            "data_sensitivity": "high",
            "cve_id": "CVE-2026-111497",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["priority"] == "P1"
    assert body["risk_level"] in {"CRITICAL", "HIGH"}
    assert body["score"] >= 86
    assert len(body["factors"]) == 5
    assert body["action_plan"]
    assert body["cve_id"] == "CVE-2026-111497"


def test_assess_low_risk_inputs_return_p3(client: TestClient):
    body = client.post(
        "/api/v1/assess",
        json={
            "asset_type": "endpoint",
            "threat_source": "ddos",
            "category": "RESEARCH",
            "region": "global",
            "exploit_status": "none",
            "exposure": "internal",
            "controls": ["edr", "mfa", "waf", "segmentation", "backup", "patch_pipeline"],
            "data_sensitivity": "low",
        },
    ).json()
    assert body["priority"] == "P3"
    assert body["score"] < 68


def test_assess_controls_reduce_score(client: TestClient):
    base = {"asset_type": "web_app", "threat_source": "phishing",
            "category": "VULN", "region": "taiwan"}
    without = client.post("/api/v1/assess", json=base).json()
    with_controls = client.post(
        "/api/v1/assess", json={**base, "controls": ["mfa", "waf"]}
    ).json()
    assert with_controls["score"] < without["score"]


def test_assess_rejects_malformed_cve(client: TestClient):
    response = client.post("/api/v1/assess", json={"cve_id": "CVE-26-1"})
    assert response.status_code == 422


def test_assess_rejects_cvss_out_of_range(client: TestClient):
    assert client.post("/api/v1/assess", json={"cvss": 11}).status_code == 422
    assert client.post("/api/v1/assess", json={"cvss": -1}).status_code == 422


def test_assess_rejects_unknown_asset_type(client: TestClient):
    assert client.post("/api/v1/assess", json={"asset_type": "toaster"}).status_code == 422


def test_assess_rejects_legacy_category_names(client: TestClient):
    # The taxonomy now uses the K-Means meta keys.
    assert client.post("/api/v1/assess", json={"category": "Malware"}).status_code == 422


# --------------------------------------------------------------------------- #
# Threat list
# --------------------------------------------------------------------------- #


def test_threats_returns_full_corpus(client: TestClient):
    body = client.get("/api/v1/threats", params={"limit": 200}).json()
    assert body["total"] == 100
    assert body["returned"] == 100
    assert all(item["action_plan"] for item in body["items"])
    assert all(item["cluster"] in {"0", "1", "2"} for item in body["items"])


def test_threats_filter_by_region(client: TestClient):
    body = client.get("/api/v1/threats", params={"region": "taiwan", "limit": 200}).json()
    assert body["total"] == 50
    assert {item["region"] for item in body["items"]} == {"taiwan"}


def test_threats_filter_by_priority(client: TestClient):
    body = client.get("/api/v1/threats", params={"priority": "P1", "limit": 200}).json()
    assert body["total"] > 0
    assert {item["priority"] for item in body["items"]} == {"P1"}


def test_threats_filters_combine(client: TestClient):
    body = client.get(
        "/api/v1/threats",
        params={"region": "global", "category": "MALWARE", "limit": 200},
    ).json()
    assert body["total"] == 9, "global cluster 2 的 9 篇就是 MALWARE"
    for item in body["items"]:
        assert item["region"] == "global"
        assert item["category"] == "MALWARE"


def test_threats_search_and_pagination(client: TestClient):
    body = client.get("/api/v1/threats", params={"q": "Flaw", "limit": 5}).json()
    assert body["total"] >= 1
    assert body["returned"] <= 5
    page = client.get("/api/v1/threats", params={"limit": 10, "offset": 95}).json()
    assert page["returned"] == 5
    assert page["total"] == 100


def test_threat_detail_and_404(client: TestClient):
    assert client.get("/api/v1/threats/1").status_code == 200
    assert client.get("/api/v1/threats/9999").status_code == 404


def test_index_page_served(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
