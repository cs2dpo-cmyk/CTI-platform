// ZoombBlur - the one place the film buys a shutter effect.
//
// A dolly-through has no element to give a velocity to: the whole plane is
// moving toward the lens. So at the moment of the swap the outgoing plane is
// drawn three times at slightly different scales, fanned in opacity. That is a
// zoom blur (radial streak), which is what a real long exposure would leave.

import { AbsoluteFill } from "remotion";

export const ZoombBlur: React.FC<{
  /** 0 = sharp, 1 = maximum streak. Drive it from the dive speed. */
  amount: number;
  children: React.ReactNode;
}> = ({ amount, children }) => {
  if (amount <= 0.01) return <AbsoluteFill>{children}</AbsoluteFill>;
  const layers = [1, 1 + 0.045 * amount, 1 + 0.09 * amount];
  const weights = [0.5, 0.3, 0.2];
  return (
    <AbsoluteFill>
      {layers.map((s, i) => (
        <AbsoluteFill
          key={i}
          style={{ opacity: weights[i] * Math.min(1, amount * 1.6), transform: `scale(${s})`, transformOrigin: "50% 50%" }}
        >
          {children}
        </AbsoluteFill>
      ))}
    </AbsoluteFill>
  );
};
