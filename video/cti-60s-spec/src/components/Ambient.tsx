// Ambient - the product's own background, painted once behind every scene.
//
// It is the site's body::before / body::after exactly (two faint washes and a
// 64px grid masked to the top), rebuilt here because the capture runs with
// those fixed layers switched off: a fixed layer only appears once in a tall
// screenshot, which leaves seams when the camera travels down the page.

import { AbsoluteFill } from "remotion";
import { colors, texture } from "../theme";

export const Ambient: React.FC = () => (
  <AbsoluteFill style={{ backgroundColor: colors.bg }}>
    <AbsoluteFill
      style={{
        background:
          "radial-gradient(120% 80% at 8% -10%, rgba(245, 158, 11, 0.07), transparent 55%)," +
          "radial-gradient(90% 70% at 92% 0%, rgba(45, 212, 191, 0.06), transparent 60%)",
      }}
    />
    <AbsoluteFill
      style={{
        backgroundImage:
          "linear-gradient(to right, rgba(148, 163, 184, 0.04) 1px, transparent 1px)," +
          "linear-gradient(to bottom, rgba(148, 163, 184, 0.04) 1px, transparent 1px)",
        backgroundSize: "64px 64px",
        maskImage: "radial-gradient(120% 90% at 50% 0%, #000 20%, transparent 78%)",
        WebkitMaskImage: "radial-gradient(120% 90% at 50% 0%, #000 20%, transparent 78%)",
      }}
    />
  </AbsoluteFill>
);

/** Film grain at the spec's 0.2, drawn once from a fixed noise table. */
export const Grain: React.FC = () => (
  <AbsoluteFill style={{ opacity: texture.grain, mixBlendMode: "overlay", pointerEvents: "none" }}>
    <svg width="100%" height="100%">
      <filter id="grain-noise">
        <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="3" seed="7" stitchTiles="stitch" />
      </filter>
      <rect width="100%" height="100%" filter="url(#grain-noise)" />
    </svg>
  </AbsoluteFill>
);

/** Vignette 0.4H -> 1.05H, per the texture spec. */
export const Vignette: React.FC = () => (
  <AbsoluteFill
    style={{
      pointerEvents: "none",
      background: "radial-gradient(120% 105% at 50% 45%, transparent 42%, rgba(4, 8, 16, 0.55) 100%)",
    }}
  />
);