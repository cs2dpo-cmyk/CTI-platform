# -*- coding: utf-8 -*-
"""生成 60 秒音效軌（標準庫，固定種子，立體聲）。

比第一版豐富的部分：
- 立體聲 + 聲場擺位（每個音效有 pan）
- 新增音色：chime（數字落定）、kick（優先級）、riser（進入重點前的上升）、
  texture（低頻底噪）、granular（散點落下的細碎顆粒）
- 段落之間用不同的質感，避免整片聽起來只有一種滴答

用法：python video/tools/make_sfx.py
"""
from __future__ import annotations

import math
import os
import random
import struct
import wave

SR = 44100
DUR = 76.0
N = int(SR * DUR)
rng = random.Random(20261113)

L = [0.0] * N
R = [0.0] * N


def add(start: float, sig: list[float], gain: float = 1.0, pan: float = 0.0) -> None:
    """pan: -1 左、0 中、+1 右（等功率）。"""
    th = (pan + 1.0) * math.pi / 4.0
    gl, gr = math.cos(th) * gain, math.sin(th) * gain
    i0 = int(start * SR)
    for k, v in enumerate(sig):
        i = i0 + k
        if 0 <= i < N:
            L[i] += v * gl
            R[i] += v * gr


def env_exp(n: int, decay: float, attack: float = 0.004) -> list[float]:
    a = max(1, int(attack * SR))
    out = []
    for i in range(n):
        e = math.exp(-decay * i / SR)
        if i < a:
            e *= i / a
        out.append(e)
    return out


def tick(freq: float = 2200.0, dur: float = 0.045, bright: float = 1.0) -> list[float]:
    n = int(dur * SR)
    e = env_exp(n, 60.0, 0.001)
    out = []
    for i in range(n):
        t = i / SR
        s = math.sin(2 * math.pi * freq * t) * 0.7 + math.sin(2 * math.pi * freq * 2.01 * t) * 0.2
        out.append((s + rng.uniform(-1, 1) * 0.22 * bright) * e[i])
    return out


def pluck(freq: float, dur: float = 0.42) -> list[float]:
    n = int(dur * SR)
    e = env_exp(n, 9.0, 0.003)
    out = []
    for i in range(n):
        t = i / SR
        s = (math.sin(2 * math.pi * freq * t) * 0.8
             + math.sin(2 * math.pi * freq * 2 * t) * 0.18
             + math.sin(2 * math.pi * freq * 3 * t) * 0.06)
        out.append(s * e[i])
    return out


def chime(freq: float, dur: float = 0.9) -> list[float]:
    """數字落定的清亮鈴音（非諧波泛音）。"""
    n = int(dur * SR)
    e = env_exp(n, 4.2, 0.002)
    out = []
    for i in range(n):
        t = i / SR
        s = (math.sin(2 * math.pi * freq * t) * 0.55
             + math.sin(2 * math.pi * freq * 2.76 * t) * 0.22
             + math.sin(2 * math.pi * freq * 5.4 * t) * 0.10)
        out.append(s * e[i])
    return out


def kick(f0: float = 130.0, f1: float = 48.0, dur: float = 0.5) -> list[float]:
    """比 thud 更短的鼓擊，帶一點高頻點擊。"""
    n = int(dur * SR)
    e = env_exp(n, 11.0, 0.001)
    out = []
    phase = 0.0
    for i in range(n):
        p = i / n
        f = f0 + (f1 - f0) * (p ** 0.4)
        phase += 2 * math.pi * f / SR
        click = rng.uniform(-1, 1) * math.exp(-2600 * i / SR) * 0.5
        out.append((math.sin(phase) * 0.92 + click) * e[i])
    return out


def thud(f0: float = 120.0, f1: float = 58.0, dur: float = 0.55) -> list[float]:
    n = int(dur * SR)
    e = env_exp(n, 7.5, 0.002)
    out = []
    phase = 0.0
    for i in range(n):
        p = i / n
        f = f0 + (f1 - f0) * (p ** 0.5)
        phase += 2 * math.pi * f / SR
        burst = rng.uniform(-1, 1) * math.exp(-900 * i / SR) * 0.35
        out.append((math.sin(phase) * 0.9 + burst) * e[i])
    return out


def swell(dur: float = 2.4, lo: float = 90.0, hi: float = 210.0, noise_amt: float = 0.35) -> list[float]:
    n = int(dur * SR)
    out = []
    phase = 0.0
    lp = 0.0
    for i in range(n):
        p = i / n
        f = lo + (hi - lo) * (p ** 1.3)
        phase += 2 * math.pi * f / SR
        e = math.sin(math.pi * p) ** 1.6
        lp += 0.06 * (rng.uniform(-1, 1) - lp)
        out.append((math.sin(phase) * 0.7 + lp * noise_amt) * e)
    return out


def whoosh(dur: float = 1.6) -> list[float]:
    n = int(dur * SR)
    out = []
    lp1 = lp2 = 0.0
    for i in range(n):
        p = i / n
        w = rng.uniform(-1, 1)
        cut = 0.02 + 0.30 * math.sin(math.pi * p)
        lp1 += cut * (w - lp1)
        lp2 += 0.02 * (w - lp2)
        out.append((lp1 - lp2) * 1.4 * (math.sin(math.pi * p) ** 1.2))
    return out


def riser(dur: float = 1.4, lo: float = 120.0, hi: float = 900.0) -> list[float]:
    """上升音：正弦滑音 + 逐漸變亮的噪聲，用在重點之前。"""
    n = int(dur * SR)
    out = []
    phase = 0.0
    lp = 0.0
    for i in range(n):
        p = i / n
        f = lo * (hi / lo) ** p
        phase += 2 * math.pi * f / SR
        cut = 0.03 + 0.5 * p
        lp += cut * (rng.uniform(-1, 1) - lp)
        amp = p ** 1.8
        out.append((math.sin(phase) * 0.35 + lp * 0.9) * amp)
    return out


def texture(dur: float = 8.0) -> list[float]:
    """低頻底噪，讓段落之間不至於真空。"""
    n = int(dur * SR)
    out = []
    lp = 0.0
    for i in range(n):
        p = i / n
        lp += 0.02 * (rng.uniform(-1, 1) - lp)
        e = math.sin(math.pi * p) ** 0.9
        out.append(lp * 2.2 * e)
    return out


def shimmer(dur: float = 5.4) -> list[float]:
    n = int(dur * SR)
    out = []
    for i in range(n):
        p = i / n
        e = math.sin(math.pi * p) ** 1.4 * 0.8
        t = i / SR
        s = (math.sin(2 * math.pi * 1320 * t) * 0.35
             + math.sin(2 * math.pi * 1975 * t) * 0.22
             + math.sin(2 * math.pi * 2640 * t) * 0.12)
        out.append(s * e * (0.75 + 0.25 * math.sin(2 * math.pi * 6.5 * t)))
    return out


def pulse(freq: float = 900.0, dur: float = 0.05) -> list[float]:
    """短促的節拍點，用來撐住長段落的律動。"""
    n = int(dur * SR)
    e = env_exp(n, 90.0, 0.001)
    out = []
    for i in range(n):
        out.append(math.sin(2 * math.pi * freq * i / SR) * e[i])
    return out


def pad(dur: float = 9.0, f1: float = 220.0, f2: float = 330.0) -> list[float]:
    """兩個微失諧的正弦鋪底，帶極慢的顫音。"""
    n = int(dur * SR)
    out = []
    ph1 = ph2 = 0.0
    for i in range(n):
        p = i / n
        ph1 += 2 * math.pi * f1 / SR
        ph2 += 2 * math.pi * f2 * 1.002 / SR
        trem = 0.6 + 0.4 * math.sin(2 * math.pi * 0.25 * i / SR)
        e = math.sin(math.pi * p) ** 0.7
        out.append((math.sin(ph1) * 0.5 + math.sin(ph2) * 0.35) * trem * e)
    return out


def granular(dur: float = 3.6, count: int = 14) -> list[list[float]]:
    """散點落下時的細碎顆粒：不回傳單一信號，改成多個短音。"""
    out = []
    for k in range(count):
        out.append(tick(700 + k * 90, 0.03, 0.6))
    return out


# ---------------------------------------------------------------- 音效時間表
CUES = [
    # --- 0–7s 世界地圖 ---
    (0.15, swell(2.6, 80, 190), 0.080, 0.00, "開場氣流"),
    (1.20, tick(1180, 0.04), 0.070, -0.55, "紅點 1"),
    (2.00, tick(1319, 0.04), 0.070, 0.50, "紅點 2"),
    (2.70, tick(1480, 0.04), 0.072, -0.35, "紅點 3"),
    (3.30, tick(1661, 0.04), 0.074, 0.60, "紅點 4"),
    (3.90, tick(1865, 0.04), 0.076, -0.60, "紅點 5"),
    (4.40, tick(2093, 0.04), 0.078, 0.40, "紅點 6"),
    (4.73, chime(1760), 0.085, -0.20, "788 落定（鈴）"),
    (4.93, chime(2093), 0.085, 0.20, "783 落定（鈴）"),
    (5.13, chime(2637), 0.085, 0.00, "35 個月落定（鈴）"),

    # --- 7–14.5s 企業痛點（下行撥音） ---
    (7.30, pluck(392.00), 0.150, -0.30, "痛點 1"),
    (9.00, pluck(349.23), 0.150, 0.30, "痛點 2"),
    (10.70, pluck(311.13), 0.150, -0.25, "痛點 3"),
    (12.40, pluck(277.18), 0.150, 0.25, "痛點 4"),

    # --- 14.5–23.5s 痛點 → 解法（上行撥音） ---
    (14.81, pluck(392.00), 0.190, -0.20, "解法 1"),
    (16.81, pluck(466.16), 0.195, 0.20, "解法 2"),
    (18.81, pluck(523.25), 0.200, -0.15, "解法 3"),
    (20.81, pluck(587.33), 0.210, 0.15, "解法 4：在地情資"),

    # --- 23.5–32s 五步流水線（底噪 + 撥音 + 計量顆粒） ---
    (23.60, texture(8.4), 0.030, 0.00, "流水線底噪"),
    (23.49, pluck(392.00), 0.180, -0.40, "步驟 1"),
    (25.09, pluck(466.16), 0.180, -0.20, "步驟 2"),
    (26.69, pluck(523.25), 0.180, 0.20, "步驟 3"),
    (28.29, pluck(587.33), 0.180, 0.40, "步驟 4"),
    (29.89, pluck(659.25), 0.200, 0.00, "步驟 5"),
    (23.70, tick(3200, 0.03, 0.8), 0.045, -0.7, "計量 1"),
    (25.30, tick(3400, 0.03, 0.8), 0.045, -0.4, "計量 2"),
    (26.90, tick(3600, 0.03, 0.8), 0.045, 0.4, "計量 3"),
    (28.50, tick(3800, 0.03, 0.8), 0.045, 0.7, "計量 4"),

    # --- 32–36.5s 四類分佈 ---
    (32.08, thud(150, 70), 0.190, -0.35, "分類柱 1"),
    (32.33, thud(140, 66), 0.160, -0.10, "分類柱 2"),
    (32.57, thud(130, 62), 0.140, 0.15, "分類柱 3"),
    (32.81, thud(120, 58), 0.120, 0.35, "分類柱 4"),
    (33.40, swell(2.2, 80, 150), 0.032, 0.00, "圖表底噪"),

    # --- 36.5–48.5s 散點名次對照 ---
    (36.74, shimmer(4.6), 0.130, 0.00, "散點落下"),
    (37.30, granular()[0], 0.050, -0.6, "顆粒 1"),
    (37.80, granular()[1], 0.050, 0.5, "顆粒 2"),
    (38.40, granular()[2], 0.050, -0.3, "顆粒 3"),
    (39.00, granular()[3], 0.052, 0.6, "顆粒 4"),
    (39.60, granular()[4], 0.052, -0.5, "顆粒 5"),
    (40.20, granular()[5], 0.054, 0.3, "顆粒 6"),
    (40.80, granular()[6], 0.054, -0.2, "顆粒 7"),
    (41.40, granular()[7], 0.056, 0.4, "顆粒 8"),
    (41.90, riser(1.30), 0.110, 0.00, "進入重點的上升"),
    (41.76, whoosh(0.9), 0.100, 0.00, "散點收束"),
    (42.45, thud(110, 52, 0.8), 0.340, 0.00, "亮出 133 → 42（全片最重）"),
    (42.75, tick(1568, 0.08), 0.140, 0.25, "指標補光"),
    (43.35, shimmer(2.8), 0.055, 0.00, "停留微光"),

    # --- 48.5–54.5s P1–P3 與 SLA ---
    (48.26, kick(150, 60), 0.200, -0.30, "P1（鼓擊）"),
    (48.64, kick(130, 54), 0.170, 0.00, "P2（鼓擊）"),
    (49.02, kick(115, 50), 0.150, 0.30, "P3（鼓擊）"),
    (50.60, chime(1318, 0.7), 0.075, 0.10, "清單補點（鈴）"),

    # --- 54.5–60s 收尾 ---
    (54.70, swell(2.4, 110, 240), 0.055, 0.00, "收尾氣流"),
    (57.20, pluck(523.25, 0.9), 0.130, 0.00, "結尾撥音"),
]

# 7–23.5s（痛點 → 解法）補上律動與鋪底，避免整段只有八個撥音
for k in range(17):
    CUES.append((7.50 + k * 0.9, pulse(760 + (k % 3) * 130), 0.030,
                 -0.45 if k % 2 else 0.45, "拍點 %d" % (k + 1)))
CUES.append((7.50, pad(7.0, 196.0, 294.0), 0.022, 0.0, "痛點段鋪底"))
CUES.append((14.50, pad(9.2, 220.0, 330.0), 0.028, 0.0, "解法段鋪底"))
for row, at in enumerate((14.81, 16.81, 18.81, 20.81)):
    CUES.append((at - 0.18, whoosh(0.55), 0.045, -0.5 + row * 0.33, "換行 %d" % (row + 1)))
CUES.append((22.40, riser(1.10, 140.0, 700.0), 0.060, 0.0, "進入流程段的上升"))

K = 80.0 / 60.0
def remap(t80):
    # 結尾段從 9.5 秒壓到 5.5 秒，前面的不動
    return t80 if t80 <= 70.5 else 70.5 + (t80 - 70.5) * (5.5 / 9.5)

for at, sig, g, pan, _label in CUES:
    t = remap(at * K)
    if t < DUR:
        add(t, sig, g, pan)


# 轉場與細節音效（絕對時間，不再隨 K 縮放）
ABS_TRANSITIONS = [9.33, 19.33, 31.33, 42.67, 48.67, 66.20, 71.00]
ABS = []
for i, b in enumerate(ABS_TRANSITIONS):
    ABS.append((b - 0.34, whoosh(0.70), 0.085, -0.55 + 0.18 * (i % 3), "轉場 %d" % (i + 1)))
    ABS.append((b - 0.05, tick(1500 + i * 90, 0.05, 1.3), 0.040, 0.30 if i % 2 else -0.30, "轉場點 %d" % (i + 1)))
for i in range(5):
    ABS.append((31.45 + i * 2.28, tick(1150 + i * 60), 0.032, -0.45 + 0.22 * i, "流程框 %d" % (i + 1)))
for i in range(4):
    ABS.append((43.15 + i * 0.58, tick(880 + i * 70), 0.028, -0.35 + 0.22 * i, "分類柱 %d" % (i + 1)))
for i in range(4):
    ABS.append((65.95 + i * 0.60, tick(1420 + i * 80), 0.026, 0.35 - 0.2 * (i % 2), "圓餅圖例 %d" % (i + 1)))
ABS.append((63.10, shimmer(1.6), 0.030, 0.0, "證據淡入"))
ABS.append((70.40, swell(1.9, 80.0, 190.0, 0.30), 0.045, 0.0, "收尾鋪底"))

for at, sig, g, pan, _l in ABS:
    if 0 <= at < DUR:
        add(at, sig, g, pan)

# ---------------------------------------------------------------- 正規化與輸出
peak = max(max(abs(x) for x in L), max(abs(x) for x in R)) or 1.0
scale = 0.72 / peak
frames = bytearray()
for i in range(N):
    l = max(-1.0, min(1.0, L[i] * scale))
    r = max(-1.0, min(1.0, R[i] * scale))
    frames += struct.pack("<hh", int(l * 32767), int(r * 32767))

out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "audio")
os.makedirs(out_dir, exist_ok=True)
out = os.path.join(out_dir, "sfx.wav")
with wave.open(out, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(bytes(frames))

print("wrote", out)
print("duration %.3fs  channels 2  peak_before_norm %.4f" % (N / SR, peak))
print("cues", len(CUES))
