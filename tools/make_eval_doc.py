"""Assemble docs/evaluation.md from the JSON reports.

Keeping the generator in the repo means the document can be rebuilt after any
model change instead of being hand-edited and drifting from the code.

    ./.venv/Scripts/python.exe tools/make_eval_doc.py
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "docs" / "evaluation.md"
LABELS = ["VULN", "MALWARE", "RESEARCH", "OTHER"]


def load(name: str) -> dict | None:
    path = DATA / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    holdout = load("holdout_report.json") or {}
    tuning = load("tuning_report.json") or {}
    kev = load("kev_report.json") or {}
    splits = load("time_split_report.json")
    snaps = load("snapshots.json") or {}

    connection = sqlite3.connect(f"file:{DATA / 'cti.db'}?mode=ro", uri=True)
    try:
        articles = connection.execute("select count(*) from threats").fetchone()[0]
        duplicates = connection.execute(
            "select count(*) from threats where duplicate_of is not null"
        ).fetchone()[0]
        first_day, last_day = connection.execute(
            "select min(published_at), max(published_at) from threats"
        ).fetchone()
        monthly = connection.execute(
            "select substr(published_at,1,7) m, count(*) c from threats group by m"
        ).fetchall()
        thin_months = sum(1 for _, count in monthly if count < 5)
    finally:
        connection.close()

    lines: list[str] = []

    def add(text: str = "") -> None:
        lines.append(text)

    add("# 評估結果（可直接引用）")
    add()
    add("> 本文件由 tools/make_eval_doc.py 從 data/*.json 自動產生，請勿手改。")
    add()

    add("## 1. 語料組成")
    add()
    add("| 項目 | 數值 |")
    add("|---|---|")
    add(f"| 文章數（原始語料） | {articles} |")
    add(f"| 重複事件 | {duplicates} |")
    add(f"| 去重後事件 | {articles - duplicates} |")
    add(
        f"| 期間 | {str(first_day)[:7]} ～ {str(last_day)[:7]}"
        f"（{len(monthly)} 個月，其中 {thin_months} 個月不到 5 筆） |"
    )
    add()

    add("## 2. 分類器表現")
    add()
    add("| 指標 | 值 | 說明 |")
    add("|---|---|---|")
    add("| 開發期準確率（in-sample） | 91% | 100 筆 gold，規則調參時使用 |")
    if holdout:
        add(f"| held-out 準確率 | {holdout['accuracy']:.0%} | 另 100 筆，雙人標註 + 第三人裁決 |")
        add(
            f"| 多數類別 baseline | {holdout['majority_baseline']['accuracy']:.0%} "
            f"| 全猜 {holdout['majority_baseline']['label']} |"
        )
        add(
            f"| 相對 baseline 提升 | "
            f"{holdout['accuracy'] - holdout['majority_baseline']['accuracy']:+.0%} | |"
        )
    add()
    add("> 注意：held-out 曾用於診斷誤差（修正產品動詞規則），因此該數字屬於看過測試集之後的結果；")
    add("> 嚴格獨立的測試需要擴充語料後重新切分。")
    add()

    if holdout:
        add("### 混淆矩陣（列＝人工標註，欄＝模型預測）")
        add()
        add("| 實際 \\ 預測 | " + " | ".join(LABELS) + " |")
        add("|---|" + "---|" * len(LABELS))
        for gold in LABELS:
            row = holdout["confusion"][gold]
            add("| **%s** | " % gold + " | ".join(str(row[p]) for p in LABELS) + " |")
        add()
        add("### 各類別指標")
        add()
        add("| 類別 | Precision | Recall | F1 | 樣本數 |")
        add("|---|---|---|---|---|")
        for label in LABELS:
            stats = holdout["per_class"][label]
            add(
                "| %s | %.2f | %.2f | %.2f | %d |"
                % (label, stats["precision"], stats["recall"], stats["f1"], stats["support"])
            )
        add()

    if tuning:
        add("## 3. 排序有效性（KEV 為 ground truth）")
        add()
        add("| 模型 | 交叉驗證 AUC |")
        add("|---|---|")
        names = {
            "baseline": "本系統（50/30/12/8 + EPSS）",
            "cvss": "純 CVSS 排序",
            "epss_only": "僅 EPSS",
            "logistic": "邏輯回歸（四因子）",
            "weights": "重新擬合權重",
        }
        for key, label in names.items():
            stats = tuning.get("cv", {}).get(key)
            if stats:
                add("| %s | %.3f ± %.3f |" % (label, stats["mean"], stats["std"]))
        add()
        if kev:
            add("| 指標 | 值 |")
            add("|---|---|")
            add("| KEV base rate（有 CVE 的列） | %.2f |" % kev["base_rate"])
            add("| precision@10 | %.2f |" % kev["precision"]["model"]["10"])
            add("| AUC（本系統 / CVSS） | %.3f / %.3f |" % (kev["auc"]["model"], kev["auc"]["cvss"]))
            add()
        add("> EPSS 單獨使用即達 0.964，高於完整模型：AUC 的功勞屬於 EPSS，")
        add("> 本系統的價值在於把利用機率轉成可執行的修補順序（SLA、曝險、資產）。")
        add()

    if splits:
        add("## 4. 時間切分回測")
        add()
        add(f"切點：{splits['cutoff']}（之前為開發窗口，之後為測試窗口）")
        add()
        add("| 窗口 | 筆數 | 已標註 | 準確率 | 有 CVE | KEV 命中 | P@10 | AUC |")
        add("|---|---|---|---|---|---|---|---|")
        for key in ("development", "test"):
            stats = splits[key]
            acc = "n/a" if stats["accuracy"] is None else f"{stats['accuracy']:.2f}"
            p10 = "n/a" if stats["precision_at_10"] is None else f"{stats['precision_at_10']:.2f}"
            auc_value = "n/a" if stats["auc"] is None else f"{stats['auc']:.2f}"
            add(
                f"| {stats['name']} | {stats['rows']} | {stats['labelled']} | {acc} | "
                f"{stats['cve_rows']} | {stats['kev_rows']} | {p10} | {auc_value} |"
            )
        add()
        add("> 重要限制一：已標註的 200 筆集中在 2025-07 之後，因此發展窗口只有")
        add("> 31 筆可評估（AUC 0.51，等同隨機，樣本太小）；測試窗口有 169 筆。")
        add("> 限制二：EPSS/KEV 為 2026-11 快照，無法還原「當時」的利用機率。")
        add()

    add("## 5. 資料溯源")
    add()
    add("| 快照 | 擷取日期 | 來源 |")
    add("|---|---|---|")
    for name, meta in snaps.items():
        add("| %s | %s | %s |" % (name, meta["generated"], meta["source"]))
    add()

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(lines)} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
