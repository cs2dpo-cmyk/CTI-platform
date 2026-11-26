// Shot 3 | beats 18-32 | 9.0-16.0 s | cluster, then comparison.
//
// v9: two blocks side by side, each given two beats to light up - left first, then
// right. While one is lit the other sits in its dark state at 18%; nothing lifts,
// nothing is dimmed by a separate layer.

import { useCurrentFrame } from "remotion";
import { inOutExpo, outExpo, seg } from "../lib/anim";
import { box, capture, clusterCount, comparePanel, frameRule, pageHeight, union } from "../assets";
import { Page, World } from "../components/World";
import { BlockLight } from "../components/BlockLight";
import { Caption, Scrim } from "../components/Caption";
import { type } from "../theme";

const cluster = box("cluster") ?? { x: 272, y: 595, w: 562, h: 661 };
const compare = comparePanel;
const both = union([cluster, compare]) ?? cluster;
const cam = frameRule(both, 40);

const LEFT_AT = 0;
const RIGHT_AT = 70;      // right starts only after the left has gone dark
const DIM_LEN = 14;       // the handover: left falls back to 0.18 over these frames

export const S03Clusters: React.FC = () => {
  const f = useCurrentFrame();
  const push = seg(f, [120, 210], [1, 1.03], inOutExpo);
  // exactly one block lit at a time: the left one gives the light back to the dark
  // state before the right one starts, never a frame with two of them lit.
  // The fade-out has to be LINEAR and has to straddle the handover. With outExpo it was
  // already at 0.99 when the next block started, so the seam frame had both blocks dark.
  // Six frames before / eight after puts the outgoing block at ~43% on the seam.
  const dimLeft = seg(f, [RIGHT_AT - 6, RIGHT_AT + 8], [0, 1]);
  const litLeft = seg(f, [LEFT_AT, LEFT_AT + 14], [0, 1], outExpo) * (1 - dimLeft);
  const litRight = seg(f, [RIGHT_AT, RIGHT_AT + 14], [0, 1], outExpo);

  return (
    <>
    <World cam={{ ...cam, z: cam.z * push }}>
      {/* the page behind, held back: without it the two lit blocks float on black and
          the "these two sit next to each other on the overview" reading is lost */}
      <div style={{ opacity: 0.38 }}>
        <Page src={capture("overview-full.png")} height={pageHeight("overview")} />
      </div>
      <BlockLight src={capture("cluster-panel.png")} box={cluster} lit={litLeft} frame={f} at={LEFT_AT} particles={14} zIndex={12} />
      {compare ? (
        <BlockLight src={capture("compare-panel.png")} box={compare} lit={litRight} frame={f} at={RIGHT_AT} particles={12} zIndex={13} />
      ) : null}
    </World>
    <Scrim height={300} strength={0.9} />
    <Caption text={"K-Means 把情資分成 " + clusterCount + " 群"} at={36} frame={f} size={type.h2} />
    </>
  );
};