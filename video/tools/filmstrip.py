# -*- coding: utf-8 -*-
"""把 30 個時間點的截圖拼成一張膠卷圖，用來看整段 60 秒的視覺節奏。"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

SRC = Path(r"C:\dev\.tmp\strip")
OUT = Path(r"C:\dev\cti-platform\video\analysis\filmstrip-60s.png")

files = sorted(SRC.glob("t*.png"), key=lambda p: int(p.stem[1:]))
if not files:
    raise SystemExit("no frames")

COLS = 6
TW, TH = 480, 270
GAP, LABEL = 10, 26
ROWS = (len(files) + COLS - 1) // COLS
TOP = 92
W = COLS * TW + (COLS + 1) * GAP
H = TOP + ROWS * (TH + LABEL + GAP) + GAP

img = Image.new("RGB", (W, H), (12, 16, 20))
d = ImageDraw.Draw(img)
try:
    f_t = ImageFont.truetype("C:/Windows/Fonts/msjh.ttc", 30)
    f = ImageFont.truetype("C:/Windows/Fonts/msjh.ttc", 18)
except Exception:
    f_t = f = ImageFont.load_default()

d.text((GAP + 6, 24), "60 秒膠卷：每 2 秒一格（30 格）", fill=(232, 236, 239), font=f_t)
d.text((GAP + 6, 60), "橘框 = 音效點落在此區間；灰底格 = 無音效", fill=(143, 154, 165), font=f)

SFX = [0.15, 1.45, 1.90, 2.35, 6.80, 9.00, 11.20, 13.40, 15.60, 18.60, 18.92, 19.24,
       19.56, 20.60, 24.55, 26.70, 26.95, 27.30, 30.80, 36.60, 37.40, 37.75, 39.60,
       44.20, 44.75, 45.30, 46.60, 52.40, 57.20]

for i, p in enumerate(files):
    t = int(p.stem[1:])
    col, row = i % COLS, i // COLS
    x = GAP + col * (TW + GAP)
    y = TOP + row * (TH + LABEL + GAP)
    im = Image.open(p).convert("RGB").resize((TW, TH), Image.LANCZOS)
    img.paste(im, (x, y))
    has_sfx = any(t - 1 <= s <= t + 1 for s in SFX)
    box = (241, 178, 92) if has_sfx else (52, 60, 70)
    d.rectangle([x, y, x + TW - 1, y + TH - 1], outline=box, width=3 if has_sfx else 1)
    label = "t = %2ds" % t + ("  ·  音效" if has_sfx else "")
    d.text((x + 4, y + TH + 4), label, fill=(241, 178, 92) if has_sfx else (120, 130, 142), font=f)

OUT.parent.mkdir(parents=True, exist_ok=True)
img.save(OUT)
print("wrote", OUT, img.size, "frames", len(files))
