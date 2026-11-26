#!/usr/bin/env python3
"""真實評估操作 · 全螢幕版：裁 16:9、放大 1080p、輕推鏡、暗角、金色小標。"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1920, 1080
SRC = 'C:/dev/cti-platform/video/flow/frames99'
OUT = 'C:/dev/cti-platform/video/flow/full'
os.makedirs(OUT, exist_ok=True)

GOLD = (232, 184, 75)
WARM = (246, 244, 235)
MUTED = (150, 158, 190)
F_MONO = 'C:/Windows/Fonts/consola.ttf'
F_CJK = 'C:/Windows/Fonts/msjh.ttc'


def font(p, s):
    return ImageFont.truetype(p, s)


names = sorted(f for f in os.listdir(SRC) if f.endswith('.jpg'))
N = len(names)

# 暗角（只算一次）
vig = Image.new('L', (W, H), 0)
ImageDraw.Draw(vig).ellipse([-W * .12, -H * .14, W * 1.12, H * 1.14], fill=255)
vig = vig.filter(ImageFilter.GaussianBlur(200))

for i, name in enumerate(names):
    p = i / max(1, N - 1)
    im = Image.open(os.path.join(SRC, name)).convert('RGB')
    # 1600x1000 → 裁 16:9（去掉上下各 50px）
    im = im.crop((0, 50, 1600, 950)).resize((W, H), Image.LANCZOS)
    # 輕推鏡 1.00 → 1.05
    z = 1.0 + 0.05 * p
    cw, ch = int(W / z), int(H / z)
    x, y = (W - cw) // 2, int((H - ch) * 0.45)
    im = im.crop((x, y, x + cw, y + ch)).resize((W, H), Image.LANCZOS)
    # 暗角
    im = Image.composite(im, Image.new('RGB', (W, H), (6, 8, 14)), vig)
    d = ImageDraw.Draw(im, 'RGBA')
    # 章節與小標
    d.text((64, 56), '03 / DECISION · LIVE ASSESSMENT', font=font(F_MONO, 18), fill=(*MUTED, 170))
    if p > 0.75:
        a = min(1.0, (p - 0.75) / 0.15)
        d.text((64, H - 92), '99 RISK · P1 · SLA 24h', font=font(F_MONO, 30), fill=(*GOLD, int(235 * a)))
        d.text((64, H - 52), 'CVE-2024-3400 · OT／ICS · 勒索軟體', font=font(F_CJK, 20), fill=(*MUTED, int(200 * a)))
    else:
        d.text((64, H - 84), '即時評估 · 實際操作', font=font(F_CJK, 24), fill=(*WARM, 150))
    im.save(os.path.join(OUT, '%04d.jpg' % i), quality=94, subsampling=1)
    if i % 20 == 0:
        print('frame', i, '/', N, flush=True)
print('done', N)
