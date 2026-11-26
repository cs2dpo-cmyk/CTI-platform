import { decode } from "../capture/png.mjs";
import fs from "node:fs";
const png = decode(fs.readFileSync("out/stills/17-diag-s10-state11.png"));
const { width, height, bpp, data } = png;
const target = [0x2b, 0x3c, 0x5a];
const tol = 14;
const cols = [];
for (let x = width - 400; x < width; x++) {
  let n = 0;
  for (let y = 0; y < height; y += 3) {
    const i = (y * width + x) * bpp;
    const r = data[i], g = data[i + 1], b = data[i + 2];
    if (Math.abs(r - target[0]) <= tol && Math.abs(g - target[1]) <= tol && Math.abs(b - target[2]) <= tol) n++;
  }
  if (n > 40) cols.push({ x, n });
}
console.log("image " + width + "x" + height + " bpp " + bpp);
console.log("columns with >40 border-coloured pixels in the right 400 px: " + cols.length);
for (const c of cols.slice(0, 10)) console.log("  x=" + c.x + "  n=" + c.n);
const bad = cols.filter((c) => c.n > 200);
console.log(bad.length === 0 ? "PASS: no full-height panel edge" : "FAIL: " + bad.length + " full-height edges");
if (cols.length) console.log("rightmost border column x=" + cols[cols.length - 1].x + "  (want >= 1860)");