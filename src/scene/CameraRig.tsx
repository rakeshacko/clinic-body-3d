import { useEffect, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { CameraControls } from "@react-three/drei";
import { useAppStore } from "../store";
import { OVERVIEW_FRAMING, SYSTEM_PRESENTATION } from "../systems/registry";
import type { Framing } from "../systems/registry";

/** Damped camera rig that tweens to each system; slow auto-rotate when idle on overview. */
export function CameraRig() {
  const controls = useRef<CameraControls>(null);
  const view = useAppStore((s) => s.view);
  const activeIndex = useAppStore((s) => s.activeIndex);
  const systems = useAppStore((s) => s.systems);
  const revealed = useAppStore((s) => s.revealed);

  // Move the camera whenever the focused target changes.
  useEffect(() => {
    const c = controls.current;
    if (!c || !revealed) return;
    let framing: Framing = OVERVIEW_FRAMING;
    if (view === "system") {
      const sys = systems[activeIndex];
      if (sys) framing = SYSTEM_PRESENTATION[sys.id].framing;
    }
    const [px, py, pz] = framing.position;
    const [tx, ty, tz] = framing.target;
    c.setLookAt(px, py, pz, tx, ty, tz, true);
  }, [view, activeIndex, systems, revealed]);

  // Slow auto-rotate on the overview.
  useFrame((_, dt) => {
    if (view === "overview" && revealed && controls.current) {
      controls.current.rotate(0.12 * dt, 0, false);
    }
  });

  return (
    <CameraControls
      ref={controls}
      makeDefault
      smoothTime={0.7}
      draggingSmoothTime={0.25}
      minDistance={0.6}
      maxDistance={3.2}
    />
  );
}
