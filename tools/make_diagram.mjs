/**
 * Generate the architecture diagram (SVG + draw.io) from one definition.
 *
 * Run:  node tools/make_diagram.mjs
 * Then render the PNG with the existing screenshot helper if needed.
 *
 * The layout is a single vertical spine with short horizontal side arrows, so a
 * reader never has to follow an elbow across the canvas.
 */
import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const nodes = [
  { id: 'src', x: 380, y: 30, w: 430, h: 92, tone: 'source', title: '① 新聞來源',
    lines: ['The Hacker News（國際，每月約 250 篇）', 'TWCERT / CC（台灣政府，每月約 5 篇）', 'iThome（台灣媒體，深頁 403 限制）'] },
  { id: 'crawl', x: 380, y: 140, w: 430, h: 64, tone: 'process', title: '② 分層擷取',
    lines: ['每月固定 15 篇國際＋5 篇台灣，鋪滿 35 個月'] },
  { id: 'corpus', x: 380, y: 222, w: 430, h: 76, tone: 'process', title: '③ 語料庫（SQLite）',
    lines: ['788 篇文章 → 去重後 741 件事件', '抽出 288 個 CVE'] },
  { id: 'enrich', x: 380, y: 316, w: 430, h: 76, tone: 'process', title: '④ 情資對照',
    lines: ['CVE → EPSS／KEV／CVSS／CWE', '同時標記「本地通報」（台灣來源）'] },
  { id: 'score', x: 380, y: 410, w: 430, h: 80, tone: 'process', title: '⑤ 分類 ＋ 評分',
    lines: ['規則分類 4 類（每篇附命中規則）', '加權評分 50／30／12／8 → 0–100 分'] },
  { id: 'priority', x: 380, y: 508, w: 430, h: 92, tone: 'decision', title: '⑥ 修補優先級',
    lines: ['KEV → P1｜EPSS≥10% 或 CVSS≥9 → P2', '曝險升／降一級（KEV 不降）', 'P1 131｜P2 134｜P3 23＋SLA'] },
  { id: 'api', x: 380, y: 618, w: 430, h: 86, tone: 'api', title: '⑦ API ＋ 儀表板',
    lines: ['FastAPI /api/v1（8 個端點）', '4 分頁：總覽／修補／評估／情資'] },

  { id: 'snap', x: 870, y: 304, w: 300, h: 100, tone: 'snapshot', title: '外部官方快照',
    lines: ['EPSS 911（利用機率）', 'KEV 1,779（已遭利用）', 'CVSS 704｜CWE 287'] },
  { id: 'assets', x: 870, y: 514, w: 300, h: 80, tone: 'snapshot', title: '企業資產清單',
    lines: ['14 台示範資產', '判斷是否對外曝險'] },
  { id: 'gap', x: 30, y: 316, w: 300, h: 76, tone: 'decision', title: '覆蓋缺口',
    lines: ['KEV 窗內 711 筆', '語料只涵蓋 80 筆（11%）'] },
  { id: 'assess', x: 30, y: 412, w: 300, h: 76, tone: 'decision', title: '即時評估',
    lines: ['輸入資產情境 → 分數、劇本', 'what-if：怎麼降級'] },
];

const edges = [
  ['src', 'crawl'], ['crawl', 'corpus'], ['corpus', 'enrich'],
  ['enrich', 'score'], ['score', 'priority'], ['priority', 'api'],
  ['snap', 'enrich'], ['assets', 'priority'],
  ['enrich', 'gap'], ['score', 'assess'],
];

const PALETTE = {
  source:   { fill: '#0b2a5b', stroke: '#3b82f6', title: '#dbeafe' },
  snapshot: { fill: '#0b3b36', stroke: '#14b8a6', title: '#ccfbf1' },
  process:  { fill: '#0d3320', stroke: '#22c55e', title: '#dcfce7' },
  decision: { fill: '#3b1d0b', stroke: '#f97316', title: '#ffedd5' },
  api:      { fill: '#2a1252', stroke: '#a855f7', title: '#f3e8ff' },
};

const W = 1200;
const H = 740;
const pos = Object.fromEntries(nodes.map((n) => [n.id, n]));
const cy = (n) => n.y + n.h / 2;

function pathFor(a, b) {
  const A = pos[a];
  const B = pos[b];
  if (Math.abs(A.x - B.x) < 4) {
    const x = A.x + A.w / 2;
    return 'M ' + x + ' ' + (A.y + A.h) + ' L ' + x + ' ' + B.y;
  }
  const y = cy(A);
  return A.x > B.x
    ? 'M ' + A.x + ' ' + y + ' L ' + (B.x + B.w) + ' ' + y
    : 'M ' + (A.x + A.w) + ' ' + y + ' L ' + B.x + ' ' + y;
}

const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

function buildSvg() {
  const out = [];
  out.push('<svg xmlns="http://www.w3.org/2000/svg" width="' + W + '" height="' + H + '" viewBox="0 0 ' + W + ' ' + H + '" font-family="\'Segoe UI\',\'Microsoft JhengHei\',sans-serif">');
  out.push('<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#94a3b8"/></marker>');
  out.push('<pattern id="dots" width="26" height="26" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="#1b2739"/></pattern></defs>');
  out.push('<rect width="100%" height="100%" fill="#060b12"/>');
  out.push('<rect width="100%" height="100%" fill="url(#dots)" opacity="0.55"/>');
  out.push('<text x="30" y="24" fill="#7e8da4" font-size="12" letter-spacing="1.5">CTI 資安風險決策支援平台 · 資料流（左＝產出／右＝輸入）</text>');
  for (const [a, b] of edges) {
    out.push('<path d="' + pathFor(a, b) + '" fill="none" stroke="#5b6b82" stroke-width="1.8" marker-end="url(#arrow)"/>');
  }
  for (const n of nodes) {
    const p = PALETTE[n.tone];
    out.push('<rect x="' + n.x + '" y="' + n.y + '" width="' + n.w + '" height="' + n.h + '" rx="12" fill="' + p.fill + '" stroke="' + p.stroke + '" stroke-width="1.5"/>');
    out.push('<text x="' + (n.x + 16) + '" y="' + (n.y + 26) + '" fill="' + p.title + '" font-size="14" font-weight="700">' + esc(n.title) + '</text>');
    n.lines.forEach((line, i) => {
      out.push('<text x="' + (n.x + 16) + '" y="' + (n.y + 48 + i * 16) + '" fill="#c3d0e0" font-size="11.5">' + esc(line) + '</text>');
    });
  }
  out.push('</svg>');
  return out.join('\n') + '\n';
}

function buildDrawio() {
  const cells = [];
  nodes.forEach((n, i) => {
    const p = PALETTE[n.tone];
    const body = '<b>' + esc(n.title) + '</b><br>' + n.lines.map(esc).join('<br>');
    cells.push('<mxCell id="n' + i + '" value="' + esc(body) + '" style="rounded=1;whiteSpace=wrap;html=1;fillColor=' + p.fill + ';strokeColor=' + p.stroke + ';fontColor=#c3d0e0;fontSize=11;align=left;spacingLeft=10;verticalAlign=top;spacingTop=8;arcSize=12;" vertex="1" parent="1"><mxGeometry x="' + n.x + '" y="' + n.y + '" width="' + n.w + '" height="' + n.h + '" as="geometry"/></mxCell>');
  });
  edges.forEach(([a, b], i) => {
    const ai = nodes.findIndex((n) => n.id === a);
    const bi = nodes.findIndex((n) => n.id === b);
    cells.push('<mxCell id="e' + i + '" style="edgeStyle=none;html=1;strokeColor=#5b6b82;endArrow=block;endFill=1;" edge="1" parent="1" source="n' + ai + '" target="n' + bi + '"><mxGeometry relative="1" as="geometry"/></mxCell>');
  });
  return '<mxfile host="app.diagrams.net"><diagram name="CTI 資料流"><mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="' + W + '" pageHeight="' + H + '" math="0" shadow="0"><root><mxCell id="0"/><mxCell id="1" parent="0"/>\n' + cells.join('\n') + '\n</root></mxGraphModel></diagram></mxfile>\n';
}

const base = fileURLToPath(new URL('../docs/', import.meta.url));
writeFileSync(base + 'architecture.svg', buildSvg(), 'utf8');
writeFileSync(base + 'architecture.drawio', buildDrawio(), 'utf8');
console.log('svg + drawio written to ' + base);
