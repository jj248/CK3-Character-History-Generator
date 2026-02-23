import { useState } from "react";
import {
  InitializationConfig,
  NegativeEvent,
  saveInitializationConfig,
  resetInitializationConfig,
} from "../api";

const EVENT_TYPE_OPTIONS = ["event_plague", "event_war", "event_battle"];

const DEFAULT_EVENT: NegativeEvent = {
  eventID: "event_plague",
  startYear: 6000,
  endYear: 6500,
  deathReason: "",
  deathMultiplier: 0.5,
  characterAgeStart: 0,
  characterAgeEnd: 60,
};

interface Props {
  config: InitializationConfig;
  onConfigChange: (cfg: InitializationConfig) => void;
}

function EventForm({
  value,
  onChange,
}: {
  value: NegativeEvent;
  onChange: (v: NegativeEvent) => void;
}) {
  const set = <K extends keyof NegativeEvent>(key: K, val: NegativeEvent[K]) =>
    onChange({ ...value, [key]: val });

  return (
    <div>
      <div className="field-row">
        <div className="field">
          <label>Event ID</label>
          <select value={value.eventID} onChange={(e) => set("eventID", e.target.value)}>
            {EVENT_TYPE_OPTIONS.map((o) => <option key={o}>{o}</option>)}
          </select>
        </div>
        <div className="field">
          <label>Death Reason ID</label>
          <input
            type="text"
            value={value.deathReason}
            placeholder="e.g. death_plague"
            onChange={(e) => set("deathReason", e.target.value)}
          />
        </div>
      </div>
      <div className="field-row">
        <div className="field">
          <label>Start Year</label>
          <input type="number" value={value.startYear} step={1} onChange={(e) => set("startYear", Number(e.target.value))} />
        </div>
        <div className="field">
          <label>End Year</label>
          <input type="number" value={value.endYear} step={1} onChange={(e) => set("endYear", Number(e.target.value))} />
        </div>
        <div className="field">
          <label>Lethality Factor (0–1)</label>
          <input type="number" value={value.deathMultiplier} step={0.05} min={0} max={1} onChange={(e) => set("deathMultiplier", Number(e.target.value))} />
        </div>
      </div>
      <div className="field-row">
        <div className="field">
          <label>Min Character Age</label>
          <input type="number" value={value.characterAgeStart} step={1} min={0} onChange={(e) => set("characterAgeStart", Number(e.target.value))} />
        </div>
        <div className="field">
          <label>Max Character Age</label>
          <input type="number" value={value.characterAgeEnd} step={1} min={0} onChange={(e) => set("characterAgeEnd", Number(e.target.value))} />
        </div>
      </div>
    </div>
  );
}

export default function NegativeEvents({ config, onConfigChange }: Props) {
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [newEvent, setNewEvent] = useState<NegativeEvent>({ ...DEFAULT_EVENT });
  const [addOpen, setAddOpen] = useState(false);
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);

  const events = [...(config.events ?? [])].sort((a, b) =>
    (a.eventID ?? "").localeCompare(b.eventID ?? "")
  );

  const show = (type: "success" | "error", text: string) => {
    setFeedback({ type, text });
    setTimeout(() => setFeedback(null), 3500);
  };

  const updateConfig = (updatedEvents: NegativeEvent[]) => {
    onConfigChange({ ...config, events: updatedEvents });
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await saveInitializationConfig({ ...config, events });
      show("success", "Events saved.");
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
      // Reload after reset — App will re-fetch on next mount; for now show message
      show("success", "Events reset to fallback. Reload to see changes.");
    } catch (err) {
      show("error", String(err));
    } finally {
      setSaving(false);
    }
  };

  const handleAdd = () => {
    updateConfig([...events, { ...newEvent }]);
    setNewEvent({ ...DEFAULT_EVENT });
    setAddOpen(false);
  };

  const handleDelete = (idx: number) => {
    const next = events.filter((_, i) => i !== idx);
    updateConfig(next);
    if (expandedIdx === idx) setExpandedIdx(null);
  };

  const handleEdit = (idx: number, updated: NegativeEvent) => {
    const next = events.map((e, i) => (i === idx ? updated : e));
    updateConfig(next);
  };

  return (
    <div>
      <h2>Negative Events</h2>
      <p style={{ color: "var(--text-muted)", marginBottom: "1rem", fontSize: "0.85rem" }}>
        Events increase the chance of character death during a specified year range.
      </p>

      <div className="btn-row">
        <button className="btn btn-secondary" onClick={() => setAddOpen((o) => !o)}>
          {addOpen ? "Cancel" : "Add New Event"}
        </button>
        <button className="btn btn-secondary" onClick={handleReset} disabled={saving}>
          Reset to Default
        </button>
        <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
          {saving ? <span className="spinner" /> : null}
          Save Changes
        </button>
      </div>

      {feedback && (
        <div className={`msg msg-${feedback.type}`}>{feedback.text}</div>
      )}

      {addOpen && (
        <div className="panel" style={{ marginTop: "0.75rem" }}>
          <h3>New Event</h3>
          <EventForm value={newEvent} onChange={setNewEvent} />
          <div className="btn-row" style={{ marginTop: "0.5rem" }}>
            <button className="btn btn-primary" onClick={handleAdd}>Add Event</button>
            <button className="btn btn-secondary" onClick={() => setAddOpen(false)}>Cancel</button>
          </div>
        </div>
      )}

      <hr className="divider" />

      {events.length === 0 && (
        <div className="msg msg-info">No events configured.</div>
      )}

      {events.map((event, idx) => (
        <div key={idx} className="accordion">
          <div className="accordion-header" onClick={() => setExpandedIdx(expandedIdx === idx ? null : idx)}>
            <span style={{ color: "var(--text-label)" }}>{event.eventID}</span>
            <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
              <span style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>
                {event.startYear} – {event.endYear}
              </span>
              <button
                className="btn btn-danger btn-sm"
                onClick={(e) => { e.stopPropagation(); handleDelete(idx); }}
              >
                Delete
              </button>
            </div>
          </div>
          {expandedIdx === idx && (
            <div className="accordion-body">
              <EventForm
                value={event}
                onChange={(updated) => handleEdit(idx, updated)}
              />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}