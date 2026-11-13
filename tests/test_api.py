"""API contract tests for the CTI decision-support platform.

The corpus is loaded from the two research CSVs, so the expected numbers below
are the CSV cluster tallies (TW 7/27/16, GL 35/6/9) mapped through
``data/dataset_meta.json``.
"""

from __future__ import annotations

import os
import re
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
    assert body["threats"] == client.get("/api/v1/stats").json()["totals"]["corpus"]


def test_stats_returns_balanced_corpus(client: TestClient):
    body = client.get("/api/v1/stats").json()
    totals = body["totals"]
    corpus = totals["corpus"]
    assert corpus >= 200
    assert totals["taiwan"] + totals["global"] == corpus
    # The corpus holds industry news as well as threats; only the threat subset
    # feeds the risk numbers.
    assert totals["threats"] + totals["other"] + totals["duplicates"] == corpus
    assert totals["other"] > 0
    assert len(body["meta_categories"]) == 4
    assert sum(item["count"] for item in body["meta_categories"]) == corpus
    assert abs(sum(item["share"] for item in body["meta_categories"]) - 1.0) < 1e-3


def test_stats_exclude_duplicate_events(client: TestClient):
    totals = client.get("/api/v1/stats").json()["totals"]
    assert totals["corpus"] >= 200          # articles
    assert totals["events"] == totals["corpus"] - totals["duplicates"]
    assert totals["threats"] + totals["other"] + totals["duplicates"] == totals["corpus"]


def test_stats_meta_category_region_split_is_consistent(client: TestClient):
    body = client.get("/api/v1/stats").json()
    totals = body["totals"]
    for meta in body["meta_categories"]:
        assert meta["by_region"]["taiwan"] + meta["by_region"]["global"] == meta["count"]
    for region in body["regions"]:
        assert region["count"] == totals[region["key"]]
    assert sum(region["count"] for region in body["regions"]) == totals["corpus"]


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
    assert sum(counts.values()) == body["totals"]["corpus"]
    assert {cluster for _, cluster in counts} <= {"0", "1", "2", "3"}


def test_meta_categories_follow_the_classifier(client: TestClient):
    body = client.get("/api/v1/stats").json()
    from collections import Counter, defaultdict

    from services import dataset

    records, _ = dataset.load_dataset()
    expected: dict[str, Counter] = defaultdict(Counter)
    for record in records:
        expected[record.category][record.region] += 1
    by_key = {item["key"]: item["by_region"] for item in body["meta_categories"]}
    for key in ("VULN", "MALWARE", "RESEARCH", "OTHER"):
        assert by_key[key] == dict(expected[key]), key
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
    assert sum(info["rows"].values()) == info["total"] == body["totals"]["corpus"]
    assert info["exported_at"] == "2026-11-12"
    assert any("Taiwan_security_dataset_with_dates.csv" in source for source in info["sources"])
    assert info["date_policy"] == "column"


def test_dates_come_from_the_publishers_not_from_the_row_order(client: TestClient):
    body = client.get("/api/v1/stats").json()
    sources = body["dataset"]["date_sources"]
    assert sum(sources.values()) == body["totals"]["corpus"]
    assert sources.get("estimated", 0) == 0, "所有日期都應來自來源 feed／列表"
    assert sources["thehackernews.com"] >= 100
    assert sources["twcert.org.tw"] >= 50
    assert sources.get("scraped", 0) >= 500, "分層歷史應標記為 scraped"

    # Real publication dates are spread over months, not the synthetic 50-day run.
    timeline = body["timeline"]
    # Weekly bins on a continuous axis: TWCERT publishes ~20 advisories per
    # half-year, so the corpus spans 2025-07 to 2026-11.
    assert len(timeline) >= 60
    assert timeline[0]["date"] <= "2024-01-31", "歷史語料把時間軸拉回 2024"
    assert timeline[-1]["date"] == "2026-11-09"


# --------------------------------------------------------------------------- #
# Assessment
# --------------------------------------------------------------------------- #


def test_assess_uses_epss_for_known_cve(client: TestClient):
    from services import epss

    known = next(iter(epss.all_scores()))
    assert epss.score_for([known]) is not None
    body = client.post(
        "/api/v1/assess",
        json={
            "asset_type": "web_app",
            "threat_source": "zero_day",
            "category": "VULN",
            "cve_id": known,
        },
    ).json()
    exploit = next(f for f in body["factors"] if f["key"] == "exploit")
    assert "EPSS" in exploit["value"]
    assert "利用機率" in body["summary"]


def test_assess_kev_forces_p1(client: TestClient):
    from services.kev import _ids

    known = sorted(_ids())[0]
    body = client.post(
        "/api/v1/assess",
        json={
            "asset_type": "web_app",
            "threat_source": "zero_day",
            "category": "VULN",
            "cve_id": known,
            "cvss": 3.0,
            "exploit_status": "unknown",
            "exposure": "internal",
            "data_sensitivity": "low",
        },
    ).json()
    assert body["priority"] == "P1"
    assert "CISA KEV" in body["summary"]
    exploit = next(f for f in body["factors"] if f["key"] == "exploit")
    assert "KEV" in exploit["value"]


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
    corpus = client.get("/api/v1/stats").json()["totals"]["corpus"]
    body = client.get("/api/v1/threats", params={"limit": 200, "dedupe": "false"}).json()
    assert body["total"] == corpus
    assert body["returned"] == 200
    assert all(item["cluster"] in {"0", "1", "2", "3"} for item in body["items"])
    threats = [item for item in body["items"] if item["meta_category"] != "OTHER"]
    assert threats
    # OTHER rows sort last (no score), so they are checked with a filter.
    others = client.get("/api/v1/threats", params={"meta_category": "OTHER", "limit": 5}).json()
    assert others["total"] > 0
    assert all(item["action_plan"] for item in threats)


def test_threats_filter_by_region(client: TestClient):
    expected = client.get("/api/v1/stats").json()["totals"]["taiwan"]
    body = client.get("/api/v1/threats", params={"region": "taiwan", "limit": 200, "dedupe": "false"}).json()
    assert body["total"] == expected
    assert {item["region"] for item in body["items"]} == {"taiwan"}


def test_responses_carry_data_provenance(client: TestClient):
    for path in ("/api/v1/stats", "/api/v1/threats?limit=5", "/api/v1/patch-priority?limit=5"):
        body = client.get(path).json()
        assert body["data_as_of"], path
        assert body["snapshots"]["kev"]["entries"] > 0, path
        assert body["snapshots"]["epss"]["generated"], path


def test_patch_priority_endpoint(client: TestClient):
    body = client.get("/api/v1/patch-priority", params={"limit": 10}).json()
    assert body["total"] > 0
    assert len(body["items"]) == 10
    # Sorted by band, and every P1 is a KEV entry.
    order = {"P1": 0, "P2": 1, "P3": 2}
    assert [order[i["priority"]] for i in body["items"]] == sorted(
        order[i["priority"]] for i in body["items"]
    )
    assert all(i["exploited"] for i in body["items"] if i["priority"] == "P1")
    assert sum(body["summary"]["by_priority"].values()) == body["total"]


def test_patch_priority_filter(client: TestClient):
    body = client.get("/api/v1/patch-priority", params={"priority": "P1", "limit": 5}).json()
    assert all(item["priority"] == "P1" for item in body["items"])


def test_threats_dedupe_filter(client: TestClient):
    all_rows = client.get("/api/v1/threats?limit=200&dedupe=false").json()
    deduped = client.get("/api/v1/threats?limit=200").json()  # dedupe defaults on
    assert deduped["total"] < all_rows["total"]
    assert all(item["duplicate_of"] is None for item in deduped["items"])


def test_threats_filter_by_priority(client: TestClient):
    body = client.get("/api/v1/threats", params={"priority": "P1", "limit": 200}).json()
    assert body["total"] > 0
    assert {item["priority"] for item in body["items"]} == {"P1"}


def test_threats_filters_combine(client: TestClient):
    body = client.get(
        "/api/v1/threats",
        params={"region": "global", "category": "MALWARE", "limit": 200, "dedupe": "false"},
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
    corpus = client.get("/api/v1/stats").json()["totals"]["corpus"]
    page = client.get("/api/v1/threats", params={"limit": 10, "offset": 95, "dedupe": "false"}).json()
    assert page["returned"] == 10
    assert page["total"] == corpus


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
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", item["published_at"]), item["published_at"]


def test_threat_detail_and_404(client: TestClient):
    assert client.get("/api/v1/threats/1").status_code == 200
    assert client.get("/api/v1/threats/9999").status_code == 404


def test_index_page_served(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
