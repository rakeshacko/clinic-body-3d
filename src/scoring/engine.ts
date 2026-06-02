import type {
  BodySystemsConfig,
  MarkerClassification,
  MarkerConfig,
  MarkerState,
  Status,
  SystemConfig,
  SystemState,
} from "./types";

/**
 * Pure marker -> system scoring engine. No rendering, no I/O.
 * All thresholds come from the supplied config; nothing clinical is hardcoded here.
 */

/** Raw distance a value sits outside its range, normalized by the borderline margin. */
function rawDeviation(value: number, marker: MarkerConfig): number {
  const { low, high } = marker.range;
  const outside = Math.max(0, low - value, value - high);
  if (outside === 0) return 0;
  const margin = marker.borderlineMargin > 0 ? marker.borderlineMargin : 1;
  return outside / margin;
}

function classify(deviation: number, hasValue: boolean): MarkerClassification {
  if (!hasValue) return "missing";
  if (deviation === 0) return "in";
  if (deviation <= 1) return "borderline";
  return "out";
}

export function scoreMarker(
  marker: MarkerConfig,
  values: Readonly<Record<string, number | null | undefined>>,
): MarkerState {
  const raw = values[marker.key];
  const hasValue = typeof raw === "number" && Number.isFinite(raw);
  const value = hasValue ? (raw as number) : null;
  const deviation = hasValue ? rawDeviation(value as number, marker) : 0;
  return {
    key: marker.key,
    label: marker.label,
    unit: marker.unit,
    range: marker.range,
    value,
    classification: classify(deviation, hasValue),
    deviation,
    weight: marker.weight,
  };
}

const CLASS_RANK: Record<MarkerClassification, number> = {
  missing: -1,
  in: 0,
  borderline: 1,
  out: 2,
};

function statusFromClassification(c: MarkerClassification): Status {
  switch (c) {
    case "out":
      return "flag";
    case "borderline":
      return "attention";
    case "in":
      return "healthy";
    default:
      return "neutral";
  }
}

/** Map a normalized deviation onto a 0..1 emissive-intensity score. */
function normalizeScore(deviation: number): number {
  return Math.min(1, Math.max(0, deviation / 2));
}

function scoreWorstOfMarkers(markers: MarkerState[]): { status: Status; score: number } {
  const present = markers.filter((m) => m.classification !== "missing");
  if (present.length === 0) return { status: "neutral", score: 0 };

  let worst = present[0];
  for (const m of present) {
    if (CLASS_RANK[m.classification] > CLASS_RANK[worst.classification]) worst = m;
    else if (
      CLASS_RANK[m.classification] === CLASS_RANK[worst.classification] &&
      m.deviation > worst.deviation
    ) {
      worst = m;
    }
  }
  return { status: statusFromClassification(worst.classification), score: normalizeScore(worst.deviation) };
}

function scoreWeightedAverage(markers: MarkerState[]): { status: Status; score: number } {
  const present = markers.filter((m) => m.classification !== "missing");
  if (present.length === 0) return { status: "neutral", score: 0 };

  const totalWeight = present.reduce((sum, m) => sum + (m.weight > 0 ? m.weight : 0), 0);
  if (totalWeight === 0) return { status: "neutral", score: 0 };

  const weightedDeviation =
    present.reduce((sum, m) => sum + m.deviation * (m.weight > 0 ? m.weight : 0), 0) / totalWeight;

  let status: Status;
  if (weightedDeviation === 0) status = "healthy";
  else if (weightedDeviation <= 1) status = "attention";
  else status = "flag";

  return { status, score: normalizeScore(weightedDeviation) };
}

export function scoreSystem(
  system: SystemConfig,
  values: Readonly<Record<string, number | null | undefined>>,
): SystemState {
  const markers = system.markers.map((m) => scoreMarker(m, values));
  const { status, score } =
    system.scoring === "weightedAverage"
      ? scoreWeightedAverage(markers)
      : scoreWorstOfMarkers(markers);

  return {
    id: system.id,
    label: system.label,
    order: system.order,
    meshes: system.meshes,
    plainLanguage: system.plainLanguage,
    status,
    score,
    markers,
  };
}

/** Score every system in the config, sorted by presentation `order`. */
export function scoreScreening(
  config: BodySystemsConfig,
  values: Readonly<Record<string, number | null | undefined>>,
): SystemState[] {
  return [...config.systems]
    .sort((a, b) => a.order - b.order)
    .map((system) => scoreSystem(system, values));
}

/** The 1–2 markers most responsible for a system's status, worst-first. */
export function drivingMarkers(system: SystemState, limit = 2): MarkerState[] {
  return [...system.markers]
    .filter((m) => m.classification !== "missing")
    .sort((a, b) => {
      const rank = CLASS_RANK[b.classification] - CLASS_RANK[a.classification];
      return rank !== 0 ? rank : b.deviation - a.deviation;
    })
    .slice(0, limit);
}
