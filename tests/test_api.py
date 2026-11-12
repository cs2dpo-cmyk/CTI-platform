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
    totals = body["totals"]
    assert totals["corpus"] == 100
    assert totals["taiwan"] == 50
    assert totals["global"] == 50
    # The corpus holds industry news as well as threats; only the threat subset
    # feeds the risk numbers.
    assert totals["threats"] + totals["other"] == totals["corpus"]
    assert totals["other"] == 15
    assert len(body["meta_categories"]) == 4
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
    # OTHER rows are not part of the matrix.
    body_total = client.get("/api/v1/stats").json()["totals"]["threats"]
    assert sum(row["count"] for row in matrix) == body_total
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


def test_meta_categories_follow_the_classifier(client: TestClient):
    body = client.get("/api/v1/stats").json()
    by_key = {item["key"]: item["by_region"] for item in body["meta_categories"]}
    # services/classify.py output on the current corpus; regenerate with
    # tools/eval_classifier.py if the rules or the CSVs change.
    assert by_key["VULN"] == {"taiwan": 10, "global": 12}
    assert by_key["MALWARE"] == {"taiwan": 19, "global": 27}
    assert by_key["RESEARCH"] == {"taiwan": 8, "global": 9}
    assert by_key["OTHER"] == {"taiwan": 13, "global": 2}
    for meta in body["meta_categories"]:
        assert meta["by_region"]["taiwan"] + meta["by_region"]["global"] == meta["count"]


def test_every_cluster_reports_a_known_dominant_category(client: TestClient):
    body = client.get("/api/v1/stats").json()
    # A cluster can mix categories now, so the field is the dominant label.
    categories = {row["category"] for row in body["clusters"]}
    assert categories <= {"VULN", "MALWARE", "RESEARCH", "OTHER"}
    for row in body["clusters"]:
        assert row["category_label"], "每個叢集都要有可讀的分類名稱"


def test_dataset_provenance_is_reported(client: TestClient):
    body = client.get("/api/v1/stats").json()
    info = body["dataset"]
    assert info["rows"] == {"taiwan": 50, "global": 50}
    assert info["total"] == 100
    assert info["exported_at"] == "2026-10-30"
    assert any("Taiwan_security_dataset_with_dates.csv" in source for source in info["sources"])
    assert info["date_policy"] == "column"


def test_dates_come_from_the_publishers_not_from_the_row_order(client: TestClient):
    body = client.get("/api/v1/stats").json()
    sources = body["dataset"]["date_sources"]
    assert sum(sources.values()) == 100
    assert sources.get("estimated", 0) == 0, "所有日期都應來自來源 feed／列表"
    assert sources["thehackernews.com"] == 50
    assert sources["twcert.org.tw"] == 20
    assert sources["ithome.com.tw"] == 30

    # Real publication dates are spread over months, not the synthetic 50-day run.
    timeline = body["timeline"]
    assert len(timeline) >= 10
    assert timeline[0]["date"] >= "2026-04-01"
    assert timeline[-1]["date"] == "2026-10-30"


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
    assert all(item["cluster"] in {"0", "1", "2"} for item in body["items"])
    threats = [item for item in body["items"] if item["meta_category"] != "OTHER"]
    others = [item for item in body["items"] if item["meta_category"] == "OTHER"]
    assert threats and others
    assert all(item["action_plan"] for item in threats)


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
    stats = client.get("/api/v1/stats").json()
    expected = next(
        item["by_region"]["global"] for item in stats["meta_categories"] if item["key"] == "MALWARE"
    )
    assert body["total"] == expected
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


def test_governance_articles_land_in_research(client: TestClient):
    body = client.get("/api/v1/threats", params={"category": "RESEARCH", "limit": 200}).json()
    titles = {item["title"] for item in body["items"]}
    assert {
        "Webinar: How to Build AI Threat Readiness Into Your Security Operations",
        "The Rise of the Threat Operator: How AI Will Redefine Security Operations and Careers",
        "Wazuh and AI for Enhanced SOC Workflows",
    } <= titles
    # RESEARCH never gets P1: it is a study/governance item, not an incident.
    for item in body["items"]:
        assert item["priority"] in {"P2", "P3"}
        assert item["source_url"].startswith("https://")


def test_other_rows_carry_no_disposition(client: TestClient):
    body = client.get("/api/v1/threats", params={"category": "OTHER", "limit": 200}).json()
    stats = client.get("/api/v1/stats").json()
    assert body["total"] == stats["totals"]["other"]
    for item in body["items"]:
        assert item["risk_score"] is None
        assert item["priority"] is None
        assert item["action_plan"] == []


def test_threat_items_expose_real_dates_and_source_links(client: TestClient):
    body = client.get("/api/v1/threats", params={"limit": 200}).json()
    for item in body["items"]:
        assert item["source_url"].startswith("https://"), item["title"]
        assert "2026-" in item["published_at"]


def test_threat_detail_and_404(client: TestClient):
    assert client.get("/api/v1/threats/1").status_code == 200
    assert client.get("/api/v1/threats/9999").status_code == 404


def test_index_page_served(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
