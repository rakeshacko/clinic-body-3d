import { useEffect } from "react";
import { Scene } from "./scene/Scene";
import { TopBar } from "./ui/TopBar";
import { Controls } from "./ui/Controls";
import { Legend } from "./ui/Legend";
import { DetailPanel } from "./ui/DetailPanel";
import { Credits } from "./ui/Credits";
import { Loader } from "./ui/Loader";
import { DEFAULT_MEMBER_ID, useActiveSystem, useAppStore } from "./store";
import { usePresenter } from "./presenter/usePresenter";

/** Wall-screen / kiosk view. */
export function App() {
  // Bind keyboard + remote sync at the top level.
  usePresenter("wall");
  const loadMember = useAppStore((s) => s.loadMember);
  const view = useAppStore((s) => s.view);
  const activeSystem = useActiveSystem();

  useEffect(() => {
    void loadMember(DEFAULT_MEMBER_ID);
  }, [loadMember]);

  return (
    <div className="stage">
      <Scene />
      <TopBar />
      <aside className="sidebar">
        {view === "overview" ? <Legend /> : activeSystem && <DetailPanel system={activeSystem} />}
      </aside>
      <Controls />
      <Credits />
      <Loader />
    </div>
  );
}
