// Shot 1 | beats 0-2 | 0.0-1.0 s | the wordmark.
// Card: opening/brand-ink-open. v2 re-authored this shot natively for 30 frames:
// the crosshair is four frames, the word presses in one frame per glyph, the
// kicker lands by frame 20, and the block lifts on frame 23. Nothing types for a
// whole second any more.

import { AbsoluteFill, useCurrentFrame } from "remotion";
import { colors, fonts, type } from "../theme";
import { enter, exit, outExpo, seg } from "../lib/anim";
import { COPY } from "../assets";
import { authored } from "../timing";

const WORD = COPY.wordmark;
const KICKER = COPY.subtitle;

export const S01Wordmark: React.FC = () => {
  // v8: the same 30-frame choreography, played over 60 frames
  const f = authored(useCurrentFrame(), "s01", 30);

  const cam = seg(f, [0, 30], [1, 1.08], outExpo);
  const vLine = seg(f, [0, 4], [0, 1], outExpo);
  const hLine = seg(f, [3, 7], [0, 1], outExpo);
  const crossFade = 1 - seg(f, [7, 13], [0, 1], outExpo);

  const lift = seg(f, [23, 30], [0, 1], outExpo);
  const wordOpacity = exit(f, 23, 6) * enter(f, 1, 5);

  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <div
        style={{
          transform: `scale(${cam}) translateY(${-lift * 40}px)`,
          opacity: 1 - lift * 0.9,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
        }}
      >
        <div style={{ position: "absolute", width: 520, height: 320, opacity: crossFade }}>
          <div
            style={{
              position: "absolute", left: "50%", top: 0, bottom: 0, width: 1,
              background: `linear-gradient(to bottom, transparent, ${colors.cyan}, transparent)`,
              transform: `scaleY(${vLine})`, transformOrigin: "center",
              boxShadow: `0 0 14px ${colors.cyan}`,
            }}
          />
          <div
            style={{
              position: "absolute", top: "50%", left: 0, right: 0, height: 1,
              background: `linear-gradient(to right, transparent, ${colors.cyan}, transparent)`,
              transform: `scaleX(${hLine})`, transformOrigin: "center",
              boxShadow: `0 0 14px ${colors.cyan}`,
            }}
          />
        </div>

        <div style={{ display: "flex", flexDirection: "row", opacity: wordOpacity, perspective: 900 }}>
          {[...WORD].map((ch, i) => {
            const t = enter(f, 1 + i, 7, outExpo);
            return (
              <span
                key={i}
                style={{
                  fontFamily: fonts.display,
                  fontSize: type.h1,
                  fontWeight: 600,
                  letterSpacing: "-0.02em",
                  lineHeight: 1.25,
                  color: colors.ink,
                  display: "inline-block",
                  transform: `translateY(${(1 - t) * 26}px) scale(${1.35 - 0.35 * t})`,
                  transformOrigin: "center bottom",
                  filter: `blur(${(1 - t) * 5}px)`,
                  opacity: t,
                }}
              >
                {ch === " " ? "\u00a0" : ch}
              </span>
            );
          })}
        </div>

        <div
          style={{
            marginTop: 26,
            height: 1,
            width: 520 * seg(f, [7, 14], [0, 1], outExpo),
            background: `linear-gradient(to right, transparent, ${colors.cyan}88, transparent)`,
          }}
        />

        <div
          style={{
            marginTop: 22,
            fontFamily: fonts.mono,
            fontSize: type.body,
            color: colors.inkSoft,
            letterSpacing: "0.08em",
            whiteSpace: "pre",
          }}
        >
          {[...KICKER].map((ch, i) => (
            <span key={i} style={{ opacity: f >= 9 + i * 0.35 ? 1 : 0 }}>{ch}</span>
          ))}
          <span
            style={{
              display: "inline-block",
              width: 10,
              height: 20,
              marginLeft: 4,
              verticalAlign: "-3px",
              background: colors.cyan,
              opacity: f < 30 && Math.floor(f / 2) % 2 === 0 ? 1 : 0,
            }}
          />
        </div>
      </div>
    </AbsoluteFill>
  );
};
