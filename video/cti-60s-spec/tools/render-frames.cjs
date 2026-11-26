// render-frames.cjs - render PNG frames, then encode with ffmpeg from disk.
//
// Why this exists: this host refuses piped stdio for child processes (spawn gives
// EPERM / write EOF), and Remotion's renderMedia pipes frames into its bundled
// ffmpeg. renderFrames only takes browser screenshots, so it survives here; the
// encode step then runs ffmpeg with file inputs, which needs no pipe.
//
// usage: node tools/render-frames.cjs <outDir> [from] [to] [concurrency]

const path = require("node:path");
const fs = require("node:fs");
const { renderFrames, selectComposition } = require("@remotion/renderer");

const root = path.resolve(__dirname, "..");
const EDGE = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";

const [, , outDir, fromS, toS, conc] = process.argv;

(async () => {
  const serveUrl = path.join(root, "build");
  const comp = await selectComposition({ serveUrl, id: "Master", browserExecutable: EDGE });
  console.log("composition:", comp.durationInFrames, "frames @", comp.fps, "fps");
  const dir = path.join(root, outDir);
  fs.mkdirSync(dir, { recursive: true });
  const range = fromS ? [Number(fromS), Number(toS ?? comp.durationInFrames - 1)] : null;
  await renderFrames({
    composition: comp,
    serveUrl,
    outputDir: dir,
    imageFormat: "png",
    inputProps: {},
    concurrency: Number(conc || 3),
    frameRange: range,
    browserExecutable: EDGE,
    chromiumOptions: { gl: "angle" },
    timeoutInMilliseconds: 120000,
    onStart: () => console.log("start"),
    onFrameUpdate: (done) => {
      if (done % 50 === 0) console.log("frames " + done);
    },
  });
  console.log("FRAMES OK " + outDir);
})().catch((e) => {
  console.error("FRAMES FAILED:", e && e.stack ? e.stack : e);
  process.exit(1);
});
