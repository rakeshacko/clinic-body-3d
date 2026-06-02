import { useEffect } from "react";
import { DEFAULT_MEMBER_ID, useAppStore } from "./store";
import { usePresenter } from "./presenter/usePresenter";
import { remoteMode } from "./presenter/protocol";

/**
 * Tablet remote (/remote). Sends presenter commands to the wall screen.
 * In local mode it syncs same-machine tabs via BroadcastChannel; with VITE_REMOTE=ws
 * it drives a separate physical tablet over the clinic LAN relay.
 */
export function Remote() {
  const presenter = usePresenter("remote");
  const loadMember = useAppStore((s) => s.loadMember);
  const systems = useAppStore((s) => s.systems);
  const activeIndex = useAppStore((s) => s.activeIndex);
  const view = useAppStore((s) => s.view);

  // Load locally so the remote can label system buttons.
  useEffect(() => {
    void loadMember(DEFAULT_MEMBER_ID);
  }, [loadMember]);

  return (
    <div className="stage">
      <div className="remote">
        <div>
          <h1>Consultation Remote</h1>
          <div style={{ color: "var(--ink-dim)", fontSize: 12 }}>
            {remoteMode === "ws" ? "Connected over clinic LAN" : "Local (same-machine) sync"}
          </div>
        </div>

        <div className="grid">
          {systems.map((s, i) => (
            <button
              key={s.id}
              onClick={() => presenter.selectIndex(i)}
              style={{
                outline: view === "system" && i === activeIndex ? "2px solid var(--accent)" : "none",
              }}
            >
              <span className="idx">System {i + 1}</span>
              <span>{s.label}</span>
              <span style={{ color: `var(--status-${s.status})`, fontSize: 12 }}>● {s.status}</span>
            </button>
          ))}
        </div>

        <div className="nav">
          <button onClick={presenter.prev}>‹ Prev</button>
          <button onClick={presenter.overview}>Overview</button>
          <button onClick={presenter.next}>Next ›</button>
        </div>
      </div>
    </div>
  );
}
