// png.mjs - a 90-line PNG reader so the capture can assert on its own output.
//
// Why not a package: the two assertions the film needs are "is this the size of
// the box I measured" and "did anything from a neighbour leak into the corners".
// Reading IHDR answers the first; unfiltering the scanlines answers the second.
// Chrome writes 8-bit RGB/RGBA, non-interlaced, so the general PNG spec is not
// needed - and anything outside that subset throws instead of mis-reading.

import zlib from "node:zlib";

const SIG = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

const read = (buf) => {
  if (!buf.subarray(0, 8).equals(SIG)) throw new Error("not a png");
  let off = 8;
  const chunks = [];
  while (off < buf.length) {
    const len = buf.readUInt32BE(off);
    const type = buf.toString("ascii", off + 4, off + 8);
    chunks.push({ type, data: buf.subarray(off + 8, off + 8 + len) });
    off += 12 + len;
    if (type === "IEND") break;
  }
  return chunks;
};

export const pngSize = (buf) => {
  const chunks = read(buf);
  const ihdr = chunks.find((c) => c.type === "IHDR");
  if (!ihdr) throw new Error("no IHDR");
  return { width: ihdr.data.readUInt32BE(0), height: ihdr.data.readUInt32BE(4) };
};

/** Decode to { width, height, bpp, data } - RGBA/RGB 8-bit, non-interlaced. */
export const decode = (buf) => {
  const chunks = read(buf);
  const ihdr = chunks.find((c) => c.type === "IHDR");
  if (!ihdr) throw new Error("no IHDR");
  const width = ihdr.data.readUInt32BE(0);
  const height = ihdr.data.readUInt32BE(4);
  const bitDepth = ihdr.data.readUInt8(8);
  const colorType = ihdr.data.readUInt8(9);
  const interlace = ihdr.data.readUInt8(12);
  if (bitDepth !== 8) throw new Error("unsupported bit depth " + bitDepth);
  if (interlace !== 0) throw new Error("interlaced png is not supported");
  if (colorType !== 2 && colorType !== 6) throw new Error("unsupported colour type " + colorType);
  const bpp = colorType === 6 ? 4 : 3;
  const idat = Buffer.concat(chunks.filter((c) => c.type === "IDAT").map((c) => c.data));
  if (!idat.length) throw new Error("no IDAT");
  const raw = zlib.inflateSync(idat);
  const stride = width * bpp;
  const out = Buffer.alloc(stride * height);

  const paeth = (a, b, c) => {
    const p = a + b - c;
    const pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c);
    return pa <= pb && pa <= pc ? a : pb <= pc ? b : c;
  };

  for (let y = 0; y < height; y++) {
    const filter = raw[y * (stride + 1)];
    const src = raw.subarray(y * (stride + 1) + 1, y * (stride + 1) + 1 + stride);
    const dst = out.subarray(y * stride, y * stride + stride);
    const up = y > 0 ? out.subarray((y - 1) * stride, y * stride) : null;
    for (let x = 0; x < stride; x++) {
      const a = x >= bpp ? dst[x - bpp] : 0;
      const b = up ? up[x] : 0;
      const c = up && x >= bpp ? up[x - bpp] : 0;
      const v = src[x];
      dst[x] = filter === 0 ? v
        : filter === 1 ? (v + a) & 0xff
        : filter === 2 ? (v + b) & 0xff
        : filter === 3 ? (v + ((a + b) >> 1)) & 0xff
        : filter === 4 ? (v + paeth(a, b, c)) & 0xff
        : (() => { throw new Error("bad filter " + filter); })();
    }
  }
  return { width, height, bpp, data: out };
};

/**
 * The four corner blocks, as { r, g, b, a } means over an n x n square.
 *
 * A block cut-out is expected to be transparent outside its rounded corners (the
 * capture runs with omitBackground) or to be the page background. Anything else
 * means a neighbour's pixels are inside the file - the one thing element
 * screenshots are supposed to make impossible, so it is worth asserting.
 */
export const cornerMean = (buf, n = 6) => {
  const { width, height, bpp, data } = decode(buf);
  const at = (x0, y0) => {
    let r = 0, g = 0, b = 0, a = 0, k = 0;
    for (let y = y0; y < Math.min(y0 + n, height); y++) {
      for (let x = x0; x < Math.min(x0 + n, width); x++) {
        const i = (y * width + x) * bpp;
        r += data[i]; g += data[i + 1]; b += data[i + 2];
        a += bpp === 4 ? data[i + 3] : 255;
        k++;
      }
    }
    return { r: Math.round(r / k), g: Math.round(g / k), b: Math.round(b / k), a: Math.round(a / k) };
  };
  return {
    tl: at(0, 0),
    tr: at(width - n, 0),
    bl: at(0, height - n),
    br: at(width - n, height - n),
  };
};
