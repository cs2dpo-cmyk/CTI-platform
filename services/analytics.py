"""Aggregations that power the CISO overview dashboard.

Every number here is derived from the rows that were loaded from the research
CSVs — there is no hard-coded distribution.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable, Protocol

from services import risk_engine

META_ORDER = ["VULN", "MALWARE", "RESEARCH", "OTHER"]
RISK_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
RISK_LABELS = {"CRITICAL": "極高風險", "HIGH": "高風險", "MEDIUM": "中風險", "LOW": "低風險"}
PRIORITY_ORDER = ["P1", "P2", "P3"]

# The only columns `build_stats` reads. `/stats` loads just these so the ORM
# never materialises the free-text columns it does not use.
STATS_COLUMNS = (
    "title", "source", "region", "category", "cluster",
    "risk_score", "risk_level", "priority", "published_at", "duplicate_of",
)


class ThreatLike(Protocol):
    title: str
    source: str
    region: str
    category: str
    cluster: str | None
    risk_score: float
    risk_level: str
    priority: str
    published_at: date


def _as_dict(threat: ThreatLike) -> dict[str, Any]:
    return {
        "title": threat.title,
        "source": threat.source,
        "region": threat.region,
        "category": threat.category,
        "cluster": threat.cluster or "",
        "risk_score": float(threat.risk_score or 0.0),
        "risk_level": threat.risk_level or "",
        "duplicate_of": getattr(threat, "duplicate_of", None),
        "priority": threat.priority or "",
        "published_at": threat.published_at,
    }


def _share(count: int, total: int) -> float:
    return round(count / total, 4) if total else 0.0


def _avg(values: Iterable[float]) -> float:
    values = list(values)
    return round(sum(values) / len(values), 1) if values else 0.0


def _cluster_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Region × cluster tally, with the Meta-Category that cluster maps to."""
    buckets: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (row["region"], row["cluster"])
        bucket = buckets.setdefault(
            key,
            {
                "region": row["region"],
                "cluster": row["cluster"],
                "category": row["category"],
                "count": 0,
                "breakdown": Counter(),
            },
        )
        bucket["count"] += 1
        bucket["breakdown"][row["category"]] += 1

    for bucket in buckets.values():
        # research_overrides can mix categories inside one cluster: report the
        # dominant one and keep the full split for the tooltip.
        dominant = bucket["breakdown"].most_common(1)[0][0]
        bucket["category"] = dominant
        bucket["breakdown"] = dict(bucket["breakdown"])
    return sorted(
        buckets.values(), key=lambda item: (item["region"], int(item["cluster"] or 0))
    )


def build_stats(threats: list[ThreatLike], dataset_info: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return every aggregation the dashboard renders, computed from the store.

    Two populations live in the corpus: threat intelligence (VULN / MALWARE /
    RESEARCH) and industry news (OTHER). Only the first drives the risk numbers,
    the averages, the decision matrix and the timeline; the second is reported
    as an explicit count so the corpus total still adds up.
    """
    rows = [_as_dict(threat) for threat in threats]
    corpus = len(rows)
    # Duplicate coverage (the same event reported by two sources) inflates every
    # rate, so the risk numbers are computed on distinct events only. The corpus
    # size still counts articles.
    duplicates = sum(1 for row in rows if row.get("duplicate_of"))
    scored = [
        row for row in rows
        if row["category"] != "OTHER" and not row.get("duplicate_of")
    ]
    total = len(scored)

    region_counts = Counter(row["region"] for row in rows)
    meta_counts = Counter(row["category"] for row in rows)
    risk_counts = Counter(row["risk_level"] for row in scored)
    priority_counts = Counter(row["priority"] for row in scored)
    source_counts = Counter(row["source"] for row in scored)

    meta_by_region: dict[str, Counter[str]] = defaultdict(Counter)
    region_meta: dict[str, Counter[str]] = defaultdict(Counter)
    region_score_sum: dict[str, float] = defaultdict(float)
    region_threats: dict[str, int] = defaultdict(int)
    for row in rows:
        meta_by_region[row["category"]][row["region"]] += 1
    for row in scored:
        region_meta[row["region"]][row["category"]] += 1
        region_score_sum[row["region"]] += row["risk_score"]
        region_threats[row["region"]] += 1

    regions = []
    for key, label in (("taiwan", "台灣在地"), ("global", "國際來源")):
        count = region_counts.get(key, 0)
        threat_count = region_threats.get(key, 0)
        top = region_meta[key].most_common(1)
        regions.append(
            {
                "key": key,
                "label": label,
                "count": count,
                "share": _share(count, corpus),
                "avg_score": round(region_score_sum[key] / threat_count, 1) if threat_count else 0.0,
                "top_category": risk_engine.CATEGORY_TAXONOMY[top[0][0]]["label"] if top else "—",
            }
        )

    meta_categories = []
    for key in META_ORDER:
        meta = risk_engine.META_CATEGORY_META[key]
        count = meta_counts.get(key, 0)
        meta_categories.append(
            {
                "key": key,
                "label": meta["label"],
                "label_en": meta["label_en"],
                "count": count,
                "share": _share(count, corpus),
                "by_region": {
                    "taiwan": meta_by_region[key].get("taiwan", 0),
                    "global": meta_by_region[key].get("global", 0),
                },
            }
        )

    clusters = _cluster_rows(rows)
    for item in clusters:
        item["label"] = f"C{item['cluster']}" if item["cluster"] != "" else "—"
        item["category_label"] = risk_engine.CATEGORY_TAXONOMY[item["category"]]["label"]

    risk_levels = [
        {
            "key": key,
            "label": RISK_LABELS[key],
            "count": risk_counts.get(key, 0),
            "share": _share(risk_counts.get(key, 0), total),
        }
        for key in RISK_ORDER
    ]

    priorities = [
        {
            "key": key,
            "label": risk_engine.PRIORITY_META[key]["label"],
            "count": priority_counts.get(key, 0),
            "share": _share(priority_counts.get(key, 0), total),
        }
        for key in PRIORITY_ORDER
    ]

    sources = [
        {"key": source, "label": source, "count": count, "share": _share(count, total)}
        for source, count in source_counts.most_common()
    ]

    # Weekly bins on a continuous axis. A corpus that spans 16 months (TWCERT
    # publishes ~20 advisories per half-year) must not plot one point per
    # *day that happens to have news*: that draws a six-month gap as one step.
    def week_start(day: date) -> date:
        return day - timedelta(days=day.weekday())

    timeline_map: dict[date, dict[str, int]] = defaultdict(lambda: {"taiwan": 0, "global": 0})
    for row in scored:
        timeline_map[week_start(row["published_at"])][row["region"]] += 1

    timeline = []
    if timeline_map:
        cursor = min(timeline_map)
        last = max(timeline_map)
        while cursor <= last:
            counts = timeline_map.get(cursor, {"taiwan": 0, "global": 0})
            timeline.append({
                "date": cursor.isoformat(),
                "taiwan": counts["taiwan"],
                "global": counts["global"],
                "total": counts["taiwan"] + counts["global"],
            })
            cursor += timedelta(days=7)

    matrix = risk_engine.build_decision_matrix(scored)

    p1 = priority_counts.get("P1", 0)
    other = sum(
        1 for row in rows if row["category"] == "OTHER" and not row.get("duplicate_of")
    )

    def dominant_meta(region: str) -> tuple[str, int]:
        best = max(meta_categories, key=lambda item: item["by_region"].get(region, 0))
        return best["label"], best["by_region"].get(region, 0)

    tw_top, tw_top_n = dominant_meta("taiwan")
    gl_top, gl_top_n = dominant_meta("global")
    top_meta = max(meta_categories, key=lambda item: item["count"], default=None)

    insights = [
        f"{total} 筆威脅情資中，{p1} 筆落入 P1（{_share(p1, total) * 100:.0f}%），"
        f"平均風險分數 {_avg(row['risk_score'] for row in scored)}，須於 24 小時內完成阻斷與修補。",
        f"Meta-Category 以「{top_meta['label'] if top_meta else '—'}」為最大族群"
        f"（{top_meta['count'] if top_meta else 0} 筆，{(top_meta['share'] * 100) if top_meta else 0:.0f}%）；"
        f"另有 {other} 筆產業與產品動態已排除於 P1–P3 與平均分數之外。",
        f"地區對比：台灣以「{tw_top}」（{tw_top_n} 筆）為主，"
        f"國際則以「{gl_top}」（{gl_top_n} 筆）為主，兩地聲量差距 {abs(tw_top_n - gl_top_n)} 筆，"
        "此時間差即是 CISO 提前部署的決策窗口。",
        f"「前瞻研究與平台治理」共 {meta_counts.get('RESEARCH', 0)} 筆"
        f"（台灣 {meta_by_region['RESEARCH'].get('taiwan', 0)} / 國際 {meta_by_region['RESEARCH'].get('global', 0)}），"
        "顯示本批語料仍以實務攻防為主，治理研究需由內部團隊補足。",
    ]

    dataset_block = dict(dataset_info or {})
    dataset_block.setdefault(
        "note", "情資由 research CSV 載入；所有統計皆由逐筆資料計算。"
    )
    accuracy = (dataset_block.get("validation") or {}).get("accuracy")

    return {
        "generated_at": datetime.now(timezone.utc),
        "model": {
            "pipeline": "TF-IDF 向量化 + K-Means 非監督式分群（主題探索）+ 逐篇規則分類 + 可解釋加權風險評分",
            "vectorizer": "Jieba 自訂資安詞典 + TF-IDF (1,000 維)",
            "clustering": "K-Means (K=3, Elbow 法選定)，僅作主題探索，不再決定 Meta-Category",
            "clusters": 3,
            "classification": "services/classify.py 規則式逐篇分類",
            "classification_accuracy": accuracy,
            "corpus": "TWCERT / iThome / The Hacker News",
            "balance": "50 台灣 : 50 國際 平衡對照組（含 12–15 篇產業動態，已排除於風險統計）",
            "scoring": "嚴重度 0.50 / 利用成熟度 0.30（EPSS 實測）/ 暴露程度 0.12 / CVE 具名 0.08；無隨機項",
        },
        "totals": {
            "corpus": corpus,
            "events": corpus - duplicates,
            "duplicates": duplicates,
            "threats": total,
            "other": other,
            "taiwan": region_counts.get("taiwan", 0),
            "global": region_counts.get("global", 0),
            "avg_score": _avg(row["risk_score"] for row in scored),
            "critical": risk_counts.get("CRITICAL", 0),
            "p1": p1,
            "days_covered": len(timeline),
        },
        "regions": regions,
        "meta_categories": meta_categories,
        "clusters": clusters,
        "dataset": dataset_block,
        "risk_levels": risk_levels,
        "priorities": priorities,
        "sources": sources,
        "timeline": timeline,
        "matrix": matrix,
        "insights": insights[:4],
    }
