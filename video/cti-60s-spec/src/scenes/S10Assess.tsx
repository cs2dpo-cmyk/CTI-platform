// Shot 10 | beats 76-110 | 38.0-55.0 s | eleven fields, filled for real.
//
// 510 frames: ten fields at 44 each, the CVSS drag at 60, ten frames of tail. The
// CVSS segment sits where the field sits in the form, so the camera never has to
// jump back up. Two things are performed rather than implied:
//   - the five native selects open. A native popup is drawn by the window manager
//     and never appears in a page screenshot, so the open list is rebuilt here with
//     the site palette and the option text the capture measured (noted on delivery).
//   - the CVSS thumb is dragged: four captured states, the pointer stuck to the
//     thumb of whichever state is on screen, press held down for the whole drag.

import { AbsoluteFill, useCurrentFrame } from "remotion";
import { camera, colors, fonts, type } from "../theme";
import { enter, inOutExpo, outExpo, seg } from "../lib/anim";
import { box, capture, DATA, field, pageHeight, stepFields } from "../assets";
import { Page } from "../components/World";
import { ClickRing, Cursor } from "../components/Cursor";

const STEP_KEYS = [
  "assetType", "threatSource", "category", "exposure", "regionGlobal", "cveId",
  "exploitStatus", "sensitivityHigh", "assetName", "assessBtn",
] as const;
const SELECTS: Record<string, string> = {
  assetType: "對外網站",
  threatSource: "國家級",
  category: "系統漏洞",
  exposure: "公開",
  exploitStatus: "已在野",
};

const STEP = 44;
const CVSS_AT = 6 * STEP;          // 264: right after the CVE field
const CVSS_LEN = 60;
const REST = 4 * STEP;             // the four fields after the slider
const DUR = 6 * STEP + CVSS_LEN + REST + 10;

const formBox = box("assess:#assessForm") ?? box("assess:#assess") ?? { x: 273, y: 194, w: 792.3, h: 627.5 };
const usable = STEP_KEYS.map((k) => field(k)).filter((b): b is NonNullable<typeof b> => !!b && b.w > 0);
const formX0 = usable.length ? Math.min(...usable.map((b) => b.x)) - 56 : 96;
const formX1 = usable.length ? Math.max(...usable.map((b) => b.x + b.w)) + 56 : 1344;
const fitZ = Math.min(camera.maxZoom, 1920 / Math.max(600, formX1 - formX0));

const resultLeft = box("result:#assessResult")?.x ?? formX1 + 140;
const frameRight = Math.min(formBox.x + formBox.w + 10, resultLeft - 12);

/**
 * Which state image is on screen. The value appears on the click frame, not at the
 * start of the step: the step index (and so the pointer target) advances on the
 * boundary, but the screenshot that carries the new value only switches at frame
 * 22 of the step, where the click happens.
 */
const CLICK_AT = 22;
const stateAt = (f: number) => {
  const shown = (local: number) => (local >= CLICK_AT ? 1 : 0);
  if (f < CVSS_AT) {
    const i = Math.min(5, Math.floor(f / STEP));
    const n = i + 1 + shown(f - i * STEP);
    return { kind: "step" as const, i, img: "assess-step" + String(n).padStart(2, "0") + ".png", layout: n };
  }
  if (f < CVSS_AT + CVSS_LEN) {
    const k = Math.min(3, Math.floor((f - CVSS_AT) / 14));
    return { kind: "cvss" as const, i: -1, k, img: "assess-cvss-" + String(k + 1).padStart(2, "0") + ".png", layout: 0 };
  }
  const j = Math.min(3, Math.floor((f - CVSS_AT - CVSS_LEN) / STEP));
  const i = 6 + j;
  const n = i + 2 + shown(f - CVSS_AT - CVSS_LEN - j * STEP);
  return { kind: "step" as const, i, img: "assess-step" + String(Math.min(11, n)).padStart(2, "0") + ".png", layout: Math.min(11, n) };
};
const boxesFor = (state: ReturnType<typeof stateAt>): Record<string, any> => {
  if (state.kind === "cvss") {
    const s = DATA.cvssStates && DATA.cvssStates[String(state.k + 1)];
    if (s && s.fields) return s.fields;
    const fallback = stepFields(7);
    return fallback ? fallback.fields : {};
  }
  const rec = stepFields(state.layout);
  return rec ? rec.fields : {};
};

export const S10Assess: React.FC = () => {
  const f = useCurrentFrame();
  const pageH = pageHeight("assess" as any) || 2600;
  const state = stateAt(f);
  const boxes = boxesFor(state);

  // the pointer target: the field of this step, or the CVSS thumb, or a menu row
  const local = state.kind === "cvss" ? (f - CVSS_AT) % 14 : f % STEP;
  const key = state.i >= 0 ? STEP_KEYS[Math.min(STEP_KEYS.length - 1, state.i)] : "cvss";
  const selectId = state.kind === "step" && SELECTS[key] ? key : null;

  const cvssState = state.kind === "cvss" && DATA.cvssStates ? DATA.cvssStates[String(state.k + 1)] : null;
  const thumb = (() => {
    const cb = (cvssState && cvssState.cvssBox) || field("cvss") || { x: 291, y: 527, w: 371, h: 36 };
    const value = (cvssState && cvssState.value) || 9.8;
    return { x: cb.x + 8 + (value / 10) * (cb.w - 16), y: cb.y + cb.h / 2 };
  })();

  const target = (() => {
    if (state.kind === "cvss") return thumb;
    const b = boxes[key] || field(key);
    return b ? { x: b.x + b.w / 2, y: b.y + b.h / 2 } : { x: 960, y: 900 };
  })();

  // the rebuilt menu of a native select, drawn under its field
  const options = selectId ? (DATA.fields && DATA.fields.options && DATA.fields.options[selectId]) || [] : [];
  const menuOpen = !!selectId && options.length > 0 && local >= 12 && local < 34;
  const chosenRow = (() => {
    const want = selectId ? SELECTS[selectId] : "";
    const idx = options.findIndex((o: any) => String(o.t).indexOf(want) >= 0);
    return idx < 0 ? 0 : idx;
  })();
  const fieldBox = selectId ? boxes[selectId] || field(selectId) : null;
  const rowH = 34;
  const menuBox = fieldBox
    ? { x: fieldBox.x, y: fieldBox.y + fieldBox.h + 4, w: fieldBox.w, h: Math.min(options.length, 6) * rowH + 8 }
    : null;
  const cursorTarget = menuOpen && menuBox && options.length
    ? (() => {
        const vis = Math.min(options.length, 6);
        const row = Math.min(chosenRow, vis - 1);
        return { x: menuBox.x + menuBox.w / 2, y: menuBox.y + 4 + row * rowH + rowH / 2 };
      })()
    : target;

  const travel = state.kind === "cvss"
    ? seg(local, [0, 4], [0, 1], inOutExpo)
    : seg(local, [0, 12], [0, 1], inOutExpo);
  const pointer = {
    x: target.x + (cursorTarget.x - target.x) * travel,
    y: target.y + (cursorTarget.y - target.y) * travel,
  };

  const z = Math.min(camera.maxZoom, fitZ * 0.99 + (menuOpen ? 0.02 : 0));
  const formH = (stepFields(state.kind === "step" ? state.layout : 7) || { formH: formBox.h }).formH || formBox.h;
  const formBottom = formBox.y + formH;
  const camX = frameRight - 960 / z;
  const halfH = 540 / z;
  const camY = Math.max(formBox.y + halfH, Math.min(pointer.y + 30, formBottom - halfH));
  const cam = { x: camX, y: camY, z };
  const screen = (p: { x: number; y: number }) => ({ x: (p.x - cam.x) * cam.z + 960, y: (p.y - cam.y) * cam.z + 540 });

  // one press only, on the click frame
  const press = state.kind === "cvss"
    ? (local >= 1 && local <= 12 ? 1 : 0)
    : Math.max(0, 1 - Math.abs(local - 22) / 2);
  const ringT = state.kind === "cvss"
    ? seg(f - CVSS_AT, [52, 60], [0, 1], outExpo)
    : seg(local, [22, 40], [0, 1], outExpo);

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg }}>
      <AbsoluteFill style={{ transform: "translate(" + (960 - cam.x * cam.z) + "px, " + (540 - cam.y * cam.z) + "px) scale(" + cam.z + ")", transformOrigin: "0 0" }}>
        <Page src={capture("assess-full.png")} height={pageH} />
        <img
          src={capture(state.img)}
          style={{ position: "absolute", left: formBox.x, top: formBox.y, width: formBox.w, height: "auto" }}
        />

        {menuOpen && menuBox
          ? (
              <div
                style={{
                  position: "absolute",
                  left: menuBox.x, top: menuBox.y, width: menuBox.w, height: menuBox.h,
                  background: colors.panelRaised,
                  border: "1px solid " + colors.line,
                  borderRadius: 6,
                  boxShadow: "0 18px 40px rgba(0,0,0,0.55)",
                  overflow: "hidden",
                  opacity: enter(local, 12, 8, outExpo),
                  transform: "translateY(" + (1 - enter(local, 12, 8, outExpo)) * -8 + "px)",
                }}
              >
                {options.slice(0, 6).map((o: any, k: number) => {
                  const active = k === chosenRow;
                  return (
                    <div
                      key={k}
                      style={{
                        height: rowH,
                        display: "flex", alignItems: "center",
                        paddingLeft: 12,
                        fontFamily: fonts.display,
                        fontSize: type.small,
                        color: active ? colors.ink : colors.inkSoft,
                        background: active ? colors.cyan + "22" : "transparent",
                        borderLeft: active ? "2px solid " + colors.cyan : "2px solid transparent",
                      }}
                    >
                      {String(o.t).slice(0, 28)}
                    </div>
                  );
                })}
              </div>
            )
          : null}
      </AbsoluteFill>

      <Cursor x={screen(pointer).x} y={screen(pointer).y} press={press} />
      <ClickRing x={screen(pointer).x} y={screen(pointer).y} t={ringT} />
    </AbsoluteFill>
  );
};

export const ASSESS_FRAMES = DUR;