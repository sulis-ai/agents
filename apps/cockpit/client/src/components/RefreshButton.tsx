// WP-012 — <RefreshButton> — manual-refresh affordance per ADR-007.
//
// Extracted from <Dashboard> in this WP (per WP risks/notes) so WP-013
// and WP-014's per-thread views can reuse it without duplication.
//
// The button takes the query key to invalidate as a prop (rather than
// hard-coding ["changes"]) so it composes cleanly with the future
// per-thread query keys.

import { useQueryClient, type QueryKey } from "@tanstack/react-query";
import styles from "./RefreshButton.module.css";

export interface RefreshButtonProps {
  /** Query key(s) to invalidate on click. */
  queryKey: QueryKey;
  /** Optional override; defaults to "Refresh". */
  label?: string;
  /** Whether a refresh is currently in flight (disables the button). */
  isFetching?: boolean;
}

export function RefreshButton({
  queryKey,
  label = "Refresh",
  isFetching = false,
}: RefreshButtonProps) {
  const client = useQueryClient();
  return (
    <button
      type="button"
      className={styles.button}
      onClick={() => client.invalidateQueries({ queryKey })}
      disabled={isFetching}
    >
      {label}
    </button>
  );
}
