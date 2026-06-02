import { describe, expect, it } from "vitest";
import { drivingMarkers, scoreScreening, scoreSystem } from "./engine";
import type { SystemConfig } from "./types";

const worstSystem: SystemConfig = {
  id: "cardiovascular",
  label: "Heart & Circulation",
  order: 1,
  meshes: ["system_cardiovascular"],
  scoring: "worstOfMarkers",
  plainLanguage: "test",
  markers: [
    { key: "ldl", label: "LDL", unit: "mg/dL", range: { low: 0, high: 100 }, borderlineMargin: 30, weight: 1 },
    { key: "hdl", label: "HDL", unit: "mg/dL", range: { low: 40, high: 200 }, borderlineMargin: 5, weight: 1 },
  ],
};

const weightedSystem: SystemConfig = {
  id: "nervous",
  label: "Brain & Nerves",
  order: 6,
  meshes: ["system_nervous"],
  scoring: "weightedAverage",
  plainLanguage: "test",
  markers: [
    { key: "b12", label: "B12", unit: "pg/mL", range: { low: 200, high: 900 }, borderlineMargin: 50, weight: 1 },
    { key: "vitd", label: "Vit D", unit: "ng/mL", range: { low: 30, high: 100 }, borderlineMargin: 10, weight: 3 },
  ],
};

describe("worstOfMarkers", () => {
  it("all markers in range -> healthy, zero score", () => {
    const s = scoreSystem(worstSystem, { ldl: 80, hdl: 60 });
    expect(s.status).toBe("healthy");
    expect(s.score).toBe(0);
    expect(s.markers.every((m) => m.classification === "in")).toBe(true);
  });

  it("one borderline marker -> attention", () => {
    // ldl 120 is 20 over high(100), margin 30 => deviation 0.67 => borderline
    const s = scoreSystem(worstSystem, { ldl: 120, hdl: 60 });
    expect(s.status).toBe("attention");
    expect(s.score).toBeGreaterThan(0);
    expect(s.score).toBeLessThan(1);
  });

  it("one out-of-range marker -> flag", () => {
    // ldl 160 is 60 over high(100), margin 30 => deviation 2 => out
    const s = scoreSystem(worstSystem, { ldl: 160, hdl: 60 });
    expect(s.status).toBe("flag");
    expect(s.markers.find((m) => m.key === "ldl")?.classification).toBe("out");
  });

  it("worst marker dominates the system status", () => {
    const s = scoreSystem(worstSystem, { ldl: 160, hdl: 38 });
    expect(s.status).toBe("flag");
    const worst = drivingMarkers(s, 1)[0];
    expect(worst.key).toBe("ldl");
  });
});

describe("weightedAverage", () => {
  it("weights the heavier marker more", () => {
    // b12 in range (dev 0, weight 1); vitd 0 (40 below low, margin 10 => dev 4, weight 3)
    // weighted avg = (0*1 + 4*3) / 4 = 3 => > 1 => flag
    const s = scoreSystem(weightedSystem, { b12: 500, vitd: 0 });
    expect(s.status).toBe("flag");
  });

  it("mild single deviation averages down to attention", () => {
    // b12 in range (dev 0, w1); vitd 25 (5 below low, margin 10 => dev 0.5, w3)
    // weighted avg = (0 + 0.5*3)/4 = 0.375 => <=1 => attention
    const s = scoreSystem(weightedSystem, { b12: 500, vitd: 25 });
    expect(s.status).toBe("attention");
  });

  it("all in range -> healthy", () => {
    const s = scoreSystem(weightedSystem, { b12: 500, vitd: 60 });
    expect(s.status).toBe("healthy");
  });
});

describe("missing markers", () => {
  it("system with no values renders neutral, not flagged", () => {
    const s = scoreSystem(worstSystem, {});
    expect(s.status).toBe("neutral");
    expect(s.score).toBe(0);
    expect(s.markers.every((m) => m.classification === "missing")).toBe(true);
  });

  it("missing one marker does not penalize; present markers still score", () => {
    const s = scoreSystem(worstSystem, { ldl: 80 });
    expect(s.status).toBe("healthy");
    expect(s.markers.find((m) => m.key === "hdl")?.classification).toBe("missing");
  });

  it("weightedAverage ignores missing markers in the denominator", () => {
    // only vitd present, borderline dev 0.5 => weighted avg 0.5 => attention
    const s = scoreSystem(weightedSystem, { vitd: 25 });
    expect(s.status).toBe("attention");
  });
});

describe("scoreScreening", () => {
  it("returns systems sorted by order", () => {
    const cfg = { version: "t", note: "", statusColorTokens: {}, systems: [weightedSystem, worstSystem] };
    const states = scoreScreening(cfg, { ldl: 80, hdl: 60, b12: 500, vitd: 60 });
    expect(states.map((s) => s.order)).toEqual([1, 6]);
  });
});
