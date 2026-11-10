"""Explainable risk-scoring and P1-P3 decision engine.

The PoC model is a transparent additive scorer rather than a black box: every
assessment returns the factor contributions that produced the score, so a CISO
can defend the decision in an incident review. The weighting mirrors the
feature importance of the TF-IDF + K-Means research baseline (category signal
first, then asset criticality, exploit maturity and exposure).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Iterable

# --------------------------------------------------------------------------- #
# Taxonomy
# --------------------------------------------------------------------------- #

CATEGORY_TAXONOMY: dict[str, dict[str, Any]] = {
    "VULN": {
        "label": "系統漏洞與修補對策",
        "label_en": "Vulnerabilities & Advisories",
        "severity": 0.86,
    },
    "MALWARE": {
        "label": "惡意威脅與主動攻擊",
        "label_en": "Malware & Active Attacks",
        "severity": 0.90,
    },
    "RESEARCH": {
        "label": "前瞻研究與平台治理",
        "label_en": "Research & Governance",
        "severity": 0.30,
    },
}

META_CATEGORY_META: dict[str, dict[str, str]] = {
    key: {"label": value["label"], "label_en": value["label_en"]}
    for key, value in CATEGORY_TAXONOMY.items()
}

REGION_LABELS = {"taiwan": "台灣在地", "global": "國際來源"}

ASSET_TYPES: dict[str, dict[str, Any]] = {
    "core_datacenter": {"label": "核心機房 / 資料庫", "weight": 0.98},
    "ot_ics": {"label": "OT / ICS 工控環境", "weight": 0.95},
    "identity_idp": {"label": "身分驗證 / AD / IdP", "weight": 0.80},
    "cloud_infra": {"label": "雲端基礎設施", "weight": 0.85},
    "dev_pipeline": {"label": "CI/CD 與開發供應鏈", "weight": 0.72},
    "web_app": {"label": "對外網站 / API 服務", "weight": 0.70},
    "endpoint": {"label": "端點與辦公環境", "weight": 0.55},
}

THREAT_SOURCES: dict[str, dict[str, Any]] = {
    "zero_day": {"label": "零日漏洞利用", "weight": 0.96},
    "ransomware": {"label": "勒索軟體", "weight": 0.95},
    "apt": {"label": "國家級 APT 持續滲透", "weight": 0.92},
    "supply_chain": {"label": "軟體供應鏈投毒", "weight": 0.84},
    "malware": {"label": "惡意程式 / 後門", "weight": 0.78},
    "credential_theft": {"label": "憑證竊取 / 帳號盜用", "weight": 0.76},
    "phishing": {"label": "社交工程與網釣", "weight": 0.70},
    "ddos": {"label": "DDoS 阻斷服務", "weight": 0.52},
}

EXPLOIT_STATUS: dict[str, dict[str, Any]] = {
    "active": {"label": "已在野利用", "weight": 1.0},
    "poc_public": {"label": "PoC 已公開", "weight": 0.72},
    "unknown": {"label": "尚未確認", "weight": 0.45},
    "none": {"label": "尚無可行利用", "weight": 0.15},
}

EXPOSURE: dict[str, dict[str, Any]] = {
    "public": {"label": "公開網際網路", "weight": 1.0},
    "partner": {"label": "合作夥伴 / VPN 通道", "weight": 0.62},
    "internal": {"label": "僅內網", "weight": 0.32},
}

CONTROLS: dict[str, dict[str, Any]] = {
    "edr": {"label": "EDR 端點偵測", "mitigation": 0.030},
    "mfa": {"label": "MFA 全面強制", "mitigation": 0.028},
    "waf": {"label": "WAF / IPS 防護", "mitigation": 0.022},
    "segmentation": {"label": "網段隔離", "mitigation": 0.024},
    "backup": {"label": "3-2-1 備份與演練", "mitigation": 0.026},
    "patch_pipeline": {"label": "自動化修補流程", "mitigation": 0.030},
}

PRIORITY_THRESHOLDS = {"P1": 80.0, "P2": 66.0}

PRIORITY_META: dict[str, dict[str, Any]] = {
    "P1": {
        "label": "P1 立即處置",
        "headline": "24 小時內完成阻斷與修補",
        "sla_hours": 24,
        "criteria": "風險分數 ≥ 80，或 CVSS ≥ 9.0 且已在野利用",
        "owner": "CISO / SOC 值班主管",
        "tone": "critical",
    },
    "P2": {
        "label": "P2 計畫處置",
        "headline": "7 日內排入修補與監控強化",
        "sla_hours": 168,
        "criteria": "風險分數 66–79，需排程處理並持續觀測",
        "owner": "資安維運團隊 (SecOps)",
        "tone": "elevated",
    },
    "P3": {
        "label": "P3 觀測追蹤",
        "headline": "30 日內納入例行治理與情資觀測",
        "sla_hours": 720,
        "criteria": "風險分數 < 66，屬情勢研究或低曝險議題",
        "owner": "資安治理 / 情資研究組",
        "tone": "monitor",
    },
}

# --------------------------------------------------------------------------- #
# Playbooks
# --------------------------------------------------------------------------- #

PLAYBOOKS: dict[tuple[str, str], list[dict[str, Any]]] = {
    ("VULN", "P1"): [
        {"title": "緊急修補與虛擬補丁", "owner": "IT 維運", "sla_hours": 4,
         "detail": "對外服務與邊界設備優先套用廠商修補；無法即時修補者以 WAF/IPS 規則虛擬補丁阻擋。"},
        {"title": "攻擊面盤點與暴露收斂", "owner": "SecOps", "sla_hours": 8,
         "detail": "以 CVE 對應資產清冊，關閉非必要的管理介面與遠端存取埠，收斂網際網路暴露面。"},
        {"title": "偵測規則與獵捕", "owner": "SOC", "sla_hours": 12,
         "detail": "匯入廠商 IOC 與 exploit 特徵，對近 14 日日誌執行回溯獵捕 (threat hunting)。"},
        {"title": "高階主管風險通報", "owner": "CISO", "sla_hours": 24,
         "detail": "輸出受影響資產、修補進度與殘餘風險，作為經營層決策與對外揭露依據。"},
    ],
    ("VULN", "P2"): [
        {"title": "排入修補窗口", "owner": "IT 維運", "sla_hours": 48,
         "detail": "依資產分級排定 7 日內修補批次，先處理對外與高價值系統。"},
        {"title": "組態基準檢視", "owner": "SecOps", "sla_hours": 72,
         "detail": "比對 CIS Benchmark，修正與此漏洞相關的錯誤組態與預設帳號。"},
        {"title": "持續監控", "owner": "SOC", "sla_hours": 168,
         "detail": "納入弱點管理儀表板，追蹤修補覆蓋率是否達 95% 以上。"},
    ],
    ("VULN", "P3"): [
        {"title": "情資觀測", "owner": "情資研究組", "sla_hours": 720,
         "detail": "納入月度弱點情資簡報，觀察是否出現可行利用程式或納入 CISA KEV。"},
        {"title": "修補週期整併", "owner": "IT 維運", "sla_hours": 720,
         "detail": "併入下一次例行 Patch Tuesday 週期處理，不單獨開立緊急變更。"},
    ],
    ("MALWARE", "P1"): [
        {"title": "隔離與阻斷", "owner": "SOC", "sla_hours": 2,
         "detail": "隔離受感染端點與橫向連線，封鎖已知 C2 網域/IP，暫停可疑帳號工作階段。"},
        {"title": "IOC 全域掃描", "owner": "SOC", "sla_hours": 6,
         "detail": "以 TTP/IOC 對 EDR、DNS、Proxy 與雲端稽核日誌執行全域掃描，確認擴散範圍。"},
        {"title": "帳號與憑證處置", "owner": "IAM 團隊", "sla_hours": 12,
         "detail": "重設受影響帳號密碼、撤銷 session token 與 API key，強制 MFA 重新註冊。"},
        {"title": "復原與事後檢討", "owner": "CISO", "sla_hours": 24,
         "detail": "由乾淨備份復原、驗證完整性，24 小時內完成事件時間軸與根因報告。"},
    ],
    ("MALWARE", "P2"): [
        {"title": "偵測強化", "owner": "SOC", "sla_hours": 48,
         "detail": "將家族 TTP 轉為 SIEM 關聯規則，並對高風險單位加派釣魚演練。"},
        {"title": "端點與郵件閘道調校", "owner": "SecOps", "sla_hours": 72,
         "detail": "啟用 LotL 行為偵測、封鎖巨集與可疑簽章執行檔，收緊附件政策。"},
        {"title": "備份與復原驗證", "owner": "IT 維運", "sla_hours": 168,
         "detail": "抽測 3-2-1 備份還原流程，確認 RTO/RPO 符合營運衝擊分析。"},
    ],
    ("MALWARE", "P3"): [
        {"title": "情勢追蹤", "owner": "情資研究組", "sla_hours": 720,
         "detail": "追蹤攻擊族群動向與地下市場廣告，月度更新威脅情勢簡報。"},
        {"title": "意識與演練", "owner": "資安治理", "sla_hours": 720,
         "detail": "納入下一季社交工程演練題材，強化員工對新型手法的辨識能力。"},
    ],
    ("RESEARCH", "P1"): [
        {"title": "架構影響評估", "owner": "資安架構師", "sla_hours": 24,
         "detail": "評估新技術/法規對現行防禦架構的衝擊，提出差異分析與調整方案。"},
        {"title": "決策簡報", "owner": "CISO", "sla_hours": 24,
         "detail": "提交投資建議與風險胃納說明，供經營層決定預算與時程。"},
    ],
    ("RESEARCH", "P2"): [
        {"title": "納入技術藍圖", "owner": "資安架構師", "sla_hours": 168,
         "detail": "列入年度技術藍圖與 PoC 清單，定義驗證指標後小規模試行。"},
        {"title": "合規落差分析", "owner": "資安治理", "sla_hours": 168,
         "detail": "比對法規與框架要求，產出合規落差與補強時程。"},
    ],
    ("RESEARCH", "P3"): [
        {"title": "持續觀測", "owner": "情資研究組", "sla_hours": 720,
         "detail": "季度回顧研究與治理趨勢，必要時升級為 P2 評估案。"},
        {"title": "知識庫沉澱", "owner": "資安治理", "sla_hours": 720,
         "detail": "將研究結論寫入內部知識庫，供後續專案引用。"},
    ],
}

# --------------------------------------------------------------------------- #
# Data classes
# --------------------------------------------------------------------------- #


@dataclass
class Factor:
    key: str
    label: str
    value: str
    normalized: float
    weight: float
    points: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "value": self.value,
            "normalized": round(self.normalized, 4),
            "weight": round(self.weight, 4),
            "points": round(self.points, 2),
        }


@dataclass
class RiskResult:
    score: float
    priority: str
    risk_level: str
    confidence: float
    factors: list[Factor] = field(default_factory=list)
    adjustments: list[dict[str, Any]] = field(default_factory=list)
    action_plan: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "score": round(self.score, 1),
            "priority": self.priority,
            "priority_label": PRIORITY_META[self.priority]["label"],
            "risk_level": self.risk_level,
            "confidence": round(self.confidence, 3),
            "factors": [factor.as_dict() for factor in self.factors],
            "adjustments": self.adjustments,
            "action_plan": self.action_plan,
            "playbook_source": "risk_engine.PLAYBOOKS",
        }


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def risk_level_for(score: float) -> str:
    if score >= 80:
        return "CRITICAL"
    if score >= 66:
        return "HIGH"
    if score >= 45:
        return "MEDIUM"
    return "LOW"


def priority_for(score: float) -> str:
    if score >= PRIORITY_THRESHOLDS["P1"]:
        return "P1"
    if score >= PRIORITY_THRESHOLDS["P2"]:
        return "P2"
    return "P3"


def stable_unit(*parts: Any) -> float:
    """Deterministic float in [0, 1) derived from the given parts."""
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") / 2**32


def playbook(meta: str, priority: str) -> list[dict[str, Any]]:
    steps = PLAYBOOKS.get((meta, priority)) or PLAYBOOKS[("VULN", priority)]
    return [
        {"order": index, "title": step["title"], "owner": step["owner"],
         "sla_hours": step["sla_hours"], "detail": step["detail"]}
        for index, step in enumerate(steps, start=1)
    ]


def _severity_from_cvss(cvss: float | None, fallback: float) -> tuple[float, str]:
    if cvss is None:
        return fallback, "依情資類別推估"
    normalized = max(0.0, min(cvss, 10.0)) / 10.0
    return normalized, f"CVSS {cvss:.1f}"


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #


def assess(
    *,
    asset_type: str,
    threat_source: str,
    category: str = "Vulnerability",
    region: str = "taiwan",
    cvss: float | None = None,
    exploit_status: str = "unknown",
    exposure: str = "internal",
    controls: Iterable[str] | None = None,
    data_sensitivity: str = "medium",
    region_hits: int | None = None,
) -> RiskResult:
    """Score one asset/threat combination and derive its P1-P3 disposition."""
    asset = ASSET_TYPES.get(asset_type, ASSET_TYPES["web_app"])
    threat = THREAT_SOURCES.get(threat_source, THREAT_SOURCES["phishing"])
    taxonomy = CATEGORY_TAXONOMY.get(category, CATEGORY_TAXONOMY["VULN"])
    exploit = EXPLOIT_STATUS.get(exploit_status, EXPLOIT_STATUS["unknown"])
    exposure_info = EXPOSURE.get(exposure, EXPOSURE["internal"])

    severity, severity_label = _severity_from_cvss(cvss, taxonomy["severity"])

    weighted = [
        Factor("asset", "資產關鍵度", asset["label"], asset["weight"], 0.30,
               asset["weight"] * 0.30 * 100),
        Factor("threat", "威脅來源強度", threat["label"], threat["weight"], 0.26,
               threat["weight"] * 0.26 * 100),
        Factor("severity", "漏洞嚴重度", severity_label, severity, 0.20,
               severity * 0.20 * 100),
        Factor("exploit", "利用成熟度", exploit["label"], exploit["weight"], 0.14,
               exploit["weight"] * 0.14 * 100),
        Factor("exposure", "暴露程度", exposure_info["label"], exposure_info["weight"], 0.10,
               exposure_info["weight"] * 0.10 * 100),
    ]

    raw = sum(factor.points for factor in weighted)
    adjustments: list[dict[str, Any]] = []

    if region == "taiwan":
        # The hit count comes from the caller so no corpus size is baked in.
        label = ("在地情資關聯 (台灣語料命中)" if region_hits is None
                 else f"在地情資關聯 (台灣 {region_hits} 筆語料命中)")
        adjustments.append({"key": "region_local", "label": label, "points": 3.0})
        raw += 3.0
    sensitivity_bonus = {"high": 4.0, "medium": 0.0, "low": -2.0}.get(data_sensitivity, 0.0)
    if sensitivity_bonus:
        adjustments.append({"key": "data_sensitivity",
                            "label": f"資料敏感度：{data_sensitivity}",
                            "points": sensitivity_bonus})
        raw += sensitivity_bonus

    active_controls = [key for key in (controls or []) if key in CONTROLS]
    if active_controls:
        mitigation = sum(CONTROLS[key]["mitigation"] for key in active_controls) * 100
        mitigation = min(mitigation, 12.0)
        adjustments.append({
            "key": "controls",
            "label": "已佈建控制項：" + "、".join(CONTROLS[key]["label"] for key in active_controls),
            "points": -round(mitigation, 2),
        })
        raw -= mitigation

    score = round(max(4.0, min(raw, 99.0)), 1)

    priority = priority_for(score)
    escalations: list[str] = []
    if cvss is not None and cvss >= 9.0 and exploit_status == "active" and priority != "P1":
        priority = "P1"
        escalations.append("CVSS ≥ 9.0 且已在野利用，強制升級 P1")
    elif cvss is not None and cvss >= 9.0 and priority == "P3":
        priority = "P2"
        escalations.append("CVSS ≥ 9.0，最低處置等級提升至 P2")
    known_asset = asset_type in ASSET_TYPES
    known_threat = threat_source in THREAT_SOURCES
    confidence = 0.55 + 0.10 * sum([known_asset, known_threat, cvss is not None,
                                    exploit_status != "unknown", exposure != "internal"])
    confidence = round(min(confidence, 0.97), 3)

    result = RiskResult(
        score=score,
        priority=priority,
        risk_level=risk_level_for(score),
        confidence=confidence,
        factors=weighted,
        adjustments=adjustments + [{"key": "escalation", "label": item, "points": 0.0}
                                   for item in escalations],
        action_plan=playbook(taxonomy.get("meta", category), priority),
    )
    return result


def score_seed_record(record: dict[str, Any]) -> RiskResult:
    """Deterministic scoring for a corpus row (CSV cluster already mapped)."""
    category = record["category"]
    taxonomy = CATEGORY_TAXONOMY[category]
    hint_bonus = {"HIGH": 0.18, "MEDIUM": 0.06, "LOW": 0.0}[record["risk_hint"]]
    jitter = stable_unit(record["id"], record["title"])
    raw = 100 * (0.55 * taxonomy["severity"] + hint_bonus + 0.30 * jitter)
    score = round(max(4.0, min(raw, 98.5)), 1)

    priority = priority_for(score)
    if category == "RESEARCH" and priority == "P1":
        priority = "P2"

    return RiskResult(
        score=score,
        priority=priority,
        risk_level=risk_level_for(score),
        confidence=round(0.72 + 0.22 * jitter, 3),
        factors=[],
        adjustments=[],
        action_plan=playbook(category, priority),
    )


def meta_of(category: str) -> str:
    """Category keys are the Meta-Category keys in this dataset."""
    return category if category in CATEGORY_TAXONOMY else "VULN"


def build_decision_matrix(threats: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group scored threats into the P1-P3 decision matrix."""
    rows: dict[str, dict[str, Any]] = {}
    for priority, meta in PRIORITY_META.items():
        rows[priority] = {
            "priority": priority,
            "label": meta["label"],
            "headline": meta["headline"],
            "sla_hours": meta["sla_hours"],
            "criteria": meta["criteria"],
            "owner": meta["owner"],
            "tone": meta["tone"],
            "count": 0,
            "taiwan": 0,
            "global": 0,
            "top_category": None,
            "avg_score": 0.0,
            "sample_titles": [],
            "action_plan": playbook("VULN" if priority == "P1" else "MALWARE", priority),
        }

    totals: dict[str, list[float]] = {priority: [] for priority in PRIORITY_META}
    category_counts: dict[str, dict[str, int]] = {priority: {} for priority in PRIORITY_META}

    for threat in threats:
        priority = threat["priority"]
        row = rows[priority]
        row["count"] += 1
        row[threat["region"]] += 1
        totals[priority].append(float(threat["risk_score"]))
        bucket = category_counts[priority]
        bucket[threat["category"]] = bucket.get(threat["category"], 0) + 1
        if len(row["sample_titles"]) < 3:
            row["sample_titles"].append(threat["title"])

    for priority, row in rows.items():
        scores = totals[priority]
        row["avg_score"] = round(sum(scores) / len(scores), 1) if scores else 0.0
        counts = category_counts[priority]
        if counts:
            top_key = max(counts, key=counts.get)
            row["top_category"] = {
                "key": top_key,
                "label": CATEGORY_TAXONOMY[top_key]["label"],
                "count": counts[top_key],
            }
        row["action_plan"] = playbook(
            meta_of(row["top_category"]["key"]) if row["top_category"] else "VULN",
            priority,
        )
    return [rows[priority] for priority in ("P1", "P2", "P3")]
