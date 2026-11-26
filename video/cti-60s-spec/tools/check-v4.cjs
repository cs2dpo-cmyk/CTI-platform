const cp = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");
const root = path.resolve(__dirname, "..");
const ffmpeg = path.join(root, "node_modules", "@remotion", "compositor-win32-x64-msvc", "ffmpeg.exe");
const out = path.join(root, "out", "check4");
fs.mkdirSync(out, { recursive: true });
const logFd = fs.openSync(path.join(out, "probe.log"), "w");
const film = path.join(root, "out", "film.mp4");
cp.spawnSync(ffmpeg, ["-hide_banner", "-i", film], { stdio: ["ignore", logFd, logFd] });
const probe = fs.readFileSync(path.join(out, "probe.log"), "utf8");
console.log(probe.split("\n").filter((l) => /Duration|Stream/.test(l)).join("\n"));
// hero moments across the 48 s cut
const times = [0.7, 3.0, 6.5, 9.0, 13.0, 15.0, 18.0, 22.0, 26.0, 29.0, 33.0, 40.0, 44.0, 47.5];
for (const t of times) {
  cp.spawnSync(ffmpeg, ["-hide_banner", "-loglevel", "error", "-y", "-ss", String(t), "-i", film, "-frames:v", "1", path.join(out, "t" + t.toFixed(1) + ".png")], { stdio: ["ignore", logFd, logFd] });
}
// dense scan across the dive handover (s04 -> s05 -> s06, 11.5-16.0 s)
for (let i = 0; i <= 26; i++) {
  const t = 14.2 + i * 0.1;
  cp.spawnSync(ffmpeg, ["-hide_banner", "-loglevel", "error", "-y", "-ss", t.toFixed(2), "-i", film, "-frames:v", "1", path.join(out, "scan" + String(i).padStart(2, "0") + ".png")], { stdio: ["ignore", logFd, logFd] });
}
console.log("frames: " + fs.readdirSync(out).filter((f) => f.endsWith(".png")).length);