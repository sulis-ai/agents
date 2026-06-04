// WP-011 — startFromIntent (FR-29/30/34; FR-N6/N9; ADR-006/007).
//
// The start-from-intent BRAIN. Two pure surfaces + one orchestrator, all
// reaching consequence ONLY through the StartChangeRunner port (the sanctioned
// `sulis-change start` path — no new write path; ADR-006):
//
//   classifyIntent(intent, kind)  — DETERMINISTIC intent → {primitive, slug}
//                                   via the change-primitives vocabulary
//                                   (FR-29). Never guesses: too little to go on
//                                   ⇒ INTENT_AMBIGUOUS with ONE clarifying
//                                   question. An investigation resolves to a
//                                   CHANGE primitive (a contained investigation,
//                                   never inline work — FR-34 / FR-N9).
//
//   StartFromIntentOrchestrator   — the propose → confirm state machine. A
//                                   propose turn classifies + proposes (starts
//                                   nothing). A confirmed turn clones-if-absent
//                                   (FR-30) then starts the change via the
//                                   runner so it lands at Recon (FR-29). The
//                                   confirm gate (reused from WP-010) is the only
//                                   thing that turns a proposal into the act
//                                   (FR-N6). All-or-nothing: a clone failure
//                                   starts no change.
//
// It performs NO fs write and starts NO process — every consequence reaches the
// board through the StartChangeRunner adapter (the one audited act site).

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits)
import type {
  StartFromIntentRequest,
  StartFromIntentStreamEvent,
} from "../../../shared/api-types";
import type { StartChangeRunner } from "../../ports/StartChangeRunner";
import {
  evaluateConfirmGate,
  type ConfirmGateRequest,
  type LiveProposal,
} from "./confirmGate";

// ─── classifyIntent — the deterministic intent → {primitive, slug} ───────────

/** The change-kind carried with an intent (investigation is still a change). */
export type IntentKind = "change" | "investigation";

/** A successful classification: a valid change primitive + slug. */
export interface IntentClassification {
  ok: true;
  primitive: string;
  slug: string;
}

/** A refusal: the intent is too thin to classify — ask, never guess (FR-29). */
export interface IntentAmbiguous {
  ok: false;
  code: "INTENT_AMBIGUOUS";
  clarifyingQuestion: string;
}

export type ClassifyResult = IntentClassification | IntentAmbiguous;

// INVESTIGATION vocabulary (FR-N9 — investigation is a change, never inline).
// A phrase here resolves to the contained-investigation primitive regardless of
// the declared kind. Mirrors conciergeRead's CONSEQUENTIAL_PHRASES style.
const INVESTIGATION_PHRASES = [
  "investigate",
  "look into",
  "looking into",
  "dig into",
  "digging into",
  "diagnose",
  "troubleshoot",
  "find out why",
  "figure out why",
  "work out why",
  "look at why",
  "root cause",
  "explore",
];

// Leading-verb → change primitive. The verb LEADS the intent ("fix the login
// loop", "add saved cards"). The vocabulary is the change-primitives set; we map
// the common founder verbs onto their primitive. A debug/diagnose verb is an
// investigation (handled above) unless it leads as a plain "fix".
const VERB_TO_PRIMITIVE: Record<string, string> = {
  fix: "fix",
  debug: "fix",
  repair: "fix",
  add: "create",
  build: "create",
  create: "create",
  make: "create",
  implement: "create",
  refactor: "refactor",
  rename: "refactor",
  remove: "delete",
  delete: "delete",
  migrate: "strangle",
  document: "document",
  test: "test",
  secure: "secure",
  harden: "harden",
};

// English stopwords stripped when deriving a slug — so "fix the login bug"
// yields the meaningful "login-bug", not "the-login-bug".
const SLUG_STOPWORDS = new Set([
  "the",
  "a",
  "an",
  "to",
  "of",
  "for",
  "in",
  "on",
  "and",
  "or",
  "is",
  "are",
  "was",
  "were",
  "why",
  "that",
  "this",
  "with",
  "into",
  "about",
  "my",
  "our",
  "your",
  "it",
  "its",
  // Contentless filler — an intent built only of these has nothing to name, so
  // it collapses below the 2-word floor ⇒ INTENT_AMBIGUOUS (never a guess).
  "do",
  "thing",
  "things",
  "stuff",
  "something",
  "some",
  "please",
]);

// Investigation/start VERBS dropped from the slug body (they pick the primitive,
// they aren't part of the descriptive name).
const VERB_WORDS = new Set([
  ...Object.keys(VERB_TO_PRIMITIVE),
  "investigate",
  "look",
  "dig",
  "diagnose",
  "troubleshoot",
  "figure",
  "work",
  "explore",
  "find",
  "out",
]);

/** CW-02: a valid change slug is 2-5 kebab-case words, first starting a letter. */
const SLUG_RE = /^[a-z][a-z0-9]*(-[a-z0-9]+){1,4}$/;

/**
 * Classify a plain-English intent into a change primitive + slug (FR-29).
 * Deterministic; never guesses (an under-specified intent ⇒ INTENT_AMBIGUOUS).
 * An investigation (by kind OR by phrase) resolves to a CHANGE primitive — a
 * contained investigation, never inline work (FR-34 / FR-N9).
 */
export function classifyIntent(intent: string, kind: IntentKind): ClassifyResult {
  const text = intent.trim().toLowerCase();
  if (text.length === 0) {
    return ambiguous();
  }

  const isInvestigation =
    kind === "investigation" ||
    INVESTIGATION_PHRASES.some((p) => new RegExp(`\\b${escapeRegExp(p)}\\b`).test(text));

  // An investigation is a CONTAINED change. It carries no behaviour change, so
  // it maps to `chore` (a housekeeping/exploration change) — but it IS a change
  // that lands at Recon, never inline work (FR-N9).
  const primitive = isInvestigation ? "chore" : primitiveFor(text);

  const slug = deriveSlug(text);
  if (slug === null) {
    return ambiguous();
  }

  return { ok: true, primitive, slug };
}

/** The primitive for a non-investigation intent, from its LEADING verb. */
function primitiveFor(text: string): string {
  const first = text.replace(/^[^a-z]+/, "").split(/\s+/)[0] ?? "";
  return VERB_TO_PRIMITIVE[first] ?? "feat";
}

/**
 * Derive a CW-02-valid slug (2-5 kebab words) from the intent: drop stopwords +
 * the leading verb, kebab-case the meaningful words, clamp to 5. Returns null
 * when fewer than 2 meaningful words remain (the intent is too thin — ambiguous,
 * never a guess).
 */
function deriveSlug(text: string): string | null {
  const words = text
    .replace(/[^a-z0-9\s]/g, " ")
    .split(/\s+/)
    .filter((w) => w.length > 0)
    .filter((w) => !SLUG_STOPWORDS.has(w))
    .filter((w) => !VERB_WORDS.has(w))
    // A slug word must START with a letter (CW-02) — drop pure-numeric leads.
    .filter((w) => /^[a-z]/.test(w));

  if (words.length < 2) return null;
  const slug = words.slice(0, 5).join("-");
  return SLUG_RE.test(slug) ? slug : null;
}

function ambiguous(): IntentAmbiguous {
  return {
    ok: false,
    code: "INTENT_AMBIGUOUS",
    clarifyingQuestion:
      "Could you say a bit more about what you'd like to change — what should be different when it's done?",
  };
}

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * Adapt a start-from-intent request to the confirm gate's request shape. The
 * gate (reused from WP-010) only ever opens on a `confirm` phase + a matching
 * token; the start-from-intent `propose` phase maps to a non-act phase so the
 * gate stays closed for it (the proposal mints/starts nothing — FR-N6).
 */
function toGateRequest(request: StartFromIntentRequest): ConfirmGateRequest {
  return {
    phase: request.phase === "confirm" ? "confirm" : "ask",
    ...(request.confirmToken !== undefined
      ? { confirmToken: request.confirmToken }
      : {}),
  };
}

// ─── the orchestrator ────────────────────────────────────────────────────────

/** The resolved Project repo a change starts against (FR-29). */
export interface ResolvedProject {
  /** Project.source.repo — the clone source when absent. */
  repo: string;
  /** Project.source.path — the local working copy path. */
  path: string;
  primaryBranch: string;
  /** True when the repo is already present locally (else clone first, FR-30). */
  present: boolean;
}

/** Where the orchestrator streams its start-from-intent events. */
export interface StartFromIntentSink {
  emit(event: StartFromIntentStreamEvent): void;
}

export interface StartFromIntentDeps {
  /** The deterministic server-side change-start (ADR-007). */
  startChangeRunner: StartChangeRunner;
  /** Resolve a productId → its Project repo (or refuse if unknown). */
  resolveProject: (productId: string) => Promise<ResolvedProject | null>;
  /** A fresh confirm token per proposal. Injected for deterministic tests. */
  newToken: () => string;
}

/** A pre-stream refusal the route maps to an HTTP status (parity w/ onboarding). */
export interface StartRefusal {
  status: number;
  code: "INTENT_AMBIGUOUS" | "START_CONFIRM_STALE" | "REPO_UNREACHABLE";
  message: string;
}

export class StartFromIntentOrchestrator {
  /** The live proposal, set on a propose turn, cleared on a completed start. */
  private live:
    | (LiveProposal & {
        primitive: string;
        slug: string;
        productId: string;
        kind: IntentKind;
      })
    | null = null;

  /**
   * The repo root resolved (and, if absent, CLONED) during a confirm pre-check —
   * carried into the streaming `handleConfirm` so the clone runs EXACTLY ONCE
   * (the pre-check is where a clone failure becomes a clean 502; the stream then
   * reuses the materialised repo). Cleared on each new turn.
   */
  private resolvedRepoRoot: string | null = null;

  constructor(private readonly deps: StartFromIntentDeps) {}

  /**
   * Side-effect-free pre-check the route uses to decide the HTTP status for the
   * PRE-STREAM refusals (parity with onboarding's lazy-open pattern):
   *   - a propose turn with an ambiguous intent ⇒ 422 INTENT_AMBIGUOUS;
   *   - a confirm turn with a stale/mismatched token ⇒ 422 START_CONFIRM_STALE;
   *   - a confirm turn whose Project repo is ABSENT and cannot be cloned ⇒ 502
   *     REPO_UNREACHABLE (all-or-nothing: no change started).
   * Returns null when the turn may stream. May clone (FR-30) as part of the
   * confirm pre-check so the clone failure is a clean status, not a 200 stream.
   */
  async precheck(request: StartFromIntentRequest): Promise<StartRefusal | null> {
    // Each turn starts with a clean resolved-repo (the carry is confirm-scoped).
    this.resolvedRepoRoot = null;

    if (request.phase === "propose") {
      const result = classifyIntent(request.intent ?? "", request.kind ?? "change");
      if (!result.ok) {
        return {
          status: 422,
          code: "INTENT_AMBIGUOUS",
          message: result.clarifyingQuestion,
        };
      }
      return null;
    }

    // confirm — the gate must be open AND the repo reachable before we stream.
    const gate = evaluateConfirmGate(toGateRequest(request), this.live);
    if (!gate.open || this.live === null) {
      return {
        status: 422,
        code: "START_CONFIRM_STALE",
        message:
          "That proposal is no longer current — let's look again before I start anything.",
      };
    }

    const project = await this.deps.resolveProject(this.live.productId);
    if (project === null) {
      return {
        status: 502,
        code: "REPO_UNREACHABLE",
        message: "I couldn't find that product's repository.",
      };
    }

    // LOCAL-FIRST (FR-30): clone an absent repo BEFORE starting. A clone failure
    // is a clean 502 with NO change started (all-or-nothing). The clone runs
    // HERE, once; `handleConfirm` reuses the materialised repo via
    // `resolvedRepoRoot` (no double-clone).
    if (!project.present) {
      const cloned = await this.deps.startChangeRunner.clone({
        sourceRepo: project.repo,
        targetPath: project.path,
      });
      if (!cloned.ok) {
        return { status: 502, code: "REPO_UNREACHABLE", message: cloned.message };
      }
      this.resolvedRepoRoot = cloned.path;
    } else {
      this.resolvedRepoRoot = project.path;
    }

    return null;
  }

  /** Run one start-from-intent turn, streaming events into `sink`. */
  async turn(
    request: StartFromIntentRequest,
    sink: StartFromIntentSink,
  ): Promise<void> {
    if (request.phase === "confirm") {
      await this.handleConfirm(request, sink);
      return;
    }
    this.handlePropose(request, sink);
  }

  /** A PROPOSE turn: classify + show the proposal (starts NOTHING; FR-N6). */
  private handlePropose(
    request: StartFromIntentRequest,
    sink: StartFromIntentSink,
  ): void {
    sink.emit({ type: "state", state: "classifying" });

    const result = classifyIntent(request.intent ?? "", request.kind ?? "change");
    if (!result.ok) {
      // The pre-check already mapped this to a 422; defensively surface it.
      sink.emit({ type: "state", state: "failed" });
      sink.emit({
        type: "error",
        code: "INTENT_AMBIGUOUS",
        message: result.clarifyingQuestion,
      });
      return;
    }

    const token = this.deps.newToken();
    this.live = {
      confirmToken: token,
      primitive: result.primitive,
      slug: result.slug,
      productId: request.productId ?? "",
      kind: request.kind ?? "change",
    };

    sink.emit({ type: "state", state: "proposing" });
    sink.emit({
      type: "proposal",
      proposal: {
        confirmToken: token,
        primitive: result.primitive,
        slug: result.slug,
      },
    });
  }

  /**
   * A CONFIRM turn: the confirm gate (FR-N6) → clone-if-absent (FR-30) → start
   * via the runner (FR-29) → emit `started` (the change at Recon). All-or-
   * nothing: a clone/start failure starts no change.
   */
  private async handleConfirm(
    request: StartFromIntentRequest,
    sink: StartFromIntentSink,
  ): Promise<void> {
    const gate = evaluateConfirmGate(toGateRequest(request), this.live);
    if (!gate.open || this.live === null) {
      sink.emit({ type: "state", state: "failed" });
      sink.emit({
        type: "error",
        code: "START_CONFIRM_STALE",
        message:
          "That proposal is no longer current — let's look again before I start anything.",
      });
      return;
    }

    const live = this.live;

    // The repo was resolved (and cloned-if-absent) by the pre-check, which runs
    // the clone exactly once. When the orchestrator is driven directly (no
    // pre-check — e.g. a unit test), fall back to resolving + cloning here.
    let repoRoot = this.resolvedRepoRoot;
    if (repoRoot === null) {
      const project = await this.deps.resolveProject(live.productId);
      if (project === null) {
        sink.emit({ type: "state", state: "failed" });
        sink.emit({
          type: "error",
          code: "REPO_UNREACHABLE",
          message: "I couldn't find that product's repository.",
        });
        return;
      }
      repoRoot = project.path;
      if (!project.present) {
        // LOCAL-FIRST (FR-30): clone an absent repo first; a clone failure starts
        // NO change (all-or-nothing).
        sink.emit({ type: "state", state: "cloning" });
        const cloned = await this.deps.startChangeRunner.clone({
          sourceRepo: project.repo,
          targetPath: project.path,
        });
        if (!cloned.ok) {
          sink.emit({ type: "state", state: "failed" });
          sink.emit({ type: "error", code: "REPO_UNREACHABLE", message: cloned.message });
          return;
        }
        repoRoot = cloned.path;
      }
    }

    // START (FR-29) — the deterministic server-side act. The change lands at
    // Recon; an investigation is CONTAINED in this change, never inline (FR-N9).
    sink.emit({ type: "state", state: "starting" });
    const started = await this.deps.startChangeRunner.start({
      repoRoot,
      primitive: live.primitive,
      slug: live.slug,
      intent: request.intent ?? "",
    });

    if (!started.ok) {
      sink.emit({ type: "state", state: "failed" });
      sink.emit({
        type: "error",
        code: started.code === "REPO_UNREACHABLE" ? "REPO_UNREACHABLE" : "SESSION_UNREACHABLE",
        message: started.message,
      });
      return;
    }

    // The act completed — clear the live proposal + resolved repo so a stale
    // re-confirm can't start twice.
    this.live = null;
    this.resolvedRepoRoot = null;

    sink.emit({ type: "started", started: started.change });
    sink.emit({ type: "state", state: "complete" });
  }
}
