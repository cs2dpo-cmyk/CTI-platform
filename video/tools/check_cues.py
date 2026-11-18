# -*- coding: utf-8 -*-
"""檢查 index.html 裡的字幕斷句是否符合規則。

用法：python video/tools/check_cues.py
失敗時回傳非 0，方便接進 CI。
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
HTML = HERE / "index.html"
DURATION = 80.0

MIN_SEC, MAX_SEC = 1.2, 6.0
MAX_CHARS = 30  # 合併句（使用者要求把兩句連讀）會超過 22
MAX_GAP = 1.6
MAX_CPS = 9.0

text = HTML.read_text(encoding="utf-8")
m = re.search(r"const SUBS = \[(.*?)\n\];", text, re.S)
if not m:
    print("找不到 SUBS 陣列")
    sys.exit(1)

body = re.sub(r"//[^\n]*", "", m.group(1))
cues = ast.literal_eval("[" + body + "]")

problems = []
for i, (start, end, label) in enumerate(cues):
    dur = end - start
    tag = "#%02d %.1f-%.1f「%s」" % (i + 1, start, end, label)
    if end <= start:
        problems.append(tag + " 時間倒置")
    if not MIN_SEC <= dur <= MAX_SEC:
        problems.append(tag + " 長度 %.2fs 不在 %.1f–%.1f" % (dur, MIN_SEC, MAX_SEC))
    if start < 0 or end > DURATION:
        problems.append(tag + " 超出 0–%.0f 秒" % DURATION)
    if len(label) > MAX_CHARS:
        problems.append(tag + " 超過 %d 字" % MAX_CHARS)
    if dur > 0 and len(label) / dur > MAX_CPS:
        problems.append(tag + " 讀速 %.1f 字/秒" % (len(label) / dur))
    if i:
        prev = cues[i - 1]
        if start < prev[1] - 1e-9:
            problems.append(tag + " 與前一條重疊")
        gap = start - prev[1]
        if gap > MAX_GAP:
            problems.append(tag + " 空窗 %.2fs" % gap)

total = sum(e - s for s, e, _ in cues)
print("字幕 %d 條，上台詞 %.1f 秒（%.0f%%）" % (len(cues), total, total / DURATION * 100))
if problems:
    print("發現 %d 個問題：" % len(problems))
    for p in problems:
        print("  " + p)
    sys.exit(1)
print("全部通過")
