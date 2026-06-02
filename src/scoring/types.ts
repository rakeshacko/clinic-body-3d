export type SystemId =
  | "cardiovascular"
  | "digestive"
  | "endocrine"
  | "respiratory"
  | "urinary"
  | "nervous"
  | "skeletal";

export type Status = "healthy" | "attention" | "flag" | "neutral";

/** How a single marker value sits relative to its reference range. */
export type MarkerClassification = "in" | "borderline" | "out" | "missing";

export type ScoringRule = "worstOfMarkers" | "weightedAverage";

export interface MarkerRange {
  low: number;
  high: number;
}

export interface MarkerConfig {
  key: string;
  label: string;
  unit: string;
  range: MarkerRange;
  /**
   * Tolerance band just outside the range that counts as "borderline" rather than
   * "out". A value within `borderlineMargin` of low/high is borderline.
   */
  borderlineMargin: number;
  weight: number;
}

export interface SystemConfig {
  id: SystemId;
  label: string;
  order: number;
  meshes: string[];
  scoring: ScoringRule;
  plainLanguage: string;
  markers: MarkerConfig[];
}

export interface BodySystemsConfig {
  version: string;
  note: string;
  statusColorTokens: Record<string, string>;
  systems: SystemConfig[];
}

export interface MarkerState {
  key: string;
  label: string;
  unit: string;
  range: MarkerRange;
  value: number | null;
  classification: MarkerClassification;
  /** 0 when in range; grows as the value moves further outside (1 ≈ edge of borderline band). */
  deviation: number;
  weight: number;
}

export interface SystemState {
  id: SystemId;
  label: string;
  order: number;
  meshes: string[];
  status: Status;
  /** Normalized 0..1 severity used to drive emissive intensity (0 = in range, 1 = well out). */
  score: number;
  plainLanguage: string;
  markers: MarkerState[];
}
