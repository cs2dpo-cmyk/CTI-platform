const cp = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");
const root = path.resolve(__dirname, "..");
const ffmpeg = path.join(root, "node_modules", "@remotion", "compositor-win32-x64-msvc", "ffmpeg.exe");
const out = path.join(root, "out", "check");
fs.mkdirSync(out, { recursive: true });
const logFd = fs.openSync(path.join(out, "ffmpeg2.log"), "w");
for (const t of [22.2, 22.6, 23.0, 29.5]) {
  const name = path.join(out, "v" + t.toFixed(1) + ".png");
  cp.spawnSync(ffmpeg, ["-hide_banner", "-loglevel", "error", "-y", "-ss", String(t), "-i", path.join(root, "out", "film.mp4"), "-frames:v", "1", name], { stdio: ["ignore", logFd, logFd], windowsHide: true, timeout: 120000 });
}
console.log(fs.readdirSync(out).filter((f) => f.startsWith("v")).join(", "));