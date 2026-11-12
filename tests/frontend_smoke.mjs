/**
 * Headless DOM smoke test for the dashboard bundle.
 *
 * jsdom cannot paint, so this does not test visuals. It does execute the real
 * charts.js + app.js against the live API and asserts the render pipeline:
 * KPI text, legend, matrix lanes, feed rows, filtering, and the assessment flow.
 */

import { readFile } from 'node:fs/promises';
import { fileURLToPath, pathToFileURL } from 'node:url';

// jsdom is a dev-only dependency:  pnpm add -D jsdom  (or npm i -D jsdom)
// JSDOM_MODULE can point at an explicit path/URL when jsdom lives elsewhere.
const jsdomSpecifier = process.env.JSDOM_MODULE || 'jsdom';
const jsdomModule = await import(
  jsdomSpecifier.startsWith('.') || jsdomSpecifier.includes(':')
    ? pathToFileURL(jsdomSpecifier).href
    : jsdomSpecifier
);
const { JSDOM, VirtualConsole } = jsdomModule;

const virtualConsole = new VirtualConsole();
virtualConsole.on('jsdomError', (error) => console.log('jsdomError:', error.message, error.stack?.split('\n')[1] ?? ''));
virtualConsole.on('error', (...args) => console.log('console.error:', ...args));

const BASE = process.env.CTI_BASE_URL || 'http://127.0.0.1:8123';
const STATIC = process.env.CTI_STATIC_DIR
  || fileURLToPath(new URL('../static', import.meta.url));

const errors = [];

function assert(condition, message) {
  if (!condition) {
    errors.push(message);
    console.log(`FAIL  ${message}`);
  } else {
    console.log(`ok    ${message}`);
  }
}

function makeChartStub(win) {
  class Chart {
    constructor(ctx, config) {
      this.ctx = ctx;
      this.config = config;
      this.data = config.data;
      this.canvas = ctx?.canvas ?? ctx;
      this.options = config.options ?? {};
      (Chart.instances ||= []).push(this);
    }
    update() { this.updated = true; }
    destroy() { this.destroyed = true; }
    isDatasetVisible() { return true; }
    setDatasetVisibility() {}
  }
  Chart.defaults = {
    font: {},
    plugins: { tooltip: {}, legend: {} },
    animation: {},
    color: '',
  };
  win.Chart = Chart;
  return Chart;
}

const html = await readFile(`${STATIC}/index.html`, 'utf8');
const chartsSrc = await readFile(`${STATIC}/js/charts.js`, 'utf8');
const appSrc = await readFile(`${STATIC}/js/app.js`, 'utf8');

// Remove CDN <script src> tags and the Tailwind config snippet: jsdom must not
// hit the network, and `tailwind` is not defined outside the browser CDN.
const stripped = html
  .replace(/<script[^>]*src="https?:\/\/[^"]*"[^>]*><\/script>/g, '')
  .replace(/<script>\s*tailwind\.config[\s\S]*?<\/script>/, '');

const dom = new JSDOM(stripped, {
  url: `${BASE}/`,
  runScripts: 'outside-only',
  pretendToBeVisual: true,
  virtualConsole,
});
const { window } = dom;

window.fetch = (input, init = {}) => {
  const url = typeof input === 'string' ? input : input.url;
  const resolved = new URL(url, BASE).href;
  if (resolved.includes('/threats')) console.log('FETCH', resolved);
  // jsdom's AbortSignal is a different implementation than Node's fetch expects.
  const { signal, ...rest } = init;
  return globalThis.fetch(resolved, rest);
};
window.HTMLCanvasElement.prototype.getContext = function getContext() {
  return {
    canvas: this,
    createLinearGradient: () => ({ addColorStop() {} }),
    createRadialGradient: () => ({ addColorStop() {} }),
    measureText: () => ({ width: 0 }),
    save() {}, restore() {}, beginPath() {}, closePath() {}, fill() {}, stroke() {}, fillRect() {},
    clearRect() {}, moveTo() {}, lineTo() {}, arc() {}, setLineDash() {},
    translate() {}, rotate() {}, scale() {},
  };
};
window.Element.prototype.scrollIntoView = () => {};
window.matchMedia = () => ({ matches: false, addEventListener() {}, removeEventListener() {} });
makeChartStub(window);

window.addEventListener('error', (event) => errors.push(`window error: ${event.message}`));
process.on('uncaughtException', (error) => errors.push(`uncaught: ${error.message}`));

// Indirect eval gives `const` its own lexical scope, unlike a real <script>, so
// re-export the namespace onto window before loading the controller.
window.eval(`${chartsSrc}\n;window.CTICharts = CTICharts;`);
window.eval(appSrc);

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
await wait(900);

const $ = (selector) => window.document.querySelector(selector);
const $$ = (selector) => Array.from(window.document.querySelectorAll(selector));

// ---------------------------------------------------------------- render checks
assert($('#kpiTotal').textContent.trim() === '100', `KPI total rendered (got "${$('#kpiTotal').textContent}")`);
assert($('#kpiTw').textContent.trim() === '50', 'KPI Taiwan count rendered');
assert($('#kpiGlobal').textContent.trim() === '50', 'KPI global count rendered');
assert($('#kpiP1').textContent.trim().length > 0 && $('#kpiP1').textContent.trim() !== '—', 'KPI P1 rendered');
assert($('#kpiTopMeta').textContent.trim() !== '—', 'KPI top meta-category rendered');
assert($('#kpiAvgScore').textContent.trim() !== '—', 'KPI average score rendered');

assert($$('#metaLegend .legend-row').length === 4, `meta legend rows (got ${$$('#metaLegend .legend-row').length})`);
assert($$('#categoryStrip .tally').length === 6, `cluster tallies (got ${$$('#categoryStrip .tally').length})`);
assert(
  $$('#categoryStrip .tally')
    .map((node) => node.textContent.replace(/\s+/g, ' ').trim())
    .join('|')
    .includes('C0'),
  'cluster tallies expose the raw cluster ids'
);
assert($('#pieCenterTotal').textContent.trim() === '100', 'pie centre total rendered');

assert($$('#matrixGrid .matrix-card').length === 3, `matrix lanes (got ${$$('#matrixGrid .matrix-card').length})`);
assert($$('#matrixGrid .step').length > 0, 'matrix playbooks rendered');

assert($$('#feedBody .feed-row').length === 25, `feed first page rows (got ${$$('#feedBody .feed-row').length})`);
assert($('#feedTotal').textContent.trim() === '100', 'feed total rendered');
assert($('#pageLabel').textContent.includes('1 / 4'), `pagination label (got "${$('#pageLabel').textContent}")`);

assert($$('#insightGrid article').length === 4, `insight cards (got ${$$('#insightGrid article').length})`);
assert(window.Chart.instances?.length === 4, `chart instances (got ${window.Chart.instances?.length})`);
assert($('#apiStatus').textContent.includes('已連線'), 'API status pill updated');

// --------------------------------------------- comparison chart: alignment + legend
{
  const statsNow = await globalThis.fetch(`${BASE}/api/v1/stats`).then((response) => response.json());
  const metaByKey = Object.fromEntries(statsNow.meta_categories.map((item) => [item.key, item]));
  const AXIS = { VULN: '漏洞與修補', MALWARE: '惡意與攻擊', RESEARCH: '研究與治理' };
  const bar = window.Chart.instances.find(
    (chart) => chart.config.type === 'bar' && chart.data.datasets.length === 2
  );

  assert(!!bar, 'comparison chart exists');
  assert(
    bar.data.labels.length === 3 && bar.data.datasets[0].data.length === 3,
    `comparison has three categories (got ${bar.data.labels.length})`
  );
  assert(
    Object.keys(AXIS).every(
      (key, index) =>
        bar.data.labels[index] === AXIS[key] &&
        bar.data.datasets[0].data[index] === (metaByKey[key]?.by_region?.taiwan ?? 0) &&
        bar.data.datasets[1].data[index] === (metaByKey[key]?.by_region?.global ?? 0)
    ),
    `comparison series align to category by key (labels=${bar.data.labels.join('|')}, tw=${bar.data.datasets[0].data.join('|')}, gl=${bar.data.datasets[1].data.join('|')})`
  );

  const legend = bar.options.plugins.legend;
  assert(legend.display === true, 'comparison legend is enabled');
  assert(
    String(legend.labels.color).toUpperCase() === '#FFFFFF',
    `legend label colour is white (got ${legend.labels.color})`
  );
  assert(legend.position === 'top', `legend position (got ${legend.position})`);

  const series = { tw: bar.data.datasets[0].data, gl: bar.data.datasets[1].data };
  // Expected values come from the API, so the assertion checks the wiring
  // rather than freezing today's classification numbers into the test.
  const expectTw = Object.keys(AXIS).map((key) => metaByKey[key]?.by_region?.taiwan ?? 0);
  const expectGl = Object.keys(AXIS).map((key) => metaByKey[key]?.by_region?.global ?? 0);
  assert(series.tw.join(',') === expectTw.join(','), `Taiwan series matches API (got ${series.tw.join(',')}, expected ${expectTw.join(',')})`);
  assert(series.gl.join(',') === expectGl.join(','), `Global series matches API (got ${series.gl.join(',')}, expected ${expectGl.join(',')})`);
  assert($('#baselineNote').textContent.includes('with_dates.csv'), 'dataset provenance is displayed');

  const items = legend.labels.generateLabels(bar);
  assert(items.length === 2, `legend entries (got ${items.length})`);
  assert(items[0].fontColor === '#2dd4bf', `Taiwan legend text colour (got ${items[0].fontColor})`);
  assert(items[1].fontColor === '#60a5fa', `Global legend text colour (got ${items[1].fontColor})`);
  assert(
    bar.options.scales.x.ticks.color === '#8b9ab2',
    `x tick colour is the muted axis tone (got ${bar.options.scales.x.ticks.color})`
  );
  assert(
    bar.options.scales.y.ticks.color === '#8b9ab2',
    `y tick colour is the muted axis tone (got ${bar.options.scales.y.ticks.color})`
  );

  assert(
    items[0].text.includes('台灣 (TWCERT + iThome)'),
    `legend names the Taiwan source (got "${items[0].text}")`
  );
  assert(
    items[1].text.includes('國際 (The Hacker News)'),
    `legend names the global source (got "${items[1].text}")`
  );
  assert(/·\s*\d+\s*篇/.test(items[0].text), `legend shows totals (got "${items[0].text}")`);

  // The panel subtitle is derived from the loaded rows, so it can never drift
  // from the CSV snapshot the way the old hard-coded window did.
  const first = statsNow.timeline[0].date;
  const last = statsNow.timeline[statsNow.timeline.length - 1].date;
  assert(
    $('#timelineRange').textContent.trim().startsWith(`${first} → ${last}`),
    `timeline subtitle follows the data (got "${$('#timelineRange').textContent}")`
  );
}

// ----------------------------------------------------------- doughnut readout
{
  const pie = window.Chart.instances.find((chart) => chart.config.type === 'doughnut');
  assert(!!pie, 'doughnut chart exists');
  assert($('#pieCenterTotal').textContent.trim() === '100', 'pie centre rests on the corpus total');

  pie.options.onHover({}, [{ index: 0 }]);
  assert(
    /^\d+(\.\d+)?%$/.test($('#pieCenterTotal').textContent.trim()),
    `hovering a slice shows its share (got "${$('#pieCenterTotal').textContent}")`
  );
  assert($('#pieCenterCaption').textContent.trim() === 'VULN', 'hovering a slice names the category');

  pie.canvas.dispatchEvent(new window.MouseEvent('mouseleave'));
  assert($('#pieCenterTotal').textContent.trim() === '100', 'leaving the doughnut restores the total');
  assert($('#pieCenterCaption').textContent.trim() === 'articles', 'leaving the doughnut restores the caption');
}

// ------------------------------------------------------------ interaction: chips
const p1Chip = $('[data-priority="P1"].chip');
p1Chip.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
await wait(600);
assert($$('#feedBody .feed-row').length > 0, 'P1 filter returned rows');
assert($('#feedTotal').textContent.trim() !== '100', 'P1 filter narrowed the total');
assert(p1Chip.getAttribute('aria-pressed') === 'true', 'P1 chip pressed state');

// -------------------------------------------------------- interaction: row expand
const firstRow = $('#feedBody .feed-row');
firstRow.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
await wait(120);
assert($$('#feedBody .feed-detail-row').length === 1, 'row expansion renders detail');
assert($$('#feedBody .feed-detail-row .step').length > 0, 'row detail shows playbook');

// ---------------------------------------------------------- interaction: matrix
const p2Card = $('.matrix-card[data-priority="P2"] .matrix-toggle');
p2Card.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
await wait(80);
assert(p2Card.getAttribute('aria-expanded') === 'true', 'matrix accordion expands');

// ---------------------------------------------------- feed: dates + outbound links
{
  const row = $('#feedBody .feed-row');
  const link = row?.querySelector('a.feed-link');
  assert(!!link, 'feed title is a link to the source article');
  assert(link.href.startsWith('https://'), `feed link points to the publisher (got ${link?.href})`);
  assert(/\d{4}-\d{2}-\d{2}/.test(row.textContent), 'feed row shows the publication date');
}

// ------------------------------------------------------- assessment flow (live API)
const form = $('#assessForm');
$('#assetType').value = 'core_datacenter';
$('#threatSource').value = 'ransomware';
$('#category').value = 'MALWARE';
$('#exposure').value = 'public';
$('#exploitStatus').value = 'active';
$('#cvssEnabled').checked = true;
$('#cvss').value = '9.8';
$('#cveId').value = 'CVE-2026-111497';
form.dispatchEvent(new window.Event('submit', { bubbles: true, cancelable: true }));
await wait(900);

assert(!$('#assessResult').classList.contains('hidden'), 'assessment result panel revealed');
assert($('#scoreValue').textContent.trim().length > 0 && $('#scoreValue').textContent.trim() !== '0', 'score ring updated');
assert($('#priorityBadge').textContent.trim() === 'P1', `assessment priority (got "${$('#priorityBadge').textContent}")`);
assert($$('#factorList .factor').length === 5, `factor rows (got ${$$('#factorList .factor').length})`);
assert($$('#resultPlan .step').length >= 3, 'assessment playbook rendered');

// --------------------------------------------------------------- invalid CVE path
$('#cveId').value = 'CVE-26-1';
$('#cveId').dispatchEvent(new window.Event('input', { bubbles: true }));
await wait(50);
assert(!$('#cveError').classList.contains('hidden'), 'invalid CVE shows inline error');
assert($('#cveId').getAttribute('aria-invalid') === 'true', 'invalid CVE marks aria-invalid');

// ------------------------------------------------------------------------- report
await wait(200);
if (errors.length) {
  console.log(`\n${errors.length} failure(s):`);
  errors.forEach((error) => console.log(` - ${error}`));
  process.exit(1);
}
console.log('\nAll dashboard smoke checks passed.');



