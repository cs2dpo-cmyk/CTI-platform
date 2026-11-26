const cp = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");
const root = path.resolve(__dirname, "..");
const ffmpeg = path.join(root, "node_modules", "@remotion", "compositor-win32-x64-msvc", "ffmpeg.exe");
const out = path.join(root, "out", "check7");
const logFd = fs.openSync(path.join(out, "log2.txt"), "w");
for (const t of [16.7, 17.0, 2.2]) {
  cp.spawnSync(ffmpeg, ["-hide_banner", "-loglevel", "error", "-y", "-ss", String(t), "-i", path.join(root, "out", "film.mp4"), "-frames:v", "1", path.join(out, "p" + t.toFixed(1) + ".png")], { stdio: ["ignore", logFd, logFd] });
}
console.log("ok");