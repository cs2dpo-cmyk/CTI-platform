#!/usr/bin/env node
/**
 * Screenshot the CTI dashboard with the browser that is already installed.
 *
 *   node tools/shot.mjs                                  # 1440x900 → .tmp/shot-1440.png
 *   node tools/shot.mjs http://127.0.0.1:8123 390 844     # 手機寬度
 *   node tools/shot.mjs --url <url> --width 768 --height 900 --out shots/tablet.png
 *
 * puppeteer-core drives Edge/Chrome already on the machine, so nothing downloads
 * a second browser. It also reports document.scrollWidth vs clientWidth, which
 * turns "does it overflow?" into a number instead of an opinion.
 */
import { existsSync } from 'node:fs';
import { mkdir } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import process from 'node:process';

const CANDIDATES = [
  process.env.CTI_BROWSER,
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
  '/usr/bin/google-chrome',
  '/usr/bin/chromium',
].filter(Boolean);

function parseArgs(argv) {
  const opts = { url: 'http://127.0.0.1:8123', width: 1440, height: 900, out: null, wait: 1200 };
  const positional = [];
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--url') opts.url = argv[++i];
    else if (arg === '--width') opts.width = Number(argv[++i]);
    else if (arg === '--height') opts.height = Number(argv[++i]);
    else if (arg === '--out') opts.out = argv[++i];
    else if (arg === '--wait') opts.wait = Number(argv[++i]);
    else if (!arg.startsWith('--')) positional.push(arg);
  }
  if (positional[0]) opts.url = positional[0];
  if (positional[1]) opts.width = Number(positional[1]);
  if (positional[2]) opts.height = Number(positional[2]);
  if (positional[3]) opts.out = positional[3];
  opts.out ||= `.tmp/shot-${opts.width}x${opts.height}.png`;
  return opts;
}

function findBrowser() {
  return CANDIDATES.find((candidate) => existsSync(candidate));
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  const executablePath = findBrowser();
  if (!executablePath) {
    console.error('找不到 Edge/Chrome。請設定 CTI_BROWSER 指向瀏覽器執行檔。');
    process.exit(1);
  }

  let puppeteer;
  try {
    ({ default: puppeteer } = await import('puppeteer-core'));
  } catch {
    console.error('缺少 puppeteer-core，請先執行：npm install');
    process.exit(1);
  }

  const browser = await puppeteer.launch({
    executablePath,
    headless: true,
    args: ['--hide-scrollbars', '--no-first-run', '--disable-gpu'],
  });

  try {
    const page = await browser.newPage();
    const consoleErrors = [];
    page.on('console', (message) => {
      if (message.type() === 'error') consoleErrors.push(message.text());
    });
    page.on('pageerror', (error) => consoleErrors.push(String(error)));

    await page.setViewport({ width: opts.width, height: opts.height, deviceScaleFactor: 1 });
    await page.goto(opts.url, { waitUntil: 'networkidle2', timeout: 60000 });

    // The dashboard fills in from /api/v1/stats; wait until the KPIs are real.
    await page
      .waitForFunction(() => {
        const node = document.querySelector('#kpiTotal');
        return node && node.textContent.trim() !== '—';
      }, { timeout: 10000 })
      .catch(() => consoleErrors.push('KPI 未在 10 秒內填入（API 或 CDN 可能失敗）'));

    await new Promise((done) => setTimeout(done, opts.wait));

    const out = resolve(process.cwd(), opts.out);
    await mkdir(dirname(out), { recursive: true });
    await page.screenshot({ path: out, fullPage: true });

    const metrics = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
      pageHeight: document.documentElement.scrollHeight,
      charts: document.querySelectorAll('.chart-frame canvas').length,
    }));

    console.log(JSON.stringify({
      saved: out,
      viewport: `${opts.width}x${opts.height}`,
      ...metrics,
      overflowX: metrics.scrollWidth > metrics.clientWidth,
      consoleErrors,
    }, null, 2));

    if (metrics.scrollWidth > metrics.clientWidth) process.exitCode = 2;
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error?.message || error);
  process.exit(1);
});
