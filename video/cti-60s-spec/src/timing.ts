// timing.ts - the film clock. 120 BPM, 30 fps, one beat = 15 frames.
//
// Every frame number in the film is derived from a beat index here; scenes are
// placed by beat, so retiming means editing this table and nothing else.
//
// v8 (65 s): 130 beats. The middle did not move at all - s06, s07 and s08 keep
// their frame counts and internal rhythm; the time was added to the opening, the
// form and the result. Scenes whose choreography predates a retime read their own
// clock through authored(), so a move keeps its shape and simply plays slower.

import beats from "../beats.json";

export const FPS = 30;
export const BEAT = 15;                 // frames per beat
export const TOTAL_BEATS = 131;         // 65.5 s
export const TOTAL_FRAMES = 1965;
export const BPM = 120;

/** Master frame of beat n (beat 0 is frame 0). */
export const beatFrame = (n: number): number => Math.round(n * BEAT);
/** Master frame of half-beat n (a cut may sit on a half beat, never off it). */
export const halfBeatFrame = (n: number): number => Math.round(n * BEAT * 0.5);

export type Shot = { id: string; title: string; start: number; end: number; duration: number };

/** The cut table, written in beats. 131 beats = 65.5 s (s08 gained one beat for the caption hold). */
const SHOT_BEATS: Array<[string, string, number, number]> = [
  ["s01", "wordmark", 0, 3],
  ["s02", "overview-kpi", 3, 17],
  ["s03", "overview-clusters", 17, 31],
  ["s04", "overview-matrix", 31, 43],
  ["s05", "dive-to-patch", 43, 47],
  ["s06", "patch-priority", 47, 56],
  ["s07", "patch-sweep", 56, 65],
  ["s08", "gap-section", 65, 73],
  ["s09", "cve-relay", 73, 77],
  ["s10", "assess-fields", 77, 111],
  ["s11", "assess-result", 111, 124],
  ["s12", "outro", 124, 131],
];

export const SHOTS = SHOT_BEATS.map(([id, title, from, to]) => ({
  id, title, start: beatFrame(from), end: beatFrame(to), duration: beatFrame(to) - beatFrame(from),
}));

export const SCENE = Object.fromEntries(SHOTS.map((s) => [s.id, s])) as Record<
  "s01" | "s02" | "s03" | "s04" | "s05" | "s06" | "s07" | "s08" | "s09" | "s10" | "s11" | "s12",
  Shot
>;

export const clamp = (v: number) => Math.max(0, Math.min(1, v));

/** Frames of a move that starts on beat `from` and lasts `beats`. */
export const frames = (nbeats: number): number => Math.round(nbeats * BEAT);

/** The frame count each scene’s choreography was authored against. */
export const AUTHORED: Record<keyof typeof SCENE, number> = {
  s01: 30,   // the opening is played at half speed in v8
  s02: 210, s03: 210, s04: 165, s05: 60, s06: 135,
  s07: 180, s08: 120, s09: 60, s10: 510, s11: 195, s12: 60,
};

/**
 * Map the scene clock onto the authored choreography.
 *
 * A scene authored against 60 frames and now cut to 105 reads its timeline at
 * 0.57x: every move keeps its shape and simply plays slower. A scene re-authored
 * for the current cut passes its own duration and reads unmodified.
 */
export const authored = (frame: number, id: keyof typeof SCENE, authoredFrames?: number): number => {
  const src = authoredFrames ?? AUTHORED[id];
  const now = SCENE[id].duration;
  return now === src ? frame : frame * (src / now);
};

// Soundtrack: none. SPEC 1 says the film is cut on a declared 120 BPM grid.
export const SOUNDTRACK: string | null = beats.audio_file;

/** Studio-only: warn when the beat grid is a placeholder rather than detected. */
export const GRID_RELIABILITY = beats.grid_reliability;