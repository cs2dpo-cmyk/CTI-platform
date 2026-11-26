// Shot 6 | beats 32-41 | 16.0-20.5 s | the patch priority table.
// Cards: ui-entrance/deck-deal-flyin + data/gauge-readout-moves +
// effects/impact-feedback. v2 dropped the fan: three rows leave the table, stack
// vertically in reverse order, then slide back into their own rows - so the shot
// shows sorting rather than a card trick. The dolly goes to 1.55 and the cards
// carry velocity blur while they travel.

import { Fragment } from "react";
import { useCurrentFrame } from "remotion";
import { camera, colors, type } from "../theme";
import { enter, inOutExpo, outExpo, seg, velBlur } from "../lib/anim";
import { box, capture, pageHeight, patchRows } from "../assets";
import { Page, World } from "../components/World";
import { Caption, Scrim } from "../components/Caption";
import { LiftParticles } from "../components/LiftParticles";

const table = box("#patchSection") ?? { x: 120, y: 320, w: 1680, h: 640 };

const LIFT_AT = 8;
const liftAt = (f: number) => seg(f, [LIFT_AT, LIFT_AT + 16], [0, 1], outExpo);
const stackAt = (f: number) => seg(f, [26, 42], [0, 1], outExpo);
const sortAt = (f: number) => seg(f, [52, 70], [0, 1], inOutExpo);

export const S06PatchDeck: React.FC = () => {
  const f = useCurrentFrame();
  const pageH = pageHeight("patch");

  const zPush = seg(f, [78, 100], [0, 0.55], inOutExpo) + seg(f, [100, 135], [0, 0.04], inOutExpo);
  const cam = { x: table.x + table.w / 2, y: table.y + 260, z: Math.min(camera.maxZoom, 1.0 + zPush) };

  const lift = liftAt(f);
  const stack = stackAt(f);
  const sort = sortAt(f);

  const centre = { x: table.x + table.w / 2, y: table.y + 210 };

  // where a card sits when stacked: reversed order, one row of height apart and
  // lifted up the page so the stack reads as floating, not as a table row
  const slot = (i: number, row: { w: number; h: number }) => ({
    x: centre.x - row.w / 2,
    y: centre.y + (2 - i) * (row.h + 14) - row.h,
  });

  return (
    <>
    <World cam={cam}>
      <Page src={capture("patch-full.png")} height={pageH} />

      {patchRows.slice(0, 3).map((row, i) => {
        const src = capture("patch-row-" + String(i + 1).padStart(2, "0") + ".png");
        const s = slot(i, row);
        // row -> stack slot (reversed) -> own row again
        const x = row.x + (s.x - row.x) * stack + (row.x - (row.x + (s.x - row.x) * stack)) * sort;
        const stackY = row.y - 26 + (s.y - (row.y - 26)) * stack;
        const y = stackY + (row.y - stackY) * sort;
        const liftY = -26 * lift * (1 - sort);

        const path = (g: number) => {
          const st = stackAt(g), so = sortAt(g);
          const sy = row.y - 26 + (s.y - (row.y - 26)) * st;
          return sy + (row.y - sy) * so;
        };
        const blur = velBlur(path, f, 0.7, 2.5);

        return (
          <Fragment key={i}>
            <div
              style={{
                position: "absolute",
                left: row.x, top: row.y, width: row.w, height: row.h,
                background: colors.bg,
                border: `1px solid ${colors.line}`,
                borderRadius: 4,
                opacity: lift * 0.92 * (1 - stack * 0.35),
                zIndex: 9,
              }}
            />
            <img
              src={src}
              style={{
                position: "absolute",
                left: x,
                top: y + liftY,
                width: row.w,
                height: row.h,
                background: colors.panel,
                borderRadius: 4,
                transform: `scale(${1 + 0.02 * stack * (1 - sort)})`,
                transformOrigin: "center",
                filter: blur > 0.15 ? `blur(${blur}px)` : undefined,
                opacity: Math.max(0.001, enter(f, LIFT_AT + i * 3, 10, outExpo)),
                boxShadow: `0 ${6 + 16 * stack * (1 - sort)}px ${12 + 38 * stack * (1 - sort)}px rgba(0,0,0,${0.35 + 0.3 * stack * (1 - sort)}), 0 0 0 1px ${colors.line}, 0 0 ${22 * stack * (1 - sort)}px ${colors.cyan}26`,
                zIndex: 10 + i,
              }}
            />
            <LiftParticles at={LIFT_AT + 6 + i * 3} box={row} count={14} rise={52} frame={f} />
          </Fragment>
        );
      })}

    </World>
    <Scrim height={400} strength={0.93} />
    <Caption text="EPSS × KEV 決定順序，不是 CVSS" at={72} frame={f} size={type.h2} />
    </>
  );
};
