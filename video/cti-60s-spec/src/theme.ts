// theme.ts - the CTI brand tokens. Every colour, font and margin in the film
// comes from here; no component hard-codes a hex. Source: the product's own CSS
// custom properties (static/css/styles.css, `:root`), which prompt.md 1.1 fixes
// as the whole palette - eight colours, and the three semantic ones may only
// dress P1/P2/P3 badges and threshold lines.

export const colors = {
  bg: "#0b1220",
  panel: "#111a2b",
  panelRaised: "#16223a",
  line: "#2b3c5a",
  ink: "#dbe6f5",
  inkSoft: "#b9c8dc",
  muted: "#7d8fae",
  cyan: "#22d3ee",
  // semantic only (P1 / P2 / P3 badges and threshold lines)
  p1: "#f87171",
  p2: "#f59e0b",
  p3: "#34d399",
} as const;

/** Second-string text is the ink colour dropped in opacity; 1.2 forbids new greys. */
export const inkAlpha = (a: number): string => {
  const v = Math.round(a * 255).toString(16).padStart(2, "0");
  return `#${colors.ink.slice(1)}${v}`;
};

export const fonts = {
  display: "Inter, 'Noto Sans TC', system-ui, sans-serif",
  body: "Inter, 'Noto Sans TC', system-ui, sans-serif",
  cjk: "'Noto Sans TC', Inter, system-ui, sans-serif",
  mono: "'JetBrains Mono', ui-monospace, monospace",
} as const;

/** The six-step scale. Nothing else is allowed on screen. */
export const type = {
  h1: 72, h2: 44, h3: 28, body: 20, small: 15, micro: 12,
} as const;

export const lineHeight = 1.25;

/** 1.3: 120 / 96 margins, 12 columns, 24 gutter - one grid for the whole film. */
export const grid = { marginX: 120, marginY: 96, columns: 12, gutter: 24 } as const;

export const canvas = { width: 1920, height: 1080 } as const;
export const canvasVertical = { width: 1080, height: 1920 } as const;

export const texture = {
  grain: 0.2,
  vignetteFrom: 0.4,
  vignetteTo: 1.05,
  glowMaxRadius: 24,
} as const;

// The capture is dpr 2 (3840 px wide), so a dolly of 2.0 still reads one
// captured pixel per output pixel. Anything past 2.0 would resample.
export const camera = { maxZoom: 2.0 } as const;

export const blendHex = (a: string, b: string, t: number): string => {
  const ch = (hex: string) => [hex.slice(1, 3), hex.slice(3, 5), hex.slice(5, 7)].map((h) => parseInt(h, 16));
  const [ar, ag, ab] = ch(a);
  const [br, bg, bb] = ch(b);
  return `#${[ar + (br - ar) * t, ag + (bg - ag) * t, ab + (bb - ab) * t]
    .map((n) => Math.round(n).toString(16).padStart(2, "0"))
    .join("")}`;
};
