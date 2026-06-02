import type { Status } from "../scoring/types";

const LABEL: Record<Status, string> = {
  healthy: "In range",
  attention: "Worth watching",
  flag: "Needs attention",
  neutral: "Not measured",
};

export function StatusPill({ status }: { status: Status }) {
  const color = `var(--status-${status})`;
  return (
    <span className="status-pill" style={{ color, background: `color-mix(in srgb, ${color} 14%, transparent)` }}>
      <span className="dot" style={{ background: color }} />
      {LABEL[status]}
    </span>
  );
}
