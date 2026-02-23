import { useEffect, useState } from "react";
import {
  LifeStagesConfig,
  fetchLifeStagesFallback,
  saveLifeStagesConfig,
  resetLifeStagesConfig,
} from "../api";
import { RateChartSingle, RateChartDual } from "./RateChart";

interface Props {
  config: LifeStagesConfig;
  onConfigChange: (cfg: LifeStagesConfig) => void;
}

// Apply a multiplier to a base rate array, clamping values to [0, 1]
function applyMultiplier(base: number[], multiplier: number): number[] {
  return base.map((r) => Math.min(r * multiplier, 1.0));
}

export default function LifeCycleModifiers({ config, onConfigChange }: Props) {
  const [baseConfig, setBaseConfig] = useState<LifeStagesConfig | null>(null);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Multiplier state for each rate group
  const [multipliers, setMultipliers] = useState({
    mortalityMale:   1.0,
    mortalityFemale: 1.0,
    marriageMale:    1.0,
    marriageFemale:  1.0,
    fertilityMale:   1.0,
    fertilityFemale: 1.0,
    desperation:     1.0,
  });

  // Load fallback (base) config for multiplier calculations
  useEffect(() => {
    fetchLifeStagesFallback()
      .then(setBaseConfig)
      .catch(() => setBaseConfig(null));
  }, []);

  const show = (type: "success" | "error", text: string) => {
    setFeedback({ type, text });
    setTimeout(() => setFeedback(null), 3500);
  };

  const setScalar = <K extends keyof LifeStagesConfig>(key: K, value: LifeStagesConfig[K]) => {
    onConfigChange({ ...config, [key]: value });
  };

  // Update a multiplier and propagate adjusted rates into the config
  const setMultiplier = (
    key: keyof typeof multipliers,
    value: number,
    configPath: [string, string?]
  ) => {
    if (!baseConfig) return;

    setMultipliers((prev) => ({ ...prev, [key]: value }));

    const [rateKey, sexKey] = configPath;

    if (sexKey) {
      const base = (baseConfig[rateKey] as Record<string, number[]>)[sexKey] ?? [];
      onConfigChange({
        ...config,
        [rateKey]: {
          ...(config[rateKey] as Record<string, number[]>),
          [sexKey]: applyMultiplier(base, value),
        },
      });
    } else {
      const base = (baseConfig[rateKey] as number[]) ?? [];
      onConfigChange({ ...config, [rateKey]: applyMultiplier(base, value) });
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await saveLifeStagesConfig(config);
      show("success", "Life cycle modifiers saved.");
    } catch (err) {
      show("error", String(err));
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    setSaving(true);
    try {
      await resetLifeStagesConfig();
      show("success", "Reset to fallback. Reload to see changes.");
      setMultipliers({ mortalityMale: 1, mortalityFemale: 1, marriageMale: 1, marriageFemale: 1, fertilityMale: 1, fertilityFemale: 1, desperation: 1 });
    } catch (err) {
      show("error", String(err));
    } finally {
      setSaving(false);
    }
  };

  const mortalityRates = config.mortalityRates ?? { Male: [], Female: [] };
  const marriageRates  = config.marriageRates  ?? { Male: [], Female: [] };
  const fertilityRates = config.fertilityRates ?? { Male: [], Female: [] };
  const desperationRates = (config.desperationMarriageRates as number[]) ?? [];

  return (
    <div>
      <h2>Life Cycle Modifiers</h2>

      <div className="btn-row">
        <button className="btn btn-secondary" onClick={handleReset} disabled={saving}>
          Reset to Default
        </button>
        <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
          {saving ? <span className="spinner" /> : null}
          Save Changes
        </button>
      </div>

      {feedback && <div className={`msg msg-${feedback.type}`}>{feedback.text}</div>}

      {/* Scalar inputs */}
      <div className="panel" style={{ marginTop: "0.75rem" }}>
        <h3>General Settings</h3>
        <div className="field-row">
          <div className="field">
            <label>Max Age Difference Between Spouses</label>
            <input type="number" min={0} max={30} value={config.marriageMaxAgeDifference ?? 10}
              onChange={(e) => setScalar("marriageMaxAgeDifference", Number(e.target.value))} />
          </div>
          <div className="field">
            <label>Maximum Number of Children</label>
            <input type="number" min={1} max={20} step={1} value={config.maximumNumberOfChildren ?? 8}
              onChange={(e) => setScalar("maximumNumberOfChildren", Number(e.target.value))} />
          </div>
          <div className="field">
            <label>Minimum Years Between Children</label>
            <input type="number" min={1} max={10} step={1} value={config.minimumYearsBetweenChildren ?? 2}
              onChange={(e) => setScalar("minimumYearsBetweenChildren", Number(e.target.value))} />
          </div>
        </div>
        <div className="field-row">
          <div className="field">
            <label>Male Bastard Chance</label>
            <input type="number" min={0} max={1} step={0.0005} value={config.bastardyChanceMale ?? 0.001}
              onChange={(e) => setScalar("bastardyChanceMale", Number(e.target.value))} />
          </div>
          <div className="field">
            <label>Female Bastard Chance</label>
            <input type="number" min={0} max={1} step={0.0005} value={config.bastardyChanceFemale ?? 0.001}
              onChange={(e) => setScalar("bastardyChanceFemale", Number(e.target.value))} />
          </div>
        </div>
      </div>

      {/* Rate charts with multiplier sliders */}
      <div className="panel">
        <h3>Desperation Marriage Rates</h3>
        <SliderRow
          label="Multiplier"
          value={multipliers.desperation}
          onChange={(v) => setMultiplier("desperation", v, ["desperationMarriageRates"])}
        />
        <RateChartSingle title="" rates={desperationRates} color="#d9a03a" seriesLabel="Desperation Rate" />
      </div>

      <div className="panel">
        <h3>Mortality Rates</h3>
        <SliderRow
          label="Male multiplier"
          value={multipliers.mortalityMale}
          onChange={(v) => setMultiplier("mortalityMale", v, ["mortalityRates", "Male"])}
        />
        <SliderRow
          label="Female multiplier"
          value={multipliers.mortalityFemale}
          onChange={(v) => setMultiplier("mortalityFemale", v, ["mortalityRates", "Female"])}
        />
        <RateChartDual
          title=""
          maleRates={mortalityRates.Male}
          femaleRates={mortalityRates.Female}
        />
      </div>

      <div className="panel">
        <h3>Marriage Rates</h3>
        <SliderRow
          label="Male multiplier"
          value={multipliers.marriageMale}
          onChange={(v) => setMultiplier("marriageMale", v, ["marriageRates", "Male"])}
        />
        <SliderRow
          label="Female multiplier"
          value={multipliers.marriageFemale}
          onChange={(v) => setMultiplier("marriageFemale", v, ["marriageRates", "Female"])}
        />
        <RateChartDual
          title=""
          maleRates={marriageRates.Male}
          femaleRates={marriageRates.Female}
        />
      </div>

      <div className="panel">
        <h3>Fertility Rates</h3>
        <SliderRow
          label="Male multiplier"
          value={multipliers.fertilityMale}
          onChange={(v) => setMultiplier("fertilityMale", v, ["fertilityRates", "Male"])}
        />
        <SliderRow
          label="Female multiplier"
          value={multipliers.fertilityFemale}
          onChange={(v) => setMultiplier("fertilityFemale", v, ["fertilityRates", "Female"])}
        />
        <RateChartDual
          title=""
          maleRates={fertilityRates.Male}
          femaleRates={fertilityRates.Female}
        />
      </div>
    </div>
  );
}

// Inline slider sub-component used only here
function SliderRow({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <div className="slider-row" style={{ marginBottom: "0.5rem" }}>
      <label style={{ minWidth: 180, margin: 0 }}>{label}</label>
      <input
        type="range"
        min={0}
        max={2}
        step={0.01}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        style={{ flex: 1 }}
      />
      <span className="slider-value">{value.toFixed(2)}</span>
    </div>
  );
}