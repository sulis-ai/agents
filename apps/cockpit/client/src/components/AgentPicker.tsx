// WP-003 — <AgentPicker>: Claude ↔ Antigravity at the composer foot (AI-07/AI-03).
//
// REUSES the ONE menu primitive (ProductControl) — the Blue constraint: the
// agent picker and the dock header tile share ProductControl, never a second
// popover. The provider choice becomes two rows (Claude / Antigravity); the
// RUNNING provider is the ticked one (AI-07 honest identity — we name the agent
// actually powering the session, not a picked-but-unapplied one).
//
// AI-03 guard: switching the provider WHILE a session is running is a confirm
// gate. The choice applies to NEW work — it never re-homes a live run — so the
// confirm wording says so, and only on confirm does the switch commit.

import { useState } from "react";
import type { ChatProvider } from "../../../shared/api-types";
import { PROVIDER_NAME } from "../lib/providerName";
import { ProductControl, type ProductRow } from "./ProductControl";
import styles from "./AgentPicker.module.css";

const PROVIDER_ROWS: ProductRow[] = [
  { productId: "pty", name: PROVIDER_NAME.pty, glyph: "monogram" },
  { productId: "agy", name: PROVIDER_NAME.agy, glyph: "monogram" },
];

export interface AgentPickerProps {
  /** The provider actually powering the session right now (the ticked one). */
  running: ChatProvider;
  /** The provider currently selected (usually === running). */
  selected: ChatProvider;
  /** True when a session is live — a switch then needs the AI-03 confirm. */
  sessionRunning: boolean;
  /** Commit the switch (the dock wires this to useProductChat.switchProvider). */
  onSwitch: (provider: ChatProvider) => void;
}

export function AgentPicker({
  running,
  selected,
  sessionRunning,
  onSwitch,
}: AgentPickerProps) {
  // A pending switch awaiting the AI-03 confirm (only set mid-session).
  const [pending, setPending] = useState<ChatProvider | null>(null);

  function handleSelect(id: string | null) {
    if (id !== "pty" && id !== "agy") return;
    const next = id as ChatProvider;
    if (next === running) return; // no-op — already running this provider.
    if (sessionRunning) {
      // AI-03: a live run is in progress — gate the switch behind a confirm.
      setPending(next);
      return;
    }
    onSwitch(next);
  }

  function confirmSwitch() {
    if (pending) onSwitch(pending);
    setPending(null);
  }

  function cancelSwitch() {
    setPending(null);
  }

  return (
    <div className={styles.agentPick}>
      {/* The picker IS the shared ProductControl primitive — no second popover.
       * `testIdPrefix` aliases the generic control to the agent-picker home so
       * the dock + tests address it precisely while the a11y model (role=menu /
       * menuitemradio / aria-checked / keyboard) is inherited from the ONE
       * primitive (the Blue constraint: no second menu). */}
      <div data-testid="agent-picker" data-running={running}>
        <ProductControl
          mode="scope"
          rows={PROVIDER_ROWS}
          selectedId={selected}
          onSelect={handleSelect}
          testIdPrefix="agent-picker"
          triggerLabel={`Powered by ${PROVIDER_NAME[running]}. Choose which AI powers this chat.`}
          // chat-ux Fix 1 — the picker lives at the composer FOOT; its menu must
          // open UPWARD or it falls off the bottom of the viewport. The shared
          // primitive's default ("down") stays for the top-of-page placements.
          placement="up"
          // chat-ux: this picker reuses ProductControl, so its search input
          // would otherwise read "Find a product" — it's choosing an AGENT.
          searchLabel="Find an agent…"
        />
      </div>

      {pending && (
        <div
          className={styles.confirm}
          data-testid="agent-switch-confirm"
          role="dialog"
          aria-label="Confirm agent switch"
        >
          <p className={styles.confirmText}>
            Switch to {PROVIDER_NAME[pending]}? Switching applies to new work in
            this chat. Work already running keeps the agent it started with.
          </p>
          <div className={styles.confirmActs}>
            <button
              type="button"
              className={styles.btnPrimary}
              data-testid="agent-switch-confirm-yes"
              onClick={confirmSwitch}
            >
              Switch to {PROVIDER_NAME[pending]}
            </button>
            <button
              type="button"
              className={styles.btnGhost}
              data-testid="agent-switch-confirm-no"
              onClick={cancelSwitch}
            >
              Keep {PROVIDER_NAME[running]}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
