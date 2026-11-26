// BlockLight - the overview language from v9: nothing travels, the block lights up
// in place (wall-reveal A). The dark state is 18% opacity sitting 20 px low; the
// light-up runs an accent comet around the block edge for eight frames, pops the
// content out with a back-out overshoot six frames later, throws a glow pulse and
// twelve specks of dust, then anneals to a 0.4 hairline that stays.
//
// No rotateX, no translateZ: the brief forbids mixing a lift into this language.

import { colors } from "../theme";
import { LiftParticles } from "./LiftParticles";

export type BlockBox = { x: number; y: number; w: number; h: number };

export const BlockLight: React.FC<{
  src: string;
  box: BlockBox;
  /** 0 = dark state, 1 = fully lit. Drive it from the beat.
  lit: number; */
  lit: number;
  frame: number;
  /** first frame of the light-up, for the dust. */
  at: number;
  particles?: number;
  zIndex?: number;
}> = ({ src, box, lit, frame, at, particles = 12, zIndex = 10 }) => {
  const t = Math.max(0, Math.min(1, lit));
  const comet = Math.min(1, Math.max(0, (frame - at) / 8));
  const pop = Math.min(1, Math.max(0, (frame - at - 6) / 8));
  const pulse = Math.sin(Math.PI * Math.min(1, comet)) * (t > 0 && t < 1 ? 1 : 0);
  const glow = t * (1 - t) * 4;
  const hairline = pop >= 1 ? 0.4 : 0;

  return (
    <>
      {/* the slot under a block that has not lit yet */}
      {t < 1 ? (
        <div
          style={{
            position: "absolute", left: box.x, top: box.y, width: box.w, height: box.h,
            border: "1px dashed " + colors.line, borderRadius: 6,
            background: "rgba(17,26,43,0.5)",
            opacity: 0.9 * (1 - t),
            zIndex: zIndex - 1,
          }}
        />
      ) : null}

      <img
        src={src}
        style={{
          position: "absolute", left: box.x, top: box.y, width: box.w, height: box.h,
          // No 0.18 base any more: the page behind now carries the card in its dim
          // state, so a second 18%-opacity copy on top of it showed the same number
          // twice, offset by the 20 px dark-state drop. The cut-out only exists once
          // the light starts.
          opacity: Math.max(0, Math.min(1, t)),
          transform: "translateY(" + (20 * (1 - t) + (pop >= 1 ? 0 : -2 * Math.sin(pop * Math.PI))) + "px) scale(" + (0.995 + 0.005 * pop) + ")",
          zIndex,
          filter: glow > 0.02 ? "brightness(" + (1 + 0.18 * glow) + ")" : undefined,
        }}
      />

      {/* the comet: 22% of the perimeter running once, plus its glow */}
      {comet > 0 && comet < 1 ? (
        <svg
          width={box.w} height={box.h}
          style={{ position: "absolute", left: box.x, top: box.y, overflow: "visible", zIndex: zIndex + 1 }}
        >
          {[6, 2.5].map((sw, i) => (
            <rect
              key={i}
              x={1} y={1} width={Math.max(0, box.w - 2)} height={Math.max(0, box.h - 2)} rx={6}
              fill="none"
              stroke={colors.cyan}
              strokeWidth={sw}
              strokeOpacity={i === 0 ? 0.5 * pulse : 0.95}
              pathLength={1}
              strokeDasharray="0.22 0.78"
              strokeDashoffset={1.22 - 1.22 * comet}
              style={{ filter: i === 0 ? "blur(3px)" : undefined }}
            />
          ))}
        </svg>
      ) : null}

      {/* the annealed hairline */}
      {hairline > 0 ? (
        <div
          style={{
            position: "absolute", left: box.x, top: box.y, width: box.w, height: box.h,
            border: "1px solid " + colors.cyan + "66", borderRadius: 6,
            opacity: hairline, zIndex: zIndex + 1,
          }}
        />
      ) : null}

      {t > 0 && t < 1 ? <LiftParticles at={at} box={box} count={particles} rise={40} frame={frame} /> : null}
    </>
  );
};