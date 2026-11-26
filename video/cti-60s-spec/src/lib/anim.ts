// anim.ts - the film's motion vocabulary: named easings and one segment helper.
//
// SPEC 6 fixes the curves: outExpo for entrances, inExpo for exits, inOutExpo
// for cameras and cursors. Nothing here calls Math.random - every jitter uses a
// seeded generator so a frame renders the same twice.

import { Easing, interpolate } from "remotion";

export const outExpo = Easing.out(Easing.exp);
export const inExpo = Easing.in(Easing.exp);
export const inOutExpo = Easing.inOut(Easing.exp);
export const outCubic = Easing.out(Easing.cubic);
export const inOutCubic = Easing.inOut(Easing.cubic);
export const linear = Easing.linear;
export const outBack = Easing.out(Easing.back(1.6));
export const springish = Easing.out(Easing.elastic(1));

/** Interpolate a frame range into a value range with clamping at both ends. */
export const seg = (
  frame: number,
  [a, b]: [number, number],
  [from, to]: [number, number],
  easing: (t: number) => number = linear,
): number => interpolate(frame, [a, b], [from, to], {
  easing,
  extrapolateLeft: "clamp",
  extrapolateRight: "clamp",
});

/** 0 before `at`, then an outExpo entrance over `len` frames, clamped at 1. */
export const enter = (frame: number, at: number, len = 15, easing = outExpo): number =>
  seg(frame, [at, at + len], [0, 1], easing);

/** 1 until `at`, then an inExpo exit over `len` frames, clamped at 0. */
export const exit = (frame: number, at: number, len = 8, easing = inExpo): number =>
  seg(frame, [at, at + len], [1, 0], easing);

/**
 * Motion blur that matches the actual speed of a value.
 *
 * `valueAt` is sampled one frame earlier; the difference is how many units the
 * thing travels per frame. `k` converts units to a blur radius, `cap` keeps a
 * smear from ever reading as a broken render (the sweep shot taught us that:
 * 9 px is not speed, it is a stain).
 */
export const velBlur = (
  valueAt: (f: number) => number,
  f: number,
  k = 0.8,
  cap = 4,
): number => {
  const d = Math.abs(valueAt(f) - valueAt(Math.max(0, f - 1)));
  return Math.min(cap, d * k);
};

/** Deterministic pseudo-random in [0,1) - a fixed seed, never Math.random. */
export const rand = (seed: number): number => {
  let t = seed + 0x6d2b79f5;
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
};

/** Cubic bezier point at t, for the CVE relay flight on shot 9. */
export const bezier = (
  t: number,
  p0: { x: number; y: number },
  p1: { x: number; y: number },
  p2: { x: number; y: number },
  p3: { x: number; y: number },
) => {
  const u = 1 - t;
  const a = u * u * u, b = 3 * u * u * t, c = 3 * u * t * t, d = t * t * t;
  return { x: a * p0.x + b * p1.x + c * p2.x + d * p3.x, y: a * p0.y + b * p1.y + c * p2.y + d * p3.y };
};