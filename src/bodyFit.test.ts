import { describe, expect, it } from "vitest";
import {
  BODY_FIT_PRESETS,
  DEFAULT_BODY_FIT,
  DEFAULT_ORGAN_FIT,
  buildAnnyQuery,
  computeSystemFit,
  sanitizeBodyFit,
  type BodyFitParams,
} from "./bodyFit";

describe("body fit", () => {
  it("builds an Anny query with global and local body controls", () => {
    const q = new URLSearchParams(buildAnnyQuery(DEFAULT_BODY_FIT));
    expect(q.get("gender")).toBe("0.000");
    expect(q.get("height")).toBe("0.420");
    expect(q.has("measure-waist-circ-incr")).toBe(true);
    expect(q.has("torso-scale-depth-incr")).toBe(true);
    expect(q.has("stomach-navel-out")).toBe(true);
  });

  it("does not scale thoracic organs directly from adiposity or muscle", () => {
    const base: BodyFitParams = {
      ...DEFAULT_BODY_FIT,
      height: 0.5,
      torsoWidth: 0.5,
      torsoDepth: 0.5,
      abdomen: 0.5,
      hips: 0.5,
      centrality: 0.5,
      weight: 0.15,
      muscle: 0.15,
    };
    const largerOuterBody = sanitizeBodyFit({ ...base, weight: 0.95, muscle: 0.95 });

    const heartBase = computeSystemFit("cardiovascular", base, DEFAULT_ORGAN_FIT);
    const heartLargerOuter = computeSystemFit("cardiovascular", largerOuterBody, DEFAULT_ORGAN_FIT);
    const lungsBase = computeSystemFit("respiratory", base, DEFAULT_ORGAN_FIT);
    const lungsLargerOuter = computeSystemFit("respiratory", largerOuterBody, DEFAULT_ORGAN_FIT);

    expect(heartLargerOuter).toEqual(heartBase);
    expect(lungsLargerOuter).toEqual(lungsBase);
  });

  it("uses height as the primary whole-body internal anatomy scale", () => {
    const shortFit = computeSystemFit("nervous", { ...DEFAULT_BODY_FIT, height: 0.1 }, DEFAULT_ORGAN_FIT);
    const tallFit = computeSystemFit("nervous", { ...DEFAULT_BODY_FIT, height: 0.9 }, DEFAULT_ORGAN_FIT);

    expect(tallFit.scale[1]).toBeGreaterThan(shortFit.scale[1]);
    expect(tallFit.scale[0]).toBeGreaterThan(shortFit.scale[0]);
    expect(tallFit.scale[2]).toBeGreaterThan(shortFit.scale[2]);
    expect(tallFit.scale[0]).toBeLessThan(tallFit.scale[1]);
    expect(tallFit.scale[2]).toBeLessThan(tallFit.scale[1]);
  });

  it("keeps representative preset transforms in conservative visual bounds", () => {
    const systems = ["cardiovascular", "respiratory", "digestive", "endocrine", "urinary", "nervous", "skeletal"] as const;
    for (const preset of BODY_FIT_PRESETS) {
      for (const system of systems) {
        const fit = computeSystemFit(system, preset.params, DEFAULT_ORGAN_FIT);
        expect(Math.max(...fit.scale)).toBeLessThanOrEqual(1.25);
        expect(Math.min(...fit.scale)).toBeGreaterThanOrEqual(0.7);
        expect(Math.max(...fit.position.map(Math.abs))).toBeLessThanOrEqual(0.21);
      }
    }
  });
});
