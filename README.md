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

### 本地通報（Taiwan Hit）

語料約 79% 來自國際來源，單看報導量會把「國際媒體寫得多」誤當成「對台灣重要」。
因此系統另外標記**同時被台灣來源報導**的 CVE（目前 288 個 CVE 中有 69 個，其中 28 個台／國都報導）：

- 修補清單：CVE 旁顯示琥珀色「本地通報」徽章，滑過可看台灣來源與標題（如 TWCERT、iThome）
- 情資流：國際來源的項目若其 CVE 也被台灣報導，會標示「本地通報 ×N」
- 卡片標題列：「本地通報 69」晶片，一眼看出本地相關比例

判讀方式：徽章代表「這個漏洞已進入台灣的通報體系」，是**本地關聯**的證據，不代表嚴重度更高。

### 決策路徑（可稽核）

修補清單的「判斷依據」欄不寫長句，而是印出實際觸發的訊號晶片，例如：

    積極利用 + 對外曝險 ↗ → P1
    CVSS ≥ 9 + 無曝險訊號 → P2

滑過該格可看完整理由（服務層產生的 reason 字串）。晶片由 API 的 path 欄位提供
（KEV／EPSS／CVSS／LOW 加上 PUBLIC／INTERNAL／NO_EXPOSURE），前端只負責翻譯成標籤，
因此「為什麼是 P1」在後端與畫面是同一份邏輯。

### CVSS 的來源（為什麼有些是空白）

CVSS 只從**文章文字**抓（標題＋內文），不是資料庫欄位。實際情況：

- 原始 200 筆有內文，擴充的 588 筆只有標題
- 即使有內文，也只有約一半的報導會寫出數字（更多只寫「critical」）
- 因此 288 個 CVE 中有 149 個（52%）原本沒有分數

補救方式是 tools/refresh_cvss.py：只針對「沒有任何文章寫過分數」的 CVE，
向 CVE.org（CIRCL 鏡像）查詢並存成 data/cvss.json。優先序是
**文章 > CVE.org 快照 > 空白**，因為文章的分數可追溯回那一則報導。

畫面上：分數後面帶「官」上標代表來自 CVE.org（文章未揭露），
滑過可看說明；完全查不到的顯示「—」，卡片標題列另有「CVSS 未知 N」統計。

要讓新快照生效必須重建資料庫（風險分數會變）：本機刪除 data/cti.db 後重啟；
Render 每次部署都是全新檔案系統，會自動重建。

### 已知被利用但未收錄（覆蓋缺口）

新聞語料只涵蓋 KEV 窗內的 80 / 711 筆（11%），因為新聞只報有故事性的漏洞，
Ivanti、Jenkins、SharePoint 這類企業端漏洞常常上不了新聞。因此另外提供
GET /api/v1/kev-uncovered：

- 列出窗內 KEV 中**沒有被任何文章報導**的 631 筆，附加入日期、EPSS、CVSS、廠商產品
- 排序：勒索軟體已利用優先，其次 EPSS，再其次 CVE 編號
- 儀表板面板可切換「僅勒索軟體」與「顯示全部」

這些項目**刻意不併入主清單**：它們沒有曝險資訊、沒有文章可追溯，
混進去會讓「判斷依據」變成假的。補漏頁回答的是「你沒看到什麼」，
主清單回答的是「你看到的先修哪個」。

### 完整清單與匯出

儀表板預設只顯示前 8 筆（給主管看的摘要），表格底部有「查看全部 288 筆」按鈕：

- 展開後一次載入全部 CVE（API 上限 300），可依 P1／P2／P3、CVE 關鍵字、
  「僅本地通報」篩選，全部在瀏覽器端完成，不重新打 API
- 「匯出 CSV」輸出目前畫面上的那份清單（含 path 與 reason），可直接貼進工單系統
- 再按一次「收合」回到前 8 筆

資料量小（288 列）是刻意的：一次載入比翻頁簡單，篩選也更即時。

### CWE 弱點類型（為什麼它不能取代 VULN/MALWARE）

CWE 是**缺陷分類法**（SQL 注入、指令注入、認證繞過…），不是新聞分類法。
它無法判斷「這篇是修補公告還是攻擊事件」，所以不用來決定 VULN/MALWARE；
它做的是另外兩件事：

1. 確認這個 CVE 是漏洞紀錄（有 CWE 就是弱點）
2. 給出可引用的**弱點類型**（例如 CWE-78 指令注入）

資料來源是 CVE.org（CIRCL 鏡像）的 problemTypes，約 **96% 的語料 CVE 有 CWE**，
存成 data/cwe.json（tools/refresh_cwe.py 更新）。評估表單在 CVE 欄查詢後會顯示
CWE 晶片；若語料把它當攻擊事件報導、但 CVE 本質是漏洞，理由欄會註明
「此 CVE 本質為漏洞，若你的情境是修補排程可改選系統漏洞」。

### 弱點類型篩選

修補清單上方有一排 CWE 弱點類型晶片（全部 288、遠端執行 32、認證繞過 52、
記憶體安全 60、其他弱點 58、未標示 13…），點一下只顯示該類型，並自動展開完整清單。

| 類型 | 涵蓋 CWE |
|---|---|
| 遠端執行 | 77、78、94、95、96、99、917、1336 |
| 反序列化 | 502、915 |
| SQL 注入 | 89 |
| XSS | 79、80、83、87 |
| 認證繞過 | 269、284、285、287、288、290、306、620、640、732、862、863 |
| 路徑遍歷 | 22、23、36、434、538 |
| SSRF／XXE | 918／611 |
| 記憶體安全 | 119、120、121、122、125、190、191、416、476、787 |
| 輸入驗證 | 20、116、128、444、707、754、1287 |
| 加密／憑證 | 259、295、327、330、347、798 |
| 資訊洩露 | 200、209、532、552 |

「未標示」代表該 CVE 還沒有 CWE 紀錄（13 個），不是分類失敗。

### 即時評估怎麼用

1. 選**資產類型**與**威脅來源**（決定因子權重）與**情資類別**
2. 選**暴露程度**（對外／內網）與**利用成熟度**（尚未確認／已知手法／已在野）
3. 勾選**已佈建控制項**（EDR、MFA、WAF、網段隔離、備份、自動化修補），每項折減分數
4. 可選填 **CVE 編號**：系統會自動帶入 EPSS 與 KEV
5. 按「執行風險評估」

結果包含：分數環、**P3/P2/P1 門檻條**（分數落在哪個區間一目了然）、決策路徑晶片、
五個因子貢獻、折減明細、**what-if 對照**、處置劇本。

分數門檻：P1 ≥ 80、P2 ≥ 66、P3 < 66（見 services/risk_engine.py）。

what-if 會用同一組條件再跑兩次（加一項控制項／改為內網），回答「要怎麼做才能降級」——
這是 CISO 真正會問的問題，而且只花兩次 API 呼叫。

### 部署商的使用流程（4 個分頁）

整個儀表板原本是一長頁，資訊密度過高。現在依工作順序切成 4 個分頁
（狀態記在網址 hash，重整後停在同一頁）：

1. **總覽** — 語料規模、P1 件數、類別分布、發布節奏、決策矩陣
2. **修補清單** — 288 個 CVE 的 P1–P3 與 SLA（可展開全部、篩選、匯出 CSV），
   下方接「KEV 覆蓋缺口」
3. **即時評估** — 輸入資產類型與情境，得到分數環、因子貢獻條、決策路徑晶片與處置劇本
4. **情資流** — 逐篇情資、搜尋與展開明細

頁首 hero 有三步流程晶片（① 看態勢 → ② 排修補 → ③ 評風險），可直接跳到對應分頁。

### 使用情境標示

頁首徽章標明系統定位為「部署商 Deployer」：聚焦內部資產曝險與修補分流，
而非事件應變（IR）或威脅獵捕（hunting）。這決定了評分權重裡曝險佔 12%、以及
修補清單以 CVE 為單位而非以事件為單位。

### 資料快照

| 快照 | 檔案 | 更新方式 |
| --- | --- | --- |
| EPSS | data/epss.json | node tools/refresh_snapshots.mjs |
| KEV | data/kev_ids.json | 同上 |
| CVSS | data/cvss.json | tools/refresh_cvss.py（只補文章沒寫的） |
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
