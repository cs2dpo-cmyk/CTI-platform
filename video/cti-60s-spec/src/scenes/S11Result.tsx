// Shot 11 | beats 110-123 | 55.0-61.5 s | the result.
//
// v8 changed the camera, not the panel: z is pinned at 1.70 for the whole shot and
// the camera slides straight down the panel from the title to the last play step.
// The seven light stops are no longer their own timeline - each frame is lit when
// the camera reaches it, so only one thing moves at a time. Every highlight is
// clipped to the panel box, which is what put a cyan frame across the score ring
// and cut the P1 badge in the previous cut.

import { AbsoluteFill, useCurrentFrame } from "remotion";
import { colors, fonts, grid, type } from "../theme";
import { enter, outExpo, seg } from "../lib/anim";
import { box, capture, pageHeight, result } from "../assets";
import { Page, World } from "../components/World";

const panel = box("result:#assessResult") ?? { x: 1105.3, y: 210, w: 523.7, h: 1057.8 };
const STOP_KEYS = [
  "result:#scoreValue", "result:#priorityBadge", "result:#resultHeadline",
  "result:#resultLevel", "result:#resultSummary", "result:#factorList", "result:#resultPlan",
];

const Z = 1.70;
const VIEW_H = 1080 / Z;               // 635 css px tall at 1.70
const CAM_X = 1920 - 1129 / 2 - 8;
// Headroom above the panel: the box the capture measured and the panel as drawn
// in result-full.png do not agree (measured: the title sits ~58 px higher in the
// image than the box implies). 111 px of headroom puts the panel title inside the
// frame at y ~90 on the first frame instead of on the top edge.
const CAM_Y0 = panel.y - 111 + VIEW_H / 2;
const CAM_Y1 = panel.y + panel.h - VIEW_H / 2 + 40;
const PAN_FROM = 15;                   // beat 1 of the shot
const PAN_TO = 180;                    // beat 12

const HEAD = (() => {
  const n = Number(String(result.score).replace(/[^0-9.]/g, ""));
  return Number.isFinite(n) && n > 0 ? n.toFixed(1) : "99.0";
})();
const META = [result.confidence, result.level].filter(Boolean).join(" · ");

export const S11Result: React.FC = () => {
  const f = useCurrentFrame();
  const pageH = pageHeight("result");

  // a straight, even slide: no easing that would stall, no push at the same time
  const pan = seg(f, [PAN_FROM, PAN_TO], [0, 1]);
  const camY = CAM_Y0 + (CAM_Y1 - CAM_Y0) * pan;
  const cam = { x: CAM_X, y: camY, z: Z };

  // the frame at which the camera reaches a stop, so the light follows the pan
  const frameAtY = (y: number) => PAN_FROM + ((y - CAM_Y0) / (CAM_Y1 - CAM_Y0)) * (PAN_TO - PAN_FROM);

  return (
    <>
    
    {/* The page is hard-clipped at the panel's left edge. A gradient scrim could not
        do this job: to hide the form it has to be opaque past x 548, and that is
        exactly where the panel starts - the amber "執行風險評估" button used to bleed
        through the left column as a washed-out gold block. The line sits 12 px left of
        the panel edge (536, not 548) so the panel keeps its own border and shadow. */}
    <div style={{ position: "absolute", inset: 0, clipPath: "inset(0 0 0 536px)" }}>
    <World cam={cam}>
      <Page src={capture("result-full.png")} height={pageH} />
      {/* No panel cut-out here: the page already carries the result panel, and a
          second copy forced into the same box is a different geometry - it made the
          first frame clip the title while the last frame showed the ring and the
          playbook at the same time, which 1.70x cannot do. One source of geometry. */}

      {/* The site fires a fixed toast after the assessment and it is baked into the
          page capture. Position measured from the capture, not guessed: the green check
          sits at css 1722-1731 x 1039-1046, so the toast box is ~1705..1907 by
          ~1025..1070. The mask is generous because everything right of the panel
          (x > 1629) is empty page background - it cannot hide content. */}
      <div style={{ position: "absolute", left: 1660, top: 995, width: 260, height: 90, background: "#0b1220" }} />

      {STOP_KEYS.map((key) => {
        const b = box(key);
        if (!b) return null;
        // clipped to the panel: a frame drawn 20 px proud of a stop near the edge
        // is exactly what overlapped the ring and cut the badge
        const x0 = Math.max(b.x - 10, panel.x);
        const y0 = Math.max(b.y - 8, panel.y);
        const x1 = Math.min(b.x + b.w + 10, panel.x + panel.w);
        const y1 = Math.min(b.y + b.h + 16, panel.y + panel.h);
        // the playbook sits below the end of the pan, so its light is tied to the
        // last beat rather than to a camera position the shot never reaches
        const at = Math.min(PAN_TO - 6, frameAtY(b.y + b.h / 2));
        const on = seg(f, [at - 2, at + 4], [0, 1], outExpo) * (1 - seg(f, [at + 18, at + 26], [0, 1], outExpo));
        if (on <= 0.01) return null;
        return (
          <div
            key={key}
            style={{
              position: "absolute",
              left: x0, top: y0, width: Math.max(0, x1 - x0), height: Math.max(0, y1 - y0),
              border: "1px solid " + colors.cyan,
              borderRadius: 6,
              boxShadow: "0 0 26px " + colors.cyan + "66, inset 0 0 30px " + colors.cyan + "22",
              opacity: on,
            }}
          />
        );
      })}
    </World>
    </div>

    {/* the left column: solid, so nothing from the form can show through */}
    <div
      style={{
        position: "absolute", left: 0, top: 0, bottom: 0, width: 536,
        background: colors.bg,
        opacity: enter(f, 6, 20, outExpo),
        pointerEvents: "none",
      }}
    />
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div style={{ position: "absolute", left: grid.marginX, top: 250, opacity: enter(f, 8, 18, outExpo) }}>
        <div style={{ fontFamily: fonts.mono, fontSize: type.micro, letterSpacing: "0.2em", color: colors.cyan }}>
          評估結果 · EXPLAINABLE SCORING
        </div>
        <div style={{ fontFamily: fonts.mono, fontSize: type.h1, color: colors.ink, letterSpacing: "-0.03em", marginTop: 14 }}>
          {HEAD}
        </div>
        <div style={{ display: "flex", alignItems: "baseline", gap: 20, marginTop: 10 }}>
          <span style={{ fontFamily: fonts.display, fontSize: type.h2, color: colors.p1 }}>{result.priority}</span>
          <span style={{ fontFamily: fonts.mono, fontSize: type.h3, color: colors.inkSoft }}>{result.sla}</span>
        </div>
        <div style={{ height: 1, width: 420, marginTop: 20, background: "linear-gradient(to right, " + colors.cyan + "aa, transparent)" }} />
        <div style={{ marginTop: 16, fontFamily: fonts.mono, fontSize: type.small, color: colors.inkSoft, lineHeight: 1.5, maxWidth: 400 }}>
          {META}
        </div>
      </div>
    </AbsoluteFill>
    </>
  );
};