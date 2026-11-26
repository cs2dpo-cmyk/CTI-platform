// Cursor - the pointer is a drawn SVG arrow, never a recorded OS cursor.
//
// Capture note: a Playwright/puppeteer screenshot never contains the OS cursor,
// so the hover highlight on screen is real rendered pixels while the arrow is
// this component, placed from measured boxes (cursor-flyover card).

import { colors } from "../theme";

export const Cursor: React.FC<{ x: number; y: number; press?: number; opacity?: number }> = ({
  x,
  y,
  press = 0,
  opacity = 1,
}) => (
  <div
    style={{
      position: "absolute",
      left: x,
      top: y,
      width: 40,
      height: 40,
      transform: `translate(-2px, -2px) scale(${1 - 0.16 * press})`,
      transformOrigin: "2px 2px",
      opacity,
      filter: `drop-shadow(0 6px 14px rgba(0, 0, 0, 0.55)) drop-shadow(0 0 10px ${colors.cyan}55)`,
    }}
  >
    <svg viewBox="0 0 24 24" width="40" height="40">
      <path
        d="M4 2 L4 20 L9.2 15.4 L12.4 22 L15.6 20.4 L12.4 14 L19.4 14 Z"
        fill={colors.ink}
        stroke="#050a12"
        strokeWidth="1.1"
        strokeLinejoin="round"
      />
    </svg>
  </div>
);

/** The click ripple: 18 frames, scale 0.3 -> 1.5, fading out. */
export const ClickRing: React.FC<{ x: number; y: number; t: number }> = ({ x, y, t }) => {
  if (t <= 0 || t >= 1) return null;
  return (
    <div
      style={{
        position: "absolute",
        left: x - 40,
        top: y - 40,
        width: 80,
        height: 80,
        borderRadius: 80,
        border: `2px solid ${colors.cyan}`,
        transform: `scale(${0.3 + 1.2 * t})`,
        opacity: 0.85 * (1 - t),
      }}
    />
  );
};