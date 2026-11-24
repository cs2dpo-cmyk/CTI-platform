
# -*- coding: utf-8 -*-
"""Three technology diagrams (16:9, 3840x2160) from one shared model.
Emits PNG (Pillow) and SVG (same coordinates) plus a self-check report."""
import os, math
from PIL import Image, ImageDraw, ImageFont

OUT = "C:/dev/cti-platform/docs/diagrams"
W, H = 3840, 2160

BG      = "#0b1220"
CARD    = "#111a2b"
CARD_2  = "#16223a"
LINE    = "#2b3c5a"
INK     = "#dbe6f5"
MUTED   = "#7d8fae"
AMBER   = "#f59e0b"
TEAL    = "#2dd4bf"
RED     = "#f87171"
VIOLET  = "#a78bfa"

CN_B = "C:/Windows/Fonts/msjhbd.ttc"
CN_R = "C:/Windows/Fonts/msjh.ttc"
MONO = "C:/Windows/Fonts/consola.ttf"
MONO_B = "C:/Windows/Fonts/consolab.ttf"

def F(path, size, idx=0):
    try:
        return ImageFont.truetype(path, size, index=idx)
    except Exception:
        return ImageFont.truetype(CN_R, size, index=0)

MIN_SIZE = [999]

def font(kind, size):
    MIN_SIZE[0] = min(MIN_SIZE[0], size)
    if kind == "cnb": return F(CN_B, size)
    if kind == "mono": return F(MONO, size)
    if kind == "monob": return F(MONO_B, size)
    return F(CN_R, size)

OVERFLOW = []
RECTS = {}

def rrect(d, box, fill, outline, width=3, radius=22):
    d.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)

def text(d, xy, s, kind="cn", size=34, color=INK):
    d.text(xy, s, font=font(kind, size), fill=color)

def text_w(s, kind, size):
    return font(kind, size).getlength(s)

def card(d, x, y, w, h, accent, title, lines, footer=None, title_size=44, body_size=34,
         fill=CARD, dash=False, fig=""):
    RECTS.setdefault(fig, []).append((x, y, x + w, y + h, title))
    if dash:
        # dashed rectangle
        step, seg = 26, 16
        for xx in range(int(x), int(x + w), step):
            d.line([xx, y, min(xx + seg, x + w), y], fill=accent, width=3)
            d.line([xx, y + h, min(xx + seg, x + w), y + h], fill=accent, width=3)
        for yy in range(int(y), int(y + h), step):
            d.line([x, yy, x, min(yy + seg, y + h)], fill=accent, width=3)
            d.line([x + w, yy, x + w, min(yy + seg, y + h)], fill=accent, width=3)
        d.rounded_rectangle([x, y, x + w, y + h], radius=22, outline=None)
    else:
        rrect(d, [x, y, x + w, y + h], fill, LINE, 3)
    d.rounded_rectangle([x, y + 18, x + 8, y + h - 18], radius=4, fill=accent)
    ty = y + 26
    if text_w(title, "cnb", title_size) > w - 60:
        OVERFLOW.append((fig, title, "title"))
    text(d, (x + 30, ty), title, "cnb", title_size, accent)
    ly = ty + title_size + 24
    for ln in lines:
        if text_w(ln, "cn", body_size) > w - 60:
            OVERFLOW.append((fig, ln, "line"))
        text(d, (x + 30, ly), ln, "cn", body_size, INK)
        ly += int(body_size * 1.42)
    if footer:
        text(d, (x + 30, y + h - 52), footer, "mono", 30, MUTED)

def arrow(d, x1, y1, x2, y2, color=MUTED, width=4, head=18):
    d.line([x1, y1, x2, y2], fill=color, width=width)
    ang = math.atan2(y2 - y1, x2 - x1)
    for da in (2.6, -2.6):
        d.line([x2, y2, x2 - head * math.cos(ang - da), y2 - head * math.sin(ang - da)],
               fill=color, width=width)

def curve(d, x1, y1, cx, cy, x2, y2, color, width=4):
    pts = []
    for i in range(41):
        t = i / 40
        pts.append(((1 - t) ** 2 * x1 + 2 * (1 - t) * t * cx + t ** 2 * x2,
                    (1 - t) ** 2 * y1 + 2 * (1 - t) * t * cy + t ** 2 * y2))
    d.line(pts, fill=color, width=width, joint="curve")

def chip(d, x, y, w, h, label, color, size=34):
    rrect(d, [x, y, x + w, y + h], CARD_2, LINE, 2, 14)
    if text_w(label, "mono", size) > w - 24:
        OVERFLOW.append(("chip", label, "chip"))
    text(d, (x + 14, y + (h - size) // 2 - 4), label, "mono", size, color)

def header(d, title, sub):
    text(d, (140, 84), title, "cnb", 62, INK)
    text(d, (144, 172), sub, "cn", 34, MUTED)

def footer(d, s):
    text(d, (140, 2032), s, "mono", 34, MUTED)

def new_canvas():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    # faint grid
    for x in range(0, W, 96):
        d.line([x, 0, x, H], fill="#101a2b", width=1)
    for y in range(0, H, 96):
        d.line([0, y, W, y], fill="#101a2b", width=1)
    return img, d

# ---------------- A. mind map ----------------
def fig_a():
    img, d = new_canvas()
    header(d, "A｜技術心智圖", "CTI 資安風險決策支援平台 · 2026 AMITAC")
    cx, cy = 1920, 1080
    cw, ch = 760, 220
    RECTS.setdefault("A", []).append((cx - cw//2, cy - ch//2, cx + cw//2, cy + ch//2, "center"))
    rrect(d, [cx - cw//2, cy - ch//2, cx + cw//2, cy + ch//2], CARD_2, AMBER, 4)
    t1 = "CTI 資安風險決策支援平台"
    text(d, (cx - text_w(t1, "cnb", 50)//2, cy - 76), t1, "cnb", 50, INK)
    t2 = "CISO Dashboard · 可解釋決策"
    text(d, (cx - text_w(t2, "cn", 34)//2, cy + 6), t2, "cn", 34, MUTED)

    branches = [
        ("資料來源", TEAL, ["The Hacker News｜每月 250 篇", "TWCERT/CC｜台灣政府 CERT", "iThome｜台灣科技媒體", "分層取樣｜每月 15＋5 篇", "語料｜788 篇／35 個月"], 220, 300),
        ("外部情資", AMBER, ["CISA KEV｜已遭利用 1,779", "FIRST EPSS｜利用機率 911", "CVSS 3.1｜嚴重度 704", "MITRE CWE｜弱點類型 287", "快照版本｜data_as_of"], 220, 845),
        ("後端服務", TEAL, ["Python 3｜FastAPI 0.162", "Uvicorn 0.54｜8 個 REST 端點", "Pydantic 2.14｜資料驗證", "SQLAlchemy 2.1｜ORM 對映", "SQLite｜單檔資料庫"], 220, 1390),
        ("分析演算法", TEAL, ["TF-IDF｜特徵向量化", "K-Means｜主題分群", "規則式分類｜4 類（κ 0.818）", "CVE 抽取｜正規式＋斷詞容錯", "星狀分群｜去重 788→783"], 2720, 300),
        ("前端介面", TEAL, ["原生 JavaScript｜無框架", "Chart.js 4.4.6｜互動圖表", "Tailwind CDN｜樣式系統", "4 工作區｜總覽/修補/評估/情資"], 2720, 845),
        ("評估與工程", VIOLET, ["雙人標註｜Cohen's κ 0.818", "AUC 回測｜以 KEV 為標準", "時間切分回測｜測試窗口 273 筆", "pytest 105｜smoke 79", "GitHub → Render 自動部署"], 2720, 1390),
    ]
    bw, bh = 900, 470
    for name, color, lines, x, y in branches:
        card(d, x, y, bw, bh, color, name, lines, fig="A", title_size=46, body_size=34)
        # connector: from the centre card edge to the branch card's inner edge
        if x < cx:
            sx_, sy_ = cx - cw // 2, cy
            tx_, ty_ = x + bw, y + 100
            curve(d, sx_, sy_, sx_ - 210, (sy_ + ty_) // 2, tx_, ty_, color, 4)
        else:
            sx_, sy_ = cx + cw // 2, cy
            tx_, ty_ = x, y + 100
            curve(d, sx_, sy_, sx_ + 210, (sy_ + ty_) // 2, tx_, ty_, color, 4)

    footer(d, "788 篇語料 ｜ 783 件事件 ｜ 288 個 CVE ｜ 排序 AUC 0.853")
    img.save(OUT + "/tech-A-mindmap.png")
    return "A"

# ---------------- B. layers ----------------
def fig_b():
    img, d = new_canvas()
    header(d, "B｜技術分層架構", "資料 → 情資對照 → 分析 → 服務 → 介面（每層可獨立驗證）")
    layers = [
        ("介面層", "UI", TEAL, ["原生 JavaScript", "Chart.js 4.4.6", "Tailwind CDN", "4 工作區"]),
        ("服務層", "API", AMBER, ["FastAPI 0.162", "Uvicorn 0.54", "Pydantic 2.14", "8 個 REST 端點", "OpenAPI /docs"]),
        ("分析層", "DECIDE", AMBER, ["規則式分類 4 類", "可解釋評分 50／30／12／8", "SSVC → P1–P3＋SLA", "CWE 12 類", "Playbook 劇本"]),
        ("情資對照層", "ENRICH", TEAL, ["CISA KEV", "FIRST EPSS", "CVSS 3.1", "MITRE CWE", "曝險推斷"]),
        ("資料層", "STORE", VIOLET, ["SQLite", "SQLAlchemy 2.1", "788 篇語料 CSV", "assets.csv"]),
    ]
    x0, y0, row_h, gap = 140, 250, 250, 34
    lw, lx = 380, 140
    for i, (name, tag, color, items) in enumerate(layers):
        y = y0 + i * (row_h + gap)
        RECTS.setdefault("B", []).append((x0, y, x0 + 2920, y + row_h, name))
        rrect(d, [x0, y, x0 + 2920, y + row_h], CARD, LINE, 3)
        d.rounded_rectangle([x0, y + 16, x0 + 8, y + row_h - 16], radius=4, fill=color)
        text(d, (x0 + 28, y + 34), name, "cnb", 40, color)
        text(d, (x0 + 28, y + 96), tag, "mono", 34, MUTED)
        text(d, (x0 + 28, y + 150), "第 " + str(i + 1) + " 層", "cn", 34, MUTED)
        # chips
        cx = x0 + lw + 40
        cy = y + 40
        for it in items:
            wch = int(text_w(it, "mono", 34) + 44)
            if cx + wch > x0 + 2880:
                cx = x0 + lw + 40
                cy += 70
            chip(d, cx, cy, wch, 60, it, INK, 34)
            cx += wch + 16

    # sidebar
    sx, sy, sw, sh = 3130, 250, 570, 1334
    RECTS.setdefault("B", []).append((sx, sy, sx + sw, sy + sh, "sidebar"))
    rrect(d, [sx, sy, sx + sw, sy + sh], CARD, LINE, 3)
    d.rounded_rectangle([sx, sy + 16, sx + 8, sy + sh - 16], radius=4, fill=AMBER)
    text(d, (sx + 28, sy + 30), "部署與工具鏈", "cnb", 40, AMBER)
    side = ["GitHub｜版本控制", "Render｜雲端自動部署", "pytest 105 項", "jsdom smoke 79 項", "快照工具：", "  EPSS／KEV／CVSS／CWE", "截圖：puppeteer", "文件：python-docx"]
    yy = sy + 106
    for s in side:
        text(d, (sx + 28, yy), s, "cn", 34, INK)
        yy += 58

    # future work (dashed)
    fy = 1660
    card(d, 140, fy, 2920, 230, VIOLET,
         "future work（尚未實作）",
         ["LLM 摘要與處置建議｜CMDB 資產串接｜Jira／ServiceNow 工單輸出"],
         fig="B", title_size=36, body_size=34, fill=BG, dash=True)

    footer(d, "8 個 REST 端點 ｜ SQLite 單檔資料庫 ｜ Render 自動部署")
    img.save(OUT + "/tech-B-layers.png")
    return "B"

# ---------------- C. pipeline ----------------
def fig_c():
    img, d = new_canvas()
    header(d, "C｜資料管線", "從新聞到修補工單：每一步用什麼技術")
    nodes = [
        ("① 新聞抓取", TEAL, ["The Hacker News", "TWCERT/CC", "iThome"], ["requests", "BeautifulSoup"]),
        ("② 分層取樣", TEAL, ["每月 15 篇國際", "＋5 篇台灣", "鋪滿 35 個月"], ["Python argparse", "CSV 建置"]),
        ("③ 語料庫", AMBER, ["788 篇 → 783 事件", "TF-IDF 向量化", "K-Means 主題分群"], ["TF-IDF", "K-Means", "SQLite"]),
        ("④ CVE 對照", AMBER, ["288 個 CVE", "KEV／EPSS／CVSS／CWE", "快照 data_as_of"], ["正規表示式", "jieba 斷詞", "JSON 快照"]),
        ("⑤ 評分與優先級", AMBER, ["四因子 50／30／12／8", "五因子即時評估", "P1–P3 ＋ SLA"], ["可解釋加權", "SSVC 概念"]),
        ("⑥ 工單／儀表板", VIOLET, ["匯出 CSV 工單", "4 個工作區", "8 個 API 端點"], ["FastAPI", "Chart.js", "Render"]),
    ]
    nw, nh, gap = 520, 400, 88
    y = 700
    xs = [140 + i * (nw + gap) for i in range(6)]
    for i, (title, color, lines, techs) in enumerate(nodes):
        x = xs[i]
        card(d, x, y, nw, nh, color, title, lines, fig="C", title_size=38, body_size=34)
        ty = y + nh + 26
        for t in techs:
            wch = int(text_w(t, "mono", 34) + 44)
            chip(d, x, ty, wch, 58, t, color, 34)
            ty += 66
        if i < 5:
            arrow(d, x + nw + 12, y + nh // 2, xs[i + 1] - 12, y + nh // 2, MUTED, 5, 20)

    # KPI strip to balance the lower half
    kpis = [("788", "篇情資語料", TEAL), ("288", "個 CVE", AMBER), ("0.853", "排序 AUC", VIOLET)]
    kx, ky, kw, kh = 140, 1640, 1120, 240
    for i, (val, label, color) in enumerate(kpis):
        x = kx + i * (kw + 60)
        RECTS.setdefault("C", []).append((x, ky, x + kw, ky + kh, label))
        rrect(d, [x, ky, x + kw, ky + kh], CARD, LINE, 3)
        d.rounded_rectangle([x, ky + 18, x + 8, ky + kh - 18], radius=4, fill=color)
        text(d, (x + 34, ky + 44), val, "monob", 78, color)
        text(d, (x + 34, ky + 152), label, "cn", 34, INK)
    footer(d, "分類準確率 73%（κ 0.818）｜ precision@10 = 1.00 ｜ SLA：24 小時／7 天／30 天")
    img.save(OUT + "/tech-C-pipeline.png")
    return "C"

# ---------------- SVG emit (same model, simplified) ----------------
def svg_a():
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Microsoft JhengHei, Noto Sans TC, sans-serif">',
             f'<rect width="{W}" height="{H}" fill="{BG}"/>']
    parts.append(f'<text x="140" y="150" fill="{INK}" font-size="62" font-weight="700">A｜技術心智圖</text>')
    parts.append(f'<text x="144" y="200" fill="{MUTED}" font-size="34">CTI 資安風險決策支援平台 · 2026 AMITAC</text>')
    parts.append(f'<rect x="{1920-380}" y="{1080-110}" width="760" height="220" rx="22" fill="{CARD_2}" stroke="{AMBER}" stroke-width="4"/>')
    parts.append(f'<text x="{1920-190}" y="{1080-10}" fill="{INK}" font-size="50" font-weight="700">CTI 資安風險決策支援平台</text>')
    parts.append(f'<text x="{1920-130}" y="{1080+50}" fill="{MUTED}" font-size="32">CISO Dashboard · 可解釋決策</text>')
    for name, color, lines, x, y, in [
        ("資料來源", TEAL, ["The Hacker News｜每月 250 篇", "TWCERT/CC｜台灣政府 CERT", "iThome｜台灣科技媒體", "分層取樣｜每月 15＋5 篇", "語料｜788 篇／35 個月"], 220, 300),
        ("外部情資", AMBER, ["CISA KEV｜已遭利用 1,779", "FIRST EPSS｜利用機率 911", "CVSS 3.1｜嚴重度 704", "MITRE CWE｜弱點類型 287", "快照版本｜data_as_of"], 220, 845),
        ("後端服務", TEAL, ["Python 3｜FastAPI 0.162", "Uvicorn 0.54｜8 個 REST 端點", "Pydantic 2.14｜資料驗證", "SQLAlchemy 2.1｜ORM 對映", "SQLite｜單檔資料庫"], 220, 1390),
        ("分析演算法", TEAL, ["TF-IDF｜特徵向量化", "K-Means｜主題分群", "規則式分類｜4 類（κ 0.818）", "CVE 抽取｜正規式＋斷詞容錯", "星狀分群｜去重 788→783"], 2720, 300),
        ("前端介面", TEAL, ["原生 JavaScript｜無框架", "Chart.js 4.4.6｜互動圖表", "Tailwind CDN｜樣式系統", "4 工作區｜總覽/修補/評估/情資"], 2720, 845),
        ("評估與工程", VIOLET, ["雙人標註｜Cohen's κ 0.818", "AUC 回測｜以 KEV 為標準", "時間切分回測｜測試窗口 273 筆", "pytest 105｜smoke 79", "GitHub → Render 自動部署"], 2720, 1390),
    ]:
        parts.append(f'<rect x="{x}" y="{y}" width="900" height="470" rx="22" fill="{CARD}" stroke="{LINE}" stroke-width="3"/>')
        parts.append(f'<rect x="{x}" y="{y+18}" width="8" height="434" rx="4" fill="{color}"/>')
        parts.append(f'<text x="{x+30}" y="{y+70}" fill="{color}" font-size="46" font-weight="700">{name}</text>')
        for i, ln in enumerate(lines):
            parts.append(f'<text x="{x+30}" y="{y+126+i*48}" fill="{INK}" font-size="34">{ln}</text>')
    parts.append(f'<text x="140" y="2062" fill="{MUTED}" font-family="Consolas, monospace" font-size="34">788 篇語料 ｜ 783 件事件 ｜ 288 個 CVE ｜ 排序 AUC 0.853</text>')
    parts.append('</svg>')
    return "\n".join(parts)

def approx_w(s, size):
    return int(sum((size * 0.60) if ord(ch) < 128 else (size * 1.02) for ch in s))

def svg_b():
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Microsoft JhengHei, Noto Sans TC, sans-serif">',
             f'<rect width="{W}" height="{H}" fill="{BG}"/>',
             f'<text x="140" y="150" fill="{INK}" font-size="62" font-weight="700">B｜技術分層架構</text>',
             f'<text x="144" y="200" fill="{MUTED}" font-size="34">資料 → 情資對照 → 分析 → 服務 → 介面（每層可獨立驗證）</text>']
    layers = [
        ("介面層", "UI", TEAL, ["原生 JavaScript", "Chart.js 4.4.6", "Tailwind CDN", "4 工作區"]),
        ("服務層", "API", AMBER, ["FastAPI 0.162", "Uvicorn 0.54", "Pydantic 2.14", "8 個 REST 端點", "OpenAPI /docs"]),
        ("分析層", "DECIDE", AMBER, ["規則式分類 4 類", "可解釋評分", "SSVC → P1–P3＋SLA", "CWE 12 類", "Playbook 劇本"]),
        ("情資對照層", "ENRICH", TEAL, ["CISA KEV", "FIRST EPSS", "CVSS 3.1", "MITRE CWE", "曝險推斷"]),
        ("資料層", "STORE", VIOLET, ["SQLite", "SQLAlchemy 2.1", "788 篇語料 CSV", "assets.csv"]),
    ]
    for i, (name, tag, color, items) in enumerate(layers):
        y = 250 + i * 284
        parts.append(f'<rect x="140" y="{y}" width="2920" height="250" rx="22" fill="{CARD}" stroke="{LINE}" stroke-width="3"/>')
        parts.append(f'<rect x="140" y="{y+16}" width="8" height="218" rx="4" fill="{color}"/>')
        parts.append(f'<text x="168" y="{y+72}" fill="{color}" font-size="40" font-weight="700">{name}</text>')
        parts.append(f'<text x="168" y="{y+118}" fill="{MUTED}" font-family="Consolas, monospace" font-size="34">{tag}</text>')
        cx = 560
        for it in items:
            wch = approx_w(it, 34) + 44
            parts.append(f'<rect x="{cx}" y="{y+40}" width="{wch}" height="60" rx="14" fill="{CARD_2}" stroke="{LINE}" stroke-width="2"/>')
            parts.append(f'<text x="{cx+22}" y="{y+82}" fill="{INK}" font-family="Consolas, monospace" font-size="34">{it}</text>')
            cx += wch + 16
    parts.append(f'<rect x="3130" y="250" width="570" height="1334" rx="22" fill="{CARD}" stroke="{LINE}" stroke-width="3"/>')
    parts.append(f'<text x="3158" y="300" fill="{AMBER}" font-size="40" font-weight="700">部署與工具鏈</text>')
    for i, s in enumerate(["GitHub｜版本控制", "Render｜雲端自動部署", "pytest 105 項", "jsdom smoke 79 項", "快照工具：EPSS／KEV", "截圖：puppeteer", "文件：python-docx"]):
        parts.append(f'<text x="3158" y="{370 + i*58}" fill="{INK}" font-size="34">{s}</text>')
    parts.append(f'<rect x="140" y="1660" width="2920" height="230" rx="22" fill="none" stroke="{VIOLET}" stroke-width="3" stroke-dasharray="16 12"/>')
    parts.append(f'<text x="170" y="1720" fill="{VIOLET}" font-size="36" font-weight="700">future work（尚未實作）</text>')
    parts.append(f'<text x="170" y="1782" fill="{INK}" font-size="34">LLM 摘要與處置建議｜CMDB 資產串接｜Jira／ServiceNow 工單輸出</text>')
    parts.append(f'<text x="140" y="2062" fill="{MUTED}" font-family="Consolas, monospace" font-size="34">8 個 REST 端點 ｜ SQLite 單檔資料庫 ｜ Render 自動部署</text>')
    parts.append('</svg>')
    return "\n".join(parts)

def svg_c():
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Microsoft JhengHei, Noto Sans TC, sans-serif">',
             f'<rect width="{W}" height="{H}" fill="{BG}"/>',
             f'<text x="140" y="150" fill="{INK}" font-size="62" font-weight="700">C｜資料管線</text>',
             f'<text x="144" y="200" fill="{MUTED}" font-size="34">從新聞到修補工單：每一步用什麼技術</text>']
    nodes = [
        ("① 新聞抓取", TEAL, ["The Hacker News", "TWCERT/CC", "iThome"], ["requests", "BeautifulSoup"]),
        ("② 分層取樣", TEAL, ["每月 15 篇國際", "＋5 篇台灣", "鋪滿 35 個月"], ["Python", "CSV 建置"]),
        ("③ 語料庫", AMBER, ["788 篇 → 783 事件", "TF-IDF 向量化", "K-Means 主題分群"], ["TF-IDF", "K-Means", "SQLite"]),
        ("④ CVE 對照", AMBER, ["288 個 CVE", "KEV／EPSS／CVSS／CWE", "快照 data_as_of"], ["正規表示式", "jieba 斷詞", "JSON 快照"]),
        ("⑤ 評分與優先級", AMBER, ["四因子 50／30／12／8", "五因子即時評估", "P1–P3 ＋ SLA"], ["可解釋加權", "SSVC 概念"]),
        ("⑥ 工單／儀表板", VIOLET, ["匯出 CSV 工單", "4 個工作區", "8 個 API 端點"], ["FastAPI", "Chart.js", "Render"]),
    ]
    for i, (title, color, lines, techs) in enumerate(nodes):
        x = 140 + i * 608
        y = 700
        parts.append(f'<rect x="{x}" y="{y}" width="520" height="400" rx="22" fill="{CARD}" stroke="{LINE}" stroke-width="3"/>')
        parts.append(f'<rect x="{x}" y="{y+18}" width="8" height="364" rx="4" fill="{color}"/>')
        parts.append(f'<text x="{x+30}" y="{y+70}" fill="{color}" font-size="38" font-weight="700">{title}</text>')
        for j, ln in enumerate(lines):
            parts.append(f'<text x="{x+30}" y="{y+126+j*48}" fill="{INK}" font-size="34">{ln}</text>')
        for j, t in enumerate(techs):
            wch = approx_w(t, 34) + 44
            parts.append(f'<rect x="{x}" y="{y+420+j*68}" width="{wch}" height="58" rx="14" fill="{CARD_2}" stroke="{LINE}" stroke-width="2"/>')
            parts.append(f'<text x="{x+22}" y="{y+460+j*68}" fill="{color}" font-family="Consolas, monospace" font-size="34">{t}</text>')
        if i < 5:
            parts.append(f'<line x1="{x+532}" y1="{y+200}" x2="{x+596}" y2="{y+200}" stroke="{MUTED}" stroke-width="5"/>')
            parts.append(f'<polygon points="{x+596},{y+200} {x+580},{y+190} {x+580},{y+210}" fill="{MUTED}"/>')
    for i, (val, label, color) in enumerate([("788", "篇情資語料", TEAL), ("288", "個 CVE", AMBER), ("0.853", "排序 AUC", VIOLET)]):
        x = 140 + i * 1180
        parts.append(f'<rect x="{x}" y="1640" width="1120" height="240" rx="22" fill="{CARD}" stroke="{LINE}" stroke-width="3"/>')
        parts.append(f'<rect x="{x}" y="1658" width="8" height="204" rx="4" fill="{color}"/>')
        parts.append(f'<text x="{x+34}" y="1730" fill="{color}" font-family="Consolas, monospace" font-size="78" font-weight="700">{val}</text>')
        parts.append(f'<text x="{x+34}" y="1806" fill="{INK}" font-size="34">{label}</text>')
    parts.append(f'<text x="140" y="2062" fill="{MUTED}" font-family="Consolas, monospace" font-size="34">分類準確率 73%（κ 0.818）｜ precision@10 = 1.00 ｜ SLA：24 小時／7 天／30 天</text>')
    parts.append('</svg>')
    return "\n".join(parts)

for fn in (fig_a, fig_b, fig_c):
    key = fn()
    print("drawn", key)

open(OUT + "/tech-A-mindmap.svg", "w", encoding="utf-8").write(svg_a())
open(OUT + "/tech-B-layers.svg", "w", encoding="utf-8").write(svg_b())
open(OUT + "/tech-C-pipeline.svg", "w", encoding="utf-8").write(svg_c())
print("svg written")

# ---------------- self-check ----------------
print("MIN font size:", MIN_SIZE[0])
print("OVERFLOW:", OVERFLOW if OVERFLOW else "none")
for key, rects in RECTS.items():
    bad = []
    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            a, b = rects[i], rects[j]
            if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                bad.append((a[4], b[4]))
    print(f"rects[{key}] = {len(rects)} overlaps: {bad if bad else 'none'}")
