const cp = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");
const root = path.resolve(__dirname, "..");
const ffmpeg = path.join(root, "node_modules", "@remotion", "compositor-win32-x64-msvc", "ffmpeg.exe");
const out = path.join(root, "out", "check11");
fs.mkdirSync(out, { recursive: true });
const logFd = fs.openSync(path.join(out, "log.txt"), "w");
const film = path.join(root, "out", "film.mp4");
// output seeking (-ss after -i) decodes and lands on the exact frame
for (const [t, n] of [["2.000", "f0060"], ["8.967", "f0269"], ["16.000", "f0480"], ["21.333", "f0640"], ["55.000", "f1650"], ["55.333", "f1660"], ["61.467", "f1844"], ["64.967", "f1949"]]) {
  cp.spawnSync(ffmpeg, ["-hide_banner", "-loglevel", "error", "-y", "-i", film, "-ss", t, "-frames:v", "1", path.join(out, n + ".png")], { stdio: ["ignore", logFd, logFd] });
}
console.log(fs.readdirSync(out).filter((f) => f.endsWith(".png")).join(", "));