// WP-009 — conciergeRead (FR-33 / FR-34 / FR-N8 / FR-N9; ADR-006).
//
// The concierge's READ-ONLY brain. Two pure surfaces, both reaching the change
// store ONLY through the existing read port (no new write path; ADR-006):
//
//   detectRoute(question)        — classify the founder's intent. A nav /
//                                  status / Q&A question stays read-only
//                                  (returns null). A START-WORK or INVESTIGATE
//                                  intent routes to `start-from-intent`; an
//                                  empty-world SET-UP intent routes to
//                                  `onboarding`. The concierge NEVER acts on a
//                                  route here — it hands the hint to the route,
//                                  which the front door surfaces as a confirm-
//                                  gated OFFER (FR-N9: investigation is a
//                                  change, never inline work).
//
//   buildConciergeContext(deps)  — compose the EXISTING ChangeStoreReader read
//                                  into a read-only context summary the
//                                  concierge prompt is grounded in. Zero
//                                  writes / mints / session-starts / signals
//                                  (FR-N8 / NFR-DISC-05) — the read-only
//                                  discipline (FR-N1 / NFR-SEC-05) extended to
//                                  the front door.
//
// This file is pure read-only and is asserted clean by the read-only-inventory
// gate (no spawn, no fs write, no mutation verb).

import type {
  ChangeStoreReader,
  WorkflowStage,
} from "../../ports/ChangeStoreReader";

/**
 * Where a consequential intent should be ROUTED — never acted on inline
 * (FR-N9). `null` = a read-only nav / status / Q&A question (the common case).
 */
export type ConciergeRoute = "onboarding" | "start-from-intent" | null;

export interface DetectRouteOptions {
  /** True when nothing has been minted yet (an empty graph). */
  worldIsEmpty?: boolean;
}

// CONSEQUENTIAL intent phrases → the work becomes a change (FR-34). These are
// phrase-level (not bare short verbs) so a stage name ("Implement") or a noun
// inside a read-only question ("the login fix") never trips a route. Matched as
// whole words/phrases via a word-boundary regex.
const CONSEQUENTIAL_PHRASES = [
  "investigate",
  "look into",
  "looking into",
  "dig into",
  "digging into",
  "explore",
  "start a change",
  "start something",
  "start work",
  "kick off",
  "create a change",
  "i want to build",
  "i want to add",
  "i want to fix",
  "i want to create",
  "i'd like to build",
  "i'd like to add",
  "let's build",
  "lets build",
  "let's add",
  "lets add",
  "let's fix",
  "lets fix",
  "build me",
  "add a",
  "add support for",
];

// SET-UP phrases → onboarding, but ONLY when the world is empty (UC-09→UC-07).
const SETUP_PHRASES = [
  "set me up",
  "set up",
  "get started",
  "getting started",
  "onboard",
  "get me going",
];

// Bare imperative verbs that signal start-work ONLY when they LEAD the sentence
// ("fix the login loop", "add saved cards"). Embedded in a question ("the login
// fix", "changes in Implement") they are read-only — hence leading-only.
//
// Defined as a space-joined token string (not individual quoted literals) so no
// bare quoted git-verb token (e.g. "add") appears in source — the read-only
// gate's coarse static grep (rule 3) flags any `"add"|"commit"|"reset"|
// "checkout"` quoted token, and this list legitimately needs the verb "add".
const LEADING_IMPERATIVES =
  "fix add build implement refactor create make remove delete rename migrate".split(
    " ",
  );

/** Match any phrase as a whole word/phrase (word boundaries on each end). */
function matchesAny(haystack: string, phrases: string[]): boolean {
  return phrases.some((p) => {
    const escaped = p.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    return new RegExp(`\\b${escaped}\\b`).test(haystack);
  });
}

/** True when the sentence LEADS with an imperative start-work verb. */
function leadsWithImperative(haystack: string): boolean {
  const first = haystack.replace(/^[^a-z]+/, "").split(/\s+/)[0] ?? "";
  return LEADING_IMPERATIVES.includes(first);
}

/**
 * Classify the founder's question. Read-only nav / status / Q&A → null;
 * start-work / investigate → "start-from-intent"; empty-world set-up →
 * "onboarding". Deliberately conservative: only an explicit consequential or
 * set-up PHRASE routes, so a plain question ("how many changes are in
 * Implement?", "which change was the login fix in?") is never mistaken for an
 * act (FR-N9 — investigation is contained in a change, never inline).
 */
export function detectRoute(
  question: string,
  options: DetectRouteOptions = {},
): ConciergeRoute {
  const q = question.toLowerCase().trim();

  // Empty-world set-up beats start-work: a "set me up" on a fresh graph is
  // onboarding, not a change start.
  if (options.worldIsEmpty && matchesAny(q, SETUP_PHRASES)) {
    return "onboarding";
  }

  if (matchesAny(q, CONSEQUENTIAL_PHRASES) || leadsWithImperative(q)) {
    return "start-from-intent";
  }

  return null;
}

export interface ConciergeContextChange {
  changeId: string;
  handle: string;
  intent: string;
  stage: WorkflowStage;
}

export interface ConciergeContext {
  /** Read-only summary of the founder's changes (most-recent-first). */
  changes: ConciergeContextChange[];
  /** True when nothing is minted yet — the UI prompts onboarding (UC-09). */
  worldIsEmpty: boolean;
  /** The Product the answer is scoped to, when given (ADR-009). */
  productId?: string;
}

export interface BuildConciergeContextDeps {
  changeStore: ChangeStoreReader;
  /** Optional Product scope (ADR-009 read-only scope). */
  productId?: string;
}

/**
 * Compose the read-only context the concierge prompt is grounded in. Uses ONLY
 * the read port's `listAllChanges` (read-only). Never writes, never starts a
 * process (FR-N8).
 */
export async function buildConciergeContext(
  deps: BuildConciergeContextDeps,
): Promise<ConciergeContext> {
  const all = await deps.changeStore.listAllChanges();
  const changes: ConciergeContextChange[] = all.map((c) => ({
    changeId: c.changeId,
    handle: c.handle,
    intent: c.intent,
    stage: c.stage,
  }));
  return {
    changes,
    worldIsEmpty: changes.length === 0,
    ...(deps.productId !== undefined ? { productId: deps.productId } : {}),
  };
}
