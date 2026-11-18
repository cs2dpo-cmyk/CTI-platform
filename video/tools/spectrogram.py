# -*- coding: utf-8 -*-
"""把 sfx.wav 畫成 波形 + 對數頻譜圖，讓人（和模型）用眼睛檢查聲音。"""
import wave, struct, os
import numpy as np
from PIL import Image, ImageDraw

WAV = r"C:\dev\cti-platform\video\audio\sfx.wav"
OUT = r"C:\dev\cti-platform\video\analysis\sfx-spectrogram.png"
os.makedirs(os.path.dirname(OUT), exist_ok=True)

w = wave.open(WAV, "rb")
n, sr = w.getnframes(), w.getframerate()
raw = w.readframes(n)
w.close()
x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
dur = n / sr

# ---- STFT ----
win = 1024
hop = 256
nfft = 1024
window = np.hanning(win).astype(np.float32)
frames = np.lib.stride_tricks.sliding_window_view(x, win)[::hop]
spec = np.abs(np.fft.rfft(frames * window, nfft))          # (T, 513)
spec_db = 20 * np.log10(spec + 1e-9)
times = np.arange(frames.shape[0]) * hop / sr

# ---- 對數頻率重採樣（30 Hz – 18 kHz） ----
freqs = np.fft.rfftfreq(nfft, 1 / sr)
rows = 620
fl = np.geomspace(30, 18000, rows)
idx = np.searchsorted(freqs, fl)
spec2 = spec_db[:, idx].T                                   # (rows, T)

# ---- 正規化到 0..1 ----
lo, hi = np.percentile(spec2, 4), np.percentile(spec2, 99.6)
norm = np.clip((spec2 - lo) / (hi - lo), 0, 1)

# ---- 色階：黑 -> 深紫 -> 橙 -> 白 ----
stops = [(0.0, (10, 12, 18)), (0.35, (58, 34, 96)), (0.62, (190, 92, 40)),
         (0.85, (241, 178, 92)), (1.0, (255, 246, 232))]
lut = np.zeros((256, 3), dtype=np.uint8)
for i in range(256):
    p = i / 255
    for k in range(len(stops) - 1):
        a, ca = stops[k]
        b, cb = stops[k + 1]
        if a <= p <= b:
            t = (p - a) / (b - a)
            lut[i] = [int(ca[j] + (cb[j] - ca[j]) * t) for j in range(3)]
            break
img_spec = lut[(norm * 255).astype(np.uint8)]                # (rows, T, 3)

W, H = 1920, 900
wave_h, gap, spec_h = 210, 40, rows
top_pad = 54
canvas = Image.new("RGB", (W, H), (15, 20, 24))
d = ImageDraw.Draw(canvas)

# ---- 波形 ----
plot_l, plot_r = 90, W - 40
pw = plot_r - plot_l
wy0, wy1 = top_pad, top_pad + wave_h
mid = (wy0 + wy1) / 2
per_px = max(1, len(x) // pw)
for px in range(pw):
    seg = x[px * per_px:(px + 1) * per_px]
    if len(seg) == 0:
        continue
    lo_v, hi_v = seg.min(), seg.max()
    d.line([(plot_l + px, mid - hi_v * wave_h * 0.48),
            (plot_l + px, mid - lo_v * wave_h * 0.48)], fill=(93, 127, 163))

# ---- 頻譜圖貼上（縮到寬度） ----
spec_img = Image.fromarray(img_spec).resize((pw, spec_h), Image.LANCZOS)
canvas.paste(spec_img, (plot_l, wy1 + gap))

# ---- 座標與標註 ----
font = None
try:
    from PIL import ImageFont
    font = ImageFont.truetype("C:/Windows/Fonts/msjh.ttc", 18)
    font_s = ImageFont.truetype("C:/Windows/Fonts/msjh.ttc", 15)
except Exception:
    pass

d.text((plot_l, 18), "sfx.wav — 波形（上）／對數頻譜 30 Hz–18 kHz（下）", fill=(232, 236, 239), font=font)
for sec in range(0, 61, 5):
    px = plot_l + int(sec / dur * pw)
    d.line([(px, wy1 + gap), (px, wy1 + gap + spec_h)], fill=(60, 70, 80))
    d.text((px - 12, wy1 + gap + spec_h + 8), str(sec), fill=(143, 154, 165), font=font_s)
d.text((plot_l - 46, wy1 + gap + spec_h // 2), "Hz", fill=(143, 154, 165), font=font_s)
for f in (100, 500, 1000, 5000, 10000):
    y = wy1 + gap + spec_h - int((np.log(f) - np.log(30)) / (np.log(18000) - np.log(30)) * spec_h)
    d.text((plot_l - 62, y - 8), str(f), fill=(90, 100, 112), font=font_s)

# ---- 音效點位置 ----
cues = [0.15, 1.45, 1.90, 2.35, 6.80, 9.00, 11.20, 13.40, 15.60,
        18.60, 18.92, 19.24, 19.56, 20.60, 24.55, 26.70, 26.95, 27.30,
        30.80, 36.60, 37.40, 37.75, 39.60, 44.20, 44.75, 45.30, 46.60,
        52.40, 57.20]
for c in cues:
    px = plot_l + int(c / dur * pw)
    d.line([(px, wy0 - 6), (px, wy0)], fill=(241, 178, 92))

canvas.save(OUT)
print("wrote", OUT, canvas.size)
print("frames", spec.shape[0], "freq bins", spec.shape[1], "db range %.0f..%.0f" % (lo, hi))
