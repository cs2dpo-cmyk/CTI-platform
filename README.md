# CTI 資安風險決策支援平台

> 基於機器學習之跨平台網路威脅情資（CTI）分析與決策支援系統
> — 嶺東 SmartTech AI 創新應用挑戰賽參賽作品 · 可部署至 Render 的全端 PoC

把 100 篇平衡語料（TWCERT 20 + iThome 30 + The Hacker News 50）經過
TF-IDF 向量化與 K-Means 分群後，以**可解釋的加權風險模型**轉譯成 CISO 可執行的
P1–P3 處置優先級、回應 SLA 與標準處置劇本（playbook）。

| 層 | 技術 |
| --- | --- |
| 前端 | HTML5 · Tailwind CSS · 原生 JavaScript (Fetch API) · Chart.js 4 |
| 後端 | Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy 2 |
| 資料庫 | SQLite（PoC）· 可切換 `DATABASE_URL` 至 PostgreSQL |
| 部署 | Render Web Service · `uvicorn main:app --host 0.0.0.0 --port $PORT` |

---

## 1. 目錄結構

```
cti-platform/
├── main.py                     # FastAPI 應用：路由、靜態檔案、生命週期
├── database.py                 # SQLite engine / Session / 建表 + 冪等種子資料
├── models.py                   # SQLAlchemy ORM：threats 資料表
├── schemas.py                  # Pydantic v2 請求 / 回應契約
├── services/
│   ├── __init__.py
│   ├── dataset.py              # 讀取 research CSV → 叢集對應 → 情資資料列
│   ├── risk_engine.py          # 可解釋風險評分 + P1-P3 分流 + 處置劇本
│   └── analytics.py            # 儀表板統計聚合與 AI 洞察文字
├── static/
│   ├── index.html              # 深色 CISO 儀表板（單頁）
│   ├── css/styles.css          # 設計系統：設計權杖、元件、動效
│   └── js/
│       ├── charts.js           # Chart.js 四張圖表（就地更新，不清空重建）
│       └── app.js              # 狀態管理、Fetch、渲染、互動
├── tests/
│   ├── test_api.py             # 20 個 API 契約測試
│   └── frontend_smoke.mjs      # jsdom 煙霧測試（需啟動本機伺服器）
├── data/
│   ├── Taiwan_security_dataset_cleaned.csv        # 研究語料（台灣 50 筆）
│   ├── Global_security_dataset_cleaned.csv        # 研究語料（國際 50 筆）
│   ├── Taiwan_security_dataset_with_dates.csv     # 加上真實發布日期（平台使用）
│   ├── Global_security_dataset_with_dates.csv     # 加上真實發布日期（平台使用）
│   ├── dataset_meta.json       # 來源、叢集對應表、日期政策
│   └── cti.db                  # 執行時自動產生（已列入 .gitignore）
├── tools/
│   └── enrich_dates.py         # 從 THN feed / TWCERT / iThome 補齊真實日期
├── dev.cmd                     # 雙擊啟動（Windows 用；會帶 ExecutionPolicy Bypass）
├── dev.ps1                     # 啟動邏輯：找 Python → 檢查套件 → 挑埠 → 開瀏覽器
├── requirements.txt            # 執行期依賴
├── requirements-dev.txt        # pytest / httpx
├── Procfile                    # web: uvicorn main:app --host 0.0.0.0 --port $PORT
├── render.yaml                 # Render Blueprint（build / start / health check）
├── runtime.txt                 # python-3.12.7
├── .gitignore
└── README.md
```

---

## 2. 快速開始（本機）

### 2.1 一鍵啟動（Windows，建議）

**雙擊 `dev.cmd`**。Windows 預設會用記事本開啟 `.ps1`，所以要透過 `.cmd` 進入。

它會自動完成這些事：

1. 依序尋找可用的 Python：專案 `.venv` → 系統 Python（若上層有 `.pylibs` 會自動加進 `PYTHONPATH`）。
2. 檢查 `fastapi / uvicorn / sqlalchemy / pydantic`，缺少時詢問是否安裝。
3. 從 8123 起挑一個空閒埠；若該埠上已經有本平台在跑，直接開瀏覽器重用，不會重複啟動。
4. 等伺服器回應健康檢查後，自動用預設瀏覽器開啟儀表板。
5. 伺服器在此視窗前景執行，**關閉視窗或 Ctrl+C 即停止**。

進階參數（在終端機執行時可用）：

```powershell
.\dev.ps1 -Port 9000 -Reload    # 指定埠號 + 熱重載
.\dev.ps1 -NoBrowser            # 不自動開瀏覽器
.\dev.ps1 -Install              # 缺套件時直接安裝，不詢問
```

> 若系統執行原則封鎖腳本（`未進行數位簽章`），改用：
> `powershell -ExecutionPolicy Bypass -File .\dev.ps1`
> `dev.cmd` 已自動帶上 `-ExecutionPolicy Bypass`，雙擊不受影響。

### 2.2 手動啟動（macOS / Linux / Render）

```bash
cd cti-platform
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt

uvicorn main:app --reload --port 8000
```

開啟 <http://127.0.0.1:8000> 即為儀表板；<http://127.0.0.1:8000/api/docs> 為 Swagger UI。

首次啟動時 `database.init_db()` 會自動建表並寫入 100 筆種子資料；
資料庫已有資料時不會重複寫入（冪等）。

### 執行測試

```bash
pip install -r requirements-dev.txt
pytest tests -q
```

測試使用獨立的 `data/test_cti.db`，不影響開發資料庫。

### 前端煙霧測試（選用）

jsdom 不負責繪製畫面，但會**實際執行** `charts.js` 與 `app.js`，對著執行中的 API
驗證渲染管線：KPI 文字、圖例、決策矩陣、情資列表、篩選、展開列與評估流程。

```bash
# 另開一個終端機啟動伺服器
uvicorn main:app --port 8123

# 安裝 jsdom（只需一次）
npm i -D jsdom      # 或 pnpm add -D jsdom

node tests/frontend_smoke.mjs
# 環境變數：CTI_BASE_URL（預設 http://127.0.0.1:8123）、CTI_STATIC_DIR、JSDOM_MODULE
```

---

## 3. API 規格

| Method | Path | 說明 |
| --- | --- | --- |
| `GET` | `/api/v1/health` | 健康檢查（Render health check 使用） |
| `GET` | `/api/v1/stats` | 全球 vs 台灣統計、Meta-Category 分布、時間軸、P1–P3 決策矩陣、AI 洞察 |
| `POST` | `/api/v1/assess` | 即時風險評估：分數、影響因子、調整項、處置劇本 |
| `GET` | `/api/v1/threats` | 情資列表，支援 `priority` / `region` / `category` / `meta_category` / `source` / `q` / `min_score` / `sort` / `limit` / `offset` |
| `GET` | `/api/v1/threats/{id}` | 單筆情資明細 |

### `POST /api/v1/assess` 範例

```bash
curl -X POST http://127.0.0.1:8000/api/v1/assess \
  -H 'Content-Type: application/json' \
  -d '{
        "asset_type": "core_datacenter",
        "threat_source": "ransomware",
        "category": "MALWARE",
        "region": "taiwan",
        "cve_id": "CVE-2026-111497",
        "cvss": 9.8,
        "exploit_status": "active",
        "exposure": "public",
        "data_sensitivity": "high",
        "controls": ["edr", "mfa"]
      }'
```

回應含 `score`、`priority`、`risk_level`、`confidence`、`factors[]`（每個因子的
權重與貢獻分數）、`adjustments[]`（在地情資 +3、控制項折減、語料佐證等）
與 `action_plan[]`（含負責人與 SLA）。

### 風險模型

```
score = 100 × (0.30 × 資產關鍵度
             + 0.26 × 威脅來源強度
             + 0.20 × 嚴重度（CVSS/10，未提供則用類別基準）
             + 0.14 × 利用成熟度
             + 0.10 × 曝險程度)
      + 在地情資關聯 (+3)
      + 資料敏感度 (±4)
      - 已佈建控制項折減 (每項 2.2–3.0，上限 12)
      + 情資語料佐證 (命中 CVE 每筆 +2，上限 6)
```

| 優先級 | 分數區間 | SLA | 負責人 |
| --- | --- | --- | --- |
| P1 立即處置 | ≥ 80，或 CVSS ≥ 9.0 且已在野利用 | 24 h | CISO / SOC 值班主管 |
| P2 計畫處置 | 66 – 79 | 7 日 | 資安維運團隊 (SecOps) |
| P3 觀測追蹤 | < 66 | 30 日 | 資安治理 / 情資研究組 |

---

## 4. 資料庫 Schema

```sql
CREATE TABLE threats (
    id            INTEGER PRIMARY KEY,
    title         TEXT    NOT NULL,
    source        VARCHAR(32)  NOT NULL,   -- TWCERT / iThome / THN
    region        VARCHAR(16)  NOT NULL,   -- taiwan / global
    category      VARCHAR(32)  NOT NULL,   -- Vulnerability / Malware / SupplyChain / Research
    meta_category VARCHAR(16)  NOT NULL,   -- VULN / MALWARE / RESEARCH
    risk_score    FLOAT   NOT NULL,
    risk_level    VARCHAR(16)  NOT NULL,   -- CRITICAL / HIGH / MEDIUM / LOW
    priority      VARCHAR(4)   NOT NULL,   -- P1 / P2 / P3
    cluster       VARCHAR(8),              -- K-Means 叢集代號（C0–C2）
    action_plan   TEXT    NOT NULL,        -- JSON 陣列的處置步驟
    cve_id        VARCHAR(24),
    published_at  DATE    NOT NULL,
    created_at    DATETIME
);
```

### 資料來源：直接讀取 research CSV（單一真實來源）

平台不再有任何寫死的統計數字。啟動時 `services/dataset.py` 會：

1. 依 `data/dataset_meta.json` 的 `taiwan_csv` / `global_csv` 讀取兩份 **with_dates** 檔
   （platform / title / cleaned_text / cluster / published_at / date_source / source_url）。
2. 以 `cluster_to_meta` 把叢集代號對應成 Meta-Category，再套用 `research_overrides`。
3. 以 `date_column`（預設 `published_at`）讀取真實發布日期，不做事後推估。
4. 交給 `risk_engine` 產生 `risk_score` / `priority` / `action_plan`，連同 `source_url` 寫入 SQLite。
5. `/api/v1/stats`、`/api/v1/threats`、決策矩陣全部由同一批資料列計算，口徑一致。

原始檔案位於 `C:\AI_Rsearch_Data`，專案內已放一份快照；要改讀原始資料夾：

```bash
CTI_DATASET_DIR=C:\AI_Rsearch_Data uvicorn main:app
```

#### 叢集 → Meta-Category 對應

| 地區 | C0 | C1 | C2 | 對應規則 |
| --- | --- | --- | --- | --- |
| 台灣 | 7 | 27 | 16 | C0、C1 → MALWARE；C2 → VULN |
| 國際 | 35 | 6 | 9 | C0、C1 → VULN；C2 → MALWARE |

判定依據是叢集內容：台灣 C2 全是修補／漏洞公告（Node.js、PHP、PostgreSQL、Exchange、
Cisco、PHP2Shell…），C0 與 C1 為攻擊事件與產業動態；國際 C0 與 C1 以漏洞與資安公告為主
（Linux Kernel、Cisco、Adobe、Wasmtime、Tailscale…），C2 為攻擊事件（ThreatsDay、
憑證外洩、PHP2Shell 實際利用、網釣活動…）。

要調整只需改 `data/dataset_meta.json` 的 `cluster_to_meta`，不需動程式碼。

`research_overrides` 目前指定三篇「AI 治理／研究」性質的文章為 RESEARCH，讓第三類在 API 與
儀表板上顯示為 3 筆：

- Webinar: How to Build AI Threat Readiness Into Your Security Operations
- The Rise of the Threat Operator: How AI Will Redefine Security Operations and Careers
- Wazuh and AI for Enhanced SOC Workflows

#### 實算結果（`GET /api/v1/stats` 即時回傳）

| Meta-Category | 台灣 | 國際 | 合計 | 佔比 |
| --- | --- | --- | --- | --- |
| 系統漏洞與修補對策（VULN） | 16 | 39 | **55** | 55% |
| 惡意威脅與主動攻擊（MALWARE） | 34 | 8 | **42** | 42% |
| 前瞻研究與平台治理（RESEARCH） | 0 | 3 | **3** | 3% |

| 決策分派 | P1 | P2 | P3 | 平均分數 |
| --- | --- | --- | --- | --- |
| 篇數 | 25 | 51 | 24 | 72.9 |

> **口徑決策（已定案）：以 CSV 為準。**
> `Global_Side-Project.ipynb` 的繪圖儲存格寫死 `meta_tw = [23, 27, 0]`、
> `meta_en = [42, 5, 3]`，與 CSV 的叢集統計（台灣 7/27/16、國際 35/6/9）不一致。
> 論文／海報上的 `65 / 32 / 3` 不再使用，簡報請改為 **55 / 42 / 3**。
>
> | 項目 | 論文原圖 | CSV 實算（現行） |
> | --- | --- | --- |
> | 台灣 VULN / MALWARE / RESEARCH | 23 / 27 / 0 | 16 / 34 / 0 |
> | 國際 VULN / MALWARE / RESEARCH | 42 / 5 / 3 | 39 / 8 / 3 |
> | 合計 | 65 / 32 / 3 | **55 / 42 / 3** |
>
> 第三類（RESEARCH）來自 `research_overrides` 指派的 3 篇文章；其餘 97 篇由叢集對應決定。
> 叢集明細會顯示混合情況（例如國際 C0 = VULN 33 + RESEARCH 2）。

#### 情資列表的日期與原始連結

`/api/v1/threats` 每筆都帶 `published_at` 與 `source_url`。前端列表的標題即為外連
（`target="_blank" rel="noopener noreferrer"`），展開列另顯示「原始報導 ↗」，
審查委員可逐筆回查原始文章；點擊連結不會觸發展開／收合。

圖表文字色：跨平台對比圖的圖例（legend）與 X/Y 軸刻度（ticks）固定為 `#FFFFFF`，
軸標題為 `#cbd5e1`，確保深色底可讀。

#### 發布日期（真實來源，非推估）

原始 CSV 只有 `title` / `cluster`，沒有日期。`tools/enrich_dates.py` 會向三個來源補齊：

| 來源 | 取得方式 | 命中 |
| --- | --- | --- |
| The Hacker News | Blogger JSON feed 的 `published` 時間戳 | 50 / 50 |
| TWCERT/CC | RSS `<pubDate>` 與年度列表 `<time>` | 20 / 20 |
| iThome | 新聞列表頁 `p.post-at` | 30 / 30 |

比對採標題正規化（去空白、統一全形標點、HTML unescape）後完全相符；僅 1 筆以
0.98 相似度近似比對。輸出檔新增四個欄位：

| 欄位 | 說明 |
| --- | --- |
| `published_at` | `YYYY-MM-DD` 實際發布日期 |
| `date_source` | `thehackernews.com` / `twcert.org.tw` / `ithome.com.tw` / `estimated` |
| `source_url` | 對應文章網址，可逐筆回查 |
| `date_note` | 近似比對或推估時的原因 |

重新產生（會覆寫 `*_with_dates.csv`）：

```bash
python tools/enrich_dates.py            # 寫檔
python tools/enrich_dates.py --report   # 只看比對結果
```

`dataset_meta.json` 的 `date_policy` 設為 `column`，平台直接讀 `published_at`；
若某列缺日期仍會退回擷取順序推估並標記 `estimated`，時間軸不會中斷。

目前分布：100 筆全部為來源實際日期（`estimated` = 0），橫跨 **2026-04-30 → 2026-10-30**，
共 15 個不同日期；國際情資集中在 10/26–10/30，台灣則因 TWCERT 發稿頻率較低而橫跨數月。

---

## 5. 部署至 Render

### 方式 A：Blueprint（建議）

1. 將 `cti-platform/` 推上 GitHub（此資料夾即為 repo 根目錄）。
2. Render → **New → Blueprint** → 選擇 repo，Render 會讀取 `render.yaml`。
3. 部署完成後開 `https://<service>.onrender.com/api/v1/health` 確認 `threats: 100`。

### 方式 B：手動 Web Service

| 設定 | 值 |
| --- | --- |
| Environment | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/api/v1/health` |

`Procfile` 內容即為上述啟動指令，亦適用於 Railway / Heroku 類平台。

### 環境變數

| 變數 | 預設 | 說明 |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./data/cti.db` | 可換成 PostgreSQL 連線字串 |
| `CTI_DATASET_DIR` | `./data` | research CSV 所在資料夾（可指向 `C:\AI_Rsearch_Data`） |
| `ALLOWED_ORIGINS` | `*` | CORS 允許來源，逗號分隔 |
| `LOG_LEVEL` | `INFO` | 日誌等級 |
| `PYTHON_VERSION` | `3.12.7` | Render 建置用 Python 版本 |

> **SQLite 與 Render 的持久化**：免費方案的檔案系統是暫時性的，重啟後資料庫會重置，
> 但應用程式啟動時會自動重新種子化 100 筆語料，因此儀表板不會壞。
> 若需要保存執行期寫入，請掛載 Render Disk 並設定
> `DATABASE_URL=sqlite:////var/data/cti.db`。

---

## 6. 設計原則（對應 skills-main / Superpowers）

**前端（emil-design-eng 風格）**

- 只對 `transform` / `opacity` / 顏色做動效；`transition` 明確列出屬性，不用 `all`。
- 自訂緩動曲線 `cubic-bezier(0.23, 1, 0.32, 1)`（ease-out），UI 動效 ≤ 300 ms。
- 所有可按壓元件在 `:active` 縮放至 `0.97`，提供即時回饋。
- 進場用 `scale(0.95) + opacity`，不用 `scale(0)`；清單以 30–80 ms 交錯進場。
- 數字使用 `font-variant-numeric: tabular-nums`，避免跳動。
- Hover 效果包在 `@media (hover: hover) and (pointer: fine)`，避免觸控誤觸。
- 完整支援 `prefers-reduced-motion`：保留顏色/透明度提示，移除位移。
- 折疊面板用 `grid-template-rows: 0fr → 1fr` 過場（可中斷），不用 height 寫死。

**後端（superpowers 架構原則）**

- 分層清楚：`models`（儲存）／`schemas`（契約）／`services`（領域邏輯）／`main`（傳輸）。
- 領域邏輯不依賴 FastAPI，`risk_engine` 可單獨測試與重用。
- 種子資料冪等（idempotent），重啟不重複寫入。
- 契約測試先於前端整合：17 個測試涵蓋統計一致性、篩選、分頁、驗證錯誤與 404。

---

## 7. 已知限制

- Tailwind 以 Play CDN 載入（PoC 便利性）；正式環境建議以 CLI 產出最小化 CSS。
- SQLite 不支援並發寫入；正式上線請改用 PostgreSQL（`DATABASE_URL` 已預留）。
- K-Means 分群結果目前以類別對應 Meta-Category 呈現，未在執行期重新訓練；
  `TF-IDF + K-Means` 屬研究階段的離線分析。
- 無身分驗證與速率限制，公開部署前應加上 API key 或 OAuth2。
