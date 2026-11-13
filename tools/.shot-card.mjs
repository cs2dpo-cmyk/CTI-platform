import puppeteer from 'puppeteer-core';
const browser = await puppeteer.launch({
  executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  headless: true, args: ['--no-first-run', '--disable-gpu'],
});
try {
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 1100, deviceScaleFactor: 2 });
  await page.goto('http://127.0.0.1:8123/', { waitUntil: 'networkidle2' });
  await new Promise((r) => setTimeout(r, 3000));
  const card = await page.$('#timelineChart');
  const panel = await card.evaluateHandle((el) => el.closest('.panel'));
  await panel.asElement().screenshot({ path: 'C:/dev/cti-platform/docs/timeline-share.png' });
  console.log('saved');
} finally { await browser.close(); }
