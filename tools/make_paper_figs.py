# -*- coding: utf-8 -*-
"""Paper figures at print resolution: 1830 px wide = 300 dpi at 15.5 cm.
Fonts sized so 8 pt text is legible when printed."""
import os, math
from PIL import Image, ImageDraw, ImageFont

os.makedirs(r"C:/dev/cti-platform/docs/paper", exist_ok=True)
KAI = r"C:/Windows/Fonts/kaiu.ttf"
MSYH = r"C:/Windows/Fonts/msyh.ttc"

def font(size):
    try:
        return ImageFont.truetype(KAI, size)
    except Exception:
        return ImageFont.truetype(MSYH, size)

INK = (17, 24, 39)
GRAY = (90, 100, 115)
FILL = (240, 244, 249)
BORDER = (60, 72, 90)

# ---------------- fig1: data-flow diagram (1830 x 1330) ----------------
W, H = 1830, 1330
img = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(img)

def box(x, y, w, h, title, lines):
    d.rounded_rectangle([x, y, x + w, y + h], radius=16, fill=FILL, outline=BORDER, width=4)
    d.text((x + 34, y + 24), title, font=font(44), fill=INK)
    for i, ln in enumerate(lines):
        d.text((x + 34, y + 82 + i * 44), ln, font=font(34), fill=(40, 48, 60))

def arrow(x1, y1, x2, y2):
    d.line([x1, y1, x2, y2], fill=GRAY, width=6)
    ang = math.atan2(y2 - y1, x2 - x1)
    for da in (2.6, -2.6):
        d.line([x2, y2, x2 - 34 * math.cos(ang - da), y2 - 34 * math.sin(ang - da)], fill=GRAY, width=6)

steps = [
    ("① 新聞來源", ["The Hacker News｜TWCERT/CC｜iThome"]),
    ("② 分層擷取", ["每月 15 篇國際 + 5 篇台灣，鋪滿 35 個月"]),
    ("③ 語料庫（SQLite）", ["788 篇 → 去重 783 件事件，抽出 288 個 CVE"]),
    ("④ 情資對照", ["CVE → EPSS／KEV／CVSS／CWE 官方快照"]),
    ("⑤ 分類與評分", ["規則分類 4 類；四因子 50／30／12／8"]),
    ("⑥ 修補優先級", ["KEV→P1；EPSS≥0.10 或 CVSS≥9→P2；曝險升降一級"]),
    ("⑦ API 與儀表板", ["FastAPI 8 端點 → 總覽／修補／評估／情資"]),
]
row_h, gap, x0, w0 = 130, 52, 560, 940
y = 40
pos = []
for t, ls in steps:
    box(x0, y, w0, row_h, t, ls)
    pos.append((x0, y, w0, row_h))
    y += row_h + gap

for i in range(len(steps) - 1):
    _, y1, _, h1 = pos[i]
    _, y2, _, _ = pos[i + 1]
    arrow(x0 + w0 // 2, y1 + h1, x0 + w0 // 2, y2)

# side boxes: inputs on the right, outputs on the left
box(60, pos[3][1] + 16, 420, 132, "外部官方快照", ["EPSS 911｜KEV 1,779"] if False else ["EPSS 911｜KEV 1,779", "CVSS 704｜CWE 287"])
box(60, pos[5][1] + 16, 420, 96, "企業資產清單", ["14 台示範資產，曝險比對"])
box(1560, pos[3][1] + 16, 250, 96, "覆蓋缺口", ["631 筆未收錄"])
box(1560, pos[4][1] + 24, 250, 96, "即時評估", ["單一情境 → 分數、劇本"])
arrow(480, pos[3][1] + 82, x0, pos[3][1] + 82)
arrow(480, pos[5][1] + 64, x0, pos[5][1] + 64)
arrow(x0 + w0, pos[3][1] + 82, 1560, pos[3][1] + 82)
arrow(x0 + w0, pos[4][1] + 72, 1560, pos[4][1] + 72)

img.save(r"C:/dev/cti-platform/docs/paper/fig1.png", dpi=(300, 300))
print("fig1", img.size)

# ---------------- fig2: AUC bars (1830 x 1000) ----------------
W2, H2 = 1830, 1000
img2 = Image.new("RGB", (W2, H2), "white")
d2 = ImageDraw.Draw(img2)
bars = [("純 CVSS", 0.561, (188, 194, 205)), ("僅 EPSS", 0.827, (120, 160, 200)), ("本系統", 0.853, (35, 45, 60))]
ax_x0, ax_y0, ax_w, ax_h = 300, 130, 1360, 620
d2.line([ax_x0, ax_y0 + ax_h, ax_x0 + ax_w, ax_y0 + ax_h], fill=INK, width=5)
d2.line([ax_x0, ax_y0, ax_x0, ax_y0 + ax_h], fill=INK, width=5)
for v in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0):
    yy = int(ax_y0 + ax_h - v * ax_h)
    d2.line([ax_x0 - 18, yy, ax_x0, yy], fill=INK, width=4)
    d2.text((ax_x0 - 120, yy - 26), f"{v:.1f}", font=font(36), fill=(40, 48, 60))
span = ax_w / 3
bw = 260
for i, (name, val, fill) in enumerate(bars):
    cx = ax_x0 + span * (i + 0.5)
    bh = val * ax_h
    d2.rounded_rectangle([cx - bw / 2, ax_y0 + ax_h - bh, cx + bw / 2, ax_y0 + ax_h], radius=12, fill=fill, outline=INK, width=4)
    d2.text((cx - 76, ax_y0 + ax_h - bh - 62), f"{val:.3f}", font=font(46), fill=INK)
    label = name if name != "本系統" else "本系統"
    tw = d2.textlength(label, font=font(42))
    d2.text((cx - tw / 2, ax_y0 + ax_h + 34), label, font=font(42), fill=INK)
    if name == "本系統":
        sub = "（50/30/12/8）"
        tw2 = d2.textlength(sub, font=font(30))
        d2.text((cx - tw2 / 2, ax_y0 + ax_h + 90), sub, font=font(30), fill=(60, 70, 85))
img2.save(r"C:/dev/cti-platform/docs/paper/fig2.png", dpi=(300, 300))
print("fig2", img2.size)
