/** Data-integration contract. The screening device/instrument integration itself is out of scope. */

export interface Marker {
  /** Stable key matching a marker `key` in body-systems.schema.json. */
  key: string;
  value: number;
}

import type { BodyType } from "../systems/registry";

export interface MemberMeta {
  id: string;
  name: string;
  age: number;
  sex: "male" | "female" | "other";
  screenedAt: string; // ISO date
  /** Optional skin-envelope override. If absent, the shell is derived from sex + age. */
  bodyType?: BodyType;
}

export interface ScreeningPayload {
  member: MemberMeta;
  /** Flat map of marker key -> numeric value. Missing keys are scored as neutral. */
  markers: Record<string, number>;
}

export type DataSource = "mock" | "api";
