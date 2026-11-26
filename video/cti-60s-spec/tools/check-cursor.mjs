import { decode } from "../capture/png.mjs";
import fs from "node:fs";
const png = decode(fs.readFileSync("out/stills/17-diag-s10-state11.png"));
const { width, height, bpp, data } = png;
const at = (x, y) => { const i = (y * width + x) * bpp; return [data[i], data[i + 1], data[i + 2]]; };
// expected, from the component math: z=2.0, camX = frameRight - 480, camY = pointer.y + 30
const formBox = { x: 273, y: 194, w: 792.328125, h: 627.5 };
const btn = { x: 879.328125, y: 824.5, w: 168, h: 34 };
const resultLeft = 1105.328125;
const frameRight = Math.min(formBox.x + formBox.w + 10, resultLeft - 12);
const z = 2.0;
const camX = frameRight - 960 / z;
const camY = (btn.y + btn.h / 2) + 30;
const sx = (x) => (x - camX) * z + 960;
const sy = (y) => (y - camY) * z + 540;
console.log("predicted button rect: x " + sx(btn.x).toFixed(0) + ".." + sx(btn.x + btn.w).toFixed(0) + "  y " + sy(btn.y).toFixed(0) + ".." + sy(btn.y + btn.h).toFixed(0));
console.log("predicted cursor centre: " + sx(btn.x + btn.w / 2).toFixed(0) + ", " + sy(btn.y + btn.h / 2).toFixed(0));
// find the drawn arrow: near-white pixels (ink #dbe6f5) in the lower middle-right
let n = 0, cx = 0, cy = 0, minX = 1e9, maxX = 0, minY = 1e9, maxY = 0;
for (let y = 380; y < 620; y++) {
  for (let x = 1500; x < 1900; x++) {
    const [r, g, b] = at(x, y);
    if (r > 200 && g > 210 && b > 225) {
      n++; cx += x; cy += y;
      if (x < minX) minX = x; if (x > maxX) maxX = x;
      if (y < minY) minY = y; if (y > maxY) maxY = y;
    }
  }
}
if (n === 0) { console.log("FAIL: no arrow pixels found near the button"); }
else {
  console.log("arrow pixels " + n + "  bbox x " + minX + ".." + maxX + "  y " + minY + ".." + maxY + "  centroid " + (cx / n).toFixed(0) + ", " + (cy / n).toFixed(0));
  const cxp = sx(btn.x + btn.w / 2), cyp = sy(btn.y + btn.h / 2);
  const dx = Math.abs(cx / n - cxp), dy = Math.abs(cy / n - cyp);
  console.log("offset from the button centre: dx " + dx.toFixed(1) + " px, dy " + dy.toFixed(1) + " px");
  const inside = minX >= sx(btn.x) - 4 && maxX <= sx(btn.x + btn.w) + 4 && minY >= sy(btn.y) - 4 && maxY <= sy(btn.y + btn.h) + 8;
  console.log(inside ? "PASS: the arrow sits on the button" : "CHECK: the arrow extends past the button rect");
}