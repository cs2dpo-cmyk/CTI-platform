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

assert($$('#metaLegend .legend-row').length === 3, `meta legend rows (got ${$$('#metaLegend .legend-row').length})`);
assert($$('#categoryStrip .tally').length === 4, `category tallies (got ${$$('#categoryStrip .tally').length})`);
assert(
  $$('#categoryStrip .tally').map((node) => node.textContent.trim().split(/\s+/)[0]).join(',') === '漏洞修補,惡意攻擊,供應鏈,研究治理',
  'category tallies carry the 4-way breakdown'
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

// ------------------------------------------------------- assessment flow (live API)
const form = $('#assessForm');
$('#assetType').value = 'core_datacenter';
$('#threatSource').value = 'ransomware';
$('#category').value = 'Malware';
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

