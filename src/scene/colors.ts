import { Color } from "three";
import type { Status } from "../scoring/types";

const FALLBACK: Record<Status, string> = {
  healthy: "#2fd6a8",
  attention: "#f3b34e",
  flag: "#f05a4f",
  neutral: "#5d7184",
};

const TOKEN: Record<Status, string> = {
  healthy: "--status-healthy",
  attention: "--status-attention",
  flag: "--status-flag",
  neutral: "--status-neutral",
};

const cache = new Map<Status, Color>();

/** Resolve a status to a THREE.Color from the CSS token (single source of truth). */
export function statusColor(status: Status): Color {
  const cached = cache.get(status);
  if (cached) return cached;
  let value = FALLBACK[status];
  if (typeof window !== "undefined") {
    const v = getComputedStyle(document.documentElement).getPropertyValue(TOKEN[status]).trim();
    if (v) value = v;
  }
  const c = new Color(value);
  cache.set(status, c);
  return c;
}

/**
 * Emissive intensity by status, scaled by how far the system sits outside range.
 * Healthy systems glow softly; flagged systems push harder.
 */
export function emissiveIntensity(status: Status, score: number): number {
  const base: Record<Status, number> = { healthy: 0.3, attention: 0.55, flag: 0.78, neutral: 0.14 };
  const gain: Record<Status, number> = { healthy: 0.12, attention: 0.6, flag: 1.05, neutral: 0 };
  return base[status] + gain[status] * Math.min(1, Math.max(0, score));
}
