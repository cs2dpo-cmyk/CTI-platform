const cp = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");
const root = path.resolve(__dirname, "..");
const ffmpeg = path.join(root, "node_modules", "@remotion", "compositor-win32-x64-msvc", "ffmpeg.exe");
const out = path.join(root, "out", "check11");
const logFd = fs.openSync(path.join(out, "log2.txt"), "w");
const film = path.join(root, "out", "film.mp4");
for (const [t, n] of [["54.800", "pre548"], ["54.967", "pre5497"], ["55.033", "f1651"], ["55.500", "f1665"], ["56.000", "f1680"]]) {
  cp.spawnSync(ffmpeg, ["-hide_banner", "-loglevel", "error", "-y", "-i", film, "-ss", t, "-frames:v", "1", path.join(out, n + ".png")], { stdio: ["ignore", logFd, logFd] });
}
console.log("done");