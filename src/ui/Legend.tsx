import { useAppStore } from "../store";
import { usePresenter } from "../presenter/usePresenter";

export function Legend() {
  const systems = useAppStore((s) => s.systems);
  const presenter = usePresenter("wall");

  return (
    <div className="legend panel">
      <span className="title">Body systems</span>
      <ul>
        {systems.map((s, i) => (
          <li key={s.id} onClick={() => presenter.selectIndex(i)}>
            <span className="dot" style={{ color: `var(--status-${s.status})`, background: `var(--status-${s.status})` }} />
            {s.label}
          </li>
        ))}
      </ul>
    </div>
  );
}
