// WP-003 — the ONE map from a registered chat provider key to its friendly,
// founder-facing name (AI-07 honest identity). Extracted at the 2-consumer
// threshold (EP-03): both <AgentPicker> (the picker rows + confirm wording) and
// <ProductChat> (the streamed reply's "who" line) name the running agent, so the
// mapping lives in exactly one place — there is no second source for what "pty"
// or "agy" is called in the UI.

import type { ChatProvider } from "../../../shared/api-types";

/** pty → Claude, agy → Antigravity (ADR-003 registered provider keys). */
export const PROVIDER_NAME: Record<ChatProvider, string> = {
  pty: "Claude",
  agy: "Antigravity",
};
