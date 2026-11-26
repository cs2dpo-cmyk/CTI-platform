// check-film.cjs - read the rendered mp4 without pipes: ffmpeg is spawned with
// its output redirected to a file descriptor (this host refuses piped stdio),
// then the log and the frames are read back from disk.

const cp = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const ffmpeg = path.join(root, "node_modules", "@remotion", "compositor-win32-x64-msvc", "ffmpeg.exe");
const out = path.join(root, "out", "check");
fs.mkdirSync(out, { recursive: true });

const logPath = path.join(out, "ffmpeg.log");
const logFd = fs.openSync(logPath, "w");

function run(args, stdioOut = null) {
  const stdio = stdioOut ? ["ignore", stdioOut, stdioOut] : ["ignore", logFd, logFd];
  const r = cp.spawnSync(ffmpeg, args, { stdio, windowsHide: true, timeout: 600000 });
  return r.status;
}

const film = path.join(root, "out", "film.mp4");
const sample = path.join(root, "out", "sample-640x360.mp4");

// 1. probe (no output file: ffmpeg prints the streams to stderr, which is the log)
run(["-hide_banner", "-i", film]);
const probe = fs.readFileSync(logPath, "utf8");
console.log(probe.split("\n").filter((l) => /Duration|Stream|frame=/i.test(l)).slice(0, 6).join("\n"));

// 2. one frame per shot, at the moment the shot has settled
const times = [0.8, 4.0, 7.0, 11.0, 16.5, 19.0, 22.5, 26.0, 30.0, 34.5, 37.0, 45.0, 52.0, 55.5, 59.0];
for (let i = 0; i < times.length; i++) {
  const t = times[i];
  const name = path.join(out, "t" + String(t.toFixed(1)).padStart(5, "0") + ".png");
  run(["-hide_banner", "-loglevel", "error", "-y", "-ss", String(t), "-i", film, "-frames:v", "1", name]);
}
const made = fs.readdirSync(out).filter((f) => f.endsWith(".png")).sort();
console.log("frames: " + made.join(", "));

// 3. the sample, same contract
run(["-hide_banner", "-i", sample]);
const probe2 = fs.readFileSync(logPath, "utf8");
console.log(probe2.split("\n").filter((l) => /Duration|Stream/i.test(l)).slice(-2).join("\n"));

for (const f of [film, sample]) {
  const st = fs.statSync(f);
  console.log(path.basename(f) + "  " + (st.size / 1024 / 1024).toFixed(2) + " MB");
}