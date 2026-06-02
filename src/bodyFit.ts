import type { SystemId } from "./scoring/types";

export type BodyFitParamKey =
  | "gender"
  | "age"
  | "height"
  | "weight"
  | "muscle"
  | "proportions"
  | "torsoWidth"
  | "torsoDepth"
  | "abdomen"
  | "hips"
  | "centrality";

export type BodyFitParams = Record<BodyFitParamKey, number>;

export interface BodyFitPreset {
  id: string;
  label: string;
  params: BodyFitParams;
}

export interface OrganFitTuning {
  heightResponse: number;
  torsoResponse: number;
  depthResponse: number;
  placementResponse: number;
}

export interface SystemFitTransform {
  position: [number, number, number];
  scale: [number, number, number];
}

const clamp01 = (v: number) => Math.max(0, Math.min(1, v));
const lerp = (a: number, b: number, t: number) => a + (b - a) * clamp01(t);

export const DEFAULT_BODY_FIT: BodyFitParams = {
  gender: 0,
  age: 0.78,
  height: 0.42,
  weight: 0.66,
  muscle: 0.26,
  proportions: 0.5,
  torsoWidth: 0.58,
  torsoDepth: 0.62,
  abdomen: 0.72,
  hips: 0.42,
  centrality: 0.95,
};

export const DEFAULT_ORGAN_FIT: OrganFitTuning = {
  heightResponse: 1,
  torsoResponse: 0.8,
  depthResponse: 0.55,
  placementResponse: 1,
};

export const BODY_FIT_PRESETS: BodyFitPreset[] = [
  {
    id: "male-central",
    label: "Male central adiposity",
    params: DEFAULT_BODY_FIT,
  },
  {
    id: "male-athletic",
    label: "Male athletic",
    params: {
      gender: 0,
      age: 0.78,
      height: 0.56,
      weight: 0.26,
      muscle: 0.46,
      proportions: 0.56,
      torsoWidth: 0.55,
      torsoDepth: 0.45,
      abdomen: 0.18,
      hips: 0.45,
      centrality: 0.25,
    },
  },
  {
    id: "female-lean",
    label: "Female lean",
    params: {
      gender: 1,
      age: 0.78,
      height: 0.32,
      weight: 0.23,
      muscle: 0.2,
      proportions: 0.54,
      torsoWidth: 0.42,
      torsoDepth: 0.35,
      abdomen: 0.18,
      hips: 0.5,
      centrality: 0.2,
    },
  },
  {
    id: "female-high-adiposity",
    label: "Female high adiposity",
    params: {
      gender: 1,
      age: 0.8,
      height: 0.42,
      weight: 0.9,
      muscle: 0.18,
      proportions: 0.5,
      torsoWidth: 0.72,
      torsoDepth: 0.7,
      abdomen: 0.86,
      hips: 0.7,
      centrality: 0.76,
    },
  },
  {
    id: "short-average",
    label: "Short average",
    params: {
      gender: 0.5,
      age: 0.8,
      height: 0.12,
      weight: 0.45,
      muscle: 0.25,
      proportions: 0.44,
      torsoWidth: 0.5,
      torsoDepth: 0.5,
      abdomen: 0.45,
      hips: 0.45,
      centrality: 0.45,
    },
  },
  {
    id: "tall-average",
    label: "Tall average",
    params: {
      gender: 0.5,
      age: 0.8,
      height: 0.86,
      weight: 0.48,
      muscle: 0.28,
      proportions: 0.58,
      torsoWidth: 0.52,
      torsoDepth: 0.5,
      abdomen: 0.42,
      hips: 0.48,
      centrality: 0.35,
    },
  },
];

export function bodyFitForMember(member?: { sex?: string; age?: number; bodyType?: string } | null): BodyFitPreset {
  if (member?.bodyType === "female-young") return BODY_FIT_PRESETS[2];
  if (member?.bodyType === "female-older") return BODY_FIT_PRESETS[3];
  if (member?.bodyType === "male-heavy") return BODY_FIT_PRESETS[0];
  if (member?.sex === "female") return BODY_FIT_PRESETS[2];
  return BODY_FIT_PRESETS[0];
}

export function sanitizeBodyFit(params: BodyFitParams): BodyFitParams {
  return Object.fromEntries(
    Object.entries(params).map(([k, v]) => [k, clamp01(Number.isFinite(v) ? v : 0)])
  ) as BodyFitParams;
}

export function buildAnnyQuery(params: BodyFitParams) {
  const p = sanitizeBodyFit(params);
  const q = new URLSearchParams();
  q.set("gender", p.gender.toFixed(3));
  q.set("age", p.age.toFixed(3));
  q.set("height", p.height.toFixed(3));
  q.set("weight", p.weight.toFixed(3));
  q.set("muscle", p.muscle.toFixed(3));
  q.set("proportions", p.proportions.toFixed(3));

  const locals: Record<string, number> = {
    "measure-waist-circ-incr": 0.06 + 0.42 * p.abdomen,
    "torso-scale-horiz-incr": 0.06 + 0.3 * p.torsoWidth,
    "torso-scale-depth-incr": 0.04 + 0.36 * p.torsoDepth,
    "measure-underbust-circ-incr": 0.04 + 0.24 * p.torsoWidth,
    "measure-frontchest-dist-incr": 0.03 + 0.18 * p.torsoDepth,
    "measure-hips-circ-incr": 0.08 + 0.38 * p.hips,
    "hip-scale-horiz-incr": 0.04 + 0.24 * p.hips,
    "hip-scale-depth-incr": 0.04 + 0.28 * Math.max(p.torsoDepth, p.centrality * 0.65),
    "hip-trans-forward": 0.03 + 0.16 * p.centrality,
    "pelvis-tone-incr": 0.02 + 0.16 * p.centrality,
    "stomach-navel-out": 0.04 + 0.3 * p.abdomen,
    "stomach-pregnant-incr": 0.02 + 0.22 * p.centrality * p.abdomen,
    "measure-thigh-circ-incr": 0.08 + 0.22 * p.weight,
    "l-upperleg-fat-incr": 0.05 + 0.26 * p.weight,
    "r-upperleg-fat-incr": 0.05 + 0.26 * p.weight,
    "measure-upperarm-circ-incr": 0.08 + 0.18 * Math.max(p.weight, p.muscle),
    "l-upperarm-fat-incr": 0.04 + 0.22 * p.weight,
    "r-upperarm-fat-incr": 0.04 + 0.22 * p.weight,
  };

  if (p.gender > 0.55) {
    locals["measure-bust-circ-incr"] = 0.12 + 0.3 * p.torsoWidth;
    locals["breast-volume-vert-up"] = 0.16 + 0.2 * p.weight;
  }

  Object.entries(locals).forEach(([k, v]) => q.set(k, clamp01(v).toFixed(3)));
  return q.toString();
}

function mild(value: number, lo: number, hi: number, response: number) {
  return lerp(1, lerp(lo, hi, value), response);
}

export function computeSystemFit(
  systemId: SystemId,
  params: BodyFitParams,
  tuning: OrganFitTuning
): SystemFitTransform {
  const p = sanitizeBodyFit(params);
  const height = mild(p.height, 0.78, 1.22, tuning.heightResponse);
  const torsoX = mild(p.torsoWidth, 0.94, 1.1, tuning.torsoResponse);
  const chestDepth = mild(p.torsoDepth, 0.94, 1.08, tuning.depthResponse);
  const abdomenDepth = mild(p.abdomen, 0.96, 1.08, tuning.depthResponse * 0.45);
  const hipX = mild(p.hips, 0.94, 1.08, tuning.torsoResponse * 0.55);
  const torsoY = mild(p.proportions, 0.95, 1.07, tuning.heightResponse * 0.6);
  const yOffset = (height - 1) * 0.16 * tuning.placementResponse;
  const pelvisOffset = (height - 1) * -0.08 * tuning.placementResponse;
  const abdomenForward = (p.centrality - 0.5) * 0.035 * tuning.placementResponse;

  switch (systemId) {
    case "cardiovascular":
      return { position: [0, yOffset - 0.02, 0], scale: [torsoX * 0.92, height * 0.86, chestDepth * 0.9] };
    case "respiratory":
      return { position: [0, yOffset - 0.07, 0], scale: [torsoX * 0.94, torsoY * 0.78, chestDepth * 0.92] };
    case "digestive":
      return {
        position: [0, pelvisOffset - 0.005, abdomenForward],
        scale: [Math.max(torsoX, hipX), torsoY * height, abdomenDepth],
      };
    case "endocrine":
      return { position: [0, yOffset, 0], scale: [torsoX, height, chestDepth] };
    case "urinary":
      return { position: [0, pelvisOffset - 0.015, abdomenForward * 0.4], scale: [hipX, height * 0.98, abdomenDepth] };
    case "nervous":
      return { position: [0, yOffset - 0.01, 0], scale: [height * 0.9, height * 0.96, height * 0.9] };
    case "skeletal":
      return { position: [0, 0, 0], scale: [torsoX * 0.8, height * 0.95, chestDepth * 0.8] };
  }
}
