# -*- coding: utf-8 -*-
"""驗收：必含數字、禁用詞、時長、分鏡完整度。"""
import re, sys

BRIEF = r"C:/dev/cti-platform/docs/demo-video-brief.md"
NARR = r"C:/dev/cti-platform/docs/demo-video-narration.txt"

REQUIRED = ["788", "783", "35 個月", "164", "624", "288", "131", "134", "23",
            "24 小時", "7 天", "30 天", "69", "32", "99", "64.6", "78.6",
            "0.853", "0.561", "73%", "0.818", "8 個端點", "50／30／12／8"]
FORBIDDEN = ["最強", "唯一", "顛覆", "賦能", "631", "11%", "補漏", "覆蓋缺口"]

brief = open(BRIEF, encoding="utf-8").read()
narr = open(NARR, encoding="utf-8").read()

rows = [l for l in brief.split("\n") if re.match(r"^\| \d+:\d\d", l)]
spoken = [r.split("|")[3].strip() for r in rows] if rows else []
table_text = " ".join(rows)

def cjk(s):
    return sum(1 for ch in s if "\u4e00" <= ch <= "\u9fff")

fails = []
missing = [t for t in REQUIRED if t not in table_text and t not in narr]
if missing:
    fails.append("必含數字缺漏（分鏡與旁白皆無）：" + "、".join(missing))

bad_narr = [w for w in FORBIDDEN if w in narr]
bad_rows = [w for w in FORBIDDEN if any(w in s for s in spoken)]
if bad_narr or bad_rows:
    fails.append(f"旁白或分鏡出現禁用詞：旁白 {bad_narr}／分鏡 {bad_rows}")

chars = cjk(narr)
speech = chars / 200.0
total = speech + len(rows) * 4 / 60.0
if not (2.8 <= total <= 4.2):
    fails.append(f"總長超出 2.8–4.2 分（語音 {speech:.2f} ＋ 停頓 {len(rows)*4/60:.2f} = {total:.2f}）")

if len(rows) < 10:
    fails.append(f"分鏡列數不足（{len(rows)} < 10）")
if "|" in narr or "#" in narr or ">" in narr:
    fails.append("旁白檔殘留 Markdown 符號")

print(f"分鏡 {len(rows)} 列｜旁白中文 {chars} 字")
print(f"預估總長：語音 {speech:.2f} 分 ＋ 停頓 {len(rows)*4/60:.2f} 分 = {total:.2f} 分")
print("必含數字：", "全部命中（%d 項）" % len(REQUIRED) if not missing else "缺 " + str(missing))
print("禁用詞：", "無" if not (bad_narr or bad_rows) else "命中")
print()
if fails:
    print("RESULT: FAIL")
    for f in fails:
        print(" -", f)
    sys.exit(1)
print("RESULT: PASS 全部驗收條件通過")
