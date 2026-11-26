// Master - the 16:9 film. One <Sequence> per shot, everything else in timing.ts.
//
// Order of layers: the ambient background the product itself paints, the shot,
// then grain and vignette once for the whole film (never per scene: a per-scene
// vignette shows its edge at every cut).

import { AbsoluteFill, Sequence, staticFile, useCurrentFrame } from "remotion";
import { Audio } from "@remotion/media";
import { Ambient, Grain, Vignette } from "./components/Ambient";
import { BEAT, SCENE, TOTAL_FRAMES, TOTAL_BEATS } from "./timing";

/** v9: the music bed, one track for the whole film, no ducking. */
const BGM = "audio/bed-65s.m4a";
import { colors } from "./theme";
import { S01Wordmark } from "./scenes/S01Wordmark";
import { S02OverviewKpi } from "./scenes/S02OverviewKpi";
import { S03Clusters } from "./scenes/S03Clusters";
import { S04Matrix } from "./scenes/S04Matrix";
import { S05Wipe } from "./scenes/S05Wipe";
import { S06PatchDeck } from "./scenes/S06PatchDeck";
import { S07Sweep } from "./scenes/S07Sweep";
import { S08Gap } from "./scenes/S08Gap";
import { S09Relay } from "./scenes/S09Relay";
import { S10Assess } from "./scenes/S10Assess";
import { S11Result } from "./scenes/S11Result";
import { S12Outro } from "./scenes/S12Outro";

const SHOT_COMPONENTS: Array<[keyof typeof SCENE, React.FC]> = [
  ["s01", S01Wordmark],
  ["s02", S02OverviewKpi],
  ["s03", S03Clusters],
  ["s04", S04Matrix],
  ["s05", S05Wipe],
  ["s06", S06PatchDeck],
  ["s07", S07Sweep],
  ["s08", S08Gap],
  ["s09", S09Relay],
  ["s10", S10Assess],
  ["s11", S11Result],
  ["s12", S12Outro],
];

/** Stage-2 sample: the beat number on screen, so cuts can be checked against the grid. */
const BeatCounter: React.FC = () => {
  const f = useCurrentFrame();
  const beat = Math.floor(f / BEAT);
  const inBeat = f % BEAT;
  return (
    <div style={{ position: "absolute", right: 40, top: 32, display: "flex", alignItems: "center", gap: 14, fontFamily: "monospace" }}>
      <div style={{ display: "flex", gap: 5 }}>
        {[0, 1, 2, 3].map((i) => (
          <div key={i} style={{ width: 10, height: 10, borderRadius: 10, background: beat % 4 === i ? colors.cyan : colors.line, opacity: beat % 4 === i ? 1 : 0.6 }} />
        ))}
      </div>
      <span style={{ color: colors.ink, fontSize: 26, letterSpacing: "0.06em" }}>
        BEAT {String(beat).padStart(3, "0")}/{TOTAL_BEATS} · F {String(f).padStart(4, "0")} · +{inBeat}
      </span>
    </div>
  );
};

export const Master: React.FC<{ texture?: boolean; counter?: boolean }> = ({ texture = true, counter = false }) => (
  <AbsoluteFill style={{ backgroundColor: colors.bg }}>
    <Ambient />
    <Audio src={staticFile(BGM)} volume={1} />
    {SHOT_COMPONENTS.map(([id, Shot]) => {
      const s = SCENE[id];
      return (
        <Sequence key={id} from={s.start} durationInFrames={s.duration} name={id + " " + s.title}>
          <Shot />
        </Sequence>
      );
    })}
    {texture ? <Vignette /> : null}
    {texture ? <Grain /> : null}
    {counter ? <BeatCounter /> : null}
  </AbsoluteFill>
);

/** Frames checked by tools/stills.mjs - one hero frame per shot the SPEC names. */
export const HERO_FRAMES = [30, 150, 375, 560, 675, 780, 900, 1000, 1120, 1400, 1750, 1900];
export const FILM_FRAMES = TOTAL_FRAMES;