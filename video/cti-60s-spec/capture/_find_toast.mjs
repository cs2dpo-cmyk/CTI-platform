import fs from "node:fs";
import { decode } from "./png.mjs";

// the toast carries a green check; scan the bottom-right of the result capture for
// greenish pixels and report the box they span. Measuring beats guessing a mask.
const img = decode(fs.readFileSync("public/captures/result-full.png"));
const isGreen = (r, g, b) => g > 150 && g > r + 60 && g > b + 40;
let x0 = 1e9, y0 = 1e9, x1 = -1, y1 = -1, hits = 0;
for (let y = Math.floor(img.height * 0.5); y < img.height; y++) {
  for (let x = Math.floor(img.width * 0.6); x < img.width; x++) {
    const i = (y * img.width + x) * img.bpp;
    if (isGreen(img.data[i], img.data[i + 1], img.data[i + 2])) {
      hits++;
      if (x < x0) x0 = x; if (x > x1) x1 = x;
      if (y < y0) y0 = y; if (y > y1) y1 = y;
    }
  }
}
console.log("capture:", img.width + "x" + img.height, "| green pixels:", hits);
if (hits) console.log("green bbox (device px):", x0 + "," + y0, "->", x1 + "," + y1);
if (hits) console.log("green bbox (css px):", (x0 / 2).toFixed(1) + "," + (y0 / 2).toFixed(1), "->", (x1 / 2).toFixed(1) + "," + (y1 / 2).toFixed(1));
