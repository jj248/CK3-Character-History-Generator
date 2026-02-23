import { useState } from "react";
import {
  Dynasty,
  InitializationConfig,
  NameInheritance,
  saveInitializationConfig,
  resetInitializationConfig,
  setInitializationFallback,
  streamSimulation,
  SimulationMessage,
} from "../api";

// ---------------------------------------------------------------------------
//  Constants
// ---------------------------------------------------------------------------

const GENDER_LAW_OPTIONS = [
  "AGNATIC",
  "AGNATIC_COGNATIC",
  "ABSOLUTE_COGNATIC",
  "ENATIC_COGNATIC",
  "ENATIC",
];

const SUCCESSION_OPTIONS = ["PRIMOGENITURE", "ULTIMOGENITURE", "SENIORITY"];

const DEFAULT_NAME_INHERITANCE: NameInheritance = {
  grandparentNameInheritanceChance: 0.05,
  parentNameInheritanceChance: 0.05,
  noNameInheritanceChance: 0.9,
};

const EMPTY_DYNASTY: Dynasty = {
  dynastyID: "",
  dynastyName: "",
  dynastyMotto: "",
  succession: "PRIMOGENITURE",
  isHouse: false,
  faithID: "",
  cultureID: "",
  gender_law: "AGNATIC_COGNATIC",
  progenitorMaleBirthYear: 6000,
  allowFirstCousinMarriage: false,
  prioritiseLowbornMarriage: false,
  nameInheritance: { ...DEFAULT_NAME_INHERITANCE },
};

// ---------------------------------------------------------------------------
//  DynastyForm - shared form for add and edit
// ---------------------------------------------------------------------------

interface DynastyFormProps {
  value: Dynasty;
  onChange: (d: Dynasty) => void;
}

function DynastyForm({ value, onChange }: DynastyFormProps) {
  const set = <K extends keyof Dynasty>(key: K, val: Dynasty[K]) =>
    onChange({ ...value, [key]: val });

  const setLanguage = (idx: number, part: "id" | "start" | "end", raw: string) => {
    const langs = [...(value.languages ?? [])];
    const parts = (langs[idx] ?? "new_lang,0,0").split(",");
    if (part === "id")    parts[0] = raw;
    if (part === "start") parts[1] = raw;
    if (part === "end")   parts[2] = raw;
    langs[idx] = parts.join(",");
    set("languages", langs);
  };

  const addLanguage = () =>
    set("languages", [...(value.languages ?? []), "new_lang,0,0"]);

  const removeLanguage = (idx: number) =>
    set("languages", (value.languages ?? []).filter((_, i) => i !== idx));

  return (
    <div>
      <div className="field-row">
        <div className="field">
          <label>Dynasty ID</label>
          <input type="text" value={value.dynastyID} onChange={(e) => set("dynastyID", e.target.value)} />
        </div>
        <div className="field">
          <label>Dynasty Name</label>
          <input type="text" value={value.dynastyName} onChange={(e) => set("dynastyName", e.target.value)} />
        </div>
        <div className="field">
          <label>Dynasty Motto</label>
          <input type="text" value={value.dynastyMotto} onChange={(e) => set("dynastyMotto", e.target.value)} />
        </div>
      </div>

      <div className="field-row">
        <div className="field">
          <label>Faith ID</label>
          <input type="text" value={value.faithID} onChange={(e) => set("faithID", e.target.value)} />
        </div>
        <div className="field">
          <label>Culture ID</label>
          <input type="text" value={value.cultureID} onChange={(e) => set("cultureID", e.target.value)} />
        </div>
        <div className="field">
          <label>Progenitor Birth Year</label>
          <input type="number" step={1} value={value.progenitorMaleBirthYear}
            onChange={(e) => set("progenitorMaleBirthYear", Number(e.target.value))} />
        </div>
      </div>

      <div className="field-row">
        <div className="field">
          <label>Succession</label>
          <select value={value.succession} onChange={(e) => set("succession", e.target.value)}>
            {SUCCESSION_OPTIONS.map((o) => <option key={o}>{o}</option>)}
          </select>
        </div>
        <div className="field">
          <label>Gender Law</label>
          <select value={value.gender_law} onChange={(e) => set("gender_law", e.target.value)}>
            {GENDER_LAW_OPTIONS.map((o) => <option key={o}>{o}</option>)}
          </select>
        </div>
      </div>

      <div className="field-row">
        <label className="checkbox-field">
          <input type="checkbox" checked={value.isHouse} onChange={(e) => set("isHouse", e.target.checked)} />
          Is House (cadet branch)
        </label>
        <label className="checkbox-field">
          <input type="checkbox" checked={value.allowFirstCousinMarriage} onChange={(e) => set("allowFirstCousinMarriage", e.target.checked)} />
          Allow First Cousin Marriage
        </label>
        <label className="checkbox-field">
          <input type="checkbox" checked={value.prioritiseLowbornMarriage} onChange={(e) => set("prioritiseLowbornMarriage", e.target.checked)} />
          Prioritise Lowborn Marriage
        </label>
      </div>

      {/* Numenor blood tier */}
      <div className="field" style={{ marginTop: "0.5rem" }}>
        <label>Numenor Blood Tier (0 = none)</label>
        <input
          type="number" min={0} max={10} step={1}
          value={value.numenorBloodTier ?? 0}
          onChange={(e) => {
            const v = Number(e.target.value);
            const updated = { ...value };
            if (v === 0) delete updated.numenorBloodTier;
            else updated.numenorBloodTier = v;
            onChange(updated);
          }}
        />
      </div>

      {/* Languages */}
      <div style={{ marginTop: "0.75rem" }}>
        <label style={{ marginBottom: "0.4rem" }}>Languages (format: language_id, start year, end year)</label>
        {(value.languages ?? []).map((entry, idx) => {
          const [lid = "", start = "0", end = "0"] = entry.split(",");
          return (
            <div key={idx} style={{ display: "grid", gridTemplateColumns: "3fr 1fr 1fr auto", gap: "0.5rem", marginBottom: "0.4rem" }}>
              <input type="text" value={lid.trim()} placeholder="language_id"
                onChange={(e) => setLanguage(idx, "id", e.target.value)} />
              <input type="number" step={1} value={Number(start.trim())} placeholder="start"
                onChange={(e) => setLanguage(idx, "start", e.target.value)} />
              <input type="number" step={1} value={Number(end.trim())} placeholder="end"
                onChange={(e) => setLanguage(idx, "end", e.target.value)} />
              <button className="btn btn-danger btn-sm" onClick={() => removeLanguage(idx)}>
                Remove
              </button>
            </div>
          );
        })}
        <button className="btn btn-secondary btn-sm" onClick={addLanguage}>
          Add Language
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
//  Main component
// ---------------------------------------------------------------------------

interface Props {
  config: InitializationConfig;
  onConfigChange: (cfg: InitializationConfig) => void;
}

export default function DynastySettings({ config, onConfigChange }: Props) {
  const [saving, setSaving] = useState(false);
  const [simRunning, setSimRunning] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [newDynasty, setNewDynasty] = useState<Dynasty>({ ...EMPTY_DYNASTY, nameInheritance: { ...DEFAULT_NAME_INHERITANCE } });
  const [addOpen, setAddOpen] = useState(false);
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);

  const show = (type: "success" | "error", text: string) => {
    setFeedback({ type, text });
    setTimeout(() => setFeedback(null), 3500);
  };

  const dynasties = [...config.dynasties].sort((a, b) =>
    (a.dynastyID ?? "").localeCompare(b.dynastyID ?? "")
  );

  const updateDynasties = (updated: Dynasty[]) => {
    onConfigChange({ ...config, dynasties: updated });
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await saveInitializationConfig({ ...config, dynasties });
      show("success", "Dynasty settings saved.");
    } catch (err) {
      show("error", String(err));
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    setSaving(true);
    try {
      await resetInitializationConfig();
      show("success", "Settings reset to fallback. Reload to see changes.");
    } catch (err) {
      show("error", String(err));
    } finally {
      setSaving(false);
    }
  };

  const handleSetFallback = async () => {
    setSaving(true);
    try {
      await saveInitializationConfig({ ...config, dynasties });
      await setInitializationFallback();
      show("success", "Current settings saved as new fallback.");
    } catch (err) {
      show("error", String(err));
    } finally {
      setSaving(false);
    }
  };

  const handleAddDynasty = () => {
    updateDynasties([...dynasties, { ...newDynasty }]);
    setNewDynasty({ ...EMPTY_DYNASTY, nameInheritance: { ...DEFAULT_NAME_INHERITANCE } });
    setAddOpen(false);
  };

  const handleDeleteDynasty = (idx: number) => {
    updateDynasties(dynasties.filter((_, i) => i !== idx));
    if (expandedIdx === idx) setExpandedIdx(null);
  };

  const handleEditDynasty = (idx: number, updated: Dynasty) => {
    updateDynasties(dynasties.map((d, i) => (i === idx ? updated : d)));
  };

  const handleDeleteAll = () => {
    onConfigChange({ ...config, dynasties: [] });
  };

  const handleRunSimulation = () => {
    setLogs([]);
    setSimRunning(true);

    const cancel = streamSimulation(
      (msg: SimulationMessage) => {
        if (msg.log)   setLogs((prev) => [...prev, msg.log!]);
        if (msg.error) setLogs((prev) => [...prev, `ERROR: ${msg.error!}`]);
      },
      () => setSimRunning(false),
      (err) => {
        setLogs((prev) => [...prev, `ERROR: ${err.message}`]);
        setSimRunning(false);
      }
    );

    // Cancel is a no-op after done; kept for reference
    void cancel;
  };

  return (
    <div>
      <h2>Dynasty Settings</h2>

      {/* Global settings */}
      <div className="panel">
        <h3>Global Simulation Settings</h3>
        <div className="field-row">
          <div className="field">
            <label>Start Year</label>
            <input type="number" step={1} value={config.minYear}
              onChange={(e) => onConfigChange({ ...config, minYear: Number(e.target.value) })} />
          </div>
          <div className="field">
            <label>End Year</label>
            <input type="number" step={1} value={config.maxYear}
              onChange={(e) => onConfigChange({ ...config, maxYear: Number(e.target.value) })} />
          </div>
          <div className="field">
            <label>Maximum Generations</label>
            <input type="number" step={1} min={1} max={200} value={config.generationMax}
              onChange={(e) => onConfigChange({ ...config, generationMax: Number(e.target.value) })} />
          </div>
        </div>
      </div>

      {/* Action buttons */}
      <div className="btn-row">
        <button className="btn btn-secondary btn-sm" onClick={() => setAddOpen((o) => !o)}>
          {addOpen ? "Cancel" : "Add Dynasty"}
        </button>
        <button className="btn btn-secondary btn-sm" onClick={handleDeleteAll} disabled={dynasties.length === 0}>
          Delete All Dynasties
        </button>
        <button className="btn btn-secondary btn-sm" onClick={handleReset} disabled={saving}>
          Reset to Default
        </button>
        <button className="btn btn-secondary btn-sm" onClick={handleSetFallback} disabled={saving}>
          Set as New Default
        </button>
        <button className="btn btn-primary btn-sm" onClick={handleSave} disabled={saving}>
          {saving ? <span className="spinner" /> : null}
          Save All Changes
        </button>
      </div>

      {feedback && <div className={`msg msg-${feedback.type}`}>{feedback.text}</div>}

      {/* Add dynasty form */}
      {addOpen && (
        <div className="panel" style={{ marginTop: "0.75rem" }}>
          <h3>New Dynasty</h3>
          <DynastyForm value={newDynasty} onChange={setNewDynasty} />
          <div className="btn-row" style={{ marginTop: "0.75rem" }}>
            <button className="btn btn-primary" onClick={handleAddDynasty}>Add Dynasty</button>
            <button className="btn btn-secondary" onClick={() => setAddOpen(false)}>Cancel</button>
          </div>
        </div>
      )}

      <hr className="divider" />

      {dynasties.length === 0 && (
        <div className="msg msg-info">No dynasties configured.</div>
      )}

      {dynasties.map((dynasty, idx) => (
        <div key={dynasty.dynastyID + idx} className="accordion">
          <div
            className="accordion-header"
            onClick={() => setExpandedIdx(expandedIdx === idx ? null : idx)}
          >
            <span style={{ color: "var(--text-label)" }}>
              {dynasty.dynastyID || "(unnamed)"}
            </span>
            <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
              <span style={{ color: "var(--text-muted)", fontSize: "0.78rem" }}>
                {dynasty.succession} / {dynasty.gender_law}
              </span>
              <button
                className="btn btn-danger btn-sm"
                onClick={(e) => { e.stopPropagation(); handleDeleteDynasty(idx); }}
              >
                Delete
              </button>
            </div>
          </div>
          {expandedIdx === idx && (
            <div className="accordion-body">
              <DynastyForm
                value={dynasty}
                onChange={(updated) => handleEditDynasty(idx, updated)}
              />
            </div>
          )}
        </div>
      ))}

      {/* Run simulation */}
      <hr className="divider" />
      <div className="panel">
        <h3>Run Simulation</h3>
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginBottom: "0.75rem" }}>
          Save all changes before running. Logs stream live below.
        </p>
        <button
          className="btn btn-primary"
          onClick={handleRunSimulation}
          disabled={simRunning}
        >
          {simRunning ? <><span className="spinner" /> Running...</> : "Run Simulation"}
        </button>

        {logs.length > 0 && (
          <div className="sim-log">
            {logs.map((line, i) => (
              <p key={i} className={line.startsWith("ERROR") ? "log-error" : ""}>
                {line}
              </p>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}