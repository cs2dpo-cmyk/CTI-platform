// Shot 9 | beats 74-78 | 37.0-39.0 s | the CVE travels to the assess form.
// Cards: ui-entrance/bezier-source-converge-merge (one element handed across a
// cut) + camera/depth-layer-moves (the old page recedes, the new one arrives).
// The string that flies is the same string printed in the table.

import { AbsoluteFill, useCurrentFrame } from "remotion";
import { colors, fonts, type } from "../theme";
import { bezier, enter, inOutExpo, outExpo, seg } from "../lib/anim";
import { authored } from "../timing";
import { camera } from "../theme";
import { box, capture, DATA, pageHeight } from "../assets";
import { Page, type Cam } from "../components/World";

const cveRow = box("cveRow") ?? box("#patchBody") ?? { x: 200, y: 460, w: 1500, h: 44 };
const formBox = box("assess:#assess") ?? { x: 120, y: 260, w: 1200, h: 900 };
const cveField = (() => {
  const f = DATA.fields && DATA.fields.cveId;
  return f && typeof f.x === "number" ? f : { x: formBox.x + 200, y: formBox.y + 520, w: 380, h: 44 };
})();

const toScreen = (p: { x: number; y: number }, cam: Cam) => ({
  x: (p.x - cam.x) * cam.z + 960,
  y: (p.y - cam.y) * cam.z + 540,
});

const Layer: React.FC<{ cam: Cam; children: React.ReactNode; style?: React.CSSProperties }> = ({ cam, children, style }) => (
  <AbsoluteFill
    style={{
      transform: `translate(${960 - cam.x * cam.z}px, ${540 - cam.y * cam.z}px) scale(${cam.z})`,
      transformOrigin: "0 0",
      ...style,
    }}
  >
    {children}
  </AbsoluteFill>
);

export const S09Relay: React.FC = () => {
  const f = authored(useCurrentFrame(), "s09");
  const overviewH = pageHeight("patch");
  const assessH = pageHeight("assess" as any) || 2400;

  const camA: Cam = {
    x: cveRow.x + cveRow.w / 2,
    y: cveRow.y + cveRow.h / 2,
    z: seg(f, [0, 20], [1.45, 1.05], inOutExpo),
  };
  const camB: Cam = {
    x: cveField.x + cveField.w / 2,
    y: cveField.y + cveField.h / 2,
    z: Math.min(camera.maxZoom, seg(f, [30, 60], [1.0, 1.38], inOutExpo)),
  };

  const dim = seg(f, [8, 22], [1, 0.25], outExpo);
  const recede = seg(f, [22, 38], [0, 1], inOutExpo);
  const arrive = seg(f, [24, 44], [0, 1], inOutExpo);

  const from = toScreen({ x: cveRow.x + 240, y: cveRow.y + cveRow.h / 2 }, camA);
  const to = toScreen({ x: cveField.x + cveField.w / 2, y: cveField.y + cveField.h / 2 }, camB);
  const flight = seg(f, [12, 32], [0, 1], inOutExpo);
  const p = bezier(flight, from, { x: from.x + 90, y: from.y - 220 }, { x: to.x - 160, y: to.y - 60 }, to);
  const flightOpacity = seg(f, [12, 16], [0, 1], outExpo) * (1 - seg(f, [46, 54], [0, 1], outExpo));

  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ opacity: 1 - recede, transform: `translateX(${-120 * recede}px)` }}>
        <Layer cam={camA}>
          <div style={{ opacity: dim }}>
            <Page src={capture("patch-full.png")} height={overviewH} />
          </div>
          {/* the selected row, kept at full strength */}
          <div
            style={{
              position: "absolute",
              left: cveRow.x - 6, top: cveRow.y - 6, width: cveRow.w + 12, height: cveRow.h + 12,
              border: `1px solid ${colors.cyan}`,
              boxShadow: `0 0 18px ${colors.cyan}55, inset 0 0 24px ${colors.cyan}22`,
              opacity: seg(f, [4, 10], [0, 1], outExpo) * (1 - seg(f, [30, 38], [0, 1], outExpo)),
            }}
          />
        </Layer>
      </AbsoluteFill>

      <AbsoluteFill style={{ opacity: arrive, transform: `translateX(${80 * (1 - arrive)}px)` }}>
        <Layer cam={camB}>
          <Page src={capture("assess-full.png")} height={assessH} />
        </Layer>
      </AbsoluteFill>

      {/* the string, drawn in screen space so it can cross between the two pages */}
      <div
        style={{
          position: "absolute",
          left: p.x,
          top: p.y,
          transform: `translate(-50%, -50%) scale(${1 + 0.08 * Math.sin(flight * Math.PI)})`,
          opacity: flightOpacity,
          fontFamily: fonts.mono,
          fontSize: type.body,
          letterSpacing: "0.04em",
          color: colors.ink,
          padding: "6px 12px",
          borderRadius: 4,
          background: "rgba(11, 18, 32, 0.86)",
          border: `1px solid ${colors.cyan}66`,
          boxShadow: `0 0 22px ${colors.cyan}33`,
          whiteSpace: "nowrap",
        }}
      >
        CVE-2026-111497
      </div>
    </AbsoluteFill>
  );
};