// temporary: render a frame range with a given concurrency, to isolate the
// "write EOF" crash that killed the full render at 0%.
const path = require("node:path");
const fs = require("node:fs");
const { renderMedia, selectComposition } = require("@remotion/renderer");

const root = path.resolve(__dirname, "..");
const EDGE = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";

const [, , out, fromS, toS, conc] = process.argv;

(async () => {
  const serveUrl = path.join(root, "build");
  const comp = await selectComposition({ serveUrl, id: "Master", browserExecutable: EDGE });
  console.log("composition ok:", comp.durationInFrames, "frames,", comp.fps, "fps");
  fs.mkdirSync(path.dirname(path.join(root, out)), { recursive: true });
  await renderMedia({
    composition: comp,
    serveUrl,
    codec: "h264",
    crf: 20,
    outputLocation: path.join(root, out),
    browserExecutable: EDGE,
    chromiumOptions: { gl: "angle" },
    imageFormat: "png",
    concurrency: Number(conc || 1),
    frameRange: [Number(fromS), Number(toS)],
    onProgress: ({ progress }) => {
      const p = Math.round(progress * 100);
      if (p % 25 === 0) console.log("progress " + p + "%");
    },
  });
  console.log("RANGE OK " + out);
})().catch((e) => {
  console.error("RANGE FAILED:", e && e.stack ? e.stack : e);
  process.exit(1);
});
