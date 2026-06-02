import { create } from "zustand";
import { scoreScreening } from "./scoring/engine";
import { bodySystemsConfig } from "./scoring/config";
import type { SystemState } from "./scoring/types";
import type { ScreeningPayload } from "./data/types";
import { loadScreening } from "./data/loadScreening";
import { MOCK_MEMBER_ORDER } from "./data/mock/members";
import {
  BODY_FIT_PRESETS,
  DEFAULT_BODY_FIT,
  DEFAULT_ORGAN_FIT,
  bodyFitForMember,
  sanitizeBodyFit,
  type BodyFitParamKey,
  type BodyFitParams,
  type OrganFitTuning,
} from "./bodyFit";

export type ViewMode = "overview" | "system";

interface AppState {
  loadStatus: "idle" | "loading" | "ready" | "error";
  error: string | null;
  memberId: string | null;
  payload: ScreeningPayload | null;
  /** Scored systems, sorted by presentation order. */
  systems: SystemState[];
  view: ViewMode;
  /** Index into `systems` when view === "system". */
  activeIndex: number;
  /** Drives the staggered light-up cascade after the shell fades in. */
  revealed: boolean;
  creditsOpen: boolean;
  bodyFitOpen: boolean;
  useAnnyShell: boolean;
  bodyPresetId: string;
  bodyFit: BodyFitParams;
  organFit: OrganFitTuning;

  loadMember: (memberId: string) => Promise<void>;
  next: () => void;
  prev: () => void;
  gotoOverview: () => void;
  selectIndex: (index: number) => void;
  selectSystem: (id: string) => void;
  setRevealed: (v: boolean) => void;
  toggleCredits: (open?: boolean) => void;
  toggleBodyFit: (open?: boolean) => void;
  setUseAnnyShell: (v: boolean) => void;
  applyBodyPreset: (presetId: string) => void;
  setBodyFitParam: (key: BodyFitParamKey, value: number) => void;
  setOrganFitParam: (key: keyof OrganFitTuning, value: number) => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  loadStatus: "idle",
  error: null,
  memberId: null,
  payload: null,
  systems: [],
  view: "overview",
  activeIndex: 0,
  revealed: false,
  creditsOpen: false,
  bodyFitOpen: false,
  useAnnyShell: true,
  bodyPresetId: "male-central",
  bodyFit: DEFAULT_BODY_FIT,
  organFit: DEFAULT_ORGAN_FIT,

  loadMember: async (memberId) => {
    set({ loadStatus: "loading", error: null, revealed: false });
    try {
      const payload = await loadScreening(memberId);
      const systems = scoreScreening(bodySystemsConfig, payload.markers);
      const preset = bodyFitForMember(payload.member);
      set({
        memberId,
        payload,
        systems,
        loadStatus: "ready",
        view: "overview",
        activeIndex: 0,
        bodyPresetId: preset.id,
        bodyFit: sanitizeBodyFit(preset.params),
      });
      // Stagger the reveal one tick after data lands so the scene can mount first.
      requestAnimationFrame(() => set({ revealed: true }));
    } catch (e) {
      set({ loadStatus: "error", error: e instanceof Error ? e.message : String(e) });
    }
  },

  next: () => {
    const { view, activeIndex, systems } = get();
    if (systems.length === 0) return;
    if (view === "overview") {
      set({ view: "system", activeIndex: 0 });
    } else if (activeIndex >= systems.length - 1) {
      set({ view: "overview" });
    } else {
      set({ activeIndex: activeIndex + 1 });
    }
  },

  prev: () => {
    const { view, activeIndex, systems } = get();
    if (systems.length === 0) return;
    if (view === "overview") {
      set({ view: "system", activeIndex: systems.length - 1 });
    } else if (activeIndex <= 0) {
      set({ view: "overview" });
    } else {
      set({ activeIndex: activeIndex - 1 });
    }
  },

  gotoOverview: () => set({ view: "overview" }),

  selectIndex: (index) => {
    const { systems } = get();
    if (index < 0 || index >= systems.length) return;
    set({ view: "system", activeIndex: index });
  },

  selectSystem: (id) => {
    const idx = get().systems.findIndex((s) => s.id === id);
    if (idx >= 0) set({ view: "system", activeIndex: idx });
  },

  setRevealed: (v) => set({ revealed: v }),
  toggleCredits: (open) => set((s) => ({ creditsOpen: open ?? !s.creditsOpen })),
  toggleBodyFit: (open) => set((s) => ({ bodyFitOpen: open ?? !s.bodyFitOpen })),
  setUseAnnyShell: (v) => set({ useAnnyShell: v }),
  applyBodyPreset: (presetId) => {
    const preset = BODY_FIT_PRESETS.find((p) => p.id === presetId);
    if (!preset) return;
    set({ bodyPresetId: preset.id, bodyFit: sanitizeBodyFit(preset.params) });
  },
  setBodyFitParam: (key, value) =>
    set((s) => ({
      bodyPresetId: "custom",
      bodyFit: sanitizeBodyFit({ ...s.bodyFit, [key]: value }),
    })),
  setOrganFitParam: (key, value) =>
    set((s) => ({
      organFit: { ...s.organFit, [key]: Math.max(0, Math.min(1.5, value)) },
    })),
}));

/** Convenience selector for the currently focused system (null on overview). */
export function useActiveSystem(): SystemState | null {
  return useAppStore((s) => (s.view === "system" ? (s.systems[s.activeIndex] ?? null) : null));
}

export const DEFAULT_MEMBER_ID = MOCK_MEMBER_ORDER.includes("m-002") ? "m-002" : MOCK_MEMBER_ORDER[0];
