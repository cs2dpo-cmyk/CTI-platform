# -*- coding: utf-8 -*-
"""Paper figures: white-background data-flow diagram and AUC comparison chart."""
import os
from PIL import Image, ImageDraw, ImageFont

os.makedirs(r"C:/dev/cti-platform/docs/paper", exist_ok=True)
KAI = r"C:/Windows/Fonts/kaiu.ttf"
MSYH = r"C:/Windows/Fonts/msyh.ttc"

def font(size, bold=False):
    try:
        return ImageFont.truetype(KAI, size)
    except Exception:
        return ImageFont.truetype(MSYH, size)

W = 1830  # 2x of final 915px (7.75cm @ 300dpi)

# ---------------- fig1: data-flow diagram ----------------
img = Image.new("RGB", (W, 1240), "white")
d = ImageDraw.Draw(img)
INK = (20, 24, 32)
GRAY = (90, 100, 115)
FILL = (243, 245, 248)
BORDER = (70, 80, 95)

def box(x, y, w, h, title, lines):
    d.rounded_rectangle([x, y, x + w, y + h], radius=14, fill=FILL, outline=BORDER, width=3)
    d.text((x + 30, y + 22), title, font=font(30, True), fill=INK)
    for i, ln in enumerate(lines):
        d.text((x + 30, y + 64 + i * 38), ln, font=font(26), fill=(45, 52, 64))

def arrow(x1, y1, x2, y2):
    d.line([x1, y1, x2, y2], fill=GRAY, width=4)
    import math
    ang = math.atan2(y2 - y1, x2 - x1)
    for da in (2.7, -2.7):
        d.line([x2, y2, x2 - 28 * math.cos(ang - da), y2 - 28 * math.sin(ang - da)], fill=GRAY, width=4)

# main spine (7 steps), centered at x=915, width 870
steps = [
    ("① 新聞來源", ["The Hacker News｜TWCERT/CC｜iThome"]),
    ("② 分層擷取", ["每月 15 篇國際 + 5 篇台灣，鋪滿 35 個月"]),
    ("③ 語料庫（SQLite）", ["788 篇 → 去重 783 件事件，抽出 288 個 CVE"]),
    ("④ 情資對照", ["CVE → EPSS／KEV／CVSS／CWE 快照"]),
    ("⑤ 規則分類 + 可解釋評分", ["4 類分類（附理由）；權重 50／30／12／8"]),
    ("⑥ 修補優先級", ["KEV→P1；EPSS≥0.10 或 CVSS≥9→P2；曝險升降一級"]),
    ("⑦ API + 儀表板", ["FastAPI 8 端點 → 總覽／修補／評估／情資"]),
]
row_h = 118
gap = 52
x0, w0 = 480, 870
y = 90
positions = []
for t, ls in steps:
    box(x0, y, w0, row_h, t, ls)
    positions.append((x0, y, w0, row_h))
    y += row_h + gap

# vertical arrows
for i in range(6):
    (_, y1, _, h1) = positions[i]
    (_, y2, _, _) = positions[i + 1]
    arrow(915, y1 + h1, 915, y2)

# side boxes
box(60, positions[3][1] + 10, 340, 160, "外部官方快照", ["EPSS 911｜KEV 1,779", "CVSS 704｜CWE 287"])
box(60, positions[5][1] + 10, 340, 100, "企業資產清單", ["14 台示範資產，曝險比對"])
box(1460, positions[3][1] + 10, 310, 100, "覆蓋缺口", ["631 筆未收錄"])
box(1460, positions[4][1] + 20, 310, 100, "即時評估", ["單一情境 → 分數、劇本"])
# side arrows
arrow(400, positions[3][1] + 69, positions[3][0], positions[3][1] + 69)
arrow(400, positions[5][1] + 59, positions[5][0], positions[5][1] + 59)
arrow(positions[3][0] + w0, positions[3][1] + 69, 1460, positions[3][1] + 69)
arrow(positions[4][0] + w0, positions[4][1] + 69, 1460, positions[4][1] + 69)

img = img.resize((915, 620), Image.LANCZOS)
img.save(r"C:/dev/cti-platform/docs/paper/fig1.png", dpi=(300, 300))
print("fig1 saved")

# ---------------- fig2: AUC bar chart ----------------
H = 900
img2 = Image.new("RGB", (W, H), "white")
d2 = ImageDraw.Draw(img2)
bars = [("純 CVSS", 0.561), ("僅 EPSS", 0.827), ("本系統", 0.853)]
labels = ["純 CVSS", "僅 EPSS", "本系統\n（50/30/12/8）"]
fills = [(190, 195, 205), (120, 160, 200), (35, 45, 60)]
# axis area
ax_x0, ax_y0, ax_w, ax_h = 260, 150, 1350, 560
d2.line([ax_x0, ax_y0 + ax_h, ax_x0 + ax_w, ax_y0 + ax_h], fill=INK, width=4)  # x axis
d2.line([ax_x0, ax_y0, ax_x0, ax_y0 + ax_h], fill=INK, width=4)               # y axis
# y ticks
for v in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0):
    yy = ax_y0 + ax_h - v * ax_h
    d2.line([ax_x0 - 14, yy, ax_x0, yy], fill=INK, width=3)
    d2.text((ax_x0 - 130, yy - 20), f"{v:.1f}", font=font(26), fill=(45, 52, 64))
bw = 250
span = ax_w / 3
for i, (name, val) in enumerate(bars):
    cx = ax_x0 + span * (i + 0.5)
    bh = val * ax_h
    d2.rounded_rectangle([cx - bw / 2, ax_y0 + ax_h - bh, cx + bw / 2, ax_y0 + ax_h],
                         radius=10, fill=fills[i], outline=INK, width=3)
    d2.text((cx - 60, ax_y0 + ax_h - bh - 52), f"{val:.3f}", font=font(32, True), fill=INK)
    lab = labels[i].split("\n")
    d2.text((cx - 120, ax_y0 + ax_h + 40), lab[0], font=font(30, True), fill=INK)
    if len(lab) > 1:
        d2.text((cx - 150, ax_y0 + ax_h + 84), lab[1], font=font(24), fill=(45, 52, 64))
img2 = img2.resize((915, 450), Image.LANCZOS)
img2.save(r"C:/dev/cti-platform/docs/paper/fig2.png", dpi=(300, 300))
print("fig2 saved")
