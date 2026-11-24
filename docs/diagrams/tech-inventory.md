# 專題技術清單（對應三張圖）

> 產出：`tech-A-mindmap`、`tech-B-layers`、`tech-C-pipeline`（PNG 3840×2160 ＋ SVG）
> 生成器：`tools/make_tech_diagrams.py`（同一份模型同時輸出 PNG 與 SVG）
> 核對方式：版本號取自 `requirements.txt`／`package.json`；規模數字取自 `docs/evaluation.md` 與即時 API

## 一、資料與語料

| 技術／來源 | 規格 | 用途 | 出處 |
|---|---|---|---|
| The Hacker News | 每月約 250 篇 | 國際情資 | 抓取腳本 |
| TWCERT/CC | 每月約 5 篇 | 台灣政府公告 | 抓取腳本 |
| iThome | 近期 50 篇 | 台灣媒體視角 | 抓取腳本 |
| 分層取樣 | 每月 15 國際＋5 台灣 | 鋪平 35 個月，避免集中近二月 | `tools/build_stratified.py` |
| 語料規模 | 788 篇／783 事件 | 分析基礎 | `data/*.csv` |
| 星狀分群去重 | 788 → 783 | 同一事件多家報導只算一次 | `services/dedup.py` |

## 二、外部官方情資（快照）

| 技術 | 資料量 | 用途 | 出處 |
|---|---|---|---|
| CISA KEV | 1,779 筆 | 「已遭實際利用」事實 | `services/kev.py`、`data/kev_full.json` |
| FIRST EPSS | 911 筆 | 未來 30 天利用機率 | `services/epss.py`、`data/epss.json` |
| CVSS 3.1 | 704 筆 | 嚴重度 | `services/cvss.py`、`data/cvss.json` |
| MITRE CWE | 287 筆（275 有值） | 弱點類型 | `services/cwe.py`、`data/cwe.json` |
| 快照版本制 | `data_as_of` 取最舊 | 避免用最新日期掩蓋舊資料 | `services/snapshots.py` |

## 三、分析與演算法

| 技術 | 規格 | 用途 | 出處 |
|---|---|---|---|
| TF-IDF | 特徵向量化 | 關鍵字詞分布 | 語料前處理 |
| K-Means | 無監督分群 | 威脅主題叢集（cluster 欄位） | 同上 |
| 規則式分類 | 4 類，附命中理由 | VULN／MALWARE／RESEARCH／OTHER | `services/classify.py` |
| CVE 抽取 | 正規式＋斷詞容錯 | 「CVE 2025 5777」→ CVE-2025-5777 | `services/cve.py` |
| 可解釋評分（文章） | 四因子 50／30／12／8 | 0–100 分，可逐項拆解 | `services/risk_engine.py` |
| 可解釋評分（即時） | 五因子 0.30／0.26／0.20／0.14／0.10 | 單一資產情境 | 同上 `assess()` |
| SSVC（Deployer） | KEV→P1；EPSS≥0.10 或 CVSS≥9→P2 | 優先級與 SLA | `services/patch_priority.py` |
| 曝險推斷 | 人工＞清單＞描述＞推斷＞未知 | 對外升一級、內網降一級 | `services/exposure.py` |
| CWE 家族分類 | 12 類／217 個 | 弱點類型篩選 | `services/cwe.py` |
| Playbook | 依類別×優先級 | 自動處置劇本 | `services/risk_engine.py` |

## 四、後端服務

| 技術 | 版本 | 用途 | 出處 |
|---|---|---|---|
| Python | 3.x | 執行環境 | — |
| FastAPI | **0.162.0** | REST API、OpenAPI 文件 | `requirements.txt` |
| Uvicorn | **0.54.0** | ASGI 伺服器 | 同上 |
| Pydantic | **2.14.2** | 請求／回應驗證 | 同上 |
| SQLAlchemy | **2.1.6** | ORM 與查詢 | 同上 |
| SQLite | 單檔 | 資料庫 | `data/cti.db` |
| REST 端點 | 8 個 | health／stats／threats／threats/{id}／assess／patch-priority／kev-uncovered／cve/{id} | `main.py` |

## 五、前端介面

| 技術 | 版本 | 用途 | 出處 |
|---|---|---|---|
| 原生 JavaScript | ES2020+，無框架 | 狀態與渲染 | `static/js/app.js` |
| Chart.js | 4.4.6（CDN） | 圓餅／堆疊長條／折線 | `static/js/charts.js` |
| Tailwind CSS | CDN | 樣式 | `static/index.html` |
| 工作區 | 4 個 | 總覽／修補清單／即時評估／情資流 | 同上 |
| 設計代幣 | CSS 變數（控制室配色） | 一致的視覺語言 | `static/css/styles.css` |

## 六、評估方法

| 技術 | 指標 | 用途 | 出處 |
|---|---|---|---|
| 雙人標註＋第三人裁決 | κ **0.818** | 標註一致性 | `services/agreement.py` |
| 分類評估 | 準確率 **73%**（基準 44%） | held-out 測試 | `tools/eval_holdout.py` |
| AUC 回測（KEV 為黃金標準） | 本系統 **0.853**／EPSS 0.827／CVSS 0.561 | 排序有效性 | `data/*.json` → `docs/evaluation.md` |
| 時間切分回測 | 測試窗口 273 筆、AUC 0.87 | 模擬用過去預測未來 | `services/time_split.py` |

## 七、工程與部署

| 技術 | 規格 | 用途 | 出處 |
|---|---|---|---|
| pytest | 105 項 | 後端契約與演算法測試 | `tests/test_*.py` |
| jsdom smoke | 79 項 | 前端渲染與互動 | `tests/frontend_smoke.mjs` |
| puppeteer-core | 24.x | 截圖驗證 | `package.json` |
| GitHub | — | 版本控制 | — |
| Render | 免費方案 | 雲端部署、推送自動更新 | `render.yaml`／設定 |

## 八、未來技術（圖中虛線標示，尚未實作）

| 技術 | 目的 |
|---|---|
| LLM 摘要與處置建議 | 生成文章摘要，規則層保留為稽核底座 |
| CMDB 資產串接 | 取代 14 台示範資產，提升曝險判定覆蓋 |
| Jira／ServiceNow 工單輸出 | 直通既有維運流程 |

## 三張圖的差異

| 版本 | 回答的問題 | 節點數 | 適合場合 |
|---|---|---|---|
| A 心智圖 | 「用了哪些技術？」 | 6 分支／25 葉 | 口試開場、總覽 |
| B 分層架構 | 「系統怎麼分層、各層用什麼？」 | 5 層＋側欄＋future | 論文插圖、評審問架構 |
| C 資料管線 | 「資料怎麼流動？」 | 6 節點＋3 KPI | 講流程、Demo 前導 |
