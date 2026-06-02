import type { ScreeningPayload } from "../types";

/**
 * Three mock members so the app runs end-to-end with zero external dependency.
 * Marker keys match config/body-systems.schema.json.
 */

const allHealthy: ScreeningPayload = {
  member: { id: "m-001", name: "Asha Rao", age: 34, sex: "female", screenedAt: "2026-05-20", bodyType: "female-young" },
  markers: {
    ldl: 82, hdl: 64, triglycerides: 95, bp_systolic: 112, bp_diastolic: 72,
    alt: 24, ast: 22, bilirubin_total: 0.6, albumin: 4.4,
    hba1c: 5.1, glucose_fasting: 88, tsh: 1.8,
    spo2: 98, fev1_pct: 102,
    creatinine: 0.8, egfr: 110, bun: 12,
    vitamin_b12: 540, vitamin_d: 48,
    calcium: 9.4,
  },
};

const metabolicFlags: ScreeningPayload = {
  member: { id: "m-002", name: "Vikram Shah", age: 47, sex: "male", screenedAt: "2026-05-21", bodyType: "male-heavy" },
  markers: {
    ldl: 168, hdl: 38, triglycerides: 210, bp_systolic: 128, bp_diastolic: 84,
    alt: 41, ast: 38, bilirubin_total: 0.7, albumin: 4.2,
    hba1c: 6.8, glucose_fasting: 132, tsh: 2.4,
    spo2: 97, fev1_pct: 96,
    creatinine: 1.0, egfr: 96, bun: 16,
    vitamin_b12: 420, vitamin_d: 36,
    calcium: 9.2,
  },
};

const mixed: ScreeningPayload = {
  member: { id: "m-003", name: "Meera Iyer", age: 52, sex: "female", screenedAt: "2026-05-22", bodyType: "female-older" },
  markers: {
    ldl: 122, hdl: 44, triglycerides: 160, bp_systolic: 134, bp_diastolic: 86,
    alt: 28, ast: 26, bilirubin_total: 0.5, albumin: 4.3,
    hba1c: 5.5, glucose_fasting: 94, tsh: 2.1,
    spo2: 98, fev1_pct: 99,
    creatinine: 0.9, egfr: 102, bun: 14,
    vitamin_b12: 380, vitamin_d: 16,
    calcium: 9.1,
  },
};

export const MOCK_MEMBERS: Record<string, ScreeningPayload> = {
  "m-001": allHealthy,
  "m-002": metabolicFlags,
  "m-003": mixed,
};

export const MOCK_MEMBER_ORDER = ["m-001", "m-002", "m-003"] as const;
