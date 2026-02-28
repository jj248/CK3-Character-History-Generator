/**
 * useValidation.ts
 *
 * A generic validation hook that maps field names to error strings.
 * Validation rules here intentionally mirror the Pydantic models in
 * api/models.py so errors are caught client-side before a round-trip.
 *
 * Usage:
 *   const { errors, validate, clearErrors } = useValidation(dynastyRules, dynasty);
 *   if (!validate()) return;  // exits early when invalid
 */

import { useCallback, useState } from "react";
import type { Dynasty, NegativeEvent } from "../api";

// ---------------------------------------------------------------------------
//  Core types
// ---------------------------------------------------------------------------

/** A map of field name to human-readable error string. Empty means valid. */
export type ValidationErrors<T> = Partial<Record<keyof T, string>>;

/** A validation rule for a single field. Returns an error string or null. */
type Rule<T, K extends keyof T> = (value: T[K], obj: T) => string | null;

/** The full rule set for a type: one optional rule per field. */
type RuleSet<T> = { [K in keyof T]?: Rule<T, K> };

// ---------------------------------------------------------------------------
//  Hook
// ---------------------------------------------------------------------------

/**
 * Runs the provided rule set against `value` on demand.
 *
 * @param rules   - Field-level validation rules.
 * @param value   - The current object to validate.
 * @returns `errors`      — current field error map (empty when clean)
 *          `validate`    — run all rules; returns true when the object is valid
 *          `clearErrors` — reset the error map (e.g. when a form is cancelled)
 */
export function useValidation<T extends object>(
  rules: RuleSet<T>,
  value: T,
): {
  errors: ValidationErrors<T>;
  validate: () => boolean;
  clearErrors: () => void;
} {
  const [errors, setErrors] = useState<ValidationErrors<T>>({});

  const validate = useCallback((): boolean => {
    const next: ValidationErrors<T> = {};

    for (const key in rules) {
      const rule = rules[key as keyof T];
      if (!rule) continue;
      const result = rule(value[key as keyof T], value);
      if (result !== null) next[key as keyof T] = result;
    }

    setErrors(next);
    return Object.keys(next).length === 0;
  }, [rules, value]);

  const clearErrors = useCallback(() => setErrors({}), []);

  return { errors, validate, clearErrors };
}

// ---------------------------------------------------------------------------
//  Dynasty rules  (mirrors api/models.py -> Dynasty + NameInheritance)
// ---------------------------------------------------------------------------

export const DYNASTY_RULES: RuleSet<Dynasty> = {
  dynastyID: (v) =>
    !v?.trim() ? "Dynasty ID is required." : null,

  dynastyName: (v) =>
    !v?.trim() ? "Dynasty Name is required." : null,

  faithID: (v) =>
    !v?.trim() ? "Faith ID is required." : null,

  cultureID: (v) =>
    !v?.trim() ? "Culture ID is required." : null,

  nameInheritance: (v) => {
    if (!v) return "Name inheritance settings are required.";
    const total =
      v.grandparentNameInheritanceChance +
      v.parentNameInheritanceChance +
      v.noNameInheritanceChance;
    return Math.abs(total - 1.0) >= 1e-6
      ? `Name inheritance chances must sum to 1.0 (currently ${total.toFixed(4)}).`
      : null;
  },
};

// ---------------------------------------------------------------------------
//  NegativeEvent rules  (mirrors api/models.py -> NegativeEvent)
// ---------------------------------------------------------------------------

export const NEGATIVE_EVENT_RULES: RuleSet<NegativeEvent> = {
  eventID: (v) =>
    !v?.trim() ? "Event ID is required." : null,

  deathReason: (v) =>
    !v?.trim() ? "Death Reason ID is required." : null,

  deathMultiplier: (v) =>
    v <= 0 ? "Lethality factor must be greater than 0." : null,

  endYear: (v, obj) =>
    v < obj.startYear ? "End year must be >= start year." : null,

  characterAgeEnd: (v, obj) =>
    v < obj.characterAgeStart ? "Max character age must be >= min character age." : null,
};