// popup-positions.mjs - where the five selects sit at the headed window's viewport.
//
// The popup of a native <select> is drawn by the OS and never appears in a browser
// screenshot, so the capture has to come from the screen itself. That means real
// mouse input, which means we need screen coordinates. This script gets them from a
// headless pass at the same CSS viewport the headed window will use (1536x864),
// which is not limited by the physical screen.
//
//   node capture/popup-positions.mjs            -> public/openPositions.json

import fs from "node:fs";
import path from "node:path";
import puppeteer from "puppeteer-core";

const BASE = "https://cti-risk-platform.onrender.com/";
const EDGE = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
// 1920x1080 css, the same viewport the headed window gets with
// --force-device-scale-factor=1 --kiosk, so the positions transfer 1:1 and the page
// layout matches the film's captures (which are all 1920 css wide).
const W = 1920, H = 1080, DPR = 1;
const OUT = path.resolve("public/openPositions.json");

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await puppeteer.launch({
  executablePath: EDGE, headless: true,
  args: ["--no-sandbox", "--force-color-profile=srgb", "--hide-scrollbars"],
});
const page = await browser.newPage();
await page.setViewport({ width: W, height: H, deviceScaleFactor: DPR });
await page.goto(BASE, { waitUntil: "networkidle2", timeout: 120000 });
await page.waitForFunction(() => {
  const e = document.querySelector("#kpiAvgScore");
  return !!e && e.textContent.trim() !== "" && e.textContent.trim() !== "\u2014";
}, { timeout: 120000 });
await page.evaluate(() => document.fonts.ready);
await page.click('button[data-tab="assess"]');
await page.waitForFunction(() => {
  const e = document.querySelector("#assessForm");
  return !!e && e.getBoundingClientRect().height > 100;
}, { timeout: 60000 });
await sleep(600);

const ids = ["assetType", "threatSource", "category", "exposure", "exploitStatus"];
const positions = await page.evaluate((keys) => {
  const out = {};
  for (const k of keys) {
    const el = document.querySelector("#" + k);
    if (!el) { out[k] = null; continue; }
    const r = el.getBoundingClientRect();
    out[k] = { x: r.x, y: r.y, w: r.width, h: r.height };
  }
  const form = document.querySelector("#assessForm");
  const fr = form.getBoundingClientRect();
  const tab = document.querySelector('button[data-tab="assess"]');
  const tr = tab ? tab.getBoundingClientRect() : null;
  return {
    selects: out,
    form: { x: fr.x, y: fr.y, w: fr.width, h: fr.height },
    tab: tr ? { x: tr.x, y: tr.y, w: tr.width, h: tr.height } : null,
    viewport: { W: window.innerWidth, H: window.innerHeight },
  };
}, ids);

fs.writeFileSync(OUT, JSON.stringify(positions, null, 2));
console.log("wrote " + OUT);
console.log(JSON.stringify(positions.selects, null, 1));
await browser.close();
