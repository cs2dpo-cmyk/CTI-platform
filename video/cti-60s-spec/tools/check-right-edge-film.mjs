import { decode } from "../capture/png.mjs";
import fs from "node:fs";
for (const file of ["out/check9/s10-end.png", "out/check9/s10-mid.png"]) {
  const png = decode(fs.readFileSync(file));
  const { width, height, bpp, data } = png;
  const cols = [];
  for (let x = width - 400; x < width; x++) {
    let n = 0;
    for (let y = 0; y < height; y += 3) {
      const i = (y * width + x) * bpp;
      const r = data[i], g = data[i + 1], b = data[i + 2];
      if (Math.abs(r - 43) <= 14 && Math.abs(g - 60) <= 14 && Math.abs(b - 90) <= 14) n++;
    }
    if (n > 40) cols.push({ x, n });
  }
  console.log(file);
  for (const c of cols) console.log("   x=" + c.x + "  n=" + c.n + (c.n > 200 ? "   <- spans the frame height" : ""));
}