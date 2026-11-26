
#!/usr/bin/env python3
"""由 render_90s.SUBS 產生 90 秒 SRT，並檢查 brief §6 的字幕規格。"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_90s import SUBS, DUR  # noqa: E402

DOCS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'docs')
OUT = os.path.join(DOCS, 'demo-video-subtitles-90s.srt')


def ts(sec: float) -> str:
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return '%02d:%02d:%02d,%03d' % (h, m, s, ms)


def width(line: str) -> float:
    w = 0.0
    for ch in line:
        o = ord(ch)
        w += 1.0 if (0x2E80 <= o <= 0x9FFF or 0xFF00 <= o <= 0xFF60 or o > 0x9FFF) else 0.5
    return w


def main() -> int:
    blocks = []
    for i, (s, e, l1, l2) in enumerate(SUBS, 1):
        blocks.append('%d\n%s --> %s\n%s\n%s' % (i, ts(s), ts(e), l1, l2))
    open(OUT, 'w', encoding='utf-8', newline='\n').write('\n\n'.join(blocks) + '\n')

    issues = []
    prev_end = 0.0
    for i, (s, e, l1, l2) in enumerate(SUBS, 1):
        d = e - s
        if d < 2.0:
            issues.append('#%d 時長 %.2fs < 2s' % (i, d))
        if s < prev_end - 1e-6:
            issues.append('#%d 與前一條重疊' % i)
        prev_end = e
        for ln in (l1, l2):
            if width(ln) > 24:
                issues.append('#%d 行寬 %.1f > 24：%s' % (i, width(ln), ln))
    if SUBS[-1][1] > DUR + 0.001:
        issues.append('結尾 %.2f 超過片長 %.2f' % (SUBS[-1][1], DUR))

    print('SRT ->', OUT)
    print('entries=%d span=%.1fs avg=%.2fs' % (len(SUBS), SUBS[-1][1], sum(e - s for s, e, _, _ in SUBS) / len(SUBS)))
    print('max_line_width=%.2f' % max(width(l) for _, _, a, b in SUBS for l in (a, b)))
    print('issues=%d' % len(issues))
    for x in issues:
        print('  -', x)
    return 1 if issues else 0


if __name__ == '__main__':
    raise SystemExit(main())
