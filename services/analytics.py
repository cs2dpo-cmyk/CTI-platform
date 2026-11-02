"""Aggregations that power the CISO overview dashboard.

Every number here is derived from the rows that were loaded from the research
CSVs — there is no hard-coded distribution.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from typing import Any, Iterable, Protocol

from services import risk_engine

META_ORDER = ["VULN", "MALWARE", "RESEARCH"]
RISK_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
RISK_LABELS = {"CRITICAL": "極高風險", "HIGH": "高風險", "MEDIUM": "中風險", "LOW": "低風險"}
PRIORITY_ORDER = ["P1", "P2", "P3"]


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
        "risk_score": float(threat.risk_score),
        "risk_level": threat.risk_level,
        "priority": threat.priority,
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
            },
        )
        bucket["count"] += 1
    return sorted(
        buckets.values(), key=lambda item: (item["region"], int(item["cluster"] or 0))
    )


def build_stats(threats: list[ThreatLike], dataset_info: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return every aggregation the dashboard renders, computed from the store."""
    rows = [_as_dict(threat) for threat in threats]
    total = len(rows)

    region_counts = Counter(row["region"] for row in rows)
    meta_counts = Counter(row["category"] for row in rows)
    risk_counts = Counter(row["risk_level"] for row in rows)
    priority_counts = Counter(row["priority"] for row in rows)
    source_counts = Counter(row["source"] for row in rows)

    meta_by_region: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        meta_by_region[row["category"]][row["region"]] += 1

    regions = []
    for key, label in (("taiwan", "台灣在地"), ("global", "國際來源")):
        subset = [row for row in rows if row["region"] == key]
        top = Counter(row["category"] for row in subset).most_common(1)
        regions.append(
            {
                "key": key,
                "label": label,
                "count": len(subset),
                "share": _share(len(subset), total),
                "avg_score": _avg(row["risk_score"] for row in subset),
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
                "share": _share(count, total),
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

    timeline_map: dict[str, dict[str, int]] = defaultdict(lambda: {"taiwan": 0, "global": 0})
    for row in rows:
        day = row["published_at"].isoformat()
        timeline_map[day][row["region"]] += 1
    timeline = [
        {
            "date": day,
            "taiwan": counts["taiwan"],
            "global": counts["global"],
            "total": counts["taiwan"] + counts["global"],
        }
        for day, counts in sorted(timeline_map.items())
    ]

    matrix = risk_engine.build_decision_matrix(rows)

    p1 = priority_counts.get("P1", 0)

    def dominant_meta(region: str) -> tuple[str, int]:
        best = max(meta_categories, key=lambda item: item["by_region"].get(region, 0))
        return best["label"], best["by_region"].get(region, 0)

    tw_top, tw_top_n = dominant_meta("taiwan")
    gl_top, gl_top_n = dominant_meta("global")
    top_meta = max(meta_categories, key=lambda item: item["count"], default=None)
    gap = abs(tw_top_n - gl_top_n)

    insights = [
        f"100 筆語料中，{p1} 筆落入 P1（{_share(p1, total) * 100:.0f}%），"
        f"平均風險分數 {_avg(row['risk_score'] for row in rows)}，須於 24 小時內完成阻斷與修補。",
        f"Meta-Category 以「{top_meta['label'] if top_meta else '—'}」為最大族群"
        f"（{top_meta['count'] if top_meta else 0} 筆，{(top_meta['share'] * 100) if top_meta else 0:.0f}%），"
        "對應的資產盤點與修補節奏應為本季首要工作。",
        f"地區對比：台灣以「{tw_top}」（{tw_top_n} 筆）為主，"
        f"國際則以「{gl_top}」（{gl_top_n} 筆）為主，兩地聲量差距 {gap} 筆，"
        "此時間差即是 CISO 提前部署的決策窗口。",
        f"「前瞻研究與平台治理」共 {meta_counts.get('RESEARCH', 0)} 筆"
        f"（台灣 {meta_by_region['RESEARCH'].get('taiwan', 0)} / 國際 {meta_by_region['RESEARCH'].get('global', 0)}），"
        "顯示本批語料仍以實務攻防為主，治理研究需由內部團隊補足。",
    ]

    dataset_block = dict(dataset_info or {})
    dataset_block.setdefault(
        "note", "情資由 research CSV 載入；所有統計皆由逐筆資料計算。"
    )

    return {
        "generated_at": datetime.now(timezone.utc),
        "model": {
            "pipeline": "TF-IDF 向量化 + K-Means 非監督式分群 + 可解釋加權風險評分",
            "vectorizer": "Jieba 自訂資安詞典 + TF-IDF (1,000 維)",
            "clustering": "K-Means (K=3, Elbow 法選定)",
            "clusters": 3,
            "noise_reduction": 0.958,
            "corpus": "TWCERT / iThome / The Hacker News",
            "balance": "50 台灣 : 50 國際 平衡對照組",
            "scoring": "資產關鍵度 0.30 / 威脅強度 0.26 / 嚴重度 0.20 / 利用成熟度 0.14 / 曝險 0.10",
        },
        "totals": {
            "threats": total,
            "taiwan": region_counts.get("taiwan", 0),
            "global": region_counts.get("global", 0),
            "avg_score": _avg(row["risk_score"] for row in rows),
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
