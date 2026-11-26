// stills.cjs - SPEC 10 stage 1: the six hero frames, the grid overlay and the
// spec card. Rendered as PNG stills from the same bundle the film renders from,
// so what is reviewed here is what the film will show.

const path = require("node:path");
const fs = require("node:fs");
const { renderStill, selectComposition } = require("@remotion/renderer");

const root = path.resolve(__dirname, "..");
const serveUrl = path.join(root, "build");
const EDGE = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";

// frame numbers are scene-local; each is chosen after the entrance has landed
// and while the camera is on the move, which is the frame the note describes.
const STILLS = [
  ["Still-S02", 100, "01-shot-02-overview-kpi.png"],
  ["Still-S03", 104, "02-shot-03-clusters.png"],
  ["Still-S06", 108, "03-shot-06-patch-priority.png"],
  ["Still-S08", 74, "04-shot-08-gap.png"],
  ["Still-S10", 140, "05-shot-10-assess.png"],
  ["Still-S11", 100, "06-shot-11-result.png"],
  ["Grid-Check", 92, "07-grid-and-safe-area.png"],
  ["Spec-Card", 0, "08-spec-card.png"],
  ["Still-S01", 26, "09-shot-01-wordmark.png"],
  ["Still-S04", 60, "16-shot-04-matrix.png"],
  ["Still-S05", 26, "10-shot-05-wipe.png"],
  ["Still-S09", 26, "11-shot-09-relay.png"],
  ["Still-S12", 50, "12-shot-12-outro.png"],
  ["Still-S07", 78, "13-shot-07-sweep.png"],
  ["Scene-S07", 44, "14-diag-s07-moving.png"],
  ["Scene-S10", 330, "17-diag-s10-state11.png"],
  ["Scene-S10", 152, "18-diag-s10-menu.png"],
  ["Scene-S11", 0, "20-diag-s11-start.png"],
  ["Scene-S11", 60, "21-diag-s11-mid.png"],
  ["Scene-S11", 194, "22-diag-s11-end.png"],
  ["Scene-S10", 300, "19-diag-s10-cvss.png"],
  ["Scene-S07", 50, "15-diag-s07-moving2.png"],
];

async function main() {
  const outDir = path.join(root, "out", "stills");
  fs.mkdirSync(outDir, { recursive: true });
  for (const [id, frame, name] of STILLS) {
    const composition = await selectComposition({ serveUrl, id, browserExecutable: EDGE });
    const output = path.join(outDir, name);
    await renderStill({ composition, serveUrl, output, frame, imageFormat: "png", browserExecutable: EDGE });
    console.log("still -> out/stills/" + name + "   (" + id + " @ " + frame + ")");
  }
  fs.writeFileSync(path.join(outDir, "manifest.json"), JSON.stringify(STILLS, null, 2));
  console.log("done: " + STILLS.length + " stills in out/stills");
}

main().catch((e) => { console.error("STILLS FAILED:", e && e.stack ? e.stack : e); process.exit(1); });