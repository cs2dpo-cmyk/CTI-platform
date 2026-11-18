# -*- coding: utf-8 -*-
"""每個音效點的頻帶能量與頻譜重心，判斷音色偏「噪聲」還是「樂音」。"""
import wave
import numpy as np

WAV = r"C:\dev\cti-platform\video\audio\sfx.wav"
CUES = [(0.15, "開場氣流"), (1.45, "tick1"), (1.90, "tick2"), (2.35, "tick3"),
        (6.80, "pluck1"), (9.00, "pluck2"), (11.20, "pluck3"), (13.40, "pluck4"),
        (15.60, "pluck5"), (18.60, "thud1"), (19.56, "thud4"),
        (24.55, "whoosh"), (30.80, "shimmer"), (37.40, "KEY_HIT"),
        (44.20, "P1"), (52.40, "收尾氣流"), (57.20, "結尾撥音")]

w = wave.open(WAV, "rb")
sr = w.getframerate()
x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
w.close()

nfft = 2048
win = np.hanning(nfft)
freqs = np.fft.rfftfreq(nfft, 1 / sr)

def band_energy(seg):
    seg = seg[:nfft] if len(seg) >= nfft else np.pad(seg, (0, nfft - len(seg)))
    s = np.abs(np.fft.rfft(seg * win))
    e = s ** 2
    tot = e.sum() or 1e-12
    low = e[freqs < 200].sum()
    mid = e[(freqs >= 200) & (freqs < 2000)].sum()
    high = e[freqs >= 2000].sum()
    centroid = (freqs * e).sum() / tot
    return low / tot, mid / tot, high / tot, centroid

print("%-10s %7s %7s %7s %9s" % ("音效", "<200Hz", "200-2k", ">2k", "重心Hz"))
rows = []
for at, name in CUES:
    i = int(at * sr)
    seg = x[i:i + int(0.35 * sr)]
    if len(seg) == 0:
        continue
    l, m, h, c = band_energy(seg)
    rows.append((name, l, m, h, c))
    print("%-10s %6.0f%% %6.0f%% %6.0f%% %9.0f" % (name, l * 100, m * 100, h * 100, c))

highs = [r for r in rows if r[3] > 0.5]
print()
print("高頻(>2k)占比超過 50% 的音效:", ", ".join(r[0] for r in highs) or "無")
print("平均頻譜重心: %.0f Hz" % (sum(r[4] for r in rows) / len(rows)))
