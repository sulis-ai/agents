// WP-009 — <AttachRepoForm> — local-path-only repo attach (ADR-021).
//
// A labelled local-path input + Cancel/Attach, driving the WP-007 `attachRepo`
// fetcher (passed in as `onAttach`, returning a Result). ADR-021 v1 behaviour:
//
//   - PATH_NOT_FOUND → a HARD, blocking inline error in plain English
//     ("We couldn't find that folder…"), mapped from the typed code so the raw
//     code never leaks to the founder (errors-are-values, WPF-02).
//   - A folder without a .git still ATTACHES (the fetcher resolves ok with a
//     project whose repo.present === false); we show a NON-blocking "not a git
//     repo yet" note and still fire onSuccess. Attach never blocks on the
//     not-a-repo condition (ADR-021).
//   - Any other typed error renders inline too (its own plain message).
//
// Tokens-only styling (var(--*); WPF-07). Standalone + props-driven; page
// wiring is WP-008/WP-010.

import { useId, useState } from "react";
// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits); pages/settings/ is one level deeper than api/, so the wire-type import is 4 levels up. Mirrors api/settings.ts.
import type { SettingsProject } from "../../../../shared/api-types";
import type { Result, SettingsError } from "../../api/settings";
import styles from "./SettingsForms.module.css";

export interface AttachRepoFormProps {
  /** The project the folder attaches to. */
  projectId: string;
  /** The typed fetcher closure: localPath → Result<SettingsProject>. */
  onAttach: (localPath: string) => Promise<Result<SettingsProject>>;
  /** Dismiss without attaching. */
  onCancel: () => void;
  /** Fired after a successful attach — the WP-008 query-invalidation callback. */
  onSuccess: (value: SettingsProject) => void;
}

/**
 * Map a typed settings error to plain English. PATH_NOT_FOUND gets the signed-
 * mockup copy verbatim; everything else falls back to the server's own message
 * (already human; the fetcher guarantees a message). The raw code is never
 * surfaced.
 */
function plainEnglish(error: SettingsError): string {
  if (error.code === "PATH_NOT_FOUND") {
    return "We couldn't find that folder. Point at a folder that already exists on your computer.";
  }
  return error.message;
}

export function AttachRepoForm({
  projectId,
  onAttach,
  onCancel,
  onSuccess,
}: AttachRepoFormProps) {
  const fieldId = useId();
  const errorId = `${fieldId}-error`;
  const noteId = `${fieldId}-note`;
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notRepoNote, setNotRepoNote] = useState(false);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    setNotRepoNote(false);
    const result = await onAttach(value);
    setBusy(false);
    if (result.ok) {
      // The attach SUCCEEDED. If the folder isn't a git repo yet, surface a
      // non-blocking note — but it has still attached (ADR-021).
      if (result.value.repo && result.value.repo.present === false) {
        setNotRepoNote(true);
      }
      onSuccess(result.value);
    } else {
      setError(plainEnglish(result.error));
    }
  }

  const describedBy =
    [error ? errorId : null, notRepoNote ? noteId : null]
      .filter(Boolean)
      .join(" ") || undefined;

  return (
    <form className={styles.formCard} onSubmit={handleSubmit} noValidate>
      <h3 className={styles.cardTitle}>Attach a folder</h3>
      <div className={styles.field}>
        <label className={styles.label} htmlFor={fieldId}>
          Local folder path
        </label>
        <input
          id={fieldId}
          className={styles.input}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          data-project-id={projectId}
          aria-describedby={describedBy}
          aria-invalid={error ? true : undefined}
        />
        {error ? (
          <p id={errorId} role="alert" className={styles.error}>
            {error}
          </p>
        ) : null}
        {notRepoNote ? (
          <p id={noteId} className={styles.warningNote}>
            Attached — not a git repo yet. That&rsquo;s fine; you can initialise
            it whenever you like.
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
          Attach
        </button>
      </div>
    </form>
  );
}
