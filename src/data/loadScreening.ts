import type { DataSource, ScreeningPayload } from "./types";
import { MOCK_MEMBERS } from "./mock/members";

const SOURCE = (import.meta.env.VITE_DATA_SOURCE ?? "mock") as DataSource;

async function loadMock(memberId: string): Promise<ScreeningPayload> {
  const payload = MOCK_MEMBERS[memberId];
  if (!payload) throw new Error(`Unknown mock member: ${memberId}`);
  // Simulate a small read latency so the load/reveal sequence is observable.
  await new Promise((r) => setTimeout(r, 120));
  return payload;
}

/**
 * `api` adapter — request/response contract for the clinic screening endpoint.
 *
 *   GET {VITE_API_BASE}/screenings/{memberId}
 *   Authorization: Bearer <clinic-machine token>   // local LAN only; no patient data leaves the machine
 *
 *   200 -> {
 *     member: { id, name, age, sex, screenedAt },
 *     markers: { [markerKey: string]: number }      // keys must match body-systems.schema.json
 *   }
 *   404 -> member/screening not found
 *
 * Wire this to the real screening device endpoint when available. Until then it throws.
 */
async function loadApi(_memberId: string): Promise<ScreeningPayload> {
  throw new Error(
    "api data source not implemented — set VITE_DATA_SOURCE=mock, or wire the clinic screening endpoint in loadScreening.ts",
  );
}

/** The single integration seam between the app and screening data. */
export function loadScreening(memberId: string): Promise<ScreeningPayload> {
  return SOURCE === "api" ? loadApi(memberId) : loadMock(memberId);
}

export const activeDataSource = SOURCE;
