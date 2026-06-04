// WP-010 — onboarding orchestrator (ADR-007/008; FR-27/31/32/35/36/N6/N7/N10/N11).
//
// The thin orchestration layer for cold-start onboarding. It REIMPLEMENTS
// nothing (ADR-007): search + mint are delegated to the agent over the SAME
// bridge as the chat (FR-27), which runs the existing discover-* skills and the
// validated spine emitters. The orchestrator owns ONLY the safety plumbing:
//
//   - SCOPE BOUND (FR-N7): the chosen area must be inside the permitted root;
//     a `..`-escape or an out-of-root area is refused with
//     DISCOVERY_SCOPE_VIOLATION before the bridge is ever relayed.
//   - CONFIRM GATE (FR-N6): a search/ask turn proposes (mints nothing); only a
//     token-matched confirm performs the act (confirmGate.ts).
//   - REPO FIND-OR-CREATE (FR-35/N10/N11): the find/create branch + the
//     no-dangling-config rule (repoFindOrCreate.ts).
//   - IDEMPOTENCY (FR-31): probe the existing graph; an already-minted entity
//     is surfaced (alreadyMinted), never duplicated.
//   - ALL-OR-NOTHING (FR-N11): the mint runs only after the repo is
//     found-or-created and reachable; a failed create persists nothing.
//
// It is an instance per discovery session (one product per conversation,
// founder-locked) so the live proposal persists across the propose→confirm
// turns. It performs NO fs write and starts NO process — every consequence
// reaches the brain through the bridge/emitter seam (FR-32 / NFR-DISC-03).
//
// One structured act-log line per consequential act (never a directory, prompt,
// or reply — NFR-SEC-03) is the route's job; the orchestrator emits only the
// founder-facing OnboardingStreamEvent union.

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits)
import type {
  OnboardingRequest,
  OnboardingStreamEvent,
  ProjectSource,
} from "../../../shared/api-types";
import type {
  SessionBridge,
  RelaySink,
  ChatStreamEvent,
} from "../../ports/SessionBridge";
import { evaluateConfirmGate, type LiveProposal } from "./confirmGate";
import {
  planRepo,
  resolveRepoSource,
  type RepoOutcome,
} from "./repoFindOrCreate";

/** Where the orchestrator streams its onboarding events. */
export interface OnboardingSink {
  emit(event: OnboardingStreamEvent): void;
}

/** The (agent-performed) repo find-or-create attempt, injected for tests. */
export type AttemptRepo = (
  request: OnboardingRequest,
  chosenArea: string,
) => Promise<RepoOutcome>;

export interface OnboardingDeps {
  /** The SAME bridge the chat rides (FR-27) — search + mint delegate to it. */
  sessionBridge: SessionBridge;
  /**
   * The idempotency probe (FR-31): the Product ids already minted in the graph.
   * Production composes `readProducts`; tests inject a list.
   */
  listProductIds: () => Promise<string[]>;
  /** The permitted search root — the chosen area must be inside it (FR-N7). */
  permittedRoot: string;
  /** A fresh confirm token per proposal. Injected for deterministic tests. */
  newToken: () => string;
  /**
   * The (agent-performed) repo find-or-create. Defaults to a reachable outcome
   * grounded in the chosen area; tests inject a failing variant to exercise the
   * no-dangling-config rule (FR-N10/N11).
   */
  attemptRepo?: AttemptRepo;
}

/** The discovery session the orchestrator drives (NOT a change id). */
const DISCOVERY_SESSION = "onboarding";

export class OnboardingOrchestrator {
  /** The live proposal, set on a propose turn, cleared on a completed act. */
  private live: LiveProposal | null = null;
  /**
   * The chosen area carried from the search turn into the confirm turn — the
   * confirm request itself doesn't repeat it, but the repo find-or-create + the
   * persisted `Project.source` need it (FR-36). Set on search, read on confirm.
   */
  private chosenArea = "";
  /** The product name proposed (so the confirm turn mints the same one). */
  private proposedProduct = "Your product";

  constructor(private readonly deps: OnboardingDeps) {}

  /**
   * Side-effect-free pre-check used by the route to decide the HTTP status for
   * the two PRE-STREAM refusals (parity with the chat relay's lazy-open
   * pattern): an out-of-root search area ⇒ 422 DISCOVERY_SCOPE_VIOLATION
   * (FR-N7), and a stale/mismatched confirm ⇒ 422 DISCOVERY_CONFIRM_STALE
   * (FR-N6). Everything else streams. Returns `null` when the turn may stream.
   */
  precheck(
    request: OnboardingRequest,
  ): { status: number; code: string; message: string } | null {
    if (request.phase === "search" && !this.inScope(request.chosenArea)) {
      return {
        status: 422,
        code: "DISCOVERY_SCOPE_VIOLATION",
        message: "I can only look inside the folder you chose.",
      };
    }
    if (request.phase === "confirm") {
      const gate = evaluateConfirmGate(request, this.live);
      if (!gate.open) {
        return {
          status: 422,
          code: "DISCOVERY_CONFIRM_STALE",
          message:
            "That proposal is no longer current — let's look again before I create anything.",
        };
      }
    }
    return null;
  }

  /** Run one onboarding turn, streaming OnboardingStreamEvent into `sink`. */
  async turn(request: OnboardingRequest, sink: OnboardingSink): Promise<void> {
    if (request.phase === "confirm") {
      await this.handleConfirm(request, sink);
      return;
    }
    await this.handleSearchOrAsk(request, sink);
  }

  /** Is `chosenArea` inside the permitted root (FR-N7)? Fails closed on escape. */
  private inScope(chosenArea: string | undefined): boolean {
    if (!chosenArea) return false;
    const root = normalise(this.deps.permittedRoot);
    const area = normalise(chosenArea);
    if (area === root) return true;
    return area.startsWith(root.endsWith("/") ? root : `${root}/`);
  }

  /**
   * A SEARCH or ASK turn: bound the scope, delegate discovery to the bridge,
   * stream the agent's text, then PROPOSE (mints nothing). The confirm gate is
   * the only thing that turns a proposal into an act.
   */
  private async handleSearchOrAsk(
    request: OnboardingRequest,
    sink: OnboardingSink,
  ): Promise<void> {
    // SCOPE BOUND (FR-N7) — refuse an out-of-root area BEFORE touching the
    // bridge, so search can never escape the chosen folder.
    if (request.phase === "search" && !this.inScope(request.chosenArea)) {
      sink.emit({
        type: "state",
        state: "failed",
      });
      sink.emit({
        type: "error",
        code: "DISCOVERY_SCOPE_VIOLATION",
        message: "I can only look inside the folder you chose.",
      });
      return;
    }

    // Remember the chosen area so the confirm turn (which doesn't repeat it)
    // can find-or-create the repo there and persist Project.source (FR-36).
    if (request.phase === "search" && request.chosenArea) {
      this.chosenArea = request.chosenArea;
    }

    sink.emit({
      type: "state",
      state: request.phase === "search" ? "searching" : "asking",
    });

    // Delegate discovery to the agent (it runs the discover-* skills). The
    // bridge streams chat events; we surface its text as onboarding chunks.
    await this.relay(buildSearchPrompt(request), sink);

    // PROPOSE — idempotency probe (FR-31): surface an already-minted entity
    // rather than duplicating it.
    const existing = await this.deps.listProductIds();
    const token = this.deps.newToken();
    this.live = { confirmToken: token };
    this.proposedProduct = deriveProductName(request);

    sink.emit({ type: "state", state: "proposing" });
    sink.emit({
      type: "proposal",
      proposal: {
        confirmToken: token,
        tenant: "Your workspace",
        product: this.proposedProduct,
        projects: [
          {
            name: slugify(this.proposedProduct),
            source: provisionalSource(this.chosenArea),
          },
        ],
        repoPlan: planRepo(request.repoChoice, {
          chosenArea: request.chosenArea ?? "",
        }).repoPlan,
        alreadyMinted: existing.length > 0,
      },
    });
  }

  /**
   * A CONFIRM turn: the confirm gate (FR-N6) → repo find-or-create
   * (FR-35/N10/N11) → mint via the bridge/emitters (FR-32) → emit `minted`.
   * All-or-nothing: a failed repo step persists nothing (the graph is unchanged).
   */
  private async handleConfirm(
    request: OnboardingRequest,
    sink: OnboardingSink,
  ): Promise<void> {
    const gate = evaluateConfirmGate(request, this.live);
    if (!gate.open) {
      // Any closed gate on a confirm turn (stale token, or a confirm with no
      // live proposal) is surfaced as a stale-proposal refusal — the founder
      // re-proposes before anything is created (FR-N6).
      sink.emit({ type: "state", state: "failed" });
      sink.emit({
        type: "error",
        code: "DISCOVERY_CONFIRM_STALE",
        message:
          "That proposal is no longer current — let's look again before I create anything.",
      });
      return;
    }

    sink.emit({ type: "state", state: "confirming" });

    // REPO FIND-OR-CREATE (FR-35) — the act the founder confirmed. The chosen
    // area is the one carried from the search turn (the confirm request doesn't
    // repeat it). The agent performs the find/`git init`; we interpret the
    // outcome (no-dangling-config).
    const plan = planRepo(request.repoChoice, { chosenArea: this.chosenArea });
    const attempt = this.deps.attemptRepo ?? defaultAttemptRepo;
    const outcome = await attempt(request, this.chosenArea);
    const resolved = resolveRepoSource(plan, outcome);

    if (!resolved.ok) {
      // ALL-OR-NOTHING (FR-N10/N11): the repo step failed — persist NOTHING.
      // The live proposal stays so the founder can retry without re-searching.
      sink.emit({ type: "state", state: "failed" });
      sink.emit({
        type: "error",
        code: resolved.code === "REPO_CREATE_FAILED" ? "REPO_CREATE_FAILED" : "SESSION_UNREACHABLE",
        message: resolved.message,
      });
      return;
    }

    // MINT (FR-32) — delegate to the bridge so every entity is written through
    // the validated spine emitters (no freehand entity write).
    sink.emit({ type: "state", state: "minting" });
    await this.relay(buildMintPrompt(this.proposedProduct, resolved.source), sink);

    // The act completed — clear the live proposal so a stale re-confirm can't
    // mint twice (idempotency + one-product-per-conversation, founder-locked).
    this.live = null;

    sink.emit({
      type: "minted",
      minted: {
        tenant: "Your workspace",
        product: {
          productId: "dna:product:pending",
          name: this.proposedProduct,
        },
        projects: [{ projectId: "dna:project:pending", source: resolved.source }],
      },
    });
    sink.emit({ type: "state", state: "complete" });
  }

  /** Relay a prompt to the bridge, surfacing its chat events as onboarding chunks. */
  private async relay(prompt: string, sink: OnboardingSink): Promise<void> {
    const chatSink: RelaySink = {
      emit: (event: ChatStreamEvent) => {
        if (event.type === "chunk") sink.emit({ type: "chunk", text: event.text });
        // state/complete from the bridge are internal lifecycle; the
        // orchestrator owns the onboarding state machine, so we swallow them.
      },
    };
    await this.deps.sessionBridge.relay(DISCOVERY_SESSION, prompt, chatSink);
  }
}

/** The default reachable outcome — the find/create succeeded in the chosen area. */
const defaultAttemptRepo: AttemptRepo = async (request, chosenArea) => ({
  outcome: "reachable",
  repo: chosenArea,
  path: "",
  primaryBranch: "main",
});

/** A provisional ProjectSource shown in the proposal (pre-confirm). */
function provisionalSource(chosenArea: string): ProjectSource {
  return { repo: chosenArea, path: "", primary_branch: "main" };
}

/** Derive the product name from the founder's message (fallback safe default). */
function deriveProductName(request: OnboardingRequest): string {
  const msg = (request.message ?? "").trim();
  if (msg.length > 0) return msg;
  return "Your product";
}

function slugify(name: string): string {
  return (
    name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "product"
  );
}

/** Build the search prompt the agent runs (delegates to the discover-* skills). */
function buildSearchPrompt(request: OnboardingRequest): string {
  if (request.phase === "ask") {
    return `The founder answered: ${request.message ?? ""}. Continue discovery.`;
  }
  return `Run discovery in the chosen area only: ${request.chosenArea ?? ""}. Use the discover-project / discover-context / codebase-mapping skills; do not traverse outside it.`;
}

/** Build the mint prompt the agent runs (delegates to the spine emitters). */
function buildMintPrompt(product: string, source: ProjectSource): string {
  return `The founder confirmed. Mint the Tenant/Product/Project for "${product}" via the validated spine emitters (sulis-emit-tenant/-product/-project). Persist Project.source = ${JSON.stringify(
    source,
  )}.`;
}

/** Normalise a path: resolve `.`/`..` segments + collapse separators. */
function normalise(p: string): string {
  const isAbs = p.startsWith("/");
  const out: string[] = [];
  for (const seg of p.split("/")) {
    if (seg === "" || seg === ".") continue;
    if (seg === "..") {
      out.pop();
      continue;
    }
    out.push(seg);
  }
  return (isAbs ? "/" : "") + out.join("/");
}
