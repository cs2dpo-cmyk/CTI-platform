// render.cjs - render stills and the film with @remotion/renderer directly.
//
// The CLI is not used: it loads remotion.config.ts through esbuild, whose
// service process needs pipes this host refuses. Bundling is done by
// tools/build.cjs instead, and this script renders from that bundle with the
// Edge install on the machine (no browser download).

const path = require("node:path");
const fs = require("node:fs");
const { renderStill, renderMedia, selectComposition } = require("@remotion/renderer");

const root = path.resolve(__dirname, "..");
const serveUrl = path.join(root, "build");
const EDGE = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";

const [, , mode, ...rest] = process.argv;

async function main() {
  if (mode === "still") {
    const [composition, frame, out] = rest;
    fs.mkdirSync(path.dirname(path.join(root, out)), { recursive: true });
    const comp = await selectComposition({ serveUrl, id: composition, browserExecutable: EDGE });
    await renderStill({
      composition: comp,
      serveUrl,
      output: path.join(root, out),
      frame: Number(frame),
      imageFormat: "png",
      browserExecutable: EDGE,
      chromiumOptions: { gl: "angle" },
      timeoutInMilliseconds: 120000,
    });
    console.log("STILL OK " + out);
    return;
  }
  if (mode === "video") {
    const [composition, out, crf] = rest;
    const comp = await selectComposition({ serveUrl, id: composition, browserExecutable: EDGE });
    await renderMedia({
      composition: comp,
      serveUrl,
      codec: "h264",
      crf: Number(crf || 19),
      outputLocation: path.join(root, out),
      browserExecutable: EDGE,
      chromiumOptions: { gl: "angle" },
      imageFormat: "png",
      concurrency: null,
      onProgress: ({ progress }) => {
        const pct = Math.round(progress * 100);
        if (pct % 10 === 0) console.log("render " + pct + "%");
      },
    });
    console.log("VIDEO OK " + out);
    return;
  }
  throw new Error("usage: render.cjs still <comp> <frame> <out.png> | video <comp> <out.mp4> [crf]");
}

main().catch((e) => { console.error("RENDER FAILED:", e && e.stack ? e.stack : e); process.exit(1); });