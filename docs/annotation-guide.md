# 標註指南（held-out 評估用）

這份文件的目的是讓**兩個人獨立標同一批新聞**，量出「標籤本身穩不穩定」。
分類器再準，也不能比它的 ground truth 更準；如果兩個人對同一則新聞的看法都
不一致，91% 或 88% 這種數字就沒有意義。

## 要標什麼

`data/holdout_labels.csv` 有 100 列，`label` 欄留空。填入以下四類之一：

| 代碼 | 類別 | 判斷依據 | 典型動詞 |
|---|---|---|---|
| `VULN` | 系統漏洞與修補對策 | 文章主體是**漏洞本身或修補**：CVE 編號、CVSS、廠商更新、修補程式 | 發布更新、修補、CVE、patch |
| `MALWARE` | 惡意威脅與主動攻擊 | 文章主體是**攻擊者或惡意程式**：勒索軟體、APT、資料外洩、殭屍網路 | 駭客利用、竊取、植入、勒索 |
| `RESEARCH` | 前瞻研究與平台治理 | 文章主體是**研究、調查、政策、AI 治理**，不是單一事件 | 研究發現、調查報告、政策、治理 |
| `OTHER` | 產業與產品動態 | 商業或產品消息：併購、財報、產品上市、人事 | 宣布、推出、收購、營收 |

## 判斷順序（照這個順序，不要憑感覺）

1. **看主語**：這篇在講「哪個東西」？漏洞 → VULN；攻擊者/惡意程式 → MALWARE；
   研究/政策 → RESEARCH；公司/產品 → OTHER。
2. **標題有「漏洞」也有「攻擊」時**：看事件主角。
   - 「XX 漏洞已遭利用，籲儘速修補」→ **VULN**（主角是漏洞，修補是行動）
   - 「駭客利用 XX 漏洞入侵 700 台伺服器」→ **MALWARE**（主角是攻擊事件）
3. **CVE 編號不是判準**：攻擊報導也會提到 CVE。
4. **研究報告即使談漏洞** → RESEARCH（例如「年度威脅回顧」「某組織的 TTP 分析」）。
5. **產業動態即使談資安** → OTHER（「某公司被收購」「產品更名」）。

## 邊界案例（請先讀過再開始）

| 標題類型 | 建議 | 理由 |
|---|---|---|
| 「Cisco 發布 IOS 更新修補 5 個漏洞」 | VULN | 主體是修補 |
| 「攻擊者利用 Cisco 漏洞植入後門」 | MALWARE | 主體是攻擊 |
| 「CISA 新增 3 個漏洞到 KEV」 | VULN | 漏洞治理動作 |
| 「研究：勒索軟體生態在 2026 年如何演變」 | RESEARCH | 研究，不是單一事件 |
| 「某資安公司被收購」 | OTHER | 商業事件 |
| 「新創推出 AI 驅動的 SOC 平台」 | OTHER | 產品消息 |

## 流程（兩個人）

1. 先各自讀完本指南，**不要討論個案**。
2. 把 `data/holdout_labels.csv` 複製成兩份：
   - A：`data/holdout_labels.csv`
   - B：`data/holdout_labels_b.csv`（已預先建立空白副本）
3. **各自獨立**填 `label` 欄（VULN / MALWARE / RESEARCH / OTHER），不要看對方的。
4. 遇到不確定：填你認為最可能的，並在 `notes` 寫下理由（例：`漏洞公告但描述攻擊`）。
5. 跑一致性：
   ```bash
./.venv/Scripts/python.exe tools/label_agreement.py --a data/holdout_labels.csv --b data/holdout_labels_b.csv
```
6. 判讀 Cohen's kappa：

| kappa | 意義 | 動作 |
|---|---|---|
| ≥ 0.80 | 幾乎完全一致 | 可以拿去評估模型 |
| 0.60–0.79 | 實質一致 | 可接受，爭議案例記錄下來 |
| 0.40–0.59 | 中等 | 先修指南（把不一致的案例寫進邊界表）再重標 |
| < 0.40 | 不可用 | 類別定義有問題，重新定義 |

7. 兩人討論不一致的案例，由第三人裁決，產生**共識版本**（覆蓋 A 的檔案）。
8. 用共識版本跑模型評估：
   ```bash
./.venv/Scripts/python.exe tools/eval_holdout.py
```

## 為什麼不能先看模型的答案

標註表刻意不含 `prediction` 欄。一旦看到模型說是 MALWARE，人會傾向同意，
量出來的就不是模型的準確率，而是「人有多容易被模型說服」。

## 這批資料的來源

100 列全部來自**沒有被 gold 標註**的那一半語料（THN 50、TWCERT 30、iThome 20），
與訓練/調參用的 100 列完全不重疊。清單產生於 `tools/make_holdout.py`，
manifest 在 `data/holdout_manifest.json`。

## 邊界修正（2026-11-13，依實際標註結果）

第一輪標註後，VULN 與 MALWARE 的邊界出現系統性偏移：A、B 兩位標註者一致地把
**入侵／外洩事件**標成 VULN（16 列），而模型與原 gold 慣例標成 MALWARE。以下規則
優先於前面的「判斷順序」。

### 一句話規則

> **有沒有「漏洞」不是重點；重點是這篇在講「一個漏洞」還是「一場已經發生的事」。**

| 情況 | 標 | 判準 |
|---|---|---|
| 廠商發布更新／公告 CVE／說明修補 | **VULN** | 動作是「修補」，主體是產品 |
| 已經有人被入侵、資料外洩、系統被加密 | **MALWARE** | 動作是「攻擊成功」，主體是受害者 |
| 研究某種攻擊手法／回顧趨勢 | **RESEARCH** | 沒有特定受害者與即時行動 |
| 公司被併購、產品上市、財報 | **OTHER** | 與攻擊、漏洞都無關 |

### 實際案例（來自第一輪標註）

| 標題 | 第一輪 | 正確 | 理由 |
|---|---|---|---|
| Chainalysis Breach Exposes All Users' Credentials | VULN | **MALWARE** | 是「已經發生」的外洩，不是漏洞公告 |
| Fireworks AI Confirms Wider Breach Affecting Customer Datasets | VULN | **MALWARE** | 同上 |
| France Blames Iran for Sabotage Attack on Refrigeration Controllers | VULN | **MALWARE** | 國家級攻擊事件 |
| LNbits Urges All Operators to Shut Down Servers Amid Attack | VULN | **MALWARE** | 主動攻擊中 |
| Installing the Fix for an Exploited WordPress Flaw… | MALWARE | **VULN** | 主體是修補程式 |
| Microsoft Researchers Show AI Agents Can Be Backdoored… | VULN | **RESEARCH** | 研究方法，不是單一事件 |
| Over 35,000 Grok-Built Apps Exposed Online | VULN | **MALWARE** | 曝險事件，不是漏洞本身 |

### 三個問句（每列都問一次）

1. 這篇有沒有**特定受害者**？有 → 幾乎就是 MALWARE。
2. 這篇的動詞是「修補／發布」還是「入侵／竊取／加密」？前者 VULN，後者 MALWARE。
3. 這篇是「某個方法的研究」還是「某個東西出事」？前者 RESEARCH。

### 爭議處理

- 先跑 `tools/make_disputes.py` 產生 `data/holdout_disputes.csv`
- 只針對爭議列，用上面的案例表裁決，填 `final` 欄
- 裁決後覆蓋 A 檔重跑 `tools/eval_holdout.py`

## 裁決結果（2026-11-13）

55 列爭議由第三人依本指南裁決，理由記錄在 `data/holdout_disputes.csv` 的 `notes` 欄。

| 項目 | 數值 |
|---|---|
| 裁決與 A 相同 | 28 / 55 |
| 裁決與 B 相同 | 30 / 55 |
| 裁決與模型相同 | 27 / 55（49%，未偏向模型） |
| κ（裁決 vs B，全 100 列） | 0.631 |

裁決後的最終成績（`tools/eval_holdout.py`）：

| 指標 | 值 |
|---|---|
| held-out 準確率 | **72%**（91% 為 in-sample） |
| 多數類別 baseline | 44% |
| 提升 | +28 個百分點 |

| 類別 | Precision | Recall | F1 | n |
|---|---|---|---|---|
| VULN | 0.92 | 0.69 | 0.79 | 32 |
| MALWARE | 0.79 | 0.86 | 0.83 | 44 |
| RESEARCH | 0.40 | 0.67 | 0.50 | 15 |
| OTHER | 0.67 | 0.22 | 0.33 | 9 |

最大誤差來源：**OTHER → RESEARCH 共 6 例**（9 例中 6 例）。分類器的 RESEARCH 規則
被 AI 產品消息的關鍵詞觸發，把「新產品／上線／募資」誤判為研究。

原始第一輪標註保留在 `data/holdout_labels_round1.csv`。

## 第二輪標註（擴充語料）

第一輪的 100 筆標在原始 200 筆上。擴充後語料變成 788 筆，新增的 588 筆從未標註，
所以再抽 100 筆做第二輪：

| 項目 | 內容 |
|---|---|
| 檔案 | `data/holdout2_labels.csv`（A）、`data/holdout2_labels_b.csv`（B） |
| 抽樣 | 588 筆中按來源比例（THN 89、TWCERT 11），跨月份輪替 |
| 排除 | 所有已標註過的 200 個標題（gold + 第一輪） |
| 判定 | 規則與本指南完全相同（含邊界案例表） |

流程：

```bash
# 1. 兩人各自填 label 欄
# 2. 算一致性
./.venv/Scripts/python.exe tools/label_agreement.py \
  --a data/holdout2_labels.csv --b data/holdout2_labels_b.csv

# 3. 列爭議並裁決（填 final 欄）
./.venv/Scripts/python.exe tools/make_disputes.py --round 2

# 4. 用裁決後的檔案評估
./.venv/Scripts/python.exe tools/eval_holdout.py --sheet data/holdout2_labels.csv
```

第二輪的價值：這是**擴充語料上的第一個真正 held-out**，可以回答
「語料變多之後，77% 還站得住嗎」。
