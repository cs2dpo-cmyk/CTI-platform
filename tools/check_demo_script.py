# -*- coding: utf-8 -*-
"""驗收：SRT 結構、必含數字、禁用詞、總長。"""
import re, sys

SRT = r"C:/dev/cti-platform/docs/demo-video-subtitles.srt"
BRIEF = r"C:/dev/cti-platform/docs/demo-video-brief.md"

REQUIRED = ["788", "783", "35 個月", "164", "624", "288", "131", "134", "23",
            "24 小時", "7 天", "30 天", "69", "32", "99", "78.6", "64.6",
            "0.853", "0.827", "0.561", "73%", "0.818", "8 個端點", "50／30／12／8"]
FORBIDDEN = ["最強", "唯一", "顛覆", "賦能", "631", "11%", "補漏", "覆蓋缺口"]

raw = open(SRT, encoding="utf-8").read().strip()
blocks = [b for b in re.split(r"\n\s*\n", raw) if b.strip()]

def to_sec(ts):
    h, m, rest = ts.split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0

cues, errors = [], []
for b in blocks:
    lines = b.split("\n")
    if len(lines) < 3:
        errors.append(f"cue 格式不足 3 行：{lines[:1]}")
        continue
    m = re.match(r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})$", lines[1].strip())
    if not m:
        errors.append(f"時間碼格式錯誤：{lines[1]!r}")
        continue
    start, end = to_sec(m.group(1)), to_sec(m.group(2))
    text = "\n".join(lines[2:]).strip()
    cues.append((start, end, text))

for i, (s, e, t) in enumerate(cues):
    if e <= s:
        errors.append(f"cue {i+1} 結束早於開始")
    if not (2.0 <= e - s <= 10.0):
        errors.append(f"cue {i+1} 顯示長度 {e-s:.1f}s 不在 2–10 秒")
    if i and s < cues[i - 1][1] - 1e-6:
        errors.append(f"cue {i+1} 與前一條重疊")
    for line in t.split("\n"):
        cjk = sum(1 for ch in line if "\u3000" <= ch <= "\u9fff")
        if cjk > 26:
            errors.append(f"cue {i+1} 單行過長（{cjk} 字）")

total = cues[-1][1] if cues else 0
if not (170 <= total <= 230):
    errors.append(f"總長 {total:.0f}s 不在 2:50–3:50")

alltext = "\n".join(t for _, _, t in cues)
missing = [r for r in REQUIRED if r not in alltext]
if missing:
    errors.append("字幕缺必含數字：" + "、".join(missing))

bad = [w for w in FORBIDDEN if w in alltext]
if bad:
    errors.append("字幕出現禁用詞：" + "、".join(bad))

brief = open(BRIEF, encoding="utf-8").read()
if "分鏡" in brief and "分鏡表" not in brief:
    pass  # brief states it deliberately omits the storyboard

print(f"字幕條數 {len(cues)}｜總長 {int(total//60)}:{int(total%60):02d}｜平均 {total/max(1,len(cues)):.1f}s/條")
print(f"必含數字 {len(REQUIRED)} 項：", "全部命中" if not missing else f"缺 {missing}")
print("禁用詞：", "無" if not bad else f"命中 {bad}")
print("結構檢查：", "OK" if not errors else f"{len(errors)} 個問題")
print()
if errors:
    print("RESULT: FAIL")
    for e in errors:
        print(" -", e)
    sys.exit(1)
print("RESULT: PASS 字幕可直接匯入剪輯軟體")
