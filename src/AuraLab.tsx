import { Suspense, useEffect } from "react";
import { Canvas } from "@react-three/fiber";
import { AdaptiveDpr, OrbitControls } from "@react-three/drei";
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
      <ambientLight intensity={0.72} color="#fff6ee" />
      <directionalLight position={[-2.4, 2.8, 2.6]} intensity={0.95} color="#9edfff" />
      <directionalLight position={[2.2, 1.4, 1.8]} intensity={0.82} color="#ff8fa8" />
      <pointLight position={[0.16, 0.62, 0.46]} intensity={0.8} color="#ffd665" distance={1.7} />
      <pointLight position={[-0.52, -0.2, 0.5]} intensity={0.62} color="#6fd4ff" distance={2.2} />
    </>
  );
}

function AuraScene() {
  return (
    <div className="aura-canvas">
      <Canvas
        gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
        camera={{ position: [0.05, 0.12, 4.15], fov: 28, near: 0.1, far: 40 }}
        dpr={[1, 2]}
      >
        <fog attach="fog" args={["#fff7ef", 3.3, 7.2]} />
        <AdaptiveDpr />
        <AuraLights />
        <Suspense fallback={null}>
          <group rotation={[0, -0.22, 0]} position={[0, -0.05, 0]}>
            <BodyShell model={SHELL_MODELS.neutral} materialMode="aura" />
          </group>
        </Suspense>
        <OrbitControls
          makeDefault
          enablePan={false}
          minDistance={3.0}
          maxDistance={5.2}
          target={[0, 0.05, 0]}
          autoRotate
          autoRotateSpeed={0.18}
        />
        <EffectComposer multisampling={0} enableNormalPass={false}>
          <Bloom
            intensity={0.34}
            luminanceThreshold={0.18}
            luminanceSmoothing={0.7}
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
