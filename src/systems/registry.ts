import type { SystemId } from "../scoring/types";

/** Camera framing for a system: where the camera sits and the point it looks at. */
export interface Framing {
  position: [number, number, number];
  target: [number, number, number];
}

export interface SystemPresentation {
  id: SystemId;
  /** GLB under /public/models. One file per system (asset-pipeline output). */
  model: string;
  framing: Framing;
}

/**
 * Per-system runtime metadata. Anchor points are approximate anatomical positions
 * in a body centered at the origin (~1.8 units tall, head ~+0.9, feet ~-0.9).
 */
export const SYSTEM_PRESENTATION: Record<SystemId, SystemPresentation> = {
  cardiovascular: { id: "cardiovascular", model: "/models/system_cardiovascular.glb", framing: { position: [0.0, 0.32, 1.35], target: [0, 0.28, 0.05] } },
  respiratory: { id: "respiratory", model: "/models/system_respiratory.glb", framing: { position: [0.0, 0.34, 1.45], target: [0, 0.3, 0] } },
  digestive: { id: "digestive", model: "/models/system_digestive.glb", framing: { position: [0.0, -0.02, 1.35], target: [0, -0.05, 0.05] } },
  endocrine: { id: "endocrine", model: "/models/system_endocrine.glb", framing: { position: [0.45, 0.5, 1.05], target: [0, 0.45, 0.05] } },
  urinary: { id: "urinary", model: "/models/system_urinary.glb", framing: { position: [0.0, -0.12, 1.35], target: [0, -0.12, 0] } },
  nervous: { id: "nervous", model: "/models/system_nervous.glb", framing: { position: [0.0, 0.74, 1.0], target: [0, 0.72, 0] } },
  skeletal: { id: "skeletal", model: "/models/system_skeletal.glb", framing: { position: [0.0, -0.02, 3.7], target: [0, -0.02, 0] } },
};

export const OVERVIEW_FRAMING: Framing = { position: [0, -0.02, 3.85], target: [0, -0.02, 0] };

/**
 * Body-type skin envelopes (MakeHuman/MPFB2, CC0). The organ systems are fixed to one
 * body-space, so only the skin shell varies per member — see asset-pipeline/03b_build_shells.py.
 */
export type BodyType = "neutral" | "female-young" | "male-heavy" | "female-older";

export const SHELL_MODELS: Record<BodyType, string> = {
  neutral: "/models/shell_neutral.glb",
  "female-young": "/models/shell_female-young.glb",
  "male-heavy": "/models/shell_male-heavy.glb",
  "female-older": "/models/shell_female-older.glb",
};

/** Pick a skin envelope for a member: explicit bodyType wins, else derive from sex + age. */
export function shellForMember(member?: { sex?: string; age?: number; bodyType?: BodyType } | null): string {
  if (member?.bodyType && SHELL_MODELS[member.bodyType]) return SHELL_MODELS[member.bodyType];
  const age = member?.age ?? 40;
  if (member?.sex === "female") return age >= 50 ? SHELL_MODELS["female-older"] : SHELL_MODELS["female-young"];
  if (member?.sex === "male") return SHELL_MODELS["male-heavy"];
  return SHELL_MODELS.neutral;
}

/** Legacy default (neutral envelope) for any caller without member context. */
export const BODY_SHELL_MODEL = SHELL_MODELS.neutral;

export const SYSTEM_IDS = Object.keys(SYSTEM_PRESENTATION) as SystemId[];
