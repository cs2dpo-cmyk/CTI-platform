// Caption - the one text move used by every scene: rise 18px, fade, outExpo.
//
// SPEC 6 fixes a single entrance curve for text and the skill asks for one text
// move repeated rather than a new trick per scene. `Scrim` is the dark wash
// that keeps the words readable over a busy page without a visible slab.

import { colors, fonts, grid, type } from "../theme";
import { enter, exit } from "../lib/anim";

export const Scrim: React.FC<{ from?: "bottom" | "top"; height?: number; strength?: number }> = ({
  from = "bottom",
  height = 420,
  strength = 0.94,
}) => (
  <div
    style={{
      position: "absolute",
      left: 0,
      right: 0,
      height,
      ...(from === "bottom" ? { bottom: 0 } : { top: 0 }),
      background:
        from === "bottom"
          ? `linear-gradient(to top, rgba(11, 18, 32, 0.97) 0%, rgba(11, 18, 32, ${strength}) 34%, rgba(11, 18, 32, 0.55) 68%, transparent 100%)`
          : `linear-gradient(to bottom, rgba(11, 18, 32, 0.97) 0%, rgba(11, 18, 32, ${strength}) 34%, rgba(11, 18, 32, 0.55) 68%, transparent 100%)`,
      pointerEvents: "none",
    }}
  />
);

export const Caption: React.FC<{
  text: string;
  at: number;
  frame: number;
  size?: number;
  mono?: boolean;
  outAt?: number;
  style?: React.CSSProperties;
}> = ({ text, at, frame, size = type.h2, mono = false, outAt, style }) => {
  const inn = enter(frame, at, 15);
  const outp = outAt === undefined ? 1 : exit(frame, outAt, 8);
  const opacity = inn * outp;
  if (opacity <= 0.001) return null;
  return (
  <div
    style={{
      position: "absolute",
      left: grid.marginX,
      bottom: grid.marginY + 40,
      maxWidth: 1320,
      opacity,
      transform: `translateY(${(1 - inn) * 18}px)`,
      fontFamily: mono ? fonts.mono : fonts.display,
      fontSize: size,
      lineHeight: 1.22,
      letterSpacing: mono ? "0.01em" : "-0.01em",
      color: colors.ink,
      textShadow: "0 2px 24px rgba(5, 10, 18, 0.8)",
      ...style,
    }}
  >
    {text}
  </div>
  );
};

/** A small mono label with a cyan tick - the only accent allowed on a label. */
export const Tick: React.FC<{ text: string; at: number; frame: number; outAt?: number; left?: number; top?: number }> = ({
  text, at, frame, outAt, left = grid.marginX, top = grid.marginY,
}) => {
  const inn = enter(frame, at, 12);
  if (inn <= 0.001) return null;
  return (
    <div style={{ position: "absolute", left, top, display: "flex", alignItems: "center", gap: 12, opacity: inn }}>
      <span style={{ width: 28, height: 2, background: colors.cyan, boxShadow: `0 0 12px ${colors.cyan}` }} />
      <span style={{ fontFamily: fonts.mono, fontSize: type.micro, letterSpacing: "0.18em", color: colors.ink, textTransform: "uppercase" }}>
        {text}
      </span>
    </div>
  );
};