// Shot 2 | beats 4-18 | 2.0-9.0 s | the hero band lights up.
//
// v9 replaced the 3D lift with the light-up language: the shot opens on the whole
// page at 0.47 (both tabs and two blocks in frame), pushes into the band, then the
// four KPI cells light one beat apart - nothing moves but the camera and the light.

import { useCurrentFrame } from "remotion";
import { inOutExpo, outExpo, seg } from "../lib/anim";
import { box, capture, frameRule, heroBand, kpiCards, pageHeight, union } from "../assets";
import { Page, World } from "../components/World";
import { BlockLight } from "../components/BlockLight";
import { Caption, Scrim } from "../components/Caption";
import { type } from "../theme";

const cards = kpiCards.slice(0, 4);
const hero = heroBand;
const band = union([hero, ...cards]) ?? box("#overview") ?? { x: 272, y: 90, w: 1376, h: 441 };
const fit = frameRule(band, 64);
const PAGE = { x: 960, y: 540, z: 0.47 };

// 30 frames of held wide shot read as a stall before anything happens; 12 frames is
// enough to register "this is the whole page" and no more.
const PUSH_FROM = 12;
const PUSH_TO = 36;
const CELL_AT = (i: number) => PUSH_TO + i * 30;   // one per beat after the push

export const S02OverviewKpi: React.FC = () => {
  const f = useCurrentFrame();
  const t = seg(f, [PUSH_FROM, PUSH_TO], [0, 1], inOutExpo);
  const drift = seg(f, [180, 210], [0, 0.03], inOutExpo);
  const cam = {
    x: PAGE.x + (fit.x - PAGE.x) * t,
    y: PAGE.y + (fit.y - PAGE.y) * t,
    z: PAGE.z + (fit.z - PAGE.z) * t + drift,
  };

  const lit = (i: number) => seg(f, [CELL_AT(i), CELL_AT(i) + 14], [0, 1], outExpo);
  // the page is the establishing shot; once the push lands, it steps back so the four
  // lit cells are the only thing at full brightness
  const pageLevel = 1 - 0.62 * seg(f, [PUSH_FROM, PUSH_TO + 12], [0, 1], outExpo);
  const pageH = pageHeight("overview");

  return (
    <>
    <World cam={cam}>
      {/* v9 dropped this and the "whole page" hold became four dim cut-outs floating on
          nothing - which is what read as a stall before the animation started. */}
      <div style={{ opacity: pageLevel }}>
        <Page src={capture("overview-full.png")} height={pageH} />
      </div>
      {hero ? <BlockLight src={capture("hero-band.png")} box={hero} lit={lit(0)} frame={f} at={CELL_AT(0)} particles={14} zIndex={12} /> : null}
      {cards.map((card, i) => (
        <BlockLight
          key={i}
          src={capture("kpi-" + String(i + 1).padStart(2, "0") + ".png")}
          box={card}
          lit={lit(i === 0 ? 0 : i)}
          frame={f}
          at={CELL_AT(i === 0 ? 0 : i)}
          particles={12}
          zIndex={14 + i}
        />
      ))}
    </World>
    <Scrim height={300} strength={0.9} />
    <Caption text="分析情資的類型" at={6} frame={f} size={type.h2} />
    </>
  );
};