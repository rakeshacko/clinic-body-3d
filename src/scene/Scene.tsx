import { Suspense } from "react";
import { Canvas } from "@react-three/fiber";
import { AdaptiveDpr, useGLTF } from "@react-three/drei";
import { useAppStore } from "../store";
import { SHELL_MODELS, SYSTEM_PRESENTATION, shellForMember } from "../systems/registry";
import { CameraRig } from "./CameraRig";
import { Lighting } from "./Lighting";
import { PostFX } from "./PostFX";
import { BodyShell } from "./BodyShell";
import { SystemMesh } from "./SystemMesh";

function Systems() {
  const systems = useAppStore((s) => s.systems);
  const view = useAppStore((s) => s.view);
  const activeIndex = useAppStore((s) => s.activeIndex);

  return (
    <>
      {systems.map((system, i) => {
        const presence =
          view === "overview" ? "overview" : i === activeIndex ? "focus" : "dim";
        return (
          <SystemMesh
            key={system.id}
            system={system}
            model={SYSTEM_PRESENTATION[system.id].model}
            presence={presence}
            revealIndex={i}
          />
        );
      })}
    </>
  );
}

// Warm the cache for every body-type shell so switching members doesn't suspend.
Object.values(SHELL_MODELS).forEach((m) => useGLTF.preload(m));

export function Scene() {
  const shellModel = useAppStore((s) => shellForMember(s.payload?.member));
  return (
    <div className="canvas-wrap">
      <Canvas
        gl={{ antialias: false, alpha: true, powerPreference: "high-performance" }}
        camera={{ position: [0, -0.02, 3.85], fov: 32, near: 0.1, far: 50 }}
        dpr={[1, 2]}
      >
        <fog attach="fog" args={["#05090d", 3.5, 8]} />
        <AdaptiveDpr pixelated />
        <Lighting />
        <Suspense fallback={null}>
          <BodyShell model={shellModel} />
          <Systems />
        </Suspense>
        <CameraRig />
        <PostFX />
      </Canvas>
    </div>
  );
}
