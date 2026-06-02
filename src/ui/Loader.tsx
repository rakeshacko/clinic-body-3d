import { useAppStore } from "../store";

export function Loader() {
  const status = useAppStore((s) => s.loadStatus);
  const error = useAppStore((s) => s.error);
  const ready = status === "ready";

  return (
    <div className={`loader${ready ? " hide" : ""}`}>
      {status === "error" ? (
        <div style={{ textAlign: "center", maxWidth: 420 }}>
          <div style={{ fontFamily: "var(--font-display)", fontSize: 20, marginBottom: 8 }}>Couldn’t load screening</div>
          <div style={{ color: "var(--ink-dim)", fontSize: 13 }}>{error}</div>
        </div>
      ) : (
        <div className="ring" />
      )}
    </div>
  );
}
