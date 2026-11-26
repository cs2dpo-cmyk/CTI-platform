const cp = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");
const root = path.resolve(__dirname, "..");
const ffmpeg = path.join(root, "node_modules", "@remotion", "compositor-win32-x64-msvc", "ffmpeg.exe");
const out = path.join(root, "out", "check10");
fs.mkdirSync(out, { recursive: true });
const logFd = fs.openSync(path.join(out, "log.txt"), "w");
const film = path.join(root, "out", "film.mp4");
cp.spawnSync(ffmpeg, ["-hide_banner", "-i", film], { stdio: ["ignore", logFd, logFd] });
console.log(fs.readFileSync(path.join(out, "log.txt"), "utf8").split("\n").filter((l) => /Duration|Stream/.test(l)).join("\n"));
console.log("size " + (fs.statSync(film).size / 1048576).toFixed(1) + " MB");
const grab = (t, name) => cp.spawnSync(ffmpeg, ["-hide_banner", "-loglevel", "error", "-y", "-ss", String(t), "-i", film, "-frames:v", "1", path.join(out, name)], { stdio: ["ignore", logFd, logFd] });
// master frames: 60=2.0s, 270=9.0s, 480=16.0s, 645=21.5s, 1292=43.07s, 1440=48.0s, 1650=55.0s, 1844=61.47s
for (const [t, n] of [[2.0, "f0060-s02-in.png"], [8.9, "f0267-s02-done.png"], [16.0, "f0480-s04-in.png"], [21.4, "f0642-s04-done.png"], [43.07, "f1292-menu.png"], [48.0, "f1440-cvss.png"], [55.0, "f1650-s11-start.png"], [61.47, "f1844-s11-end.png"]]) grab(t, n);
for (let i = 0; i <= 20; i++) grab((21.5 + i * 0.1).toFixed(2), "scan" + String(i).padStart(2, "0") + ".png");
console.log("ok " + fs.readdirSync(out).filter((f) => f.endsWith(".png")).length + " frames");