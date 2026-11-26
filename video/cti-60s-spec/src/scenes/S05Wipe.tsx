// Shot 5 | beats 43-47 | 21.5-23.5 s | the change of page.
//
// v9: an iris match, not a light band. The circle opens out of the row that carries
// the CVE and swallows the frame; the new page is already underneath it, so the
// boundary is a clip-path circle rather than a dissolve. The circle centre is
// pinned at (960, 540) - the camera is aimed at the row, so the row sits on the
// centre and only the radius and the dolly move, from one value of t.

import { AbsoluteFill, useCurrentFrame } from "remotion";
import { colors } from "../theme";
import { inOutExpo, seg } from "../lib/anim";
import { box, capture, pageHeight } from "../assets";
import { Page, World } from "../components/World";

const row = box("cveRow") ?? box("#patchBody") ?? { x: 273, y: 328, w: 1374, h: 61 };
const ROW_C = { x: row.x + row.w / 2, y: row.y + row.h / 2 };
const PAGE_C = { x: 960, y: 540 };

const R0 = 200;
// the corner distance from the circle centre is sqrt(960^2 + 540^2) = 1101.8, and the
// frame is 1920x1080 so the farthest corner from (960,540) is half the diagonal;
// 1260 clears it with room. 1150 did not, which left an arc in the corner.
const R_COVER = 1102;
const R1 = 1260;

export const S05Wipe: React.FC = () => {
  const f = useCurrentFrame();
  const overviewH = pageHeight("overview");
  const patchH = pageHeight("patch");

  const t = seg(f, [0, 60], [0, 1], inOutExpo);
  const R = R0 + (R1 - R0) * t;

  // the new page dollies out of the row and settles on the page centre
  const cam = {
    x: ROW_C.x + (PAGE_C.x - ROW_C.x) * t,
    y: ROW_C.y + (PAGE_C.y - ROW_C.y) * t,
    z: 2.0 - 1.0 * t,
  };
  const covered = R >= R_COVER;
  // the ring has to be gone before the clip can be dropped, or it stays painted on
  // top of the new page as a leftover arc
  const ringFade = 1 - seg(f, [34, 46], [0, 1]);
  const oldDim = 0.45 * t;

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg }}>
      {/* the old page, full frame, behind the iris - pushed back as the iris grows so
          the circle reads as where the film is going, not as a magnifier */}
      <World cam={{ x: PAGE_C.x, y: PAGE_C.y, z: 1.0 }}>
        <Page src={capture("overview-full.png")} height={overviewH} />
      </World>
      <AbsoluteFill style={{ background: colors.bg, opacity: oldDim, pointerEvents: "none" }} />

      {/* the new page, revealed inside the circle */}
      <AbsoluteFill
        style={{
          clipPath: covered ? undefined : "circle(" + R.toFixed(1) + "px at " + PAGE_C.x + "px " + PAGE_C.y + "px)",
        }}
      >
        <World cam={cam}>
          <Page src={capture("patch-full.png")} height={patchH} />
        </World>
      </AbsoluteFill>

      {/* the iris edge: 2 px cyan, 8 px glow, gone once the circle covers the frame */}
      {!covered && ringFade > 0.01 ? (
        <div
          style={{
            position: "absolute",
            left: PAGE_C.x - R, top: PAGE_C.y - R,
            width: R * 2, height: R * 2,
            borderRadius: R,
            border: "2px solid " + colors.cyan,
            boxShadow: "0 0 8px " + colors.cyan + "aa, inset 0 0 8px " + colors.cyan + "55",
            opacity: ringFade,
          }}
        />
      ) : null}
    </AbsoluteFill>
  );
};