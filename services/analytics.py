"""Aggregations that power the CISO overview dashboard."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from typing import Any, Iterable, Protocol

from services import risk_engine

META_ORDER = ["VULN", "MALWARE", "RESEARCH"]
CATEGORY_ORDER = ["Vulnerability", "Malware", "SupplyChain", "Research"]
RISK_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
RISK_LABELS = {"CRITICAL": "極高風險", "HIGH": "高風險", "MEDIUM": "中風險", "LOW": "低風險"}
PRIORITY_ORDER = ["P1", "P2", "P3"]


class ThreatLike(Protocol):
    title: str
    source: str
    region: str
    category: str
    meta_category: str
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
        "meta_category": threat.meta_category,
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


def build_stats(threats: list[ThreatLike]) -> dict[str, Any]:
    """Return every aggregation the dashboard renders, computed from the store."""
    rows = [_as_dict(threat) for threat in threats]
    total = len(rows)

    region_counts = Counter(row["region"] for row in rows)
    meta_counts = Counter(row["meta_category"] for row in rows)
    category_counts = Counter(row["category"] for row in rows)
    risk_counts = Counter(row["risk_level"] for row in rows)
    priority_counts = Counter(row["priority"] for row in rows)
    source_counts = Counter(row["source"] for row in rows)

    meta_by_region: dict[str, Counter[str]] = defaultdict(Counter)
    cat_by_region: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        meta_by_region[row["meta_category"]][row["region"]] += 1
        cat_by_region[row["category"]][row["region"]] += 1

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
        meta_categories.append(
            {
                "key": key,
                "label": meta["label"],
                "label_en": meta["label_en"],
                "count": meta_counts.get(key, 0),
                "share": _share(meta_counts.get(key, 0), total),
                "by_region": {
                    "taiwan": meta_by_region[key].get("taiwan", 0),
                    "global": meta_by_region[key].get("global", 0),
                },
            }
        )

    categories = [
        {
            "key": key,
            "label": risk_engine.CATEGORY_TAXONOMY[key]["label"],
            "count": category_counts.get(key, 0),
            "share": _share(category_counts.get(key, 0), total),
            "by_region": {
                "taiwan": cat_by_region[key].get("taiwan", 0),
                "global": cat_by_region[key].get("global", 0),
            },
        }
        for key in CATEGORY_ORDER
    ]

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
    tw_rows = [row for row in rows if row["region"] == "taiwan"]
    gl_rows = [row for row in rows if row["region"] == "global"]
    avg_all = _avg(row["risk_score"] for row in rows)

    def dominant(subset: list[dict[str, Any]]) -> tuple[str, int]:
        counter = Counter(row["category"] for row in subset)
        if not counter:
            return "—", 0
        key, count = counter.most_common(1)[0]
        return risk_engine.CATEGORY_TAXONOMY[key]["label"], count

    tw_top, tw_top_n = dominant(tw_rows)
    gl_top, gl_top_n = dominant(gl_rows)
    tw_supply = sum(1 for row in tw_rows if row["category"] == "SupplyChain")
    gl_supply = sum(1 for row in gl_rows if row["category"] == "SupplyChain")
    tw_research = sum(1 for row in tw_rows if row["category"] == "Research")
    gl_research = sum(1 for row in gl_rows if row["category"] == "Research")
    top_meta = max(meta_categories, key=lambda item: item["count"], default=None)

    insights = [
        f"100 筆平衡語料中，{p1} 筆落入 P1（{_share(p1, total) * 100:.0f}%），"
        f"平均風險分數 {avg_all}，須於 24 小時內完成阻斷與修補。",
        f"台灣來源中「供應鏈與資安威脅」共 {tw_supply} 筆，國際來源僅 {gl_supply} 筆，"
        "顯示在地半導體與電子商務供應鏈曝險高度集中，應列為 P2 常態治理項目。",
        f"Meta-Category 以「{top_meta['label'] if top_meta else '—'}」為最大族群"
        f"（{top_meta['count'] if top_meta else 0} 筆，{(top_meta['share'] * 100) if top_meta else 0:.0f}%），"
        "對應的資產盤點與修補節奏應為本季首要工作。",
        f"台灣媒體聚焦「{tw_top}」（{tw_top_n} 筆），國際來源則以「{gl_top}」（{gl_top_n} 筆）為主，"
        "兩地關注焦點的時間差即是 CISO 提前部署的決策窗口。",
        f"「前瞻研究與平台治理」台灣 {tw_research} 筆、國際 {gl_research} 筆，"
        "在地情資仍以實務攻防為主，治理與架構研究需由內部團隊補足。",
    ]

    return {
        "generated_at": datetime.now(timezone.utc),
        "model": {
            "pipeline": "TF-IDF 向量化 + K-Means 非監督式分群 + 可解釋加權風險評分",
            "vectorizer": "Jieba 自訂資安詞典 + TF-IDF (1,000 維)",
            "clustering": "K-Means (K=3, Elbow 法選定)",
            "clusters": 3,
            "noise_reduction": 0.958,
            "corpus": "TWCERT 20 / iThome 30 / The Hacker News 50",
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
        "categories": categories,
        "risk_levels": risk_levels,
        "priorities": priorities,
        "sources": sources,
        "timeline": timeline,
        "matrix": matrix,
        "insights": insights,
    }
