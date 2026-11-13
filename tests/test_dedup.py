from services.dedup import (
    Item,
    extract_cves,
    group_duplicates,
    normalize_title,
    title_similarity,
)


def test_extract_cves_normalises_case_and_dedupes():
    found = extract_cves("cve-2026-1234 and CVE-2026-1234, plus CVE-2025-99999")
    assert found == frozenset({"CVE-2026-1234", "CVE-2025-99999"})


def test_extract_cves_ignores_text_without_ids():
    assert extract_cves("no identifiers here") == frozenset()
    assert extract_cves(None) == frozenset()


def test_normalize_title_folds_width_and_punctuation():
    assert normalize_title("ＣＶＥ-2026-1234！") == normalize_title("cve 2026 1234")


def test_title_similarity_flags_republished_story():
    a = "Cisco BroadWorks 漏洞遭積極利用，PoC 已公開"
    b = "Cisco BroadWorks 漏洞遭積極利用 PoC 已公開"
    assert title_similarity(a, b) > 0.8


def test_title_similarity_keeps_different_stories_apart():
    a = "Microsoft Exchange 更新修補 CVE-2026-1"
    b = "Lazarus 濫用南韓資安軟體部署惡意程式"
    assert title_similarity(a, b) < 0.3


def test_group_duplicates_merges_same_cve_across_sources():
    items = [
        Item(key=1, title="Exchange 修補公告", source="TWCERT", cve_text="CVE-2026-62911"),
        Item(key=2, title="Exchange patch ships", source="THN", cve_text="CVE-2026-62911"),
        Item(key=3, title="完全不同的新聞", source="iThome"),
    ]
    groups = group_duplicates(items)
    sizes = sorted(len(group.keys) for group in groups)
    assert sizes == [1, 2]
    merged = next(group for group in groups if len(group.keys) == 2)
    assert merged.reasons == {"cve"}


def test_group_duplicates_merges_by_title_and_url():
    items = [
        Item(key=1, title="同一個標題的新聞內容", source="A"),
        Item(key=2, title="同一個標題的新聞內容！", source="B"),
        Item(key=3, title="", source="C", url="https://example.com/x"),
        Item(key=4, title="", source="D", url="https://example.com/x"),
    ]
    groups = group_duplicates(items)
    assert len(groups) == 2
    assert {tuple(group.keys) for group in groups} == {(1, 2), (3, 4)}


def test_group_duplicates_handles_empty_input():
    assert group_duplicates([]) == []


def test_group_duplicates_catches_daily_digest_containment():
    digest = "【資安日報】11月11日，駭客利用大數據平臺Qubole被竊憑證，入侵數十家企業AWS環境竊取資料"
    story = "駭客利用大數據平臺Qubole被竊憑證，入侵數十家企業AWS環境竊取資料"
    items = [
        Item(key=1, title=digest, source="iThome"),
        Item(key=2, title=story, source="iThome"),
        Item(key=3, title="Node.js 發布安全性更新修補十項漏洞", source="iThome"),
    ]
    groups = group_duplicates(items)
    merged = next(group for group in groups if len(group.keys) == 2)
    assert merged.keys == [1, 2]
    assert "digest" in merged.reasons


def test_short_titles_are_not_merged_by_containment():
    # No CVE to fall back on, and too few shingles for the containment guard.
    items = [
        Item(key=1, title="Exchange 修補", source="A"),
        Item(key=2, title="Exchange 修補 已遭利用且廠商發布更新", source="B"),
    ]
    groups = group_duplicates(items)
    assert len(groups) == 2
