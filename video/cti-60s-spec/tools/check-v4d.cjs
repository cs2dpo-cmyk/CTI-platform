const cp = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");
const root = path.resolve(__dirname, "..");
const ffmpeg = path.join(root, "node_modules", "@remotion", "compositor-win32-x64-msvc", "ffmpeg.exe");
const out = path.join(root, "out", "check7");
fs.mkdirSync(out, { recursive: true });
const logFd = fs.openSync(path.join(out, "log.txt"), "w");
const film = path.join(root, "out", "film.mp4");
cp.spawnSync(ffmpeg, ["-hide_banner", "-i", film], { stdio: ["ignore", logFd, logFd] });
console.log(fs.readFileSync(path.join(out, "log.txt"), "utf8").split("\n").filter((l) => /Duration|Stream/.test(l)).join("\n"));
console.log("size " + (fs.statSync(film).size / 1048576).toFixed(1) + " MB");
for (const t of [21.0, 21.5, 22.0, 22.5, 23.0, 24.0, 18.0]) {
  cp.spawnSync(ffmpeg, ["-hide_banner", "-loglevel", "error", "-y", "-ss", String(t), "-i", film, "-frames:v", "1", path.join(out, "f" + t.toFixed(1) + ".png")], { stdio: ["ignore", logFd, logFd] });
}
console.log("ok");