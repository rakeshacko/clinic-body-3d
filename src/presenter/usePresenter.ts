import { useCallback, useEffect } from "react";
import { useAppStore } from "../store";
import { presenterChannel, type PresenterCommand } from "./protocol";

/** Apply a presenter command to the local store. */
function apply(cmd: PresenterCommand) {
  const s = useAppStore.getState();
  switch (cmd.type) {
    case "NEXT": return s.next();
    case "PREV": return s.prev();
    case "OVERVIEW": return s.gotoOverview();
    case "SELECT_INDEX": return s.selectIndex(cmd.index);
    case "SELECT_SYSTEM": return s.selectSystem(cmd.id);
    case "LOAD_MEMBER": return void s.loadMember(cmd.memberId);
  }
}

/**
 * Presenter controller. Returns command dispatchers that update local state AND
 * broadcast to any connected remote/wall peer. Also subscribes to inbound commands
 * and binds clinic-clicker-friendly keyboard shortcuts.
 *
 * `role`:
 *  - "wall"   listens for remote commands and applies them (also reacts to local keys).
 *  - "remote" sends commands; it does not need to render the scene.
 */
export function usePresenter(role: "wall" | "remote" = "wall") {
  const dispatch = useCallback((cmd: PresenterCommand) => {
    apply(cmd);
    presenterChannel.send(cmd);
  }, []);

  // Inbound commands from peers.
  useEffect(() => presenterChannel.subscribe(apply), []);

  // Keyboard bindings (both roles, so a keyboard on either device works).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      switch (e.key) {
        case "ArrowRight":
        case "PageDown":
        case " ":
          e.preventDefault();
          dispatch({ type: "NEXT" });
          break;
        case "ArrowLeft":
        case "PageUp":
          e.preventDefault();
          dispatch({ type: "PREV" });
          break;
        case "Escape":
        case "Home":
          dispatch({ type: "OVERVIEW" });
          break;
        default:
          if (/^[1-8]$/.test(e.key)) dispatch({ type: "SELECT_INDEX", index: Number(e.key) - 1 });
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [dispatch, role]);

  return {
    next: () => dispatch({ type: "NEXT" }),
    prev: () => dispatch({ type: "PREV" }),
    overview: () => dispatch({ type: "OVERVIEW" }),
    selectIndex: (index: number) => dispatch({ type: "SELECT_INDEX", index }),
    selectSystem: (id: string) => dispatch({ type: "SELECT_SYSTEM", id }),
    loadMember: (memberId: string) => dispatch({ type: "LOAD_MEMBER", memberId }),
  };
}
