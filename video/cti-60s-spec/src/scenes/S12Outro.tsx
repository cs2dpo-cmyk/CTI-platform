// Shot 12 | beats 123-130 | 61.5-65.0 s | the close.
//
// v9.1: the lead word is back to the card's mechanics, because the first pass had the
// slide going the wrong way: translateX ran 0 -> -100 px, which pushed "P1" into
// "先修" and then swallowed it (the ending read "先修 ，其餘排程"). Three corrections:
//
//   1. the offset starts at slideDistance and returns to 0 - the lead word lands in
//      its own slot, not 100 px to the left of it;
//   2. the transform lives on the LINE, with transform-origin at the lead word's
//      centre and the baseline - scaling a span about its own left edge can never
//      centre it, it just grows to the right;
//   3. all three values are measured at mount behind delayRender, never estimated:
//      line width, lead centre, baseline (from a zero-size inline-block ruler).
//
// The push-in, the shared ZOOM_EASE for shrink+slide, the lift with the subline in the
// same window and the 1.02 hold with no fade are unchanged from v9.

import { AbsoluteFill, continueRender, delayRender, Easing, useCurrentFrame } from "remotion";
import { useEffect, useRef, useState } from "react";
import { colors, fonts, type } from "../theme";
import { seg } from "../lib/anim";
import { COPY } from "../assets";

const ZOOM_EASE = Easing.bezier(0.5, 0, 0.05, 1);
const HOLD_IN = Easing.bezier(0.25, 1, 0.5, 1);
const OUT_CUBIC = Easing.out(Easing.cubic);

const INITIAL = 3.3;          // 3.3 x 72 px = 238 px: big enough to fill the frame
const HEAD = "先修";
const LEAD = "P1";
const TAIL = "，其餘排程";

type Measured = { ratio: number; base: number; slide: number };

const FALLBACK: Measured = { ratio: 0.34, base: 0, slide: 300 };

export const S12Outro: React.FC = () => {
  const f = useCurrentFrame();
  const lineRef = useRef<HTMLDivElement | null>(null);
  const leadRef = useRef<HTMLSpanElement | null>(null);
  const rulerRef = useRef<HTMLSpanElement | null>(null);
  const [m, setM] = useState<Measured | null>(null);
  const [handle] = useState(() => delayRender("measure the lead word"));

  useEffect(() => {
    if (m) return;
    let cancelled = false;
    const run = async () => {
      try {
        await (document as any).fonts?.ready;
      } catch {
        /* fonts API missing: measure anyway */
      }
      if (cancelled) return;
      const line = lineRef.current;
      const lead = leadRef.current;
      const ruler = rulerRef.current;
      if (!line || !lead || !ruler) {
        continueRender(handle);
        return;
      }
      const lineW = line.offsetWidth;
      const leadC = lead.offsetLeft + lead.offsetWidth / 2;
      const ratio = lineW > 0 ? leadC / lineW : FALLBACK.ratio;
      setM({ ratio, base: ruler.offsetTop, slide: lineW * (0.5 - ratio) });
      continueRender(handle);
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [m, handle]);

  const pushIn = seg(f, [0, 15], [1, 1.06], HOLD_IN);
  const shrink = seg(f, [15, 27], [0, 1], ZOOM_EASE);
  const slide = seg(f, [15, 45], [0, 1], ZOOM_EASE);
  const leadScale = INITIAL * pushIn * (1 - shrink) + shrink;
  const shift = (m ?? FALLBACK).slide * (1 - slide);

  const headIn = shrink;
  const tailIn = seg(f, [20, 32], [0, 1], OUT_CUBIC);
  const liftIn = seg(f, [45, 60], [0, -56], OUT_CUBIC);
  const subIn = seg(f, [45, 60], [0, 1], OUT_CUBIC);
  const drift = seg(f, [92, 105], [1, 1.02], OUT_CUBIC);

  const measured = m !== null;

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg }}>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <div
          style={{
            transform: "translateY(" + liftIn + "px) scale(" + drift + ")",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            visibility: measured ? "visible" : "hidden",
          }}
        >
          <div
            ref={lineRef}
            style={{
              display: "flex",
              alignItems: "baseline",
              fontFamily: fonts.display,
              fontSize: type.h1,
              fontWeight: 600,
              letterSpacing: "-0.03em",
              lineHeight: 1.1,
              color: colors.ink,
              whiteSpace: "nowrap",
              transform: "translateX(" + shift + "px) scale(" + leadScale + ")",
              // the two numbers this whole shot depends on
              transformOrigin: (m ?? FALLBACK).ratio * 100 + "% " + (m ?? FALLBACK).base + "px",
            }}
          >
            <span style={{ display: "inline-block", opacity: headIn, marginRight: "0.22em" }}>{HEAD}</span>
            <span ref={leadRef} style={{ display: "inline-block", color: colors.p1, fontWeight: 600 }}>{LEAD}</span>
            <span style={{ display: "inline-block", opacity: tailIn }}>{TAIL}</span>
            {/* the ruler: a zero-size inline-block whose offsetTop is the baseline */}
            <span ref={rulerRef} style={{ display: "inline-block", width: 0, height: 0 }} />
          </div>

          <div
            style={{
              marginTop: 26,
              fontFamily: fonts.mono,
              fontSize: type.body,
              color: colors.inkSoft,
              opacity: subIn * 0.95,
            }}
          >
            {COPY.wordmark + " · " + COPY.url}
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
