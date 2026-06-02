import type { MarkerState, SystemState } from "../scoring/types";
import { StatusPill } from "./StatusPill";

/** Position of a value within (and beyond) its reference range, as a 0..100% bar offset. */
function markerBar(m: MarkerState) {
  if (m.value === null) return null;
  const span = m.range.high - m.range.low || 1;
  const pct = Math.max(-0.2, Math.min(1.2, (m.value - m.range.low) / span));
  const left = `${Math.max(0, Math.min(100, pct * 100))}%`;
  const color = `var(--status-${m.classification === "in" ? "healthy" : m.classification === "borderline" ? "attention" : "flag"})`;
  return { left, color };
}

export function DetailPanel({ system }: { system: SystemState }) {
  const present = system.markers.filter((m) => m.classification !== "missing");
  return (
    <aside className="detail panel" key={system.id}>
      <StatusPill status={system.status} />
      <h2>{system.label}</h2>
      <p className="plain">{system.plainLanguage}</p>
      <div className="markers">
        {present.length === 0 && (
          <div className="marker">
            <div className="label">No markers measured for this system in this screening.</div>
          </div>
        )}
        {present.map((m) => {
          const bar = markerBar(m);
          return (
            <div className="marker" key={m.key}>
              <div className="row">
                <span className="label">{m.label}</span>
                <span className="value">
                  {m.value}
                  <small>{m.unit}</small>
                </span>
              </div>
              <div className="range">Reference {m.range.low}–{m.range.high} {m.unit}</div>
              {bar && (
                <div className="bar">
                  <i style={{ left: bar.left, width: 8, marginLeft: -4, background: bar.color, boxShadow: `0 0 8px ${bar.color}` }} />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </aside>
  );
}
