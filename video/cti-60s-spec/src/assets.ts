// assets.ts - everything the film knows about the captured page.
//
// capture/capture.mjs writes public/data.json (measured values and page sizes)
// and public/bboxes.json (element boxes in page CSS px). The film never
// guesses a number that one of those two files already holds: the copy on
// screen and the geometry the camera aims at both come from here.
//
// A missing entry falls back to a fraction of the page, so a partial capture
// still renders - it just says so in the console.

import { camera } from "./theme";
import { staticFile } from "remotion";
import boxesJson from "../public/bboxes.json";
import dataJson from "../public/data.json";

export type Box = { x: number; y: number; w: number; h: number };

export const DATA = dataJson as any;
export const BOXES = boxesJson as any;

export const capture = (file: string): string => staticFile("captures/" + file);

/** A measured box, or null when that capture step did not record one. */
export const box = (key: string): Box | null => {
  const b = BOXES[key];
  if (!b || typeof b.x !== "number" || typeof b.y !== "number") return null;
  return { x: b.x, y: b.y, w: b.w, h: b.h };
};

export const pageHeight = (tab: "overview" | "patch" | "assess" | "result"): number => {
  const size = DATA[tab + "PageSize"];
  return size && typeof size.h === "number" ? size.h : 2160;
};

/** Centre of a box, or a fractional fallback on the page. */
export const centre = (b: Box | null, pageH: number, fx = 0.5, fy = 0.3) =>
  b ? { x: b.x + b.w / 2, y: b.y + b.h / 2 } : { x: 1920 * fx, y: pageH * fy };

export const kpiCards: Box[] = Array.isArray(BOXES.kpiCards) ? BOXES.kpiCards : [];

export const patchRows: Box[] = Array.isArray(BOXES.patchRows) ? BOXES.patchRows : [];

export const field = (name: string): Box | null => {
  const f = DATA.fields && DATA.fields[name];
  return f && typeof f.x === "number" ? f : null;
};

// ------------------------------------------------------------------ copy
// Every string below is either verbatim from prompt.md 8 or a measured value.
export const COPY = {
  wordmark: "CTI 資安風險決策支援平台",
  subtitle: "CISO Dashboard · 從情資到決策",
  kpiLabels: ["全球預警", "在地落地", "解析情資樣本", "Meta-Category", "平均風險分數"],
  clusters: "K-Means 把情資分成",
  matrix: "P3 < 66 · P2 66–79 · P1 ≥ 80",
  patch: "EPSS × KEV 決定順序，不是 CVSS",
  gap: "還沒進 KEV 名單的，已經在打你",
  cve: "CVE-2026-111497",
  outro: "先修 P1，其餘排程",
  url: "cti-risk-platform.onrender.com",
} as const;

// ------------------------------------------------------- measured values
export const kpi = {
  total: DATA.kpi?.total ?? "—",
  tw: DATA.kpi?.tw ?? "—",
  global: DATA.kpi?.global ?? "—",
  p1: DATA.kpi?.p1 ?? "—",
  avgScore: DATA.kpi?.avgScore ?? "—",
  critical: DATA.kpi?.critical ?? "—",
  topMeta: DATA.kpi?.topMeta ?? "—",
  clusterCaption: DATA.kpi?.clusterCaption ?? "",
};

export const patch = {
  total: DATA.patch?.total ?? DATA.patch?.count ?? "",
  count: DATA.patch?.count ?? "",
  viewAll: DATA.patch?.viewAll ?? "",
  rows: DATA.patch?.rowCount ?? 0,
  expandedRows: DATA.patchExpanded?.rows ?? 0,
  expandedCount: DATA.patchExpanded?.count ?? "",
};

export const gap = {
  covered: DATA.gap?.covered ?? "",
  window: DATA.gap?.window ?? "",
  rows: DATA.gap?.rowCount ?? 0,
};

export const result = {
  score: DATA.result?.score ?? "—",
  priority: DATA.result?.priority ?? "—",
  level: DATA.result?.level ?? "",
  sla: DATA.result?.sla ?? "",
  headline: DATA.result?.headline ?? "",
  summary: DATA.result?.summary ?? "",
  confidence: DATA.result?.confidence ?? "",
};

/** The cluster count, read from the panel itself (the caption lists C0..Cn). */
export const clusterCount: string = (() => {
  const declared = DATA.kpi?.classifyCount;
  if (typeof declared === "number" && declared > 0) return String(declared);
  const caption = String(DATA.kpi?.clusterCaption ?? "") + " " + String(DATA.kpi?.pieCaption ?? "");
  const named = caption.match(/C\d+/g);
  if (named && named.length > 0) return String(named.length);
  const groups = caption.match(/(\d+)\s*[群類]/);
  if (groups) return groups[1];
  const legend = Array.isArray(DATA.kpi?.legend) ? DATA.kpi.legend.length : 0;
  return legend > 0 ? String(legend) : "4";
})();
/** v5: the hero band (headline + its stat boxes) as one lightable layer. */
export const heroBand: Box | null = box("hero");
/** v5: the comparison panel that sits beside the cluster panel. */
export const comparePanel: Box | null = box("compare");
/** v5: the three decision-matrix cards, one capture each. */
export const matrixCards: Box[] = Array.isArray(BOXES.matrixCards) ? BOXES.matrixCards : [];

/** Union of boxes, for a frame that must hold several blocks at once. */
export const union = (boxes: Array<Box | null | undefined>): Box | null => {
  const list = boxes.filter((b): b is Box => !!b && typeof b.w === "number" && b.w > 0);
  if (list.length === 0) return null;
  const x = Math.min(...list.map((b) => b.x));
  const y = Math.min(...list.map((b) => b.y));
  const right = Math.max(...list.map((b) => b.x + b.w));
  const bottom = Math.max(...list.map((b) => b.y + b.h));
  return { x, y, w: right - x, h: bottom - y };
};

/**
 * v5 FrameRule: one block is the whole composition. z fits the box plus its
 * padding on both axes, so nothing that lives outside the block can enter frame.
 */
export const frameRule = (b: Box, pad: number, grow = 1) => ({
  x: b.x + b.w / 2,
  y: b.y + b.h / 2,
  z: Math.min(
    camera.maxZoom,
    1920 / (b.w * grow + 2 * pad),
    1080 / (b.h * grow + 2 * pad),
  ),
});

/** How much larger a lifted block is drawn: scale 1.06 x 1400/(1400-90). */
export const LIFT_GROW = 1.06 * (1400 / (1400 - 90));

/** v6 A1: per-step field boxes recorded by the capture, keyed by filled-field count. */
export const stepFields = (n: number): { fields: Record<string, Box>; formH: number } | null => {
  const s = DATA.stepFields && DATA.stepFields[String(n)];
  if (!s) return null;
  const { formH, ...fields } = s as Record<string, unknown>;
  return { fields: fields as Record<string, Box>, formH: typeof formH === "number" ? formH : 0 };
};

/** Proves at render time whether the numbers on screen are measured or fallback. */
export const measured = {
  capturedAt: DATA.capturedAt ?? null,
  hasKpi: typeof DATA.kpi?.avgScore === "string" && DATA.kpi.avgScore !== "—",
  hasResult: typeof DATA.result?.score === "string" && DATA.result.score !== "—",
  hasBoxes: Object.keys(BOXES).length > 0,
};