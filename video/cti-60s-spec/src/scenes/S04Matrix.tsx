// Shot 4 | beats 32-43 | 16.0-21.5 s | the three lanes light in order.
//
// v9: preparation (dashed slots, page held at 0.6), then P1, P2, P3 light one beat
// after another - exactly one lane lit at a time - then a 1.04 drift and a static
// hold. No rotation, no translateZ anywhere.

import { AbsoluteFill, useCurrentFrame } from "remotion";
import { colors } from "../theme";
import { inOutExpo, outExpo, seg } from "../lib/anim";
import { box, capture, frameRule, matrixCards, pageHeight, union } from "../assets";
import { Page, World } from "../components/World";
import { BlockLight } from "../components/BlockLight";
import { Caption, Scrim } from "../components/Caption";
import { type } from "../theme";

const grid = box("#matrixGrid");
const cards = matrixCards.slice(0, 3);
const frameBox = grid ?? union(cards) ?? { x: 273, y: 1734, w: 1374, h: 219 };
const fit = frameRule(frameBox, 64);

const PREP = 15;
const CELL_AT = (i: number) => PREP + i * 30;
const DIM_LEN = 14;       // the previous lane falls back to 0.18 over these frames

/**
 * Cumulative: once a lane has lit it stays lit - P1, then P1+P2, then P1+P2+P3. The
 * earlier version took the light back before the next lane lit, which read as "only
 * one of these matters at a time", the opposite of what the shot is saying.
 */
const litAt = (f: number, i: number): number => seg(f, [CELL_AT(i), CELL_AT(i) + 10], [0, 1], outExpo);

export const S04Matrix: React.FC = () => {
  const f = useCurrentFrame();
  const drift = seg(f, [125, 155], [0, 0.04], inOutExpo);
  const cam = { ...fit, z: fit.z * (1 + drift) };
  const dim = 0.6 * (1 - seg(f, [PREP, PREP + 30], [0, 1], outExpo));
  const lit = (i: number) => litAt(f, i);

  return (
    <>
    <World cam={cam}>
      <div style={{ opacity: 0.38 }}>
        <Page src={capture("overview-full.png")} height={pageHeight("overview")} />
      </div>
      {cards.length > 0
        ? cards.map((card, i) => (
            <BlockLight
              key={i}
              src={capture("matrix-card-" + String(i + 1).padStart(2, "0") + ".png")}
              box={card}
              lit={lit(i)}
              frame={f}
              at={CELL_AT(i)}
              particles={12}
              zIndex={12 + i}
            />
          ))
        : (
            <BlockLight src={capture("matrix-panel.png")} box={frameBox} lit={lit(0)} frame={f} at={CELL_AT(0)} particles={14} />
          )}
    </World>
    <AbsoluteFill style={{ background: colors.bg, opacity: dim, pointerEvents: "none" }} />
    <Scrim height={300} strength={0.9} />
    <Caption text="根據嚴重程度 分成P1~P3" at={50} frame={f} size={type.h2} />
    </>
  );
};