import puppeteer from 'puppeteer-core';
const browser = await puppeteer.launch({
  executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  headless: true, args: ['--no-first-run', '--disable-gpu'],
});
try {
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e).slice(0, 160)));
  await page.setViewport({ width: 1440, height: 1100 });
  await page.goto('http://127.0.0.1:8123/', { waitUntil: 'networkidle2' });
  await new Promise((r) => setTimeout(r, 2500));
  const info = await page.evaluate(() => {
    const chart = Array.from(Object.values(window.Chart?.instances || {})).find((c) => c.config.type === 'line');
    if (!chart) return { chart: null };
    const share = chart.data.datasets[2]?.data || [];
    const last = share[share.length - 1];
    return {
      datasets: chart.data.datasets.map((d) => d.label),
      axes: Object.keys(chart.options.scales),
      lastShare: last == null ? null : Number(last).toFixed(0) + '%',
      firstShare: share[0] == null ? null : Number(share[0]).toFixed(0) + '%',
      counts: chart.data.datasets.slice(0, 2).map((d) => d.data[d.data.length - 1]),
    };
  });
  console.log(JSON.stringify({ info, errors }, null, 1));
} finally { await browser.close(); }
