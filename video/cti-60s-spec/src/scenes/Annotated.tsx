// Annotated - a hero frame with the six-line note SPEC 10 stage 1 asks for,
// written under the picture instead of in a separate document.
//
// The strip sits inside the bottom 96 px safe area, which the film itself keeps
// empty of text (SPEC 5); on a review still that is exactly the space to use.

import { AbsoluteFill } from "remotion";
import { Ambient } from "../components/Ambient";
import { colors, fonts, grid, type } from "../theme";

export type Note = { shot: string; time: string; idea: string; moving: string; camera: string; cut: string };

export const makeAnnotated = (Shot: React.FC, note: Note): React.FC => {
  const Annotated: React.FC = () => (
    <AbsoluteFill>
      <Ambient />
      <Shot />
      <div
        style={{
          position: "absolute", left: 0, right: 0, bottom: 0, height: 96,
          background: "rgba(7, 12, 22, 0.96)",
          borderTop: `1px solid ${colors.line}`,
          display: "flex", alignItems: "center",
          paddingLeft: grid.marginX, paddingRight: grid.marginX,
          fontFamily: fonts.mono, fontSize: type.micro, color: colors.inkSoft,
        }}
      >
        {([[
          "SHOT", note.shot],
          ["TIME", note.time],
          ["IDEA", note.idea],
          ["MOVING", note.moving],
          ["CAMERA", note.camera],
          ["CUT", note.cut]] as Array<[string, string]>).map(([k, v]) => (
          <div key={k} style={{ flex: k === "IDEA" ? 1.7 : 1, paddingRight: 18 }}>
            <div style={{ color: colors.cyan, letterSpacing: "0.16em", marginBottom: 6 }}>{k}</div>
            <div style={{ color: colors.ink, lineHeight: 1.3 }}>{v}</div>
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
  return Annotated;
};