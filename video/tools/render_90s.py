
#!/usr/bin/env python3
"""CTI 90 秒 demo 影片：逐幀渲染（Pillow）。畫面是 t 的純函數。

資料來源：video/data-90s.json（由本機 /api/v1/patch-priority 產生）
用法：
  python render_90s.py --all  --out <dir>
  python render_90s.py --times 2,6,13,22,30,38,45,52,60,68,76,86 --out <dir>
"""
from __future__ import annotations
import argparse, json, math, os
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1920, 1080
FPS = 30
DUR = 90.0

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(os.path.dirname(HERE), 'data-90s.json')
D = json.load(open(DATA_PATH, encoding='utf-8'))

BG = (15, 20, 24)
PANEL = (19, 26, 32)
INK = (232, 236, 239)
MUTE = (143, 154, 165)
DIM = (90, 101, 112)
LINE = (58, 69, 80)
BLUE = (93, 127, 163)
HI = (241, 178, 92)
WHITE = (242, 245, 247)

F_SANS = 'C:/Windows/Fonts/msjh.ttc'
F_BOLD = 'C:/Windows/Fonts/msjhbd.ttc'
F_MONO = 'C:/Windows/Fonts/consola.ttf'


@lru_cache(maxsize=512)
def font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    path = {'sans': F_SANS, 'bold': F_BOLD, 'mono': F_MONO}[kind]
    return ImageFont.truetype(path, size)


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ss(a, b, x):
    if b == a:
        return 1.0 if x >= b else 0.0
    t = clamp((x - a) / (b - a))
    return t * t * (3 - 2 * t)


def eo(x):
    return 1 - (1 - clamp(x)) ** 3


def ease(x):
    t = clamp(x)
    return 2 * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 2 / 2


def lerp(a, b, t):
    return a + (b - a) * t


CJK = set('，、（）／：；！？「」→←↑↓·')


def has_cjk(s: str) -> bool:
    return any('\u2e80' <= ch <= '\u9fff' or ch in CJK for ch in s)


GLYPH_MAP = {'\u2265': '>=', '\u2264': '<=', '\u2192': '\u2192', '\u2013': '-'}


def T(d, xy, s, size, color, alpha=1.0, anchor='ls', kind='sans'):
    if alpha <= 0.003:
        return
    for k2, v2 in GLYPH_MAP.items():
        s = s.replace(k2, v2)
    if kind == 'mono' and has_cjk(s):
        kind = 'sans'
    d.text(xy, s, font=font(kind, size), fill=(color[0], color[1], color[2], int(255 * clamp(alpha))), anchor=anchor)


def tw(d, s, size, kind='sans'):
    if kind == 'mono' and has_cjk(s):
        kind = 'sans'
    return d.textlength(s, font=font(kind, size))


def panel(d, box, r=14, fill=None, outline=None, alpha=1.0, width=1):
    if alpha <= 0.003:
        return
    fa = None if fill is None else (fill[0], fill[1], fill[2], int(255 * clamp(alpha) * (fill[3] / 255 if len(fill) == 4 else 1)))
    oa = None if outline is None else (outline[0], outline[1], outline[2], int(255 * clamp(alpha)))
    d.rounded_rectangle(box, radius=r, fill=fa, outline=oa, width=width)


def make_bg():
    img = Image.new('RGB', (W, H), BG)
    px = img.load()
    for y in range(H):
        t = y / (H - 1)
        r = int(lerp(11, 15, t)); g = int(lerp(16, 20, t)); b = int(lerp(19, 24, t))
        for x in range(0, W, 8):
            px[x, y] = (r, g, b)
            px[x + 1, y] = (r, g, b)
            px[x + 2, y] = (r, g, b)
            px[x + 3, y] = (r, g, b)
            px[x + 4, y] = (r, g, b)
            px[x + 5, y] = (r, g, b)
            px[x + 6, y] = (r, g, b)
            px[x + 7, y] = (r, g, b)
    glow = Image.new('L', (W, H), 0)
    gd = ImageDraw.Draw(glow)
    gd.ellipse([W * 0.5 - 900, H * 0.42 - 700, W * 0.5 + 900, H * 0.42 + 700], fill=34)
    glow = glow.filter(ImageFilter.GaussianBlur(160))
    tint = Image.new('RGB', (W, H), (40, 46, 66))
    img = Image.composite(tint, img, glow)
    d = ImageDraw.Draw(img, 'RGBA')
    for y in range(90, H, 90):
        d.line([(0, y), (W, y)], fill=(44, 54, 64, 26), width=1)
    return img.convert('RGBA')


BG_IMG = None


def badge(d, x, y, text, color, alpha=1.0, size=20, padx=12, h=32):
    w = tw(d, text, size) + padx * 2
    panel(d, [x, y, x + w, y + h], r=6, fill=(color[0], color[1], color[2], 40), outline=None, alpha=alpha)
    T(d, (x + padx, y + h / 2 + size * 0.36), text, size, color, alpha=alpha, kind='mono')


# --------------------------------------------------------------------------- #
# S1 0–11s 標題 → 痛點
# --------------------------------------------------------------------------- #
def s_title(d, lt, a):
    a1 = a * (1 - ss(3.1, 3.9, lt))
    if a1 > 0:
        T(d, (W / 2, 452), 'CTI 資安風險決策支援平台', 78, INK, a1, anchor='ms', kind='bold')
        T(d, (W / 2, 540), '90 秒實機操作示範', 34, HI, a1 * ss(0.5, 1.3, lt), anchor='ms')
        lw = 420 * eo(lt / 1.2)
        d.line([(W / 2 - lw, 590), (W / 2 + lw, 590)], fill=(LINE[0], LINE[1], LINE[2], int(200 * a1)), width=2)
    a2 = a * ss(3.4, 4.3, lt)
    if a2 > 0:
        T(d, (W / 2, 300), '每天數百則新聞，團隊只有 1–3 人', 46, INK, a2, anchor='ms', kind='bold')
        T(d, (W / 2, 368), '問題不是沒有資訊，而是不知道先修哪一個', 28, MUTE, a2 * ss(4.0, 5.0, lt), anchor='ms')
        chips = [('01', '情資太多'), ('02', '先修哪一個'), ('03', '期限沒依據'), ('04', '在地被漏掉')]
        x0 = W / 2 - 2 * 300 - 30
        for i, (n, s) in enumerate(chips):
            e = eo((lt - 4.4 - i * 0.28) / 0.7)
            if e <= 0:
                continue
            x = x0 + i * 320
            y = 520 + (1 - e) * 24
            panel(d, [x, y, x + 280, y + 150], r=12, fill=(19, 26, 32, 210), outline=LINE, alpha=a2 * e)
            T(d, (x + 26, y + 52), n, 26, HI, a2 * e, kind='mono')
            T(d, (x + 26, y + 108), s, 30, INK, a2 * e, kind='bold')


# --------------------------------------------------------------------------- #
# S2 10.6–18.6s KPI
# --------------------------------------------------------------------------- #
def s_kpi(d, lt, a):
    k = D['kpi']
    cards = [
        (str(k['corpus']), '篇中英文情資', '語料'),
        (str(k['events']), '件去重事件', '事件'),
        (str(k['months']), '個月時間跨度', '期間'),
        (str(D['patch']['total']), '個 CVE 排入清單', '修補'),
    ]
    T(d, (200, 250), '三個數字，說明這份語料的規模', 40, INK, a * ss(0.2, 0.9, lt), kind='bold')
    T(d, (200, 300), 'TWCERT · iThome · The Hacker News', 24, MUTE, a * ss(0.3, 1.0, lt), kind='mono')
    for i, (num, unit, tag) in enumerate(cards):
        e = eo((lt - 0.5 - i * 0.2) / 1.0)
        if e <= 0:
            continue
        x = 200 + i * 400
        y = 400 + (1 - e) * 26
        panel(d, [x, y, x + 360, y + 250], r=14, fill=(19, 26, 32, 220), outline=LINE, alpha=a * e)
        T(d, (x + 30, y + 58), tag, 22, DIM, a * e, kind='mono')
        val = str(round(int(num) * eo((lt - 0.5 - i * 0.2) / 1.4)))
        T(d, (x + 30, y + 158), val, 84, INK if i < 3 else HI, a * e, kind='mono')
        T(d, (x + 30, y + 210), unit, 26, MUTE, a * e)
    e2 = eo((lt - 1.6) / 1.0)
    if e2 > 0:
        y = 730
        panel(d, [200, y, 1720, y + 120], r=14, fill=(19, 26, 32, 200), outline=LINE, alpha=a * e2)
        total = k['taiwan'] + k['global']
        bar_x, bar_w = 260, 900
        wt = bar_w * (k['taiwan'] / total)
        panel(d, [bar_x, y + 52, bar_x + wt, y + 84], r=16, fill=HI, alpha=a * e2)
        panel(d, [bar_x + wt + 4, y + 52, bar_x + bar_w, y + 84], r=16, fill=BLUE, alpha=a * e2)
        T(d, (bar_x, y + 42), '台灣 ' + str(k['taiwan']) + ' 篇', 22, HI, a * e2, kind='mono')
        T(d, (bar_x + bar_w, y + 42), '國際 ' + str(k['global']) + ' 篇', 22, BLUE, a * e2, anchor='rs', kind='mono')
        T(d, (bar_x + bar_w + 60, y + 78), '本地通報與國際來源並重', 24, MUTE, a * e2)


# --------------------------------------------------------------------------- #
# S3 18.2–34.2s 修補清單
# --------------------------------------------------------------------------- #
def s_table(d, lt, a):
    p = D['patch']
    rows = D['rows']
    e = eo((lt - 0.1) / 0.7)
    if e <= 0:
        return
    T(d, (160, 180), '修補清單', 44, INK, a * e, kind='bold')
    T(d, (160, 228), str(p['total']) + ' 個 CVE · 每一列都附判斷依據', 26, MUTE, a * e)
    for i, (lab, col) in enumerate([('KEV', HI), ('EPSS', BLUE), ('CVSS', MUTE), ('CWE', MUTE)]):
        badge(d, 1180 + i * 118, 176, lab, col, a * e)
    panel(d, [160, 280, 1760, 880], r=14, fill=(17, 23, 29, 225), outline=LINE, alpha=a * e)
    # 表頭
    cols = [(190, 'CVE'), (560, '弱點'), (740, 'CVSS'), (880, 'EPSS'), (1010, '優先級'), (1170, '判斷依據')]
    for x, name in cols:
        T(d, (x, 324), name, 20, DIM, a * e, kind='mono')
    d.line([(180, 344), (1740, 344)], fill=(LINE[0], LINE[1], LINE[2], int(160 * a * e)), width=1)
    fade_filter = ss(7.6, 8.6, lt)
    for i, r in enumerate(rows):
        er = eo((lt - 0.5 - i * 0.16) / 0.6)
        if er <= 0:
            continue
        y = 376 + i * 54
        dimapplied = 1.0
        if fade_filter > 0 and not r['taiwan']:
            dimapplied = lerp(1.0, 0.34, fade_filter)
        al = a * er * dimapplied
        if i % 2 == 0:
            d.rectangle([170, y - 24, 1750, y + 24], fill=(24, 31, 38, int(120 * al)))
        T(d, (190, y + 8), r['cve'], 22, INK, al, kind='mono')
        T(d, (560, y + 8), r['weakness'] or '—', 22, MUTE, al)
        cv = '—' if r['cvss'] is None else ('%.1f' % r['cvss'])
        T(d, (740, y + 8), cv, 22, INK, al, kind='mono')
        ep = '—' if r['epss'] is None else ('%.2f' % r['epss'])
        T(d, (880, y + 8), ep, 22, MUTE, al, kind='mono')
        pcol = HI if r['priority'] == 'P1' else (BLUE if r['priority'] == 'P2' else MUTE)
        badge(d, 1005, y - 12, r['priority'], pcol, al, size=18, h=28)
        reason = r['reason'] if r['reason'] else ('KEV 命中' if r['exploited'] else '依 EPSS 與 CVSS')
        T(d, (1170, y + 8), reason[:20], 21, MUTE, al)
    ef = eo((lt - 7.8) / 0.8)
    if ef > 0:
        y = 812
        T(d, (190, y + 8), '篩選', 22, DIM, a * ef)
        badge(d, 270, y - 16, '本地通報 ' + str(p['taiwan_reported']), HI, a * ef, size=20, h=38)
        badge(d, 540, y - 16, '遠端執行 ' + str(p['rce']), BLUE, a * ef, size=20, h=38)
        T(d, (800, y + 8), '→ 匯出 CSV，直接變成工單', 24, INK, a * ef)


# --------------------------------------------------------------------------- #
# S4 33.8–41.6s 優先級甜甜圈
# --------------------------------------------------------------------------- #
def s_priority(d, lt, a):
    p = D['patch']
    e = eo((lt - 0.2) / 0.8)
    if e <= 0:
        return
    T(d, (200, 210), '三個等級，對應三種處理時限', 40, INK, a * e, kind='bold')
    T(d, (200, 258), 'P1 = KEV 命中；P2 = EPSS ≥ 0.10 或 CVSS ≥ 9.0', 24, MUTE, a * e)
    cx, cy, r = 600, 570, 210
    segs = [(p['P1'], HI, 'P1'), (p['P2'], BLUE, 'P2'), (p['P3'], (150, 172, 198), 'P3')]
    total = sum(s[0] for s in segs)
    grow = eo((lt - 0.5) / 1.4)
    ang = -90.0
    box = [cx - r, cy - r, cx + r, cy + r]
    for cnt, col, _ in segs:
        sweep = 360.0 * cnt / total * grow
        if sweep > 0.2:
            d.arc(box, ang, ang + sweep, fill=(col[0], col[1], col[2], int(255 * a * e)), width=54)
        ang += sweep
    d.ellipse([cx - r * 0.62, cy - r * 0.62, cx + r * 0.62, cy + r * 0.62], fill=(15, 20, 24, int(255 * a * e)))
    T(d, (cx, cy + 14), str(total), 64, INK, a * e, anchor='ms', kind='mono')
    T(d, (cx, cy + 62), '個 CVE', 24, DIM, a * e, anchor='ms')
    legend = [(p['P1'], HI, 'P1', 'SLA 24 小時', '立刻處理'),
              (p['P2'], BLUE, 'P2', 'SLA 7 天', '本週排入'),
              (p['P3'], (150, 172, 198), 'P3', 'SLA 30 天', '例行排程')]
    for i, (cnt, col, name, sla, note) in enumerate(legend):
        el = eo((lt - 0.8 - i * 0.22) / 0.7)
        if el <= 0:
            continue
        y = 430 + i * 120
        panel(d, [980, y - 34, 1700, y + 62], r=10, fill=(19, 26, 32, 200), outline=None, alpha=a * el)
        d.rectangle([1006, y - 12, 1030, y + 12], fill=(col[0], col[1], col[2], int(255 * a * el)))
        T(d, (1052, y + 10), name, 34, INK, a * el, kind='bold')
        T(d, (1130, y + 10), str(cnt) + ' 個', 30, col, a * el, kind='mono')
        T(d, (1270, y + 10), sla, 26, MUTE, a * el)
        T(d, (1500, y + 10), note, 24, DIM, a * el)
    en = eo((lt - 1.8) / 0.8)
    T(d, (980, 800), '其中 ' + str(p['exploited']) + ' 個已遭實際利用（CISA KEV）', 24, HI, a * en)


# --------------------------------------------------------------------------- #
# S5 41.2–57.2s 即時評估 / what-if / 權重
# --------------------------------------------------------------------------- #
def s_assess(d, lt, a):
    e = eo((lt - 0.1) / 0.7)
    if e <= 0:
        return
    T(d, (160, 180), '即時評估：清單沒有的情境', 42, INK, a * e, kind='bold')
    T(d, (160, 228), '填六個欄位，得到分數、等級與理由', 25, MUTE, a * e)
    fields = [('CVE', 'CVE-2024-3400'), ('曝險', '對外網站'), ('CVSS', '9.8'),
              ('控制項', 'EDR'), ('資產', '官網'), ('產業', '製造')]
    phase2 = ss(5.0, 6.0, lt)     # 改 CVSS 9.0
    phase3 = ss(8.4, 9.4, lt)     # 內網 + 三控制
    vals = []
    for name, v in fields:
        if name == 'CVSS':
            v = '9.0' if phase2 > 0.5 else '9.8'
        if name in ('控制項',):
            v = 'WAF／隔離／備份' if phase3 > 0.5 else ('EDR' if phase2 < 0.5 else 'EDR')
        if name == '曝險':
            v = '內網' if phase3 > 0.5 else '對外網站'
        vals.append((name, v))
    panel(d, [160, 290, 820, 700], r=14, fill=(19, 26, 32, 220), outline=LINE, alpha=a * e)
    for i, (name, v) in enumerate(vals):
        y = 350 + i * 56
        T(d, (196, y), name, 22, DIM, a * e, kind='mono')
        panel(d, [330, y - 30, 780, y + 8], r=8, fill=(26, 34, 42, 230), outline=LINE, alpha=a * e)
        col = INK
        if name == '曝險' and phase3 > 0.5:
            col = HI
        T(d, (352, y - 3), v, 24, col, a * e)
    # 分數
    score = D['assess']['hi']
    lbl, colr = 'P1', HI
    if phase3 > 0.5:
        score = D['assess']['low']; lbl, colr = 'P3', (150, 172, 198)
    elif phase2 > 0.5:
        score = D['assess']['mid']; lbl, colr = 'P2', BLUE
    cx, cy, r = 1300, 470, 140
    eg = eo((lt - 1.6) / 1.2)
    d.arc([cx - r, cy - r, cx + r, cy + r], -90, -90 + 360 * (score / 100.0) * eg,
          fill=(colr[0], colr[1], colr[2], int(255 * a * e)), width=26)
    shown = score * eg
    T(d, (cx, cy + 18), '%.1f' % shown, 74, INK, a * e, anchor='ms', kind='mono')
    T(d, (cx, cy + 74), '風險分數', 22, DIM, a * e, anchor='ms')
    if eg > 0.5:
        badge(d, cx - 44, cy - 118, lbl, colr, a * e, size=26, h=44)
    # 權重
    ew = eo((lt - 10.6) / 0.9)
    if ew > 0:
        T(d, (160, 760), '四因子權重（固定，可拆解）', 26, INK, a * ew, kind='bold')
        wl = [('嚴重度 50', 50, HI), ('利用成熟度 30', 30, BLUE), ('曝露程度 12', 12, (150, 172, 198)), ('CVE 具名 8', 8, MUTE)]
        for i, (name, w, col) in enumerate(wl):
            x = 160 + i * 400
            panel(d, [x, 830, x + 360, 856], r=6, fill=(26, 34, 42, 220), alpha=a * ew)
            panel(d, [x, 830, x + 360 * (w / 50.0), 856], r=6, fill=col, alpha=a * ew)
            T(d, (x, 816), name, 22, MUTE, a * ew)


# --------------------------------------------------------------------------- #
# S6 56.8–72.2s 散點與名次
# --------------------------------------------------------------------------- #
def s_scatter(d, lt, a):
    e = eo((lt - 0.1) / 0.7)
    if e <= 0:
        return
    n = D['scatter']['n']
    pts = D['scatter']['pts']
    k = D['kev_rank']
    T(d, (240, 200), '同一批 CVE，兩種排法', 42, INK, a * e, kind='bold')
    T(d, (240, 248), str(n) + ' 個 CVE · 橙點 = KEV 已確認遭利用（' + str(k['exploited_n']) + ' 個）', 24, MUTE, a * e)
    px, py, pw, ph = 300, 320, 720, 520
    d.line([(px, py + ph), (px + pw, py + ph)], fill=(LINE[0], LINE[1], LINE[2], int(220 * a * e)), width=1)
    d.line([(px, py), (px, py + ph)], fill=(LINE[0], LINE[1], LINE[2], int(220 * a * e)), width=1)
    d.line([(px, py), (px + pw, py + ph)], fill=(LINE[0], LINE[1], LINE[2], int(140 * a * e)), width=1)
    T(d, (px, py + ph + 44), '← 按 CVSS 名次 靠前', 20, MUTE, a * e, kind='mono')
    T(d, (px - 14, py - 18), '↑ 按本系統 名次 靠前', 20, MUTE, a * e, kind='mono')
    T(d, (px + pw, py - 16), '對角線 = 兩種排法一致', 18, DIM, a * e, anchor='rs')
    for (xr, yr, flag) in pts:
        p = (lt - 1.0 - (xr / n) * 4.0) / 0.5
        if p <= 0:
            continue
        ee = eo(p)
        x = px + (xr / (n - 1)) * pw
        y = py + (yr / (n - 1)) * ph
        if flag:
            rr2 = 5.0 * ee
            d.ellipse([x - 16, y - 16, x + 16, y + 16], fill=(241, 178, 92, int(38 * a * e * ee)))
            d.ellipse([x - rr2, y - rr2, x + rr2, y + rr2], fill=(HI[0], HI[1], HI[2], int(255 * a * e * ee)))
        else:
            rr3 = 3.0 * ee
            d.ellipse([x - rr3, y - rr3, x + rr3, y + rr3], fill=(143, 154, 165, int(110 * a * e * ee)))
    sx = 1180
    cards = [
        (str(k['exploited_n']), '個已遭利用', 'KEV 命中'),
        (str(k['cvss_median']) + ' → ' + str(k['eng_median']), '名次中位數', 'CVSS → 本系統'),
        ('前 ' + str(k['eng_max']) + ' 名', '全部提前', '94 個都進前段'),
    ]
    for i, (big, sub, note) in enumerate(cards):
        ec = eo((lt - 3.2 - i * 0.3) / 0.8)
        if ec <= 0:
            continue
        y = 380 + i * 130
        panel(d, [sx, y - 50, 1700, y + 62], r=12, fill=(19, 26, 32, 210), outline=None, alpha=a * ec)
        T(d, (sx + 24, y + 16), big, 46, HI if i < 2 else INK, a * ec, kind='mono')
        T(d, (sx + 24, y + 52), sub + ' · ' + note, 22, MUTE, a * ec)


# --------------------------------------------------------------------------- #
# S7 71.8–80.2s 回測與端點
# --------------------------------------------------------------------------- #
def s_eval(d, lt, a):
    ev = D['eval']
    e = eo((lt - 0.1) / 0.7)
    if e <= 0:
        return
    T(d, (160, 190), '回測：排序真的有效', 42, INK, a * e, kind='bold')
    tiles = [('本系統 AUC', '%.3f' % ev['auc'], HI), ('EPSS AUC', '%.3f' % ev['epss'], BLUE), ('純 CVSS AUC', '%.3f' % ev['cvss'], MUTE)]
    for i, (name, val, col) in enumerate(tiles):
        et = eo((lt - 0.4 - i * 0.3) / 0.8)
        if et <= 0:
            continue
        x = 160 + i * 420
        panel(d, [x, 280, x + 380, 480], r=14, fill=(19, 26, 32, 220), outline=LINE, alpha=a * et)
        T(d, (x + 28, 340), name, 24, MUTE, a * et)
        T(d, (x + 28, 430), val, 72, col, a * et, kind='mono')
    e2 = eo((lt - 1.8) / 0.9)
    if e2 > 0:
        panel(d, [160, 540, 1760, 700], r=14, fill=(19, 26, 32, 210), outline=None, alpha=a * e2)
        T(d, (200, 634), '分類 held-out ' + str(ev['acc']) + '%', 44, INK, a * e2, kind='bold')
        T(d, (700, 634), 'κ ' + ('%.3f' % ev['kappa']), 40, HI, a * e2, kind='mono')
        T(d, (960, 634), '（不引用 in-sample 91%）', 24, DIM, a * e2)
    e3 = eo((lt - 2.8) / 0.9)
    if e3 > 0:
        T(d, (200, 800), str(ev['endpoints']) + ' 個 REST 端點，全部有自動文件', 32, INK, a * e3)
        T(d, (200, 852), '/api/docs · FastAPI · SQLite · Chart.js', 24, MUTE, a * e3, kind='mono')


# --------------------------------------------------------------------------- #
# S8 79.8–90s 收尾
# --------------------------------------------------------------------------- #
def s_close(d, lt, a):
    e = eo((lt - 0.2) / 1.1)
    if e <= 0:
        return
    T(d, (W / 2, 440), 'CTI 資安風險決策支援平台', 74, INK, a * e, anchor='ms', kind='bold')
    T(d, (W / 2, 528), '把情資語料，變成做得到的處置順序', 34, HI, a * e * ss(0.6, 1.4, lt), anchor='ms')
    lw = 480 * e
    d.line([(W / 2 - lw, 580), (W / 2 + lw, 580)], fill=(LINE[0], LINE[1], LINE[2], int(210 * a * e)), width=2)
    T(d, (W / 2, 660), '788 篇語料 · 783 個事件 · 288 個 CVE · 94 個已遭利用', 24, MUTE, a * e, anchor='ms')
    T(d, (W / 2, 704), '示範資產 · 不含真實公司或個資', 22, DIM, a * e, anchor='ms')


SEGS = [
    (s_title, 0.0, 11.0),
    (s_kpi, 10.6, 18.6),
    (s_table, 18.2, 34.2),
    (s_priority, 33.8, 41.6),
    (s_assess, 41.2, 57.2),
    (s_scatter, 56.8, 72.2),
    (s_eval, 71.8, 80.2),
    (s_close, 79.8, 90.0),
]

SUBS = [
    (0.6, 4.4, 'CTI 資安風險決策支援平台', '90 秒實機操作示範'),
    (4.6, 10.8, '每天數百則新聞，團隊只有 1–3 人', '問題是：先修哪一個？'),
    (11.2, 18.4, '788 篇中英文情資、783 件事件', '台灣 164、國際 624、橫跨 35 個月'),
    (18.6, 26.0, '修補清單：288 個 CVE', '對照 KEV、EPSS、CVSS、CWE'),
    (26.2, 33.8, '本地通報 69 個、遠端執行 32 個', '匯出 CSV，直接變成工單'),
    (34.0, 41.4, 'P1 131（24 小時）／P2 134（7 天）', 'P3 23（30 天）；其中 94 個已遭利用'),
    (41.6, 50.2, '即時評估：CVSS 9.8、對外、已勾 EDR', '結果 99.0 分、P1；換情境 78.6 分、P2'),
    (50.4, 57.0, '改內網＋WAF／隔離／備份 → 64.6 分 P3', '權重固定 50／30／12／8，可拆解'),
    (57.2, 64.6, '已遭利用的 94 個 CVE', '名次中位數從 149 前移到 50'),
    (64.8, 71.8, '全部落在前 131 名', '回測 AUC 0.853，純 CVSS 0.561'),
    (72.0, 79.8, '分類 held-out 73%、κ 0.818', '8 個 REST 端點，數字都能重跑'),
    (80.0, 89.4, '所有數字都能在論文與 API 重跑驗證', 'CTI 資安風險決策支援平台'),
]


def render(t, bg):
    img = bg.copy()
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, 'RGBA')
    for fn, a0, b0 in SEGS:
        if t < a0 - 0.05 or t > b0 + 0.05:
            continue
        alpha = ss(a0, a0 + 0.6, t) * (1 - ss(b0 - 0.6, b0, t))
        if alpha <= 0.002:
            continue
        fn(d, t - a0, alpha)
    # 字幕
    for s0, e0, l1, l2 in SUBS:
        if t < s0 - 0.2 or t > e0 + 0.2:
            continue
        al = ss(s0, s0 + 0.3, t) * (1 - ss(e0 - 0.3, e0, t))
        if al <= 0.01:
            continue
        wmax = max(tw(d, l1, 32), tw(d, l2, 32))
        bx = W / 2 - wmax / 2 - 40
        d.rounded_rectangle([bx, 918, W / 2 + wmax / 2 + 40, 1042], radius=10,
                            fill=(7, 8, 12, int(150 * al)))
        T(d, (W / 2, 972), l1, 32, WHITE, al, anchor='ms')
        T(d, (W / 2, 1016), l2, 32, (212, 220, 227), al, anchor='ms')
    # 進度條 + 頁腳
    d.rectangle([0, H - 6, W * clamp(t / DUR), H], fill=(241, 178, 92, 230))
    T(d, (W - 40, H - 22), '資料：/api/v1/patch-priority · docs/evaluation.md（2026-11-24）', 16, (74, 84, 94), 0.9, anchor='rs', kind='mono')
    img.alpha_composite(layer)
    return img.convert('RGB')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--times', default='')
    ap.add_argument('--fps', type=int, default=FPS)
    ap.add_argument('--start', type=int, default=0)
    ap.add_argument('--end', type=int, default=-1)
    ap.add_argument('--quality', type=int, default=90)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    global BG_IMG
    BG_IMG = make_bg()
    if args.all:
        total = int(DUR * args.fps)
        stop = total if args.end < 0 else min(args.end, total)
        for i in range(args.start, stop):
            t = i / args.fps
            img = render(t, BG_IMG)
            img.save(os.path.join(args.out, '%04d.jpg' % i), quality=args.quality, subsampling=1)
            if i % 150 == 0:
                print('frame', i, '/', total, flush=True)
        print('done', total, flush=True)
    else:
        for s in args.times.split(','):
            t = float(s)
            img = render(t, BG_IMG)
            img.save(os.path.join(args.out, 't%05.1f.png' % t))
            print('rendered t=', t, flush=True)


if __name__ == '__main__':
    main()
