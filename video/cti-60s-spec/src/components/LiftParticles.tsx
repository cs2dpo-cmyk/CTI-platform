// LiftParticles - the dust a panel kicks up when it floats off the page.
//
// SPEC 5 keeps the accent cyan and forbids full-screen glow, so the particles are
// small, additive, and confined to the box they belong to. Deterministic: seeded
// rand, never Math.random, so a frame renders the same twice.

import { useCurrentFrame } from "remotion";
import { colors } from "../theme";
import { rand } from "../lib/anim";

export const LiftParticles: React.FC<{
  /** Local frame the lift starts on. */
  at: number;
  /** Box the dust rises from, in page CSS px. */
  box: { x: number; y: number; w: number; h: number };
  /** How many specks. 18-28 reads as dust, more reads as confetti. */
  count?: number;
  /** How far a speck travels, in page px. */
  rise?: number;
  frame: number;
}> = ({ at, box, count = 22, rise = 70, frame }) => {
  const t = (frame - at) / 44;
  if (t <= 0 || t >= 1.35) return null;
  return (
    <>
      {Array.from({ length: count }).map((_, i) => {
        const seed = i * 131 + 7;
        const r1 = rand(seed);
        const r2 = rand(seed + 51);
        const r3 = rand(seed + 97);
        const delay = r1 * 0.35;
        const life = 0.55 + r2 * 0.45;
        const age = (t - delay) / life;
        if (age <= 0 || age >= 1) return null;
        const x = box.x + 14 + r3 * (box.w - 28);
        const y = box.y + r1 * box.h - age * rise * (0.55 + r2 * 0.9);
        const size = 2 + r2 * 3.5;
        const op = Math.sin(Math.PI * age) * (0.35 + r3 * 0.45);
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: x, top: y,
              width: size, height: size,
              borderRadius: size,
              background: colors.cyan,
              opacity: op,
              boxShadow: `0 0 ${6 + size * 2}px ${colors.cyan}`,
            }}
          />
        );
      })}
    </>
  );
};
