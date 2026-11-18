/**
 * Render four "tech style" design directions for the CTI dashboard.
 *
 * Each variant is a token set (colour, radius, shadow, type, motion) applied to
 * the same mock layout, so the differences you see are the spec differences and
 * not a different composition. Output: docs/design/variant-{a,b,c,d}.png
 */
import puppeteer from 'puppeteer-core';
import { writeFileSync } from 'node:fs';

const VARIANTS = [
  {
    id: 'a', name: 'A · Terminal / Data-Ops', label: '最小終端機',
    bg: '#05070c', surface: '#0a0f17', surface2: '#0d1420', line: '#1b2534',
    text: '#d7e2f0', muted: '#6b7c93', faint: '#3d4b5f',
    accent: '#22d3ee', accent2: '#34d399', warn: '#fbbf24', danger: '#fb7185',
    radius: '2px', radiusCard: '3px', shadow: 'none', glow: 'none',
    font: "'Segoe UI','Microsoft JhengHei',sans-serif", mono: "'Cascadia Code','Consolas',monospace",
    density: 'compact', motion: '0ms', texture: 'grid',
    borders: '1px solid #1b2534',
  },
  {
    id: 'b', name: 'B · Holographic / Neon', label: '全像霓虹',
    bg: '#070a18', surface: '#0c1226', surface2: '#111a33', line: '#25325c',
    text: '#e6ecff', muted: '#8b9ac4', faint: '#4d5b85',
    accent: '#7c5cff', accent2: '#22d3ee', warn: '#fbbf24', danger: '#fb7185',
    radius: '12px', radiusCard: '16px', shadow: '0 12px 40px rgba(124,92,255,.22)', glow: '0 0 24px rgba(34,211,238,.35)',
    font: "'Segoe UI Variable','Segoe UI','Microsoft JhengHei',sans-serif", mono: "'JetBrains Mono','Consolas',monospace",
    density: 'comfortable', motion: '180ms', texture: 'noise',
    borders: '1px solid rgba(124,92,255,.35)',
  },
  {
    id: 'c', name: 'C · Swiss Enterprise', label: '瑞士企業白',
    bg: '#f5f7fb', surface: '#ffffff', surface2: '#eef2f8', line: '#dfe6f0',
    text: '#0f172a', muted: '#5a6b85', faint: '#94a3b8',
    accent: '#4f46e5', accent2: '#0ea5e9', warn: '#d97706', danger: '#e11d48',
    radius: '8px', radiusCard: '12px', shadow: '0 1px 2px rgba(15,23,42,.06), 0 8px 24px rgba(15,23,42,.06)', glow: 'none',
    font: "'Segoe UI','Microsoft JhengHei',sans-serif", mono: "'Consolas','Courier New',monospace",
    density: 'airy', motion: '150ms', texture: 'none',
    borders: '1px solid #dfe6f0',
  },
  {
    id: 'd', name: 'D · Control Room', label: '控制室',
    bg: '#0b1220', surface: '#111a2b', surface2: '#16223a', line: '#22304a',
    text: '#dbe6f5', muted: '#7d8fae', faint: '#4b5c7a',
    accent: '#f59e0b', accent2: '#2dd4bf', warn: '#fbbf24', danger: '#f87171',
    radius: '4px', radiusCard: '6px', shadow: 'inset 0 1px 0 rgba(255,255,255,.04), 0 2px 8px rgba(0,0,0,.35)', glow: 'none',
    font: "'Segoe UI','Microsoft JhengHei',sans-serif", mono: "'Cascadia Code','Consolas',monospace",
    density: 'compact', motion: '120ms', texture: 'grid',
    borders: '1px solid #22304a',
  },
];

const DENSITY = {
  compact:   { pad: 14, gap: 10, row: 34, kpi: 20 },
  comfortable: { pad: 20, gap: 16, row: 42, kpi: 24 },
  airy:      { pad: 24, gap: 20, row: 46, kpi: 26 },
};

function html(v) {
  const d = DENSITY[v.density];
  const isLight = v.id === 'c';
  const texture = v.texture === 'grid'
    ? 'background-image:linear-gradient(' + (isLight ? 'rgba(15,23,42,.045)' : 'rgba(120,160,220,.06)') + ' 1px,transparent 1px),linear-gradient(90deg,' + (isLight ? 'rgba(15,23,42,.045)' : 'rgba(120,160,220,.06)') + ' 1px,transparent 1px);background-size:48px 48px;'
    : v.texture === 'noise'
      ? 'background-image:radial-gradient(rgba(255,255,255,.06) 1px,transparent 1px);background-size:3px 3px;'
      : '';

  const rows = [
    ['CVE-2024-3400', 'PAN-OS 指令注入', 100, 10.0, 'P1', 'KEV'],
    ['CVE-2023-4966', 'Citrix Bleed', 100, 9.4, 'P1', 'KEV'],
    ['CVE-2026-109618', 'SonicWall 後門', 82, 10.0, 'P1', 'KEV'],
    ['CVE-2025-0282', 'Ivanti 認證繞過', 47, 9.0, 'P2', '—'],
  ];

  return '<!doctype html><html><head><meta charset="utf-8"><style>'
    + '*{box-sizing:border-box;margin:0;padding:0}'
    + 'body{width:1200px;height:800px;background:' + v.bg + ';color:' + v.text + ';font-family:' + v.font + ';' + texture + ';overflow:hidden}'
    + '.wrap{padding:28px 32px}'
    + '.top{display:flex;align-items:center;justify-content:space-between;margin-bottom:' + (d.gap + 6) + 'px}'
    + '.brand{display:flex;align-items:center;gap:10px}'
    + '.mark{width:30px;height:30px;border-radius:' + v.radius + ';background:linear-gradient(135deg,' + v.accent + ',' + v.accent2 + ');box-shadow:' + v.glow + '}'
    + '.brand h1{font-size:15px;font-weight:700;letter-spacing:-.01em}'
    + '.brand p{font-family:' + v.mono + ';font-size:10px;color:' + v.muted + ';letter-spacing:.08em;text-transform:uppercase}'
    + '.nav{display:flex;gap:4px}'
    + '.nav span{font-size:12px;padding:6px 12px;border-radius:' + v.radius + ';color:' + v.muted + '}'
    + '.nav span.on{background:' + v.surface2 + ';color:' + v.text + ';border:' + v.borders + '}'
    + '.status{font-family:' + v.mono + ';font-size:11px;color:' + v.accent2 + ';display:flex;align-items:center;gap:6px}'
    + '.dot{width:6px;height:6px;border-radius:50%;background:' + v.accent2 + ';box-shadow:' + v.glow + '}'
    + '.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:' + d.gap + 'px;margin-bottom:' + (d.gap + 6) + 'px}'
    + '.kpi{background:' + v.surface + ';border:' + v.borders + ';border-radius:' + v.radiusCard + ';padding:' + d.pad + 'px;box-shadow:' + v.shadow + '}'
    + '.kpi b{display:block;font-family:' + v.mono + ';font-size:' + (d.kpi + 8) + 'px;font-weight:700;letter-spacing:-.02em;margin-top:6px}'
    + '.kpi small{font-family:' + v.mono + ';font-size:9.5px;letter-spacing:.1em;text-transform:uppercase;color:' + v.faint + '}'
    + '.kpi .sub{font-size:11px;color:' + v.muted + ';margin-top:4px}'
    + '.panel{background:' + v.surface + ';border:' + v.borders + ';border-radius:' + v.radiusCard + ';box-shadow:' + v.shadow + ';overflow:hidden}'
    + '.head{display:flex;align-items:center;justify-content:space-between;padding:' + (d.pad - 2) + 'px ' + (d.pad + 2) + 'px;border-bottom:' + v.borders + '}'
    + '.head h2{font-size:13.5px;font-weight:700}'
    + '.head p{font-family:' + v.mono + ';font-size:9.5px;color:' + v.faint + ';letter-spacing:.1em;text-transform:uppercase;margin-top:2px}'
    + 'table{width:100%;border-collapse:collapse;font-size:12.5px}'
    + 'th{font-family:' + v.mono + ';font-size:9.5px;letter-spacing:.1em;text-transform:uppercase;color:' + v.faint + ';text-align:left;padding:8px ' + (d.pad + 2) + 'px;border-bottom:' + v.borders + '}'
    + 'td{padding:' + (d.row / 2 - 4) + 'px ' + (d.pad + 2) + 'px;border-bottom:1px solid ' + v.line + ';vertical-align:middle}'
    + 'tr:last-child td{border-bottom:none}'
    + '.cve{font-family:' + v.mono + ';font-size:12px;color:' + v.accent + '}'
    + '.bar{width:120px;height:5px;border-radius:3px;background:' + v.surface2 + ';overflow:hidden}'
    + '.bar i{display:block;height:100%;background:linear-gradient(90deg,' + v.accent2 + ',' + v.accent + ')}'
    + '.num{font-family:' + v.mono + ';font-size:12px}'
    + '.badge{display:inline-block;font-family:' + v.mono + ';font-size:10px;font-weight:700;padding:3px 8px;border-radius:' + (v.id === 'b' ? '999px' : v.radius) + ';border:1px solid ' + v.danger + '55;color:' + v.danger + ';background:' + v.danger + '18}'
    + '.badge.p2{border-color:' + v.warn + '55;color:' + v.warn + ';background:' + v.warn + '18}'
    + '.tag{font-family:' + v.mono + ';font-size:10px;color:' + v.muted + ';border:1px solid ' + v.line + ';padding:2px 6px;border-radius:' + v.radius + '}'
    + '.foot{display:flex;align-items:center;justify-content:space-between;margin-top:' + (d.gap + 6) + 'px}'
    + '.btns{display:flex;gap:8px}'
    + '.btn{font-size:12px;padding:8px 14px;border-radius:' + v.radius + ';border:' + v.borders + ';color:' + v.text + ';background:' + v.surface2 + '}'
    + '.btn.primary{background:linear-gradient(135deg,' + v.accent + ',' + v.accent2 + ');color:' + (isLight ? '#fff' : '#04121a') + ';border:none;font-weight:700;box-shadow:' + (v.id === 'b' ? v.glow : 'none') + '}'
    + '.note{font-family:' + v.mono + ';font-size:10px;color:' + v.faint + '}'
    + '</style></head><body><div class="wrap">'
    + '<div class="top"><div class="brand"><div class="mark"></div><div><h1>CTI 資安風險決策平台</h1><p>' + v.name + '</p></div></div>'
    + '<div class="nav"><span class="on">總覽</span><span>修補清單</span><span>即時評估</span><span>情資流</span></div>'
    + '<div class="status"><span class="dot"></span>API 已連線</div></div>'
    + '<div class="kpis">'
    + '<div class="kpi"><small>Corpus</small><b>788</b><div class="sub">台灣 164 · 國際 624</div></div>'
    + '<div class="kpi"><small>P1 立即處置</small><b>' + '131' + '</b><div class="sub">24 小時內</div></div>'
    + '<div class="kpi"><small>KEV 覆蓋</small><b>11%</b><div class="sub">80 / 711</div></div>'
    + '<div class="kpi"><small>平均風險</small><b>60.9</b><div class="sub">288 個 CVE</div></div></div>'
    + '<div class="panel"><div class="head"><div><h2>修補優先級</h2><p>Patch Priority · EPSS + KEV</p></div><span class="tag">曝光：開</span></div>'
    + '<table><thead><tr><th>CVE</th><th>情資</th><th>EPSS</th><th>CVSS</th><th>優先級</th><th>判斷依據</th></tr></thead><tbody>'
    + rows.map((r) => '<tr><td class="cve">' + r[0] + '</td><td>' + r[1] + '</td>'
        + '<td><div class="bar"><i style="width:' + r[2] + '%"></i></div></td>'
        + '<td class="num">' + r[3].toFixed(1) + '</td>'
        + '<td><span class="badge' + (r[4] === 'P2' ? ' p2' : '') + '">' + r[4] + '</span></td>'
        + '<td><span class="tag">' + r[5] + '</span></td></tr>').join('')
    + '</tbody></table></div>'
    + '<div class="foot"><div class="note">資料截止 2026-11-13 · build 20261118</div>'
    + '<div class="btns"><span class="btn">匯出 CSV</span><span class="btn primary">執行風險評估</span></div></div>'
    + '</div></body></html>';
}

const browser = await puppeteer.launch({
  executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  headless: true, args: ['--no-first-run', '--disable-gpu'],
});
try {
  for (const v of VARIANTS) {
    const file = 'C:/dev/cti-platform/docs/design/variant-' + v.id + '.html';
    writeFileSync(file, html(v), 'utf8');
    const page = await browser.newPage();
    await page.setViewport({ width: 1200, height: 800, deviceScaleFactor: 2 });
    await page.goto('file:///' + file.replace(/\\/g, '/'), { waitUntil: 'networkidle2' });
    await page.screenshot({ path: 'C:/dev/cti-platform/docs/design/variant-' + v.id + '.png' });
    await page.close();
    console.log('rendered', v.id, v.name);
  }
} finally {
  await browser.close();
}
