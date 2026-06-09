// WP-009 — <ConfirmRemoveDialog> — the files-are-safe remove confirmation.
//
// Remove = soft-delete (ADR-020): the brain entity's sys_status flips to
// "deleted"; NOTHING on the founder's disk is touched. SPEC binding decision 4
// — "remove = unlink the pointer only; never delete files on disk" — is
// surfaced to the founder here as the positive-tinted "Your files are safe"
// note. That note is load-bearing reassurance, not decoration (WP-VIS item 8);
// the test asserts its presence verbatim.
//
// Driven by the WP-007 typed fetcher (passed in as `onConfirm`, returning a
// Result). On success it fires the WP-008 query-invalidation callback
// (`onSuccess`); on a typed error it renders the message inline (errors-are-
// values, WPF-02). Tokens-only styling (var(--*); WPF-07). Standalone +
// props-driven; page wiring is WP-008/WP-010.

import { useId, useState } from "react";
import type { Result } from "../../api/settings";
import styles from "./SettingsForms.module.css";

export interface ConfirmRemoveDialogProps {
  /** The thing being removed, e.g. "design-tokens" (used in copy). */
  entityName: string;
  /** Dialog heading, e.g. 'Remove "design-tokens"?'. */
  title: string;
  /** The typed fetcher closure performing the soft-delete. */
  onConfirm: () => Promise<Result<void>>;
  /** Dismiss without removing. */
  onCancel: () => void;
  /** Fired after a successful remove — the WP-008 query-invalidation callback. */
  onSuccess: () => void;
}

export function ConfirmRemoveDialog({
  entityName,
  title,
  onConfirm,
  onCancel,
  onSuccess,
}: ConfirmRemoveDialogProps) {
  const titleId = useId();
  const errorId = `${titleId}-error`;
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleConfirm() {
    if (busy) return;
    setBusy(true);
    setError(null);
    const result = await onConfirm();
    setBusy(false);
    if (result.ok) {
      onSuccess();
    } else {
      setError(result.error.message);
    }
  }

  return (
    <div
      className={styles.dialog}
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
    >
      <h3 id={titleId} className={styles.cardTitle}>
        {title}
      </h3>
      <p className={styles.dialogBody}>
        This removes {entityName} from the cockpit and unlinks the folder it
        points at.
      </p>
      <div className={styles.safeNote}>
        <span aria-hidden="true">🛡️</span>
        <span>
          <strong>Your files are safe.</strong> Nothing on your computer is
          deleted — this only removes the link. The folder and its contents stay
          exactly where they are.
        </span>
      </div>
      {error ? (
        <p id={errorId} role="alert" className={styles.error}>
          {error}
        </p>
      ) : null}
      <div className={styles.actions}>
        <button
          type="button"
          className={`${styles.btn} ${styles.btnGhost}`}
          onClick={onCancel}
        >
          Cancel
        </button>
        <button
          type="button"
          className={`${styles.btn} ${styles.btnDanger}`}
          onClick={handleConfirm}
          disabled={busy}
        >
          Remove the link
        </button>
      </div>
    </div>
  );
}
