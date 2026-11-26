// Shot 7 | beats 54-66 | 27.0-33.0 s | "查看全部" and the full corpus.
// Card: rhythm/speed-ramp-freeze. The strip is ten real screenshots of the
// table scroller, stacked and translated: nothing scrolls in the browser, the
// film moves the strip (SPEC 7: zero scroll). Each four-beat group ends in a
// micro-pause, and the blur is tied to the actual per-frame speed.

import { useCurrentFrame } from "remotion";
import { colors, fonts, type } from "../theme";
import { inOutCubic, inOutExpo, seg } from "../lib/anim";
import { authored } from "../timing";
import { box, capture, DATA, pageHeight, patch } from "../assets";
import { Page, World } from "../components/World";
import { Caption, Scrim } from "../components/Caption";

const table = box("#patchSection") ?? { x: 120, y: 320, w: 1680, h: 640 };
const body = box("strip") ?? box("#patchBody") ?? { x: table.x + 24, y: table.y + 190, w: table.w - 48, h: 380 };

// the capture holds ten slices; using seven of them halves the travel per frame,
// which is what actually makes the CVE text readable while the strip moves
const SEGMENTS = Math.min(7, Math.max(2, (DATA.strip && DATA.strip.segments) || 10));
const MOVE = 18;                       // authored frames per slice move (was 11)
const STEP = 25;                       // authored frames per slice, move + pause
const STRIDE = Math.max(120, Math.round(body.h));
// the window shows part of one slice, so the page is still readable around it
const WINDOW = Math.min(STRIDE, 1120);

const TRAVEL = Math.max(1, SEGMENTS * STRIDE - 1120);

const offsetAt = (f: number): number => {
  let y = 0;
  for (let k = 0; k < SEGMENTS; k++) {
    const start = 4 + k * STEP;
    y += seg(f, [start, start + MOVE], [0, 1], inOutCubic);
  }
  // normalise: the last slice must end exactly at the bottom of the window
  return (y / SEGMENTS) * TRAVEL;
};

export const S07Sweep: React.FC = () => {
  const f = authored(useCurrentFrame(), "s07");
  const pageH = pageHeight("patch");

  const z = seg(f, [0, 40], [1.3, 1.1], inOutExpo) + seg(f, [110, 180], [0, 0.08], inOutExpo);
  const cam = { x: body.x + body.w / 2, y: body.y + body.h / 2, z };

  const y = offsetAt(f);
  const speed = Math.abs(y - offsetAt(Math.max(0, f - 1)));
  // 9 px was a stain, not speed: at this scale anything over ~3.5 px turns the
  // CVE column into a smear. The wash follows the same cap so it cannot out-run it.
  const blur = Math.min(1.2, speed / 40);

  return (
    <>
    <World cam={cam}>
      <Page src={capture("patch-full.png")} height={pageH} />

      {/* the strip window sits exactly on the table body */}
      <div
        style={{
          position: "absolute",
          left: body.x, top: body.y, width: body.w, height: WINDOW,
          overflow: "hidden",
          background: colors.panel,
          boxShadow: `0 0 0 1px ${colors.line}`,
        }}
      >
        <div style={{ position: "absolute", left: 0, top: -y, width: body.w, filter: blur > 0.4 ? `blur(${blur}px)` : undefined }}>
          {Array.from({ length: SEGMENTS }).map((_, i) => (
            <img
              key={i}
              src={capture("strip-" + String(i).padStart(2, "0") + ".png")}
              style={{ display: "block", width: body.w, height: STRIDE }}
            />
          ))}
        </div>
        {/* the scan wash that sells the speed */}
        <div
          style={{
            position: "absolute", inset: 0,
            background: `linear-gradient(to bottom, ${colors.cyan}00, ${colors.cyan}18 45%, ${colors.cyan}00)`,
            opacity: Math.min(0.45, blur / 10),
          }}
        />
      </div>

    </World>
    <Scrim height={400} strength={0.94} />
    <Caption text={COUNT_LINE} at={20} frame={f} size={type.h2} />
    </>
  );
};

const COUNT_LINE = (() => {
  const n = patch.expandedRows || patch.rows;
  return n ? "全量 " + n + " 筆逐條掃過" : "查看全部 · 全量掃過";
})();