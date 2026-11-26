# CTI · CISO Dashboard — 48 秒產品片

依 `prompt.md`（v3.0）、`storyboard.md` 與 `revision-prompt-v4.md` 建置：1920×1080、30 fps、
1440 幀、96 拍（120 BPM，1 拍 = 15 幀）、12 鏡、零滾動、推鏡上限 2.00×（素材 dpr 2，2.00 仍 1:1）。

## 怎麼跑

在**一般 PowerShell 視窗**執行（不要透過 agent 的沙箱：這台機器上被沙箱啟動的子程序
無法開瀏覽器，詳見 `docs/video/notes.md`）：

```powershell
cd C:\dev\cti-platform\video\cti-60s-spec
.\film.ps1                  # 階段一：抓頁 → 打包 → 出 8 張審片幀
.\film.ps1 -SkipCapture     # 已有抓頁素材，只重打包與出幀
.\film.ps1 -SkipCapture -Film   # 階段三：直接出成片 out/film.mp4
```

第一次會自動 `npm ci`（已含 `package-lock.json`）。

## 產出

| 路徑 | 內容 |
|---|---|
| `out/stills/` | 6 張英雄幀（含六項註記條）＋ 12 欄網格/安全區版 ＋ 規格卡 |
| `out/sample-640x360.mp4` | 階段二小樣：640×360、關質感、畫面右上顯示拍號 |
| `out/film.mp4` | 成片（H.264 crf 16，1920×1080，30 fps，1440 幀） |
| `public/captures/` | 抓頁素材（頁面全圖、KPI 卡、面板、表格條帶、表單逐欄、結果面板） |
| `public/data.json` | 抓頁當下量到的數值（KPI、筆數、99.0 / P1 / SLA…） |
| `public/bboxes.json` | 所有目標元素的 CSS px 座標，鏡頭的瞄準點都由它推導 |

## 檔案結構

```
capture/capture.mjs     抓頁：Edge + puppeteer-core，viewport 1920×1080、dpr 2
src/timing.ts           全片唯一的時間真相：12 鏡的起止拍 → 幀
src/theme.ts            品牌 token：8 色、3 字體、6 級字階、邊距、質感
src/assets.ts           把 data.json / bboxes.json 變成鏡頭可用的座標與文案
src/components/         Ambient（站上環境光）、World（2.5D 相機）、Cursor、Caption
src/scenes/S01..S12      12 個鏡頭，每鏡對應分鏡表一張鏡頭卡
src/Master.tsx          12 個 Sequence 組成整片；質感層只在最外層畫一次
tools/build.cjs         打包（webpack；不經 esbuild，見 notes）
tools/stills.cjs        階段一審片幀
tools/render.cjs        呼叫 @remotion/renderer 出 still / mp4（用本機 Edge）
```

## 換內容

只改 `src/theme.ts`（配色/字階/邊距）與 `src/timing.ts`（拍點），再改 `src/assets.ts` 的
`COPY`。文案若來自 `data.json` 就是抓頁實測值，不需要手改。

## 已知限制

- **需在你自己的終端機執行**：agent session 的沙箱無法啟動任何 Chromium 系瀏覽器。
- 抓頁依賴 `C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe`；換瀏覽器請改
  `capture/capture.mjs` 與 `tools/stills.cjs`、`tools/render.cjs` 的 `EDGE`/`browserExecutable`。
- 品質驗收（鏡頭節奏、是否對拍）需要人看片；我只能驗到型別、打包與素材數值。