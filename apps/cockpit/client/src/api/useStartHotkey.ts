// WP-002 — useStartHotkey() (ADR-002 — the minimal global hotkey accelerant).
//
// A single small global keydown handler that maps Cmd/Ctrl+N and Cmd/Ctrl+K to
// navigate("/start") — the SAME destination as the WP-001 front-door button
// (ADR-001), so the accelerant cannot drift into a second path. It is NOT a
// command palette (ADR-002 rejected alternative).
//
// Mounted once in WorkspaceShell so it is live on every route the chrome wraps.
// Mirrors the existing ProductSwitcher idiom exactly: a document "keydown"
// listener added/removed inside a useEffect with cleanup. Pure client
// navigation — no network, so no timeout/retry/breaker applies (TDD Armor).

import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

/**
 * True when the event target is a text-entry surface (input, textarea, or a
 * contenteditable element). The hotkey no-ops in these cases so typing in the
 * composer or the intent box is never hijacked (ADR-002).
 */
function isTypingTarget(el: EventTarget | null): boolean {
  if (!(el instanceof HTMLElement)) return false;
  const tag = el.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA") return true;
  // `isContentEditable` is the real-DOM signal; fall back to the attribute,
  // which is also present on the element jsdom hands us (jsdom does not
  // implement the isContentEditable getter).
  if (el.isContentEditable) return true;
  const editable = el.getAttribute("contenteditable");
  return editable !== null && editable !== "false";
}

/**
 * Mounts a global ⌘N / ⌘K accelerant to the "/start" front door. Call once,
 * high in the chrome (WorkspaceShell), so it is workspace-global.
 */
export function useStartHotkey(): void {
  const navigate = useNavigate();

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      const isStartChord =
        (e.metaKey || e.ctrlKey) && (e.key === "n" || e.key === "k");
      if (!isStartChord) return;

      // Never hijack typing — and do NOT preventDefault when we don't act,
      // so the browser's native binding is left untouched (ADR-002).
      if (isTypingTarget(e.target)) return;

      // Claim the key only when it acts.
      e.preventDefault();
      navigate("/start");
    }

    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [navigate]);
}
