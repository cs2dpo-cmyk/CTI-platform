// capture.mjs - real page capture for the CTI 60s film.
//
// Run it in a normal terminal (not inside the agent sandbox: that sandbox
// cannot start a browser at all). It drives the installed Edge through
// puppeteer-core, at viewport 1920x1080 and deviceScaleFactor 2, and waits on
// DOM state instead of sleeping.
//
// Why the page background is made transparent: the site paints two fixed
// ambient washes, a 64px grid and a rain canvas behind everything. In a tall
// capture those fixed layers only appear once, which leaves seams when the
// camera travels. So they are switched off here and the film repaints the same
// ambient layer once (src/components/Ambient.tsx), which keeps real alpha, real
// layout and no seams.

import puppeteer from "puppeteer-core";
import fs from "node:fs";
import path from "node:path";
import { cornerMean, pngSize } from "./png.mjs";

const BASE = "https://cti-risk-platform.onrender.com/";
const EDGE = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
const OUT = path.resolve("public/captures");
const W = 1920, H = 1080, DPR = 2;

fs.mkdirSync(OUT, { recursive: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const log = (...a) => console.log(...a);

async function warmup() {
  for (let i = 0; i < 60; i++) {
    try {
      const r = await fetch(BASE, { signal: AbortSignal.timeout(15000) });
      if (r.ok) { log("warmup ok (" + i + ")"); return; }
    } catch { /* render.com cold start */ }
    log("waiting for the site to wake up...");
    await sleep(2000);
  }
  throw new Error("the site never answered 200 within 120 s");
}

const data = { capturedAt: new Date().toISOString(), base: BASE, viewport: { W, H, DPR } };
const boxes = {};

async function main() {
  await warmup();

  const browser = await puppeteer.launch({
    executablePath: EDGE,
    headless: true,
    args: ["--no-sandbox", "--force-color-profile=srgb", "--hide-scrollbars", "--font-render-hinting=none"],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: W, height: H, deviceScaleFactor: DPR });

  await page.goto(BASE, { waitUntil: "networkidle2", timeout: 120000 });
  await page.waitForFunction(
    () => { const e = document.querySelector("#kpiAvgScore"); return !!e && e.textContent.trim() !== "" && e.textContent.trim() !== "\u2014"; },
    { timeout: 120000 },
  );
  await page.evaluate(() => document.fonts.ready);

  await page.addStyleTag({ content:
    "html,body{background:transparent !important;}" +
    "body::before{display:none !important}body::after{display:none !important}" +
    "#rain{display:none !important}" });

  const settle = async () => {
    await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))));
    await sleep(160);
  };
  const toTop = async () => {
    await page.evaluate(() => window.scrollTo({ top: 0, left: 0, behavior: "instant" }));
    await sleep(260);
    await settle();
  };
  const hideSticky = async (hide) => page.evaluate((on) => {
    for (const el of document.querySelectorAll("header, nav, [style*='sticky'], [style*='fixed']")) {
      if (on) el.setAttribute("data-dsh-hidden", "1");
      else el.removeAttribute("data-dsh-hidden");
      el.style.visibility = on ? "hidden" : "";
    }
  }, hide);
  const shotPage = async (name) => { await toTop(); await page.screenshot({ path: path.join(OUT, name), fullPage: true, omitBackground: true }); log("  page -> " + name); };
  const shotEl = async (sel, name) => {
    const el = await page.$(sel);
    if (!el) throw new Error("missing element for screenshot: " + sel);
    await el.scrollIntoView();
    await settle();
    await el.screenshot({ path: path.join(OUT, name), omitBackground: true });
    log("  el   -> " + name + "  (" + sel + ")");
  };
  const boxOf = (sel) => page.evaluate((s) => {
    const el = document.querySelector(s);
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return { x: r.x + window.scrollX, y: r.y + window.scrollY, w: r.width, h: r.height };
  }, sel);
  const record = async (key, sel) => { const b = await boxOf(sel); if (!b) log("  !! no box: " + sel); boxes[key] = b || { missing: true, sel }; };

  // ------------------------------------------------------------------ overview
  log("[1/5] overview");
  await page.evaluate(() => window.scrollTo(0, 0));
  data.overviewPageSize = await page.evaluate(() => ({ w: document.documentElement.scrollWidth, h: document.documentElement.scrollHeight }));
  await shotPage("overview-full.png");
  for (const s of ["#overview", "#matrix", "#matrixGrid", "#insightGrid", "#pieCenterTotal", "#clusterCaption", "#metaLegend"]) await record(s, s);

  boxes.kpiCards = await page.evaluate(() => [...document.querySelectorAll("#overview article.panel")].map((el, i) => {
    const r = el.getBoundingClientRect();
    return { i, x: r.x + scrollX, y: r.y + scrollY, w: r.width, h: r.height };
  }));
  const kpiEls = await page.$$("#overview article.panel");
  for (let i = 0; i < kpiEls.length; i++) {
    await kpiEls[i].scrollIntoView();
    await settle();
    await kpiEls[i].screenshot({ path: path.join(OUT, "kpi-" + String(i + 1).padStart(2, "0") + ".png"), omitBackground: true });
  }
  log("  kpi cards: " + kpiEls.length);

  // the threat-cluster panel and the matrix, as their own cut-outs
  const clusterSel = "#overview .panel:has(#clusterPieChart)";
  const hasCluster = await page.evaluate(() => !!document.querySelector("#clusterPieChart"));
  if (hasCluster) {
    await page.evaluate(() => {
      const panel = document.querySelector("#clusterPieChart").closest(".panel") || document.querySelector("#clusterPieChart").parentElement;
      panel.setAttribute("data-capture", "cluster");
      const r = panel.getBoundingClientRect();
      window.__cluster = { x: r.x + scrollX, y: r.y + scrollY, w: r.width, h: r.height };
    });
    boxes.cluster = await page.evaluate(() => window.__cluster);
    await shotEl("[data-capture=cluster]", "cluster-panel.png");
  } else { log("  !! cluster panel not found"); }
  await shotEl("#matrix", "matrix-panel.png");

  // ------------------------------------------- overview blocks for the 3D lift
  // v5: shots 2-4 lift one block at a time out of the page, so every block needs
  // its own cut-out and its own box. Element screenshots, not clips: a clip can
  // contain a neighbour, an element screenshot cannot - its box is the element's
  // box, and neighbours are siblings outside it.
  //
  // Two assertions run on every file written here (see capture/png.mjs):
  //   1. the PNG must be exactly the measured box at deviceScaleFactor 2;
  //   2. the four corners must be transparent or page-dark. Anything else means a
  //      neighbour's pixels are inside the file, which is the one failure the
  //      "only this block in frame" requirement cannot survive.
  {
    const pageDark = (c) => c.a < 60 || (c.r <= 20 && c.g <= 30 && c.b <= 48);

    const assertShot = (file, box, name) => {
      const buf = fs.readFileSync(file);
      const size = pngSize(buf);
      const ew = Math.round(box.w * DPR), eh = Math.round(box.h * DPR);
      if (Math.abs(size.width - ew) > 1 || Math.abs(size.height - eh) > 1) {
        throw new Error("size " + name + ": png " + size.width + "x" + size.height + " != box " + ew + "x" + eh);
      }
      for (const [k, c] of Object.entries(cornerMean(buf, 4))) {
        if (!pageDark(c)) {
          throw new Error("bleed " + name + ": corner " + k + " is rgba(" + c.r + "," + c.g + "," + c.b + "," + c.a + "), neither transparent nor page dark");
        }
      }
    };

    const freeze = (on) => page.evaluate((f) => {
      let s = document.getElementById("dsh-freeze");
      if (f && !s) {
        s = document.createElement("style");
        s.id = "dsh-freeze";
        s.textContent = "*{animation:none !important;transition:none !important;caret-color:transparent !important;}";
        document.head.appendChild(s);
      } else if (!f && s) {
        s.remove();
      }
    }, on);

    const blockShot = async (sel, name, key, tag) => {
      const info = await page.evaluate((s, t) => {
        const el = document.querySelector(s);
        if (!el) return { error: "missing " + s };
        if (t) el.setAttribute("data-capture", t);
        const r = el.getBoundingClientRect();
        return { box: { x: r.x + scrollX, y: r.y + scrollY, w: r.width, h: r.height } };
      }, sel, tag || null);
      if (info.error) throw new Error(info.error);
      const node = await page.$(tag ? "[data-capture=" + tag + "]" : sel);
      if (!node) throw new Error("no handle for " + name);
      await node.scrollIntoView();
      await settle();
      const file = path.join(OUT, name);
      await node.screenshot({ path: file, omitBackground: true });
      boxes[key] = info.box;
      assertShot(file, info.box, name);
      log("  block -> " + name + "  " + Math.round(info.box.w) + "x" + Math.round(info.box.h) + " css");
    };

    try {
    await freeze(true);

    // the hero band: headline plus its three stat boxes, one element
    await blockShot('section[aria-labelledby="heroTitle"]', "hero-band.png", "hero");

    // the compare panel is whichever .panel owns the comparison chart
    const compareOk = await page.evaluate(() => {
      const chart = document.querySelector("#comparisonBarChart");
      const panel = chart && (chart.closest(".panel") || chart.parentElement);
      if (!panel) return false;
      panel.setAttribute("data-capture", "compare");
      return true;
    });
    if (!compareOk) throw new Error("compare panel not found (#comparisonBarChart)");
    await blockShot("[data-capture=compare]", "compare-panel.png", "compare");

    // the three decision-matrix cards, one file each (never one grid sliced in three)
    const cardCount = await page.evaluate(() => document.querySelectorAll("#matrixGrid > *").length);
    if (cardCount < 3) throw new Error("matrix cards: expected 3, found " + cardCount);
    boxes.matrixCards = [];
    for (let i = 0; i < 3; i++) {
      const tag = "mc" + (i + 1);
      await page.evaluate((t, idx) => {
        document.querySelectorAll("#matrixGrid > *")[idx].setAttribute("data-capture", t);
      }, tag, i);
      await blockShot("[data-capture=" + tag + "]", "matrix-card-" + String(i + 1).padStart(2, "0") + ".png", "matrixCard" + (i + 1));
      boxes.matrixCards.push(boxes["matrixCard" + (i + 1)]);
    }

    await freeze(false);
    log("  overview blocks: hero + compare + " + boxes.matrixCards.length + " matrix cards");
    } catch (err) {
      await freeze(false).catch(() => {});
      log("  !! overview block capture failed, the rest of the run continues: " + (err && err.message ? err.message : String(err)));
    }
  }

  data.kpi = await page.evaluate(() => {
    const t = (s) => { const e = document.querySelector(s); return e ? e.innerText.replace(/\s+/g, " ").trim() : null; };
    return {
      total: t("#kpiTotal"), tw: t("#kpiTw"), global: t("#kpiGlobal"),
      p1: t("#kpiP1"), p1Share: t("#kpiP1Share"),
      topMeta: t("#kpiTopMeta"), topMetaShare: t("#kpiTopMetaShare"),
      avgScore: t("#kpiAvgScore"), critical: t("#kpiCritical"),
      pieTotal: t("#pieCenterTotal"), pieCaption: t("#pieCenterCaption"),
      clusterCaption: t("#clusterCaption"), sampleNote: t("#sampleNote"),
      matrixHint: t("#matrixHint"),
      classifyCount: (() => {
        const panel = document.querySelector("#clusterPieChart");
        const text = panel && panel.closest(".panel") ? panel.closest(".panel").innerText : "";
        const m = text.match(/(\d+)\s*類/);
        return m ? Number(m[1]) : null;
      })(),
      matrixCells: [...document.querySelectorAll("#matrixGrid > *")].map((e) => e.innerText.replace(/\s+/g, " ").trim()).slice(0, 12),
    };
  });
  log("  kpi total=" + data.kpi.total + " avg=" + data.kpi.avgScore + " p1=" + data.kpi.p1);

  // --------------------------------------------------------------------- patch
  log("[2/5] patch");
  await page.click('button[data-tab="patch"]');
  await page.waitForFunction(() => document.querySelectorAll("tbody#patchBody tr").length > 3, { timeout: 60000 });
  await settle();
  data.patchPageSize = await page.evaluate(() => ({ w: document.documentElement.scrollWidth, h: document.documentElement.scrollHeight }));
  await shotPage("patch-full.png");
  for (const s of ["#patchSection", "#patchBody", "#patchViewAll", "#gapSection", "#gapBody"]) await record(s, s);
  await shotEl("#patchSection", "patch-section.png");

  data.patch = await page.evaluate(() => {
    const t = (s) => { const e = document.querySelector(s); return e ? e.innerText.replace(/\s+/g, " ").trim() : null; };
    return {
      count: t("#patchCount"), total: t("#patchTotal"), asOf: t("#patchAsOf"), viewAll: t("#patchViewAll"),
      thead: [...document.querySelectorAll("#patchSection thead th")].map((th) => th.innerText.replace(/\s+/g, " ").trim()),
      rows: [...document.querySelectorAll("tbody#patchBody tr")].slice(0, 6).map((tr) => [...tr.querySelectorAll("td")].map((td) => td.innerText.replace(/\s+/g, " ").trim())),
      rowCount: document.querySelectorAll("tbody#patchBody tr").length,
    };
  });
  log("  rows=" + data.patch.rowCount + "  viewAll=\"" + data.patch.viewAll + "\"");

  // the first three rows as their own cut-outs (shot 6 fans them like dealt cards).
  // Clipped from the page, not element.screenshot(): an element handle here can come
  // back without a box while the table is re-rendering, which silently wrote nothing.
  boxes.patchRows = [];
  {
    const bodyBox = boxes["#patchBody"];
    const rowH = await page.evaluate(() => {
      const rows = document.querySelectorAll("#patchBody tr");
      if (rows.length < 2) return 55;
      const a = rows[0].getBoundingClientRect();
      const b = rows[1].getBoundingClientRect();
      return Math.max(20, Math.round((b.top - a.top) * 100) / 100);
    });
    data.rowHeight = rowH;
    for (let i = 0; i < 3; i++) {
      const clip = { x: bodyBox.x, y: bodyBox.y + i * rowH, width: bodyBox.w, height: rowH };
      await page.screenshot({ path: path.join(OUT, "patch-row-" + String(i + 1).padStart(2, "0") + ".png"), clip, omitBackground: true });
      boxes.patchRows.push({ i, x: clip.x, y: clip.y, w: clip.width, h: clip.height });
    }
    log("  patch row cut-outs: " + boxes.patchRows.length);
  }

  // the row that carries the CVE the film relays into the assessment form
  boxes.cveRow = await page.evaluate(() => {
    const tr = [...document.querySelectorAll("#patchBody tr")].find((r) => r.textContent.includes("CVE-2026-111497"));
    if (!tr) return null;
    const r = tr.getBoundingClientRect();
    return { x: r.x + scrollX, y: r.y + scrollY, w: r.width, h: r.height };
  });
  log("  CVE row: " + (boxes.cveRow ? "found" : "NOT in the first rows"));

  log("[3/5] gap section (never clicking 顯示全部)");
  data.gap = await page.evaluate(() => {
    const t = (s) => { const e = document.querySelector(s); return e ? e.innerText.replace(/\s+/g, " ").trim() : null; };
    return {
      covered: t("#gapCovered"), window: t("#gapWindowTotal"), asOf: t("#gapAsOf"), note: t("#gapNote"),
      thead: [...document.querySelectorAll("#gapSection thead th")].map((th) => th.innerText.replace(/\s+/g, " ").trim()),
      rows: [...document.querySelectorAll("#gapBody tr")].slice(0, 5).map((tr) => [...tr.querySelectorAll("td")].map((td) => td.innerText.replace(/\s+/g, " ").trim())),
      rowCount: document.querySelectorAll("#gapBody tr").length,
    };
  });
  await shotEl("#gapSection", "gap-panel.png");
  log("  gap rows=" + data.gap.rowCount + " covered=" + data.gap.covered);

  // expand the patch table, then take 10 non-overlapping strips of it
  log("  expanding the patch table");
  const before = data.patch.rowCount;
  await page.click("#patchViewAll");
  await page.waitForFunction((n) => document.querySelectorAll("tbody#patchBody tr").length > n + 40, { timeout: 60000 }, before)
    .catch(() => log("  !! the table did not grow, using what is there"));
  await settle();
  data.patchExpanded = await page.evaluate(() => ({
    rows: document.querySelectorAll("tbody#patchBody tr").length,
    count: document.querySelector("#patchCount") ? document.querySelector("#patchCount").innerText.trim() : null,
    viewAll: document.querySelector("#patchViewAll") ? document.querySelector("#patchViewAll").innerText.replace(/\s+/g, " ").trim() : null,
  }));
  log("  expanded rows=" + data.patchExpanded.rows + "  count=" + data.patchExpanded.count);
  await shotPage("patch-expanded-full.png");

  // Ten non-overlapping slices of the table body, taken as clipped screenshots so
  // the film can translate them (the page never scrolls on screen). The sticky
  // header is hidden first: it would otherwise sit on top of the first slice.
  {
    await hideSticky(true);
    const body = await page.evaluate(() => {
      const r = document.querySelector("#patchBody").getBoundingClientRect();
      return { x: r.x + scrollX, y: r.y + scrollY, w: r.width, h: r.height };
    });
    const STRIDE = 900;
    const segments = Math.min(10, Math.max(1, Math.floor(body.h / STRIDE)));
    data.strip = { stride: STRIDE, segments, tableHeight: body.h };
    boxes.strip = { x: body.x, y: body.y, w: body.w, h: STRIDE };
    for (let i = 0; i < segments; i++) {
      const clip = { x: body.x, y: body.y + i * STRIDE, width: body.w, height: STRIDE };
      await page.evaluate((top) => window.scrollTo({ top: Math.max(0, top - 60), behavior: "instant" }), clip.y);
      await sleep(140);
      await page.screenshot({ path: path.join(OUT, "strip-" + String(i).padStart(2, "0") + ".png"), clip, omitBackground: true });
      log("  strip " + String(i).padStart(2, "0") + " @ page y " + Math.round(clip.y));
    }
    await hideSticky(false);
  }

  // -------------------------------------------------------------------- assess
  log("[4/5] assess form");
  await page.click('button[data-tab="assess"]');
  await page.waitForFunction(() => { const e = document.querySelector("#assess"); return !!e && e.getBoundingClientRect().height > 100; }, { timeout: 60000 });
  await settle();
  await page.evaluate(() => window.scrollTo(0, 0));
  data.assessPageSize = await page.evaluate(() => ({ w: document.documentElement.scrollWidth, h: document.documentElement.scrollHeight }));
  await shotPage("assess-full.png");
  for (const s of ["#assess", "#assessForm", "#assessBtn", "#assessResult"]) await record("assess:" + s, s);

  data.fields = await page.evaluate(() => {
    const out = {};
    const take = (k, el) => { if (!el) { out[k] = null; return; } const r = el.getBoundingClientRect(); out[k] = { x: r.x + scrollX, y: r.y + scrollY, w: r.width, h: r.height }; };
    take("assetType", document.querySelector("#assetType"));
    take("threatSource", document.querySelector("#threatSource"));
    take("category", document.querySelector("#category"));
    take("exposure", document.querySelector("#exposure"));
    take("regionGlobal", [...document.querySelectorAll("#assess button[data-form-region]")].find((b) => b.textContent.includes("國際來源")));
    take("cveId", document.querySelector("#cveId"));
    take("cvss", document.querySelector("#cvss"));
    take("exploitStatus", document.querySelector("#exploitStatus"));
    take("sensitivityHigh", [...document.querySelectorAll('#assess button[data-group="sensitivity"]')].find((b) => b.dataset.value === "high"));
    take("assetName", document.querySelector("#assetName"));
    take("assessBtn", document.querySelector("#assessBtn"));
    out.options = {};
    for (const id of ["assetType", "threatSource", "category", "exposure", "exploitStatus"]) {
      const s = document.querySelector("#" + id);
      out.options[id] = s ? [...s.options].map((o) => ({ v: o.value, t: o.textContent.trim() })) : [];
    }
    return out;
  });

  const hover = async (sel) => {
    const el = await page.$(sel);
    if (!el) return;
    const b = await el.boundingBox();
    if (b) await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2);
    await sleep(150);
  };
  // Every step records the field boxes it was taken with: the form grows by one
  // hint line once CVSS carries a value, and a cursor aimed with boxes from the
  // short layout lands ~55px above the button on the tall steps. The film reads
  // these per-step boxes instead of assuming the layout never moves.
  const takeFields = () => page.evaluate(() => {
    const out = {};
    const take = (k, el) => {
      if (!el) { out[k] = null; return; }
      const r = el.getBoundingClientRect();
      out[k] = { x: r.x + scrollX, y: r.y + scrollY, w: r.width, h: r.height };
    };
    take("assetType", document.querySelector("#assetType"));
    take("threatSource", document.querySelector("#threatSource"));
    take("category", document.querySelector("#category"));
    take("exposure", document.querySelector("#exposure"));
    take("regionGlobal", [...document.querySelectorAll("#assess button[data-form-region]")].find((b) => b.textContent.includes("國際來源")));
    take("cveId", document.querySelector("#cveId"));
    take("cvss", document.querySelector("#cvss"));
    take("exploitStatus", document.querySelector("#exploitStatus"));
    take("sensitivityHigh", [...document.querySelectorAll('#assess button[data-group="sensitivity"]')].find((b) => b.dataset.value === "high"));
    take("assetName", document.querySelector("#assetName"));
    take("assessBtn", document.querySelector("#assessBtn"));
    const form = document.querySelector("#assessForm");
    out.formH = form ? form.getBoundingClientRect().height : null;
    return out;
  });

  data.stepFields = {};
  const step = async (n) => {
    await settle();
    const el = await page.$("#assessForm");
    if (el) await el.screenshot({ path: path.join(OUT, "assess-step" + String(n).padStart(2, "0") + ".png"), omitBackground: true });
    data.stepFields[n] = await takeFields();
    log("  step " + String(n).padStart(2, "0") + "  formH=" + Math.round(data.stepFields[n].formH || 0));
  };
  const selectByText = async (id, text) => {
    const ok = await page.evaluate((sel, t) => {
      const s = document.querySelector(sel);
      if (!s) return "no element";
      const opt = [...s.options].find((o) => o.textContent.trim().includes(t));
      if (!opt) return "no option: " + [...s.options].map((o) => o.textContent.trim()).join(" | ");
      s.value = opt.value;
      s.dispatchEvent(new Event("input", { bubbles: true }));
      s.dispatchEvent(new Event("change", { bubbles: true }));
      return true;
    }, "#" + id, text);
    if (ok !== true) throw new Error("select " + id + " <- " + text + ": " + ok);
  };

  await hover("#assetType"); await step(1); await selectByText("assetType", "對外網站");
  await hover("#threatSource"); await step(2); await selectByText("threatSource", "國家級");
  await hover("#category"); await step(3); await selectByText("category", "系統漏洞");
  await hover("#exposure"); await step(4); await selectByText("exposure", "公開");
  await page.evaluate(() => [...document.querySelectorAll("#assess button[data-form-region]")].find((b) => b.textContent.includes("國際來源")).click());
  await step(5);
  await page.click("#cveId", { clickCount: 3 });
  await page.type("#cveId", "CVE-2026-111497", { delay: 20 });
  await step(6);
  const slider = await page.$("#cvss");
  const sb = await slider.boundingBox();
  await page.mouse.move(sb.x + 8 + 0.75 * (sb.width - 16), sb.y + sb.height / 2);
  await page.mouse.down();
  await page.mouse.move(sb.x + 8 + 0.98 * (sb.width - 16), sb.y + sb.height / 2, { steps: 16 });
  await page.mouse.up();
  data.cvssAfterDrag = await page.$eval("#cvss", (e) => Number(e.value));

  // v8: four slider states, so the film can show the thumb being dragged rather
  // than a single "after" frame. Each one records the real value, the form height
  // and that state’s field boxes.
  data.cvssStates = {};
  for (const [i, value] of [7.5, 8.3, 9.1, 9.8].entries()) {
    await page.evaluate((v) => {
      const el = document.querySelector("#cvss");
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
      setter.call(el, String(v));
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
    }, value);
    await settle();
    const cvssBox = await page.evaluate(() => {
      const r = document.querySelector("#cvss").getBoundingClientRect();
      return { x: r.x + scrollX, y: r.y + scrollY, w: r.width, h: r.height };
    });
    const fields = await takeFields();
    const formEl = await page.$("#assessForm");
    await formEl.screenshot({ path: path.join(OUT, "assess-cvss-" + String(i + 1).padStart(2, "0") + ".png"), omitBackground: true });
    data.cvssStates[String(i + 1)] = { value, cvssBox, formH: fields.formH, fields };
    log("  cvss state " + (i + 1) + " = " + value + "  formH=" + Math.round(fields.formH));
  }

  await step(7);
  await hover("#exploitStatus"); await selectByText("exploitStatus", "已在野");
  await step(8);
  await page.evaluate(() => [...document.querySelectorAll('#assess button[data-group="sensitivity"]')].find((b) => b.dataset.value === "high").click());
  await step(9);
  await hover("#assetName");
  await page.type("#assetName", "tw-fintech-prod-api-01", { delay: 16 });
  await step(10);
  await hover("#assessBtn");
  await step(11);
  await shotPage("assess-filled-full.png");
  log("  cvss after drag = " + data.cvssAfterDrag);

  // -------------------------------------------------------------------- result
  log("[5/5] the assessment result");
  await page.click("#assessBtn");
  await page.waitForFunction(() => {
    const r = document.querySelector("#assessResult");
    const v = document.querySelector("#scoreValue");
    if (!r || r.offsetParent === null || !v) return false;
    const n = parseFloat(v.textContent.replace(/[^0-9.]/g, ""));
    return Number.isFinite(n) && n > 0;
  }, { timeout: 90000 });
  await sleep(900);
  await page.evaluate(() => document.querySelector("#assessResult").scrollIntoView({ block: "center" }));
  await settle();
  data.resultPageSize = await page.evaluate(() => ({ w: document.documentElement.scrollWidth, h: document.documentElement.scrollHeight }));
  await shotPage("result-full.png");
  await shotEl("#assessResult", "result-panel.png");
  await record("result:#assessResult", "#assessResult");
  for (const s of ["#scoreRing", "#scoreValue", "#priorityBadge", "#resultHeadline", "#resultLevel", "#resultSla", "#resultSummary", "#factorList", "#resultPlan"])
    await record("result:" + s, s);

  data.result = await page.evaluate(() => {
    const t = (s) => { const e = document.querySelector(s); return e ? e.innerText.replace(/\s+/g, " ").trim() : null; };
    return {
      score: t("#scoreValue"), priority: t("#priorityBadge"), headline: t("#resultHeadline"),
      level: t("#resultLevel"), sla: t("#resultSla"), confidence: t("#resultConfidence"),
      summary: t("#resultSummary"), owner: t("#resultOwner"), plan: t("#resultPlan"),
      factors: [...document.querySelectorAll("#factorList > *")].map((e) => e.innerText.replace(/\s+/g, " ").trim()),
      adjustments: [...document.querySelectorAll("#adjustmentList > *")].map((e) => e.innerText.replace(/\s+/g, " ").trim()),
    };
  });
  log("  RESULT " + JSON.stringify({ score: data.result.score, priority: data.result.priority, sla: data.result.sla }));

  fs.writeFileSync(path.resolve("public/bboxes.json"), JSON.stringify(boxes, null, 2));
  fs.writeFileSync(path.resolve("public/data.json"), JSON.stringify(data, null, 2));
  log("wrote public/bboxes.json and public/data.json");
  await browser.close();
}

main().catch((e) => { console.error("CAPTURE FAILED:", e && e.stack ? e.stack : e); process.exit(1); });