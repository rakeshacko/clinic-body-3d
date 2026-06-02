import { create } from "zustand";
import { scoreScreening } from "./scoring/engine";
import { bodySystemsConfig } from "./scoring/config";
import type { SystemState } from "./scoring/types";
import type { ScreeningPayload } from "./data/types";
import { loadScreening } from "./data/loadScreening";
import { MOCK_MEMBER_ORDER } from "./data/mock/members";

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

  loadMember: (memberId: string) => Promise<void>;
  next: () => void;
  prev: () => void;
  gotoOverview: () => void;
  selectIndex: (index: number) => void;
  selectSystem: (id: string) => void;
  setRevealed: (v: boolean) => void;
  toggleCredits: (open?: boolean) => void;
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

  loadMember: async (memberId) => {
    set({ loadStatus: "loading", error: null, revealed: false });
    try {
      const payload = await loadScreening(memberId);
      const systems = scoreScreening(bodySystemsConfig, payload.markers);
      set({ memberId, payload, systems, loadStatus: "ready", view: "overview", activeIndex: 0 });
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
}));

/** Convenience selector for the currently focused system (null on overview). */
export function useActiveSystem(): SystemState | null {
  return useAppStore((s) => (s.view === "system" ? (s.systems[s.activeIndex] ?? null) : null));
}

export const DEFAULT_MEMBER_ID = MOCK_MEMBER_ORDER.includes("m-002") ? "m-002" : MOCK_MEMBER_ORDER[0];
