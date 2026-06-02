import raw from "../../config/body-systems.schema.json";
import type { BodySystemsConfig } from "./types";

/**
 * The clinical mapping is the one human-owned input. It is imported as JSON and
 * narrowed to our config type here so the rest of the app sees a typed value.
 */
export const bodySystemsConfig = raw as unknown as BodySystemsConfig;

export function getSystemConfig(id: string) {
  return bodySystemsConfig.systems.find((s) => s.id === id);
}
