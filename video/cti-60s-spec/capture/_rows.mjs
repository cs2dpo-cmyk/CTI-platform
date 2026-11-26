import fs from "node:fs";
import { decode } from "./png.mjs";

// Find the gap table's row separators by scanning for horizontal hairline runs.
const img = decode(fs.readFileSync("public/captures/gap-panel.png"));
const bpp = img.bpp;
const DPR = 2;
console.log("gap-panel.png:", img.width + "x" + img.height, "=> css", img.width / DPR + "x" + img.height / DPR);

// a separator is a row where a long run of pixels is lighter than the panel fill
const isLine = (r, g, b) => r > 30 && r < 90 && g > 45 && g < 110 && b > 70 && b < 140;
const x0 = Math.floor(img.width * 0.05), x1 = Math.floor(img.width * 0.95);
const rows = [];
for (let y = 0; y < img.height; y++) {
  let n = 0;
  for (let x = x0; x < x1; x += 3) {
    const i = (y * img.width + x) * bpp;
    if (isLine(img.data[i], img.data[i + 1], img.data[i + 2])) n++;
  }
  if (n > (x1 - x0) / 3 * 0.55) rows.push(y);
}
// collapse adjacent rows into single separators
const seps = [];
for (const y of rows) {
  if (!seps.length || y - seps[seps.length - 1] > 4) seps.push(y);
}
console.log("separators (css y):", seps.map((y) => (y / DPR).toFixed(1)).join(", "));
const gaps = [];
for (let i = 1; i < seps.length; i++) gaps.push((seps[i] - seps[i - 1]) / DPR);
console.log("pitch (css):", gaps.map((g) => g.toFixed(1)).join(", "));
if (seps.length) console.log("first separator css y:", (seps[0] / DPR).toFixed(1));
