# -*- coding: utf-8 -*-
"""把 60 秒的畫面段落／音效／字幕畫成三軌時間軸，用來看節奏。"""
import ast, re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(r"C:\dev\cti-platform\video")
html = (ROOT / "index.html").read_text(encoding="utf-8")
sfx = (ROOT / "tools" / "make_sfx.py").read_text(encoding="utf-8")

m = re.search(r"const SUBS = \[(.*?)\n\];", html, re.S)
cues = ast.literal_eval("[" + re.sub(r"//[^\n]*", "", m.group(1)) + "]")
sfx_at = [float(x) for x in re.findall(r"^\s*\((\d+\.\d+),", sfx, re.M)]
sfx_at = [t for t in sfx_at if t < 60]

SCENES = [
    (0.0, 7.0, "開場：世界地圖（示意）"),
    (6.55, 14.5, "企業痛點"),
    (14.05, 23.5, "痛點 → 解法"),
    (23.05, 32.0, "五步流水線"),
    (31.55, 36.5, "四類分佈"),
    (36.05, 48.5, "CVE 排序對照"),
    (48.05, 54.5, "P1–P3 與 SLA"),
    (54.05, 60.0, "收尾"),
]

W, H = 1920, 980
BG, INK, MUTE, DIM = (15, 20, 24), (232, 236, 239), (143, 154, 165), (70, 80, 92)
BAR, HI, LINE = (93, 127, 163), (241, 178, 92), (44, 52, 64)

img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)
try:
    f_title = ImageFont.truetype("C:/Windows/Fonts/msjh.ttc", 30)
    f = ImageFont.truetype("C:/Windows/Fonts/msjh.ttc", 19)
    f_s = ImageFont.truetype("C:/Windows/Fonts/msjh.ttc", 16)
except Exception:
    f_title = f = f_s = ImageFont.load_default()

L, R = 150, W - 60
def X(sec): return L + (sec / 60.0) * (R - L)

d.text((60, 34), "60 秒節奏時間軸", fill=INK, font=f_title)
d.text((60, 76), "上：畫面段落　中：音效點　下：字幕斷句　最底：每 2 秒的事件密度", fill=MUTE, font=f_s)

# 秒刻線
for s in range(0, 61, 5):
    x = X(s)
    d.line([(x, 130), (x, H - 90)], fill=LINE)
    d.text((x - 10, H - 74), str(s), fill=DIM, font=f_s)

# --- 軌 1：畫面段落 ---
y1, h1 = 150, 90
d.text((60, y1 + 6), "畫面", fill=MUTE, font=f)
d.text((60, y1 + 32), "%d 段" % len(SCENES), fill=DIM, font=f_s)
for i, (a, b, name) in enumerate(SCENES):
    x0, x1 = X(a), X(b)
    col = (36, 46, 58) if i % 2 == 0 else (44, 56, 70)
    d.rectangle([x0, y1, x1, y1 + h1], fill=col, outline=(58, 70, 86))
    if x1 - x0 > 90:
        d.text((x0 + 10, y1 + 14), name, fill=INK, font=f_s)
    d.text((x0 + 10, y1 + 56), "(%.1fs)" % (b - a), fill=DIM, font=f_s)

# --- 軌 2：音效 ---
y2 = 300
d.text((60, y2 + 6), "音效", fill=MUTE, font=f)
d.text((60, y2 + 32), "%d 點" % len(sfx_at), fill=DIM, font=f_s)
d.line([(L, y2 + 60), (R, y2 + 60)], fill=LINE)
for t in sfx_at:
    x = X(t)
    d.line([(x, y2), (x, y2 + 60)], fill=HI, width=2)

# --- 軌 3：字幕 ---
y3 = 430
d.text((60, y3 + 6), "字幕", fill=MUTE, font=f)
d.text((60, y3 + 32), "%d 條" % len(cues), fill=DIM, font=f_s)
for i, (s, e, label) in enumerate(cues):
    x0, x1 = X(s), X(e)
    d.rectangle([x0 + 1, y3 + 8, max(x0 + 3, x1 - 1), y3 + 46], fill=(58, 74, 96))
    d.text((x0 + 4, y3 + 54), str(i + 1), fill=DIM, font=f_s)

# --- 軌 4：事件密度（每 2 秒） ---
y4 = 640
d.text((60, y4 + 6), "密度", fill=MUTE, font=f)
d.text((60, y4 + 32), "每 2 秒", fill=DIM, font=f_s)
buckets = [0] * 30
for t in sfx_at:
    buckets[min(29, int(t // 2))] += 1
for s, e, _ in cues:
    buckets[min(29, int(s // 2))] += 1
for a, b, _ in SCENES:
    buckets[min(29, int(a // 2))] += 1
mx = max(buckets) or 1
for i, c in enumerate(buckets):
    x = X(i * 2) + 4
    bh = (c / mx) * 130
    col = HI if c >= 4 else BAR
    d.rectangle([x, y4 + 160 - bh, x + (R - L) / 30 - 8, y4 + 160], fill=col)
    d.text((x + 2, y4 + 166), str(c), fill=DIM, font=f_s)

# 死寂區標記（沒有字幕也沒有音效）
flat = []
cursor = 0.0
while cursor < 60:
    hit = any(abs(t - cursor) < 2.5 for t in sfx_at) or any(s <= cursor <= e for s, e, _ in cues)
    if not hit:
        start = cursor
        while cursor < 60 and not (any(abs(t - cursor) < 2.5 for t in sfx_at) or any(s <= cursor <= e for s, e, _ in cues)):
            cursor += 0.5
        flat.append((start, cursor))
    else:
        cursor += 0.5
for a, b in flat:
    if b - a >= 1.5:
        d.rectangle([X(a), 150, X(b), y4 + 160], outline=(120, 60, 60))
        d.text((X(a) + 4, 900), "安靜 %.1fs" % (b - a), fill=(190, 120, 120), font=f_s)

out = ROOT / "analysis" / "rhythm-timeline.png"
img.save(out)
print("wrote", out)
print("scenes", len(SCENES), "sfx", len(sfx_at), "cues", len(cues))
print("density", buckets)
print("quiet windows", [(round(a, 1), round(b, 1)) for a, b in flat if b - a >= 1.5])
