// Block3D - a captured block that can leave the page as its own layer.
//
// v4 overview shots were one flat page screenshot pushed by the camera, so a
// "lift" could only be a translateY plus a shadow, and the neighbours always came
// along. This component is the fix: one element capture per block, a perspective
// wrapper, and three separate things that read as height -
//   the transform (translateZ + rotateX + a little rotateY + scale),
//   a shadow drawn on the base plane underneath it,
//   an edge light that only the lifted block carries.
// SPEC 5 keeps the accent cyan and forbids full-screen glow, so the light is a
// 26 px halo at 18 percent and nothing else.

import { colors } from "../theme";
import { LiftParticles } from "./LiftParticles";

export type BlockBox = { x: number; y: number; w: number; h: number };

/** The paper a block lifts off: a flat plate in the page surface colour. */
export const BlockPlate: React.FC<{ box: BlockBox; pad?: number; opacity?: number }> = ({ box, pad = 26, opacity = 1 }) => (
  <div
    style={{
      position: "absolute",
      left: box.x - pad, top: box.y - pad,
      width: box.w + pad * 2, height: box.h + pad * 2,
      borderRadius: 10,
      background: "rgba(17, 26, 43, 0.55)",
      border: "1px solid " + colors.line,
      opacity,
      zIndex: 1,
    }}
  />
);

export const Block3D: React.FC<{
  src: string;
  box: BlockBox;
  /** Transform progress: 0 sitting on the page, 1 fully lifted. */
  lift: number;
  /** Edge light and shadow, rising 6-14 frames after the transform starts. */
  glow?: number;
  /** 0 = untouched, 1 = fully dimmed (brightness 0.45, no move, no scale). */
  dim?: number;
  frame: number;
  /** Frame the lift starts on. */
  at: number;
  particles?: number;
  zIndex?: number;
}> = ({ src, box, lift, glow = 0, dim = 0, frame, at, particles = 14, zIndex = 10 }) => {
  const z = 90 * lift;
  const rotX = -10 * lift;
  const rotY = 6 * lift;
  const scale = 1 + 0.06 * lift;
  const g = Math.min(1, glow);
  return (
    <>
      {/* the shadow, painted on the base plane rather than stuck to the block */}
      <div
        style={{
          position: "absolute",
          left: box.x + 6, top: box.y + 20,
          width: box.w, height: box.h,
          background: "radial-gradient(50% 50% at 50% 50%, rgba(0,0,0,0.62), rgba(0,0,0,0) 72%)",
          filter: "blur(24px)",
          transform: "translateY(" + 26 * lift + "px) scale(" + (1 + 0.04 * lift) + ")",
          opacity: 0.9 * g,
          pointerEvents: "none",
          zIndex: 2,
        }}
      />
      <div
        style={{
          position: "absolute",
          left: box.x, top: box.y, width: box.w, height: box.h,
          perspective: 1400,
          perspectiveOrigin: "50% 40%",
          zIndex,
        }}
      >
        <img
          src={src}
          style={{
            width: "100%",
            height: "100%",
            display: "block",
            borderRadius: 6,
            transform: "translateZ(" + z + "px) rotateX(" + rotX + "deg) rotateY(" + rotY + "deg) scale(" + scale + ")",
            transformOrigin: "center 62%",
            backfaceVisibility: "hidden",
            filter:
              dim > 0
                ? "brightness(" + (1 - 0.55 * dim) + ") saturate(" + (1 - 0.2 * dim) + ") contrast(" + (1 - 0.05 * dim) + ")"
                : undefined,
            boxShadow:
              g > 0.02
                ? "0 0 0 1px rgba(34, 211, 238, " + 0.4 * g + "), 0 0 26px rgba(34, 211, 238, " + 0.18 * g + ")"
                : undefined,
          }}
        />
      </div>
      {particles > 0 && lift > 0 ? <LiftParticles at={at} box={box} count={particles} rise={64} frame={frame} /> : null}
    </>
  );
};