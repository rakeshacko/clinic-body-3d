import { Suspense, useEffect } from "react";
import { Canvas } from "@react-three/fiber";
import { AdaptiveDpr, OrbitControls } from "@react-three/drei";
import { AdditiveBlending } from "three";
import { Bloom, EffectComposer, SMAA } from "@react-three/postprocessing";
import { KernelSize } from "postprocessing";
import { BODY_FIT_PRESETS, type BodyFitParamKey } from "./bodyFit";
import { useAppStore } from "./store";
import { BodyShell } from "./scene/BodyShell";
import { SHELL_MODELS } from "./systems/registry";

const BODY_PARAM_LABELS: Array<[BodyFitParamKey, string]> = [
  ["gender", "Sex shape"],
  ["age", "Age"],
  ["height", "Height"],
  ["weight", "Adiposity"],
  ["muscle", "Muscle"],
  ["proportions", "Proportions"],
  ["torsoWidth", "Torso width"],
  ["torsoDepth", "Ribcage depth"],
  ["abdomen", "Abdomen"],
  ["hips", "Hips"],
  ["centrality", "Central fat"],
];

function AuraLights() {
  return (
    <>
      <ambientLight intensity={1.5} color="#fff8ef" />
      <directionalLight position={[-2.4, 2.8, 2.6]} intensity={2.1} color="#b9edff" />
      <directionalLight position={[2.2, 1.4, 1.8]} intensity={1.8} color="#ff96ae" />
      <pointLight position={[0.18, 0.58, 0.42]} intensity={2.2} color="#ffd55a" distance={1.4} />
      <pointLight position={[-0.55, -0.28, 0.5]} intensity={1.35} color="#65cfff" distance={1.9} />
    </>
  );
}

function AuraGlow() {
  return (
    <group>
      <mesh position={[0.14, 0.56, 0.22]} scale={[0.2, 0.3, 0.16]}>
        <sphereGeometry args={[1, 48, 32]} />
        <meshBasicMaterial color="#ffd45b" transparent opacity={0.32} depthWrite={false} blending={AdditiveBlending} />
      </mesh>
      <mesh position={[0.22, 0.51, 0.18]} scale={[0.18, 0.25, 0.14]}>
        <sphereGeometry args={[1, 48, 32]} />
        <meshBasicMaterial color="#ff7f95" transparent opacity={0.24} depthWrite={false} blending={AdditiveBlending} />
      </mesh>
      <mesh position={[-0.34, -0.18, 0.05]} scale={[0.48, 0.72, 0.2]}>
        <sphereGeometry args={[1, 48, 32]} />
        <meshBasicMaterial color="#72d8ff" transparent opacity={0.14} depthWrite={false} blending={AdditiveBlending} />
      </mesh>
    </group>
  );
}

function AuraScene() {
  return (
    <div className="aura-canvas">
      <Canvas
        gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
        camera={{ position: [0, 0.08, 2.55], fov: 28, near: 0.1, far: 40 }}
        dpr={[1, 2]}
      >
        <fog attach="fog" args={["#fff7ef", 1.85, 5.2]} />
        <AdaptiveDpr />
        <AuraLights />
        <Suspense fallback={null}>
          <group rotation={[0, -0.16, 0]} position={[0, -0.02, 0]}>
            <BodyShell model={SHELL_MODELS.neutral} materialMode="aura" />
            <AuraGlow />
          </group>
        </Suspense>
        <OrbitControls
          makeDefault
          enablePan={false}
          minDistance={1.75}
          maxDistance={4.2}
          target={[0, 0.03, 0]}
          autoRotate
          autoRotateSpeed={0.28}
        />
        <EffectComposer multisampling={0} enableNormalPass={false}>
          <Bloom
            intensity={0.9}
            luminanceThreshold={0.08}
            luminanceSmoothing={0.55}
            mipmapBlur
            kernelSize={KernelSize.HUGE}
          />
          <SMAA />
        </EffectComposer>
      </Canvas>
    </div>
  );
}

function ParamSlider({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="aura-slider">
      <span>
        {label}
        <b>{value.toFixed(2)}</b>
      </span>
      <input type="range" min={0} max={1} step={0.01} value={value} onChange={(e) => onChange(Number(e.target.value))} />
    </label>
  );
}

function AuraControls() {
  const bodyPresetId = useAppStore((s) => s.bodyPresetId);
  const bodyFit = useAppStore((s) => s.bodyFit);
  const applyBodyPreset = useAppStore((s) => s.applyBodyPreset);
  const setBodyFitParam = useAppStore((s) => s.setBodyFitParam);

  return (
    <aside className="aura-panel">
      <div className="aura-panel-head">
        <div>
          <div className="aura-kicker">Anny body lab</div>
          <h1>Soft aura material</h1>
        </div>
        <a href="/" className="aura-link">Review</a>
      </div>

      <label className="aura-select">
        Preset
        <select value={bodyPresetId} onChange={(e) => applyBodyPreset(e.target.value)}>
          {bodyPresetId === "custom" && <option value="custom">Custom</option>}
          {BODY_FIT_PRESETS.map((preset) => (
            <option key={preset.id} value={preset.id}>{preset.label}</option>
          ))}
        </select>
      </label>

      <div className="aura-sliders">
        {BODY_PARAM_LABELS.map(([key, label]) => (
          <ParamSlider key={key} label={label} value={bodyFit[key]} onChange={(value) => setBodyFitParam(key, value)} />
        ))}
      </div>
    </aside>
  );
}

export function AuraLab() {
  const setRevealed = useAppStore((s) => s.setRevealed);
  const setUseAnnyShell = useAppStore((s) => s.setUseAnnyShell);

  useEffect(() => {
    setUseAnnyShell(true);
    setRevealed(true);
  }, [setRevealed, setUseAnnyShell]);

  return (
    <div className="aura-stage">
      <AuraScene />
      <AuraControls />
    </div>
  );
}
