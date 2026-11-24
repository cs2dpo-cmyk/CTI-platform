# -*- coding: utf-8 -*-
"""Generate the silent-demo subtitle track (SRT) plus a compact cue sheet.
One source of truth: CUES below drives both files."""
import os

OUT = r"C:/dev/cti-platform/docs"
CUES = [
    (0,   4,  "CTI 資安風險決策支援平台", "實機操作示範", "黑底標題卡"),
    (4,   10, "每天數百則新聞，團隊只有 2–3 人", "問題是：先修哪一個？", "切到總覽頁頂部"),
    (10,  17, "788 篇中英文情資", "去重後 783 件事件，橫跨 35 個月", "指左上 KPI 卡"),
    (17,  24, "台灣 164 篇、國際 624 篇", "四類別可切換", "滑過圓餅圖"),
    (24,  30, "最重要的頁面：修補清單", "", "點「修補清單」分頁"),
    (30,  38, "288 個 CVE", "對照 KEV、EPSS、CVSS、CWE", "停在表頭與第一列"),
    (38,  46, "P1 131（24 小時）", "P2 134（7 天）、P3 23（30 天）", "指 P1/P2/P3 徽章"),
    (46,  54, "每列都附判斷依據", "例：KEV 命中＋對外曝險 → P1", "滑過「判斷依據」欄"),
    (54,  62, "篩選「本地通報」", "台灣來源報導過的漏洞：69 個 CVE", "點「僅本地通報」"),
    (62,  70, "也可依 CWE 弱點類型篩選", "例如遠端執行 32 個", "點「遠端執行」晶片"),
    (70,  76, "匯出 CSV", "直接變成工單", "點「匯出 CSV」"),
    (76,  84, "清單沒有的情境：即時評估", "填六個欄位即可", "切到即時評估"),
    (84,  92, "CVE-2024-3400、對外網站", "CVSS 9.8、已勾 EDR", "選填表單"),
    (92,  100, "結果：99.0 分、P1", "", "執行評估，指分數環"),
    (100, 108, "理由：KEV 命中、對外曝險", "CWE-77 命令注入", "滑過決策路徑晶片"),
    (108, 116, "權重固定 50／30／12／8", "每一分都能拆解", "指因子列表"),
    (116, 124, "換一個情境：CVSS 9.0、對外", "結果 78.6 分、P2", "改欄位重跑"),
    (124, 132, "改成內網＋WAF＋隔離＋備份", "結果 64.6 分、P3", "勾控制項重跑"),
    (132, 140, "同一個漏洞，不同情境", "等級就不同——這就是 what-if", "兩張結果卡對照"),
    (140, 148, "情資流保留原始報導", "可追溯每一則來源", "切到情資流並捲動"),
    (148, 156, "API 8 個端點", "全部有自動文件（/api/docs）", "開 /api/docs 新分頁"),
    (156, 164, "回測：AUC 0.853", "EPSS 0.827、純 CVSS 0.561", "回首頁"),
    (164, 172, "分類 held-out 準確率 73%", "κ 0.818", "停在右上 API 已連線"),
    (172, 180, "所有數字都能在論文與 API 重跑驗證", "", "結尾定格"),
]


def stamp(sec, ms=0):
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def srt_text(c):
    lines = [c[2]] + ([c[3]] if c[3] else [])
    return "\n".join(lines)


os.makedirs(OUT, exist_ok=True)
with open(OUT + "/demo-video-subtitles.srt", "w", encoding="utf-8") as f:
    for i, c in enumerate(CUES, 1):
        start, end = c[0], c[1]
        f.write(f"{i}\n{stamp(start)} --> {stamp(end)}\n{srt_text(c)}\n\n")

# cue sheet: time | subtitle | operation note
rows = ["| 時間 | 字幕（畫面下方） | 操作註釋 |", "|---|---|---|"]
for c in CUES:
    t = f"{c[0]//60:02d}:{c[0]%60:02d}–{c[1]//60:02d}:{c[1]%60:02d}"
    sub = "<br>".join([c[2]] + ([c[3]] if c[3] else []))
    rows.append(f"| {t} | {sub} | {c[4]} |")
with open(OUT + "/demo-video-cues.md", "w", encoding="utf-8") as f:
    f.write("\n".join(rows) + "\n")

print("cues:", len(CUES), "| duration:", stamp(CUES[-1][1]))
print("srt bytes:", os.path.getsize(OUT + "/demo-video-subtitles.srt"))
