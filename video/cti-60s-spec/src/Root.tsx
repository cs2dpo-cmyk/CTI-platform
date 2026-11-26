// Root - the master composition plus one debug composition per shot.
//
// Fonts: the three families SPEC 1.2 allows, nothing else. Inter and JetBrains
// Mono carry the Latin and the figures, Noto Sans TC the Chinese; a shot that
// needs a fourth family is a bug.

import { loadFont as loadInter } from "@remotion/google-fonts/Inter";
import { loadFont as loadMono } from "@remotion/google-fonts/JetBrainsMono";
import { loadFont as loadNoto } from "@remotion/google-fonts/NotoSansTC";
import { AbsoluteFill, Composition } from "remotion";
import { Master } from "./Master";
import { FPS, SCENE, TOTAL_FRAMES } from "./timing";
import { canvas } from "./theme";
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
import { GridCheck } from "./scenes/GridCheck";
import { SpecCard } from "./scenes/SpecCard";
import { makeAnnotated } from "./scenes/Annotated";

loadInter("normal", { weights: ["400", "500", "600", "700"], subsets: ["latin"] });
loadMono("normal", { weights: ["400", "500", "600"], subsets: ["latin"] });
loadNoto("normal", { weights: ["400", "700"], subsets: ["chinese-traditional"] });

const DEBUG: Array<[string, React.FC, number]> = [
  ["Scene-S01", S01Wordmark, SCENE.s01.duration],
  ["Scene-S02", S02OverviewKpi, SCENE.s02.duration],
  ["Scene-S03", S03Clusters, SCENE.s03.duration],
  ["Scene-S04", S04Matrix, SCENE.s04.duration],
  ["Scene-S05", S05Wipe, SCENE.s05.duration],
  ["Scene-S06", S06PatchDeck, SCENE.s06.duration],
  ["Scene-S07", S07Sweep, SCENE.s07.duration],
  ["Scene-S08", S08Gap, SCENE.s08.duration],
  ["Scene-S09", S09Relay, SCENE.s09.duration],
  ["Scene-S10", S10Assess, SCENE.s10.duration],
  ["Scene-S11", S11Result, SCENE.s11.duration],
  ["Scene-S12", S12Outro, SCENE.s12.duration],
];

const STILL_S01 = makeAnnotated(S01Wordmark, { shot: "01", time: "拍 0–4 · 0.0–2.0 s", idea: "字標：CTI 資安風險決策支援平台", moving: "準星描畫 / 字標逐字壓印", camera: "1.00 → 1.08（慢一倍）", cut: "拍 4" });
const STILL_S04 = makeAnnotated(S04Matrix, { shot: "04", time: "拍 32–43 · 16.0–21.5 s", idea: "決策矩陣：整頁推入後 P1→P2→P3 輪浮", moving: "推入 → 三輪抬升", camera: "1.00 → 1.28", cut: "拍 43" });
const STILL_S05 = makeAnnotated(S05Wipe, { shot: "05", time: "拍 43–47 · 21.5–23.5 s", idea: "光帶掃過：左新頁、右舊頁", moving: "120px 光刃 / clip-path 分界", camera: "固定 1.00", cut: "拍 47" });
const STILL_S09 = makeAnnotated(S09Relay, { shot: "09", time: "拍 72–76 · 36.0–38.0 s", idea: "CVE 編號從表格接力到表單", moving: "命中框 / 字串貝茲飛行", camera: "1.45 → 1.05 → 1.38", cut: "拍 76" });
const STILL_S12 = makeAnnotated(S12Outro, { shot: "12", time: "拍 123–130 · 61.5–65.0 s", idea: "先修 P1，其餘排程", moving: "收合到字標 + 網址", camera: "1.30 → 1.00", cut: "片尾" });
const STILL_S02 = makeAnnotated(S02OverviewKpi, { shot: "02", time: "拍 4–18 · 2.0–9.0 s", idea: "全球預警：整頁推入標題列＋四張 KPI 卡", moving: "推入 2 拍後四卡錯位浮起", camera: "1.00 → 1.14", cut: "拍 18" });
const STILL_S03 = makeAnnotated(S03Clusters, { shot: "03", time: "拍 18–32 · 9.0–16.0 s", idea: "威脅主題分群 ｜ 跨平台對比", moving: "左先浮、右後浮，另一塊 dim 0.45", camera: "FrameRule 1.17（雙塊）", cut: "拍 32" });
const STILL_S06 = makeAnnotated(S06PatchDeck, { shot: "06", time: "拍 47–56 · 23.5–28.0 s", idea: "EPSS × KEV 決定順序，不是 CVSS", moving: "三列抽卡 / 垂直堆疊 / 歸位", camera: "1.00 → 1.55", cut: "拍 56" });
const STILL_S07 = makeAnnotated(S07Sweep, { shot: "07", time: "拍 56–65 · 28.0–32.5 s", idea: "查看全部：全量逐條掃過", moving: "條帶位移 / 速度模糊（≤2.5px）", camera: "1.30 → 1.10 → 1.18", cut: "拍 65" });
const STILL_S08 = makeAnnotated(S08Gap, { shot: "08", time: "拍 65–72 · 32.5–36.0 s", idea: "沒有進情資的名單，也要注意", moving: "五條帶錯位歸位", camera: "1.00 → 1.20", cut: "拍 72" });
const STILL_S10 = makeAnnotated(S10Assess, { shot: "10", time: "拍 76–110 · 38.0–55.0 s", idea: "11 欄位：下拉展開、CVSS 拖曳", moving: "游標 / 選單 / 滑桿拖曳", camera: "貼合表單，選單開時 +0.02", cut: "拍 110" });
const STILL_S11 = makeAnnotated(S11Result, { shot: "11", time: "拍 110–123 · 55.0–61.5 s", idea: "99.0 · P1 · SLA 24h：決策落地", moving: "鏡頭由標題下移到劇本，光框跟拍", camera: "固定 1.70", cut: "拍 123" });

const STILLS: Array<[string, React.FC, number]> = [
  ["Still-S02", STILL_S02, SCENE.s02.duration],
  ["Still-S03", STILL_S03, SCENE.s03.duration],
  ["Still-S06", STILL_S06, SCENE.s06.duration],
  ["Still-S08", STILL_S08, SCENE.s08.duration],
  ["Still-S10", STILL_S10, SCENE.s10.duration],
  ["Still-S11", STILL_S11, SCENE.s11.duration],
  ["Still-S01", STILL_S01, SCENE.s01.duration],
  ["Still-S04", STILL_S04, SCENE.s04.duration],
  ["Still-S05", STILL_S05, SCENE.s05.duration],
  ["Still-S07", STILL_S07, SCENE.s07.duration],
  ["Still-S09", STILL_S09, SCENE.s09.duration],
  ["Still-S12", STILL_S12, SCENE.s12.duration],
  ["Grid-Check", GridCheck, SCENE.s02.duration],
  ["Spec-Card", SpecCard, 30],
];

/** Stage 2: 640x360, no grain or vignette, beat number in the corner. */
const Sample: React.FC = () => (
  <AbsoluteFill style={{ backgroundColor: "#000" }}>
    <div style={{ width: 1920, height: 1080, transform: "scale(0.3333333)", transformOrigin: "0 0" }}>
      <Master texture={false} counter />
    </div>
  </AbsoluteFill>
);

export const RemotionRoot: React.FC = () => (
  <>
    <Composition id="Master" component={Master} defaultProps={{ texture: true, counter: false }} durationInFrames={TOTAL_FRAMES} fps={FPS} width={canvas.width} height={canvas.height} />
    <Composition id="Sample" component={Sample} durationInFrames={TOTAL_FRAMES} fps={FPS} width={640} height={360} />
    {STILLS.map(([id, Scene, duration]) => (
      <Composition key={id} id={id} component={Scene} durationInFrames={duration} fps={FPS} width={canvas.width} height={canvas.height} />
    ))}
    {DEBUG.map(([id, Scene, duration]) => (
      <Composition key={id} id={id} component={Scene} durationInFrames={duration} fps={FPS} width={canvas.width} height={canvas.height} />
    ))}
  </>
);