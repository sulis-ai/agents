// WP-009 — <EntityForm> — the shared create/edit form (ADR-019/020).
//
// One labelled field + hint + Cancel/Save, driving the WP-007 typed fetcher
// (passed in as `onSubmit`, returning a Result — errors-are-values, WPF-02).
// The SAME component backs product-create, product-rename, project-create and
// project-rename: the caller supplies the title/label/hint/submit-label and an
// `onSubmit` closure over `writeProduct` / `writeProject`. On a typed error the
// message renders INLINE (role="alert", linked to the field via
// aria-describedby) — never a thrown opaque. On success it invokes the WP-008
// query-invalidation callback (`onSuccess`) so the tree + switcher refresh.
//
// Tokens-only styling via SettingsForms.module.css (var(--*); WPF-07).
// Standalone + props-driven; the page wiring is WP-008/WP-010.

import { useId, useState } from "react";
import type { Result } from "../../api/settings";
import styles from "./SettingsForms.module.css";

export interface EntityFormProps<T> {
  /** Card heading, e.g. "Rename product" / "Add a project". */
  title: string;
  /** The field label (a real <label>, never a placeholder). */
  label: string;
  /** Helper hint shown under the field. */
  hint: string;
  /** Pre-filled value (edit) or "" (create). */
  initialValue: string;
  /** Submit button text, e.g. "Save" / "Add". */
  submitLabel: string;
  /** The typed fetcher closure: name → Result. Errors-are-values (WPF-02). */
  onSubmit: (name: string) => Promise<Result<T>>;
  /** Dismiss without saving. */
  onCancel: () => void;
  /** Fired after a successful save — the WP-008 query-invalidation callback. */
  onSuccess: (value: T) => void;
}

export function EntityForm<T>({
  title,
  label,
  hint,
  initialValue,
  submitLabel,
  onSubmit,
  onCancel,
  onSuccess,
}: EntityFormProps<T>) {
  const fieldId = useId();
  const hintId = `${fieldId}-hint`;
  const errorId = `${fieldId}-error`;
  const [value, setValue] = useState(initialValue);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    const result = await onSubmit(value);
    setBusy(false);
    if (result.ok) {
      onSuccess(result.value);
    } else {
      setError(result.error.message);
    }
  }

  return (
    <form className={styles.formCard} onSubmit={handleSubmit} noValidate>
      <h3 className={styles.cardTitle}>{title}</h3>
      <div className={styles.field}>
        <label className={styles.label} htmlFor={fieldId}>
          {label}
        </label>
        <input
          id={fieldId}
          className={styles.input}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          aria-describedby={error ? `${hintId} ${errorId}` : hintId}
          aria-invalid={error ? true : undefined}
        />
        <p id={hintId} className={styles.hint}>
          {hint}
        </p>
        {error ? (
          <p id={errorId} role="alert" className={styles.error}>
            {error}
          </p>
        ) : null}
      </div>
      <div className={styles.actions}>
        <button
          type="button"
          className={`${styles.btn} ${styles.btnGhost}`}
          onClick={onCancel}
        >
          Cancel
        </button>
        <button
          type="submit"
          className={`${styles.btn} ${styles.btnPrimary}`}
          disabled={busy}
        >
          {submitLabel}
        </button>
      </div>
    </form>
  );
}
