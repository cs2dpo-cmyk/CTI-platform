// World - the 2.5D camera. One measured page plane, one camera triple.
//
// SPEC 7: no scrolling anywhere in the film. Vertical travel is the camera
// moving over a page that never moves. `x`/`y` are page CSS px the camera
// looks at, `z` is the dolly (1.00 = the page exactly fills 1920 px, capped at
// 1.40 by the SPEC because the capture is dpr 2).

import { AbsoluteFill } from "remotion";
import type { ReactNode } from "react";
import { canvas, colors } from "../theme";

export type Cam = { x: number; y: number; z: number };

export const World: React.FC<{ cam: Cam; children: ReactNode; shake?: { x: number; y: number } }> = ({
  cam,
  children,
  shake,
}) => {
  const { width, height } = canvas;
  const tx = width / 2 - cam.x * cam.z + (shake?.x ?? 0);
  const ty = height / 2 - cam.y * cam.z + (shake?.y ?? 0);
  return (
    <AbsoluteFill style={{ overflow: "hidden", backgroundColor: colors.bg }}>
      <AbsoluteFill
        style={{
          transform: `translate(${tx}px, ${ty}px) scale(${cam.z})`,
          transformOrigin: "0 0",
        }}
      >
        {children}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/** A captured page, laid out at its own CSS size. */
export const Page: React.FC<{ src: string; height: number; opacity?: number }> = ({ src, height, opacity = 1 }) => (
  <img
    src={src}
    style={{ position: "absolute", left: 0, top: 0, width: 1920, height, opacity }}
  />
);

/** An element cut-out, placed at the page position the capture measured. */
export const Cut: React.FC<{
  src: string;
  box: { x: number; y: number; w: number; h: number };
  style?: React.CSSProperties;
}> = ({ src, box, style }) => (
  <img src={src} style={{ position: "absolute", left: box.x, top: box.y, width: box.w, height: box.h, ...style }} />
);