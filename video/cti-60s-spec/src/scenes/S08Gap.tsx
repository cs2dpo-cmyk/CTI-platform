// Shot 8 | beats 65-72 | 32.5-36.0 s | known-exploited but not in the KEV feed.
//
// v9.2: replaced the five-band offset (which shifted rows that were already baked
// into the screenshot - a fake entrance) with row-embed. Five rows fall in from
// above, tip flat with rotateX and seat into their own slots, each knocking a 2px
// cyan seam out of its bottom edge. The rest of the table stays at 0.3 brightness,
// so the five that land read as the new ones.
//
// The rows are texture slices of gap-panel.png (backgroundPosition offset), never
// redrawn - redrawn rows show a visible font-rendering difference from the page.
// Each slot is patched with the panel colour first, or the baked-in row shows
// through underneath the falling copy (the card calls that 重影).

import { AbsoluteFill, Easing, useCurrentFrame } from "remotion";
import { colors, type } from "../theme";
import { seg } from "../lib/anim";
import { box, capture, frameRule } from "../assets";
import { World } from "../components/World";
import { Caption, Scrim } from "../components/Caption";

const panel = box("#gapSection") ?? { x: 272, y: 853, w: 1376, h: 766 };
const body = box("#gapBody") ?? { x: 273, y: 1028, w: 1374, h: 552 };

// Measured from gap-panel.png by scanning for the row separators: the first data
// row starts at panel-local y 175 (== #gapBody.y) and the pitch is 46 css px. The
// 61 px in data.json belongs to the PATCH table, not this one - using it drifted
// every slice by 15 px per row and produced a ghosted double table.
const ROW_H = 46;
const N = 5;
const rows = Array.from({ length: N }, (_, i) => ({
  x: body.x, y: body.y + i * ROW_H, w: body.w, h: ROW_H,
}));

// frame the five rows plus the panel title above them
const frameBox = { x: body.x - 36, y: panel.y + 8, w: body.w + 72, h: ROW_H * N + 230 };
const fit = frameRule(frameBox, 40);

const CUE = (i: number) => 8 + i * 15;          // one row per beat
const LAND = (i: number) => CUE(i) + 12;        // 12-frame fall
const FLIGHT = Easing.bezier(0.5, 0, 0.8, 0.75); // still moving fast at the end
const SEAM_EASE = Easing.out(Easing.cubic);

export const S08Gap: React.FC = () => {
  const f = useCurrentFrame();

  // the camera slides down the table and pushes a little while the rows fall
  const drift = seg(f, [0, 100], [0, 1], Easing.inOut(Easing.exp));
  const cam = { x: fit.x, y: fit.y + 34 * drift, z: fit.z * (1 + 0.06 * drift) };

  const prep = seg(f, [0, 8], [0, 1]);

  return (
    <>
    <World cam={cam}>
      {/* the whole table, held back so only the five landing rows read as new */}
      <img
        src={capture("gap-panel.png")}
        style={{
          position: "absolute", left: panel.x, top: panel.y, width: panel.w, height: panel.h,
          filter: "brightness(0.3)",
        }}
      />

      {rows.map((r, i) => {
        const air = 1 - seg(f, [CUE(i), LAND(i)], [0, 1], FLIGHT);
        // nothing is drawn before its cue: a row sitting 120 px above its slot at
        // 25% opacity reads as a ghost of the row that already landed there
        const started = f >= CUE(i);
        const fadeIn = Math.min(1, (f - CUE(i)) / 3);
        const press = seg(f, [LAND(i), LAND(i) + 2], [0, 1]) * (1 - seg(f, [LAND(i) + 2, LAND(i) + 10], [0, 1]));
        const scale = 0.995 + 0.065 * air + 0.005 * press;
        const seam = seg(f, [LAND(i), LAND(i) + 5], [0, 1], SEAM_EASE)
          * (1 - seg(f, [LAND(i) + 5, LAND(i) + 13], [0, 1]));

        return (
          <div key={i}>
            {/* the slot: patched with the panel colour so the baked row cannot show
                through, plus a dashed outline until the row seats */}
            {air > 0.01 ? (
              <div
                style={{
                  position: "absolute", left: r.x, top: r.y, width: r.w, height: r.h,
                  background: colors.panel,
                  border: "1px dashed " + colors.line,
                  opacity: Math.min(1, air + 0.2) * prep,
                }}
              />
            ) : null}

            <div
              style={{
                position: "absolute", left: r.x, top: r.y, width: r.w, height: r.h,
                overflow: "hidden",
                perspective: 900,
                transform: "translateY(" + -90 * air + "px) rotateX(" + 16 * air + "deg) scale(" + scale + ")",
                transformOrigin: "center bottom",
                opacity: started ? Math.max(0, fadeIn) * (1 - 0.25 * air) : 0,
              }}
            >
              <img
                src={capture("gap-panel.png")}
                style={{
                  position: "absolute",
                  left: -(r.x - panel.x),
                  top: -(r.y - panel.y),
                  width: panel.w, height: panel.h,
                }}
              />
            </div>

            {/* the seam: 2 px cyan, from the centre outwards, once */}
            {seam > 0.01 ? (
              <div
                style={{
                  position: "absolute",
                  left: r.x + (r.w * (1 - seam)) / 2,
                  top: r.y + r.h - 2,
                  width: r.w * seam,
                  height: 2,
                  background: colors.cyan,
                  boxShadow: "0 0 7px " + colors.cyan,
                  opacity: 1 - Math.max(0, seam - 0.7) / 0.3,
                }}
              />
            ) : null}
          </div>
        );
      })}
    </World>
    <AbsoluteFill style={{ background: colors.bg, opacity: 0.6 * (1 - prep), pointerEvents: "none" }} />
    <Scrim height={300} strength={0.9} />
    {/* at 68, the 15-frame entrance is done by 83 and the caption then holds for 36
        frames to the end of the shot - the extra beat went to the hold, not to the gap
        before it */}
    <Caption text="沒有進情資的名單，也要注意" at={68} frame={f} size={type.h2} />
    </>
  );
};
