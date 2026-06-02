import { useAppStore } from "../store";
import { usePresenter } from "../presenter/usePresenter";

export function Controls() {
  const presenter = usePresenter("wall");
  const view = useAppStore((s) => s.view);
  const activeIndex = useAppStore((s) => s.activeIndex);
  const count = useAppStore((s) => s.systems.length);

  const progress = view === "overview" ? `${count} systems` : `${activeIndex + 1} / ${count}`;

  return (
    <div className="controls panel">
      <button onClick={presenter.prev} aria-label="Previous">‹ Prev</button>
      <span className="progress">{progress}</span>
      <button onClick={presenter.next} className="primary" aria-label="Next">Next ›</button>
      <button onClick={presenter.overview} disabled={view === "overview"}>Overview</button>
    </div>
  );
}
