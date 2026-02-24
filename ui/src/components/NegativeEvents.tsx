/**
 * NegativeEvents.tsx
 *
 * Manages negative events that raise character death rates during a specified
 * year and age window. Validates all required fields before adding or saving,
 * mirroring the server-side Pydantic rules in api/models.py.
 */

import { useState } from "react";
import {
  InitializationConfig,
  NegativeEvent,
  saveInitializationConfig,
  resetInitializationConfig,
} from "../api";
import {
  NEGATIVE_EVENT_RULES,
  useValidation,
  ValidationErrors,
} from "../hooks/useValidation";

// ---------------------------------------------------------------------------
//  Constants
// ---------------------------------------------------------------------------

const EVENT_TYPE_OPTIONS = ["event_plague", "event_war", "event_battle"] as const;

const DEFAULT_EVENT: NegativeEvent = {
  eventID: "event_plague",
  startYear: 6000,
  endYear: 6500,
  deathReason: "",
  deathMultiplier: 0.5,
  characterAgeStart: 0,
  characterAgeEnd: 60,
};

// ---------------------------------------------------------------------------
//  FieldError — inline error label beneath a form input
// ---------------------------------------------------------------------------

function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return <span className="field-error">{message}</span>;
}

// ---------------------------------------------------------------------------
//  EventForm — shared form for add and inline edit
// ---------------------------------------------------------------------------

interface EventFormProps {
  value: NegativeEvent;
  onChange: (v: NegativeEvent) => void;
  errors?: ValidationErrors<NegativeEvent>;
}

function EventForm({ value, onChange, errors = {} }: EventFormProps) {
  const set = <K extends keyof NegativeEvent>(key: K, val: NegativeEvent[K]) =>
    onChange({ ...value, [key]: val });

  return (
    <div>
      <div className="field-row">
        <div className="field">
          <label>Event ID</label>
          <select
            value={value.eventID}
            aria-invalid={!!errors.eventID}
            onChange={(e) => set("eventID", e.target.value)}
          >
            {EVENT_TYPE_OPTIONS.map((o) => <option key={o}>{o}</option>)}
          </select>
          <FieldError message={errors.eventID} />
        </div>
        <div className="field">
          <label>Death Reason ID</label>
          <input
            type="text"
            value={value.deathReason}
            placeholder="e.g. death_plague"
            aria-invalid={!!errors.deathReason}
            onChange={(e) => set("deathReason", e.target.value)}
          />
          <FieldError message={errors.deathReason} />
        </div>
      </div>

      <div className="field-row">
        <div className="field">
          <label>Start Year</label>
          <input
            type="number"
            value={value.startYear}
            step={1}
            onChange={(e) => set("startYear", Number(e.target.value))}
          />
        </div>
        <div className="field">
          <label>End Year</label>
          <input
            type="number"
            value={value.endYear}
            step={1}
            aria-invalid={!!errors.endYear}
            onChange={(e) => set("endYear", Number(e.target.value))}
          />
          <FieldError message={errors.endYear} />
        </div>
        <div className="field">
          <label>Lethality Factor (0–1)</label>
          <input
            type="number"
            value={value.deathMultiplier}
            step={0.05}
            min={0}
            max={1}
            aria-invalid={!!errors.deathMultiplier}
            onChange={(e) => set("deathMultiplier", Number(e.target.value))}
          />
          <FieldError message={errors.deathMultiplier} />
        </div>
      </div>

      <div className="field-row">
        <div className="field">
          <label>Min Character Age</label>
          <input
            type="number"
            value={value.characterAgeStart}
            step={1}
            min={0}
            onChange={(e) => set("characterAgeStart", Number(e.target.value))}
          />
        </div>
        <div className="field">
          <label>Max Character Age</label>
          <input
            type="number"
            value={value.characterAgeEnd}
            step={1}
            min={0}
            aria-invalid={!!errors.characterAgeEnd}
            onChange={(e) => set("characterAgeEnd", Number(e.target.value))}
          />
          <FieldError message={errors.characterAgeEnd} />
        </div>
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

export default function NegativeEvents({ config, onConfigChange }: Props) {
  const [saving, setSaving]           = useState(false);
  const [feedback, setFeedback]       = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [newEvent, setNewEvent]       = useState<NegativeEvent>({ ...DEFAULT_EVENT });
  const [addOpen, setAddOpen]         = useState(false);
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);

  const { errors: newEventErrors, validate: validateNew, clearErrors: clearNew } =
    useValidation(NEGATIVE_EVENT_RULES, newEvent);

  const events = [...(config.events ?? [])].sort((a, b) =>
    (a.eventID ?? "").localeCompare(b.eventID ?? "")
  );

  const show = (type: "success" | "error", text: string) => {
    setFeedback({ type, text });
    setTimeout(() => setFeedback(null), 3500);
  };

  const updateConfig = (updatedEvents: NegativeEvent[]) =>
    onConfigChange({ ...config, events: updatedEvents });

  // ── Save / reset ──────────────────────────────────────────────────────────

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
      show("success", "Events reset to fallback. Reload to see changes.");
    } catch (err) {
      show("error", String(err));
    } finally {
      setSaving(false);
    }
  };

  // ── Event CRUD ────────────────────────────────────────────────────────────

  const handleAdd = () => {
    if (!validateNew()) return;
    updateConfig([...events, { ...newEvent }]);
    setNewEvent({ ...DEFAULT_EVENT });
    clearNew();
    setAddOpen(false);
  };

  const handleCancelAdd = () => {
    clearNew();
    setAddOpen(false);
  };

  const handleDelete = (idx: number) => {
    updateConfig(events.filter((_, i) => i !== idx));
    if (expandedIdx === idx) setExpandedIdx(null);
  };

  const handleEdit = (idx: number, updated: NegativeEvent) =>
    updateConfig(events.map((e, i) => (i === idx ? updated : e)));

  // ── Render ────────────────────────────────────────────────────────────────

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
          <EventForm
            value={newEvent}
            onChange={setNewEvent}
            errors={newEventErrors}
          />
          <div className="btn-row" style={{ marginTop: "0.5rem" }}>
            <button className="btn btn-primary" onClick={handleAdd}>
              Add Event
            </button>
            <button className="btn btn-secondary" onClick={handleCancelAdd}>
              Cancel
            </button>
          </div>
        </div>
      )}

      <hr className="divider" />

      {events.length === 0 && (
        <div className="msg msg-info">No events configured.</div>
      )}

      {events.map((event, idx) => (
        <EditableEventRow
          key={event.eventID + idx}
          event={event}
          isExpanded={expandedIdx === idx}
          onToggle={() => setExpandedIdx(expandedIdx === idx ? null : idx)}
          onEdit={(updated) => handleEdit(idx, updated)}
          onDelete={() => handleDelete(idx)}
        />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
//  EditableEventRow — accordion row with its own isolated validation state
// ---------------------------------------------------------------------------

interface EditableEventRowProps {
  event: NegativeEvent;
  isExpanded: boolean;
  onToggle: () => void;
  onEdit: (updated: NegativeEvent) => void;
  onDelete: () => void;
}

function EditableEventRow({
  event,
  isExpanded,
  onToggle,
  onEdit,
  onDelete,
}: EditableEventRowProps) {
  const { errors, validate } = useValidation(NEGATIVE_EVENT_RULES, event);

  const handleChange = (updated: NegativeEvent) => {
    onEdit(updated);
    validate();
  };

  return (
    <div className="accordion">
      <div className="accordion-header" onClick={onToggle}>
        <span style={{ color: "var(--text-label)" }}>{event.eventID}</span>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <span style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>
            {event.startYear} – {event.endYear}
          </span>
          <button
            className="btn btn-danger btn-sm"
            onClick={(e) => { e.stopPropagation(); onDelete(); }}
          >
            Delete
          </button>
        </div>
      </div>

      {isExpanded && (
        <div className="accordion-body">
          <EventForm
            value={event}
            onChange={handleChange}
            errors={errors}
          />
        </div>
      )}
    </div>
  );
}