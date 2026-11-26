// SpecCard - the one page in the review set that is not a shot: the palette,
// the two type families and the six-step scale, the margins and the beat ladder.
// It exists so a reviewer can hold the tokens against any frame.

import { AbsoluteFill } from "remotion";
import { colors, fonts, grid, type } from "../theme";

const SWATCHES: Array<[string, string]> = [
  ["--bg", colors.bg],
  ["--panel", colors.panel],
  ["--panel-raised", colors.panelRaised],
  ["--line", colors.line],
  ["--ink", colors.ink],
  ["--ink-soft", colors.inkSoft],
  ["--muted", colors.muted],
  ["--cyan", colors.cyan],
];

const SCALE: Array<[string, number]> = [
  ["h1", type.h1], ["h2", type.h2], ["h3", type.h3],
  ["body", type.body], ["small", type.small], ["micro", type.micro],
];

export const SpecCard: React.FC = () => (
  <AbsoluteFill style={{ backgroundColor: colors.bg, padding: grid.marginY, fontFamily: fonts.display }}>
    <div style={{ fontFamily: fonts.mono, fontSize: type.micro, letterSpacing: "0.2em", color: colors.cyan }}>
      SPEC · CTI CISO DASHBOARD · 60.0 s · 1920×1080 · 30 fps · 120 BPM · 1800 f
    </div>
    <div style={{ display: "flex", gap: 16, marginTop: 40 }}>
      {SWATCHES.map(([name, hex]) => (
        <div key={name} style={{ flex: 1 }}>
          <div style={{ height: 120, background: hex, border: "1px solid " + colors.line }} />
          <div style={{ marginTop: 10, fontFamily: fonts.mono, fontSize: type.micro, color: colors.inkSoft }}>{name}</div>
          <div style={{ fontFamily: fonts.mono, fontSize: type.micro, color: colors.muted }}>{hex}</div>
        </div>
      ))}
    </div>
    <div style={{ display: "flex", gap: 60, marginTop: 64 }}>
      <div style={{ flex: 1 }}>
        <div style={{ fontFamily: fonts.mono, fontSize: type.micro, color: colors.cyan, letterSpacing: "0.16em" }}>TYPE SCALE</div>
        {SCALE.map(([name, px]) => (
          <div key={name} style={{ display: "flex", alignItems: "baseline", gap: 20, marginTop: 14 }}>
            <span style={{ fontFamily: fonts.mono, fontSize: type.micro, color: colors.muted, width: 56 }}>{name}</span>
            <span style={{ fontSize: px, color: colors.ink, lineHeight: 1.1 }}>決策 P1 {px}</span>
          </div>
        ))}
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ fontFamily: fonts.mono, fontSize: type.micro, color: colors.cyan, letterSpacing: "0.16em" }}>GRID</div>
        <div style={{ fontSize: type.h3, color: colors.ink, marginTop: 18, lineHeight: 1.5 }}>
          左右 120 px · 上下 96 px · 12 欄 · gutter 24 px<br />
          推鏡上限 1.40× · 切點只落整拍或半拍<br />
          顆粒 0.2 · 暗角 0.4H→1.05H · 發光僅 cyan
        </div>
        <div style={{ fontFamily: fonts.mono, fontSize: type.small, color: colors.inkSoft, marginTop: 34, lineHeight: 1.6 }}>
          1 拍 = 15 幀 = 0.5 s · 全片 120 拍<br />
          元件進場 outExpo 15/23 f · 出場 inExpo 8 f<br />
          相機 12–15 f inOutExpo · 游標 15–22 f
        </div>
        <div style={{ fontFamily: fonts.mono, fontSize: type.body, color: colors.cyan, marginTop: 34 }}>
          Inter · Noto Sans TC · JetBrains Mono
        </div>
      </div>
    </div>
  </AbsoluteFill>
);