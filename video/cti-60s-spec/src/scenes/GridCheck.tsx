// GridCheck - SPEC 10 stage 1 asks for one frame with the 12-column grid and the
// safe area drawn over it. It wraps shot 2 so the overlay is checked against the
// real page rather than against a drawing.

import { AbsoluteFill } from "remotion";
import { colors, fonts, grid, type } from "../theme";
import { S02OverviewKpi } from "./S02OverviewKpi";

const colW = (1920 - grid.marginX * 2 - grid.gutter * (grid.columns - 1)) / grid.columns;
const LABEL = "12 COL · GUTTER 24 · MARGIN 120/96 · SAFE AREA 96 (RED)";

export const GridCheck: React.FC = () => (
  <AbsoluteFill>
    <S02OverviewKpi />
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {Array.from({ length: grid.columns }).map((_, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            left: grid.marginX + i * (colW + grid.gutter),
            top: 0,
            width: colW,
            height: 1080,
            background: "rgba(34, 211, 238, 0.06)",
            borderLeft: "1px solid rgba(34, 211, 238, 0.28)",
            borderRight: "1px solid rgba(34, 211, 238, 0.28)",
          }}
        />
      ))}
      <div style={{ position: "absolute", left: grid.marginX, top: grid.marginY, right: grid.marginX, bottom: grid.marginY, border: "1px solid rgba(34, 211, 238, 0.55)" }} />
      <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: grid.marginY, background: "rgba(248, 113, 113, 0.12)", borderTop: "1px dashed rgba(248, 113, 113, 0.7)" }} />
      <div style={{ position: "absolute", left: 24, top: 24, fontFamily: fonts.mono, fontSize: type.micro, color: colors.cyan, letterSpacing: "0.14em" }}>
        {LABEL}
      </div>
    </AbsoluteFill>
  </AbsoluteFill>
);