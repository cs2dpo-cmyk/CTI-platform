import { decode } from "../capture/png.mjs";
import fs from "node:fs";
const png = decode(fs.readFileSync("public/captures/result-full.png"));
const { width, height, bpp, data } = png;
const at = (x, y) => { const i = (y * width + x) * bpp; return [data[i], data[i + 1], data[i + 2]]; };
const x0 = 2210, x1 = 3258;
// panel surface is #111a2b; the page behind is #0b1220 (darker)
let firstPanelRow = -1, longest = 0;
for (let y = 160; y < height; y += 2) {
  let run = 0, best = 0;
  for (let x = x0; x < x1; x += 4) {
    const [r, g, b] = at(x, y);
    if (Math.abs(r - 17) <= 5 && Math.abs(g - 26) <= 5 && Math.abs(b - 43) <= 6) { run += 4; if (run > best) best = run; }
    else run = 0;
  }
  if (best > 180) { firstPanelRow = y; longest = best; break; }
}
console.log("first row that is mostly panel surface: " + firstPanelRow + " device = " + (firstPanelRow / 2).toFixed(1) + " css  (run " + longest + ")");
console.log("bbox says the panel starts at 210 css");