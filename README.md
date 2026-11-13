# CTI 資安風險決策支援平台

> 跨平台網路威脅情資（CTI）分析與決策支援系統 — 嶺東 SmartTech AI 創新應用挑戰賽參賽作品，
> 可部署至 Render 的全端 PoC。

把情資語料轉成 CISO 可執行的 **P1–P3 處置優先級、回應 SLA 與修補清單**。
分類採規則式（可稽核、可重現），利用機率採 FIRST EPSS，已遭利用的事實採 CISA KEV，
再以資產曝險調整修補順序。

## 目前狀態（2026-11-13）

| 項目 | 值 |
| --- | --- |
| 語料 | **788 篇**（平衡對照 200 + 自然語料 588）｜35 個月（2024-01 ～ 2026-11） |
| 去重後事件 | 783（5 筆重複已合併） |
| 分類器（開發期） | 91%（100 筆 gold，in-sample） |
| 分類器（第一輪 held-out） | 77%（κ 0.741） |
| 分類器（第二輪 held-out） | **73%**（κ 0.818；多數類別 baseline 44%） |
| 排序（KEV 為 ground truth） | precision@10 **1.00**、AUC **0.843**（純 CVSS 0.546） |
| 時間切分回測 | 測試窗口 AUC 0.88（發展窗口 0.51，樣本僅 24 筆） |
| 測試 | 後端 82 項、前端 smoke 58 項 |

> 對外引用的數字一律以 docs/evaluation.md 為準，該檔案由 tools/make_eval_doc.py 自動產生。

| 層 | 技術 |
| --- | --- |
| 前端 | HTML5 · Tailwind CSS · 原生 JavaScript (Fetch API) · Chart.js 4 |
| 後端 | Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy 2 |
| 資料庫 | SQLite（PoC）· 可切換 `DATABASE_URL` 至 PostgreSQL |
| 外部資料 | FIRST EPSS、CISA KEV、資產清單（皆為版本化快照） |
| 部署 | Render Web Service · `uvicorn main:app --host 0.0.0.0 --port $PORT` |

---

## 1. 目錄結構

```
cti-platform/
├── main.py                     # FastAPI 應用：路由、靜態檔案、生命週期
├── database.py                 # engine / Session / 建表 + 冪等種子 + 升級步驟
├── models.py                   # ORM：threats（含 cve_ids、duplicate_of）
├── schemas.py                  # Pydantic 契約（含 DataProvenance）
├── services/
│   ├── classify.py             # 逐篇規則分類（四類）＋ 證據抽取
│   ├── cve.py                  # CVE 抽取（容忍 jieba 斷詞後的「cve 2025 5777」）
│   ├── dataset.py              # 讀取 CSV（含擴充語料）→ 分類 → 評分
│   ├── risk_engine.py          # 可解釋評分、P1–P3、處置劇本、控制項折減
│   ├── analytics.py            # 統計聚合（以去重後事件為單位）
│   ├── dedup.py                # 近重複偵測（URL／CVE／標題／digest 包含）
│   ├── epss.py / kev.py        # 外部快照查詢
│   ├── patch_priority.py       # 修補優先級（EPSS + KEV + 曝險）
│   ├── exposure.py / assets.py # 曝險推斷與資產清單比對
│   ├── snapshots.py            # 快照版本與 data_as_of
│   ├── agreement.py            # Cohen's kappa 等標註一致性
│   └── time_split.py           # 時間切分（標註感知的切點選擇）
├── static/                     # 單頁儀表板（HTML / CSS / JS）
├── tools/                      # 抓取、標註、評估、文件產生（見第 5 節）
├── tests/                      # 後端 pytest + 前端 jsdom smoke
├── docs/
│   ├── evaluation.md           # 唯一有效的評估結果（自動產生）
│   ├── annotation-guide.md     # 標註指南（含爭議類型判定表）
│   └── scrape-feasibility.md   # 語料擴充的可行性實測
└── data/                       # 語料 CSV、快照 JSON、標註檔
```

---

## 2. 快速開始

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt          # Windows
./.venv/Scripts/python.exe -m uvicorn main:app --host 127.0.0.1 --port 8123
# http://127.0.0.1:8123/        儀表板
# http://127.0.0.1:8123/api/docs OpenAPI
```

第一次啟動會從 data/*.csv 建立 SQLite 並評分（約 2 秒）。

### 執行測試

```bash
PYTHONPATH=./.pylibs ./.venv/Scripts/python.exe -m pytest tests -q   # 82 項
node tests/frontend_smoke.mjs                                        # 58 項（需先啟動服務）
```

前端 smoke 的預期值直接從 /api/v1/stats 取得，**語料變動不會讓測試整批失敗**。

---

## 3. API 規格

| 方法 | 路徑 | 用途 |
| --- | --- | --- |
| GET | /api/v1/health | 健康檢查（含語料筆數、資料版本） |
| GET | /api/v1/stats | 統計、類別分布、時間軸、決策矩陣、data_as_of |
| GET | /api/v1/threats | 情資列表；支援 priority / region / source / 搜尋 / 分頁 / dedupe |
| GET | /api/v1/threats/{id} | 單筆明細（含處置劇本、CVE 清單） |
| POST | /api/v1/assess | 即時風險評估；帶 cve_id 時自動查 EPSS／KEV |
| GET | /api/v1/patch-priority | 修補清單（EPSS + KEV + 曝險），可加 ?exposure=false 對照 |

三個統計端點都回傳 `data_as_of`、`stale_days` 與各快照的來源與筆數。

### 範例

```bash
curl "http://127.0.0.1:8123/api/v1/patch-priority?limit=5"
curl "http://127.0.0.1:8123/api/v1/threats?priority=P1&dedupe=true"
curl -X POST http://127.0.0.1:8123/api/v1/assess \
  -H 'Content-Type: application/json' \
  -d '{"asset_type":"web_app","threat_source":"zero_day","cve_id":"CVE-2023-4966"}'
```

---

## 4. 評分與優先級

### 情資評分（語料）

```
score = 100 × (0.50 × 嚴重度 + 0.30 × 利用機率 + 0.12 × 暴露 + 0.08 × CVE 具名)
利用機率：有 CVE 時採 EPSS 實測值，否則退回文字判斷
```

### 修補優先級（CVE 層級）

| 級別 | 條件 | SLA |
| --- | --- | --- |
| P1 | 列入 CISA KEV（已遭利用） | 24 小時 |
| P2 | 對外曝險且 EPSS ≥ 0.10 或 CVSS ≥ 9.0 | 7 天 |
| P3 | 其餘 | 30 天 |

曝險來源順序：人工指定 → 資產清單 → 情資描述 → 產品名推斷 → 未知。
對外曝險升一級、內網降一級、未知維持；KEV 永不降級。

### 資料快照

| 快照 | 檔案 | 更新方式 |
| --- | --- | --- |
| EPSS | data/epss.json | node tools/refresh_snapshots.mjs |
| KEV | data/kev_ids.json | 同上 |
| 資產 | data/assets.csv | tools/asset_import.py --file ... --apply |

data/snapshots.json 記錄每個快照的來源與擷取日期；data_as_of 取**最舊**的那一個。

---

## 5. 工具（tools/）

| 類別 | 工具 |
| --- | --- |
| 抓取 | build_corpus.py、build_stratified.py（按月分層）、import_expanded.py |
| 標註 | make_holdout.py、make_relabel.py、label_agreement.py、make_disputes.py、apply_relabel.py |
| 評估 | eval_classifier.py、eval_holdout.py、eval_round2.py、kev_precision.py、tune_weights.py、time_split_eval.py、simulate_digest_class.py |
| 分析 | dataset_comparison.py（平衡 vs 自然）、dedup_report.py、patch_report.py、export_audit.py |
| 文件 | make_eval_doc.py（產生 docs/evaluation.md） |
| 維運 | asset_import.py、refresh_snapshots.mjs、shot.mjs（截圖） |

---

## 6. 部署至 Render

render.yaml 已包含 Blueprint 設定；推送 main 後自動部署。

| 環境變數 | 說明 |
| --- | --- |
| PORT | Render 自動注入 |
| DATABASE_URL | 選填；未設定時使用 data/cti.db（SQLite） |
| CTI_DATASET_DIR | 選填；指向替代的語料資料夾 |

免費方案冷啟動約 30 秒，部署約 5–15 分鐘。

---

## 7. 已知限制

| 限制 | 說明 |
| --- | --- |
| 語料區域傾斜 | 國際 79% / 台灣 21%。平衡樣本與自然語料的比較見 docs/evaluation.md 第 7 節 |
| 平衡樣本會放大急迫性 | P1 佔比：平衡樣本 20%、自然語料 2.6%；儀表板已加註說明 |
| 週報／彙整類爭議 | 佔語料 2.5%，兩個標註者與分類器三方說法不同，尚未定案 |
| 發布節奏的週間斷層 | 分層抓取每月取最新 N 篇，導致週圖月初空缺、月底尖峰；圖上已標註抽樣方式 |
| 沒有認證 | API 目前公開，正式部署前需加 API key |
| 資產清單為示範資料 | 14 台，曝險覆蓋 44% |
| 快照需手動更新 | 逾時不會自動告警，僅反映在 data_as_of |

---

## 8. 文件

| 文件 | 內容 |
| --- | --- |
| docs/evaluation.md | 唯一有效的評估結果（自動產生） |
| docs/annotation-guide.md | 標註指南、爭議類型判定表、κ 流程 |
| docs/scrape-feasibility.md | 各來源可回溯深度與語料擴充決策 |
