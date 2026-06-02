import { BODY_FIT_PRESETS, type BodyFitParamKey, type OrganFitTuning } from "../bodyFit";
import { useAppStore } from "../store";

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

const ORGAN_PARAM_LABELS: Array<[keyof OrganFitTuning, string]> = [
  ["heightResponse", "Organ height"],
  ["torsoResponse", "Organ width"],
  ["depthResponse", "Organ depth"],
  ["placementResponse", "Placement"],
];

function Slider({
  label,
  value,
  min = 0,
  max = 1,
  step = 0.01,
  onChange,
}: {
  label: string;
  value: number;
  min?: number;
  max?: number;
  step?: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="fit-slider">
      <span>
        {label}
        <b>{value.toFixed(2)}</b>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </label>
  );
}

export function BodyFitPanel() {
  const open = useAppStore((s) => s.bodyFitOpen);
  const useAnnyShell = useAppStore((s) => s.useAnnyShell);
  const bodyPresetId = useAppStore((s) => s.bodyPresetId);
  const bodyFit = useAppStore((s) => s.bodyFit);
  const organFit = useAppStore((s) => s.organFit);
  const toggleBodyFit = useAppStore((s) => s.toggleBodyFit);
  const setUseAnnyShell = useAppStore((s) => s.setUseAnnyShell);
  const applyBodyPreset = useAppStore((s) => s.applyBodyPreset);
  const setBodyFitParam = useAppStore((s) => s.setBodyFitParam);
  const setOrganFitParam = useAppStore((s) => s.setOrganFitParam);

  if (!open) return null;

  return (
    <aside className="body-fit-panel panel">
      <div className="fit-head">
        <div>
          <div className="eyebrow">Body fit</div>
          <h2>Anny tuning</h2>
        </div>
        <button className="icon-btn" onClick={() => toggleBodyFit(false)}>Close</button>
      </div>

      <div className="fit-row">
        <label>
          Preset
          <select value={bodyPresetId} onChange={(e) => applyBodyPreset(e.target.value)}>
            {bodyPresetId === "custom" && <option value="custom">Custom</option>}
            {BODY_FIT_PRESETS.map((preset) => (
              <option key={preset.id} value={preset.id}>{preset.label}</option>
            ))}
          </select>
        </label>
        <label className="fit-toggle">
          <input
            type="checkbox"
            checked={useAnnyShell}
            onChange={(e) => setUseAnnyShell(e.target.checked)}
          />
          Anny shell
        </label>
      </div>

      <div className="fit-section">
        <div className="fit-title">Outer body</div>
        {BODY_PARAM_LABELS.map(([key, label]) => (
          <Slider
            key={key}
            label={label}
            value={bodyFit[key]}
            onChange={(value) => setBodyFitParam(key, value)}
          />
        ))}
      </div>

      <div className="fit-section">
        <div className="fit-title">Organ response</div>
        {ORGAN_PARAM_LABELS.map(([key, label]) => (
          <Slider
            key={key}
            label={label}
            value={organFit[key]}
            min={0}
            max={1.5}
            onChange={(value) => setOrganFitParam(key, value)}
          />
        ))}
      </div>
    </aside>
  );
}
