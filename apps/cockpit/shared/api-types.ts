// WP-001 — shared API types for the cockpit (TDD §5.1).
//
// Every server route shape and every client component prop that crosses
// the HTTP wire imports its type from this file. No runtime code lives
// here — these are pure type declarations. Keeping them in `shared/`
// (not `server/` and not `client/`) keeps the wire contract symmetric;
// either side can be regenerated against the same source.
//
// References:
// - TDD §5.1 (the canonical shapes).
// - TDD §9 (cross-import boundary — shared/ stays inside apps/cockpit/).

export type WorkflowStage =
  | "recon"
  | "specify"
  | "design"
  | "implement"
  | "review"
  | "ship"
  // Terminal stages — past the six-stage workflow. A 'shipped' change is
  // archived: worktree + branch + record all preserved as the audit trail,
  // surfaced in the Sidebar's collapsed "Shipped" section (#38).
  | "shipped";

export type Liveness =
  | { status: "running"; pid: number }
  | { status: "not-running" }
  // `unknown` is first-class: the probe couldn't determine the process state
  // and renders it distinctly rather than implying not-running (FR-41).
  | { status: "unknown"; reason: string };

/**
 * Whether a change is waiting on the founder, and why. Lifted from
 * `ChangeStatus.needsAttention` so both the status read and the board feed
 * import one shape — never two copies (CF-02 / DRY). `reason` is null when
 * the change is idle-but-fine (FR-12 — idle is NOT flagged).
 */
export interface NeedsAttention {
  flagged: boolean;
  reason: "blocked" | "waiting-on-decision" | "stopped-mid-reply" | null;
}

/**
 * The board's cheap change-health verdict. `"unknown"` is first-class — a
 * fresh or degraded change must read honestly ("too early to tell"), not
 * masquerade as on-track (FR-31). `"worth-a-look"` is carried by the wire but
 * the producer does not emit it yet — it lands when the scope-drift OODA
 * signal arrives (ADR-001); additive, no re-layout.
 */
export type ChangeHealthState =
  | "on-track"
  | "off-track"
  | "worth-a-look"
  | "unknown";

export interface ChangeHealth {
  /** producer emits on/off-track + unknown now; worth-a-look deferred (ADR-001/FR-31). */
  state: ChangeHealthState;
  /** plain-English reason from a fixed set — never the reply body (NFR-SEC-03/FR-32). */
  reason: string;
}

export interface Change {
  changeId: string;
  /** e.g. "CH-01KSJA" */
  handle: string;
  slug: string;
  /** "create" | "fix" | … (free-form across change kinds) */
  primitive: string;
  branch: string;
  worktreePath: string;
  /** one-line summary */
  intent: string;
  baseBranch: string;
  /** for the diff baseline; may be null in legacy records */
  baseSha: string | null;
  /** ISO 8601 UTC */
  createdAt: string;
  /** ISO 8601 UTC (from state.json) */
  updatedAt: string;
  stage: WorkflowStage;
  liveness: Liveness;
  /** Whether the change is waiting on the founder, and why (FR-30; CF-02). */
  needsAttention: NeedsAttention;
  /** Cheap on/off-track-or-unknown health read for the board card (FR-30/31). */
  health: ChangeHealth;
  /**
   * ISO 8601 UTC of the last activity; `null` ⇒ no-recency (FR-42). Drives the
   * relative-time label and the working/live split.
   */
  lastActivityAt: string | null;
}

export interface ChangeDetail extends Change {
  /** absolute paths to the JSONL files belonging to this change */
  transcriptPaths: string[];
}

export interface TreeNode {
  name: string;
  /** relative to the worktree root */
  path: string;
  kind: "file" | "directory";
  /** false → leaf; UI doesn't request children */
  hasChildren: boolean;
}

export interface FileContents {
  /** relative path */
  path: string;
  /** for copy-to-clipboard */
  absolutePath: string;
  /** null when binary or truncated */
  content: string | null;
  binary: boolean;
  truncated: boolean;
  sizeBytes: number;
  /** hint for Monaco's syntax highlighter */
  language: string | null;
}

/** One path that differs between the change's base commit and its worktree. */
export interface ChangedFile {
  /** relative to the worktree root */
  path: string;
  status: "new" | "edited" | "removed";
  /** added lines (git numstat); null = binary/unknown (numstat "-"). WP-P02 fills these. */
  added: number | null;
  /** removed lines (git numstat); null = binary/unknown. */
  removed: number | null;
}

/**
 * The change's changed-files set (base commit → worktree). `baseKnown`
 * is false for a legacy change with no recorded base sha — the list is
 * empty and the UI says so rather than implying "nothing changed".
 */
export interface ChangedFiles {
  files: ChangedFile[];
  baseKnown: boolean;
}

// ─── Provenance (WP-P01 contract; ADR-010/011) ───────────────────────────────
//
// The read projection over the change's brain entities + autonomous runs that
// powers the Provenance view (`GET /api/changes/:id/provenance`). Edge resolve
// stays server-side; the focused per-requirement trace is a `?focus=<reqId>`
// variant on the same endpoint (ADR-011). All shapes are named + reusable; the
// producer (WP-P05) and consumer (WP-P06) import these verbatim, never redeclare.

/** The dashboard front door — four plain-English digest tiles. */
export interface ProvenanceDigest {
  /** completed autonomous runs ("what it did"). */
  did: number;
  /** requirements verified-by-test vs total ("what it covered"). */
  covered: { verified: number; total: number };
  /** decision entities ("what it decided"). */
  decided: number;
  /** the agent's own gaps + self-critique ("what it flagged") — the trust tile. */
  flagged: {
    count: number;
    topGap: string | null;
    selfCritique: string | null;
  };
}

/** One step within an autonomous run (from a lifecyclerun's _step_runs). */
export interface RunStep {
  step: string;
  outcome: string;
  detail: string | null;
  gap: string | null;
  selfCritique: string | null;
}

/** One autonomous run (a lifecyclerun) — lens A, the run log. */
export interface RunLogEntry {
  runId: string;
  workflow: string | null;
  stepName: string;
  /** ISO 8601 */
  at: string;
  outcome: string;
  confidence: number | null;
  finalVerdict: string | null;
  steps: RunStep[];
}

/** One column of the Why → What → How → Tested coverage map — lens B. */
export type CoverageColumn =
  | { axis: "why"; items: { id: string; title: string }[] }
  | { axis: "what"; items: { id: string; title: string; verified: boolean }[] }
  | {
      axis: "how";
      items: { id: string; title: string; kind: "design" | "decision" }[];
    }
  | {
      axis: "tested";
      items: {
        id: string;
        title: string;
        outcome: "pass" | "skip" | "fail";
        /** Whether this row is an authored scenario or an actual test result —
         *  the TESTED column mixes both; the UI labels each by its real kind. */
        kind: "scenario" | "testresult";
      }[];
    };

/** The single per-requirement focused trace (lens B drill-in; `?focus=<reqId>`). */
export interface FocusedTrace {
  requirementId: string;
  why: { id: string; title: string }[];
  how: { id: string; title: string; kind: "design" | "decision" }[];
  tested: { id: string; title: string; outcome: "pass" | "skip" | "fail" }[];
}

/** The Provenance read projection (`GET /api/changes/:id/provenance`). */
export interface ProvenanceView {
  changeId: string;
  digest: ProvenanceDigest;
  /** lens A — the autonomous runs, newest first. */
  runLog: RunLogEntry[];
  /** lens B — the Why/What/How/Tested columns. */
  coverage: CoverageColumn[];
}

// ─── WP-P08 — change-origin attribution (ADR-012/013) ────────────────────────
//
// The honesty flag. ALWAYS present on every Origin variant (TDD §3.3): the seam
// never presents an inference as a recorded fact. `"inferred"` means "we worked
// this out from the timeline"; `"recorded"` means "the commit/sidecar stamped
// it" (the recorded path arrives with stamping — WP-P12/P13). A recorded origin
// OVERRIDES an inferred one (ADR-012).
export type Attribution = "inferred" | "recorded";

/**
 * Where a file's change came from. A discriminated union on `kind`:
 *   - `autonomous` — a brain `lifecyclerun` (the agent's own autonomous run).
 *   - `assisted`   — a chat conversation turn (a human-in-the-loop session).
 *   - `unknown`    — neither correlated; carries a plain-English `reason`.
 *     `unknown` is NOT an error — it is the honest "we couldn't tell" answer.
 *
 * Every variant carries `attribution` (the honesty flag — ADR-012, TDD §3.3).
 */
export type Origin =
  | {
      kind: "autonomous";
      run: { runId: string; workflow: string | null; outcome: string };
      /** The run's recorded confidence (0..1), or null when absent. */
      confidence: number | null;
      attribution: Attribution;
    }
  | {
      kind: "assisted";
      conversation: {
        conversationId: string;
        turn: number;
        /** The turn's plain-English summary (FE), or null when unavailable. */
        summary: string | null;
      };
      attribution: Attribution;
    }
  | {
      kind: "unknown";
      /** Plain-English reason we could not attribute (never a guess). */
      reason: string;
      attribution: Attribution;
    };

/** One file's origin within a change (the per-file row of the change list). */
export interface FileOrigin {
  /** Path relative to the repo root. */
  path: string;
  origin: Origin;
}

/**
 * One origin result (`GET /api/changes/:id/origin?path=<relpath>`): the origin
 * of a single file, or the change-level origin when `path` is null.
 */
export interface OriginView {
  changeId: string;
  /** null = change-level origin; a relpath = that one file's origin. */
  path: string | null;
  origin: Origin;
}

/**
 * The whole-change origin list (`GET /api/changes/:id/origin`): one inferred
 * `FileOrigin` per changed file.
 */
export interface ChangeOriginView {
  changeId: string;
  files: FileOrigin[];
}

export interface FileDiff {
  path: string;
  absolutePath: string;
  /** null = file did not exist at base_sha */
  base: string | null;
  /** null = file deleted in the worktree */
  current: string | null;
  binary: boolean;
  truncated: boolean;
  language: string | null;
}

export type TranscriptMessage =
  | {
      kind: "user";
      uuid: string;
      timestamp: string;
      text: string;
    }
  | {
      kind: "assistant";
      uuid: string;
      timestamp: string;
      blocks: AssistantBlock[];
    }
  | {
      kind: "system";
      uuid: string;
      timestamp: string;
      subtype: string;
      text: string;
    };

export type AssistantBlock =
  | { kind: "text"; text: string }
  | { kind: "tool-use"; toolName: string; input: unknown }
  | { kind: "tool-result"; toolUseId: string; content: unknown };

// ─── WP-003 — contract-preview wire types ─────────────────────────────────
//
// The cockpit serves the renderers' (WP-001/002) rendered artifacts —
// CONTRACT.html + UI.html — read from the shared `CONTRACT.manifest.json`
// (TDD §2.3 the data seam; ADR-001 read-only). The summary endpoint
// (`GET /api/changes/:id/contract`) returns `ContractAvailability`, which the
// per-change "open data contract / open UI" links read to decide what to
// render (present / no-UI note / unavailable). The cockpit never parses the
// contracts itself; this shape is a projection of the manifest.

/** The data-contract half of the manifest (what was rendered). */
export interface DataContractSummary {
  /** "servicespec" | "openapi" | "raw" | "none" (renderer-reported). */
  format: string;
  /** The primary contract's name, when the renderer derived one. */
  name: string | null;
}

/** The UI-contract half: present (a UI.html exists) or none (+ a note). */
export type UiContractSummary =
  | { status: "present" }
  | { status: "none"; note: string };

/**
 * Whether a change's rendered contracts are reachable, and what they are.
 *
 *   - `ready`        → the worktree resolved (present, or recreated on
 *                      demand); `dataContract` + `uiContract` describe what
 *                      the manifest carries. `present` is false when the
 *                      worktree resolved but no manifest has been rendered
 *                      yet (the links show a "not rendered yet" affordance).
 *   - `unavailable`  → the worktree is gone and couldn't be reached
 *                      (a shipped change that isn't recreatable, or a
 *                      recreate that failed / a malformed handle the
 *                      shape-guard refused). `note` is a plain message.
 */
export type ContractAvailability =
  | {
      status: "ready";
      /** false → worktree present but no CONTRACT.manifest.json yet. */
      present: boolean;
      dataContract: DataContractSummary | null;
      uiContract: UiContractSummary;
    }
  | { status: "unavailable"; note: string };

// ─── WP-007 — terminal attach wire types ──────────────────────────────────
//
// The cockpit consumes a PTY-backed session's terminal over the SAME
// Unix-domain socket the base contract defines (§2.8) — no new channel
// (ADR-003). These types mirror the §2.13.1 wire shape the socket speaks
// for the attach methods. They are the type-level conformance check the
// TerminalBridge port (apps/cockpit/server/ports/TerminalBridge.ts) is built
// against; the recorded byte fixtures are the runtime conformance check.
//
// Raw terminal bytes are base64-encoded on the wire (NDJSON is text; terminal
// bytes are binary — base64 is the boring binary-in-JSON encoding, §2.13.1).
// The port decodes `term.data` → Uint8Array so consumers never see base64.

/** The phase a `term` frame belongs to: the initial scrollback snapshot, or
 *  the live byte feed that follows it (§2.12 snapshot-then-live join). */
export type TermPhase = "snapshot" | "live";

/**
 * One `term` line of an `attach` streaming response (§2.13.1). `data` is the
 * base64-encoded raw PTY byte chunk; `encoding` is always "base64" on the
 * current wire. The port decodes this to bytes — `TermFrame` is the wire
 * shape, not what consumers handle.
 */
export interface TermFrame {
  data: string;
  encoding: "base64";
  phase: TermPhase;
}

/**
 * The ack returned by `feed` (§2.13.1): how many keystroke bytes the PTY
 * master accepted. Mirrors the write side's `{ written }` result.
 */
export interface FeedAck {
  written: number;
}

/**
 * The result of `open(io_mode:"pty")` (§2.13.1) as the terminal port surfaces
 * it: the session key, its (always "pty" here) io-mode, and how many viewers
 * are currently attached (0 = headless, §2.12.5).
 */
export interface TerminalOpenResult {
  key: string;
  ioMode: "pty";
  viewerCount: number;
}

/**
 * The three-category terminal error model (§2.15), as a typed value the
 * component renders — never a thrown opaque (WPF: errors are values).
 *
 *   - NOT_PTY_SESSION (expected) — attach/feed/resize on a pipe-mode session.
 *   - NO_SESSION      (expected) — no session for the key.
 *   - SOCKET_CLOSED   (protocol) — attach stream dropped mid-feed.
 *   - PTY_OPEN_FAILED (internal) — os.openpty()/spawn-with-pty failed.
 */
export type TerminalErrorCode =
  | "NOT_PTY_SESSION"
  | "NO_SESSION"
  | "SOCKET_CLOSED"
  | "PTY_OPEN_FAILED";

export type TerminalErrorCategory = "expected" | "protocol" | "internal";

export interface TerminalError {
  category: TerminalErrorCategory;
  code: TerminalErrorCode;
  message: string;
}

/**
 * The component-facing emission of `attach`: either a decoded byte chunk
 * (with its phase) or a typed, narrowable error. This is the "errors are
 * values" surface — a consumer iterates results and renders both bytes and
 * errors without try/catch (WPF-02).
 */
export type AttachResult =
  | { ok: true; bytes: Uint8Array; phase: TermPhase }
  | { ok: false; error: TerminalError };

/**
 * The live byte stream an `attach` yields once errors are unwrapped: the
 * snapshot bytes first, then live bytes (§2.12). Consumers that only care
 * about bytes (piping straight into xterm.js `Terminal.write()`) use this;
 * consumers that must render errors use `AttachResult`.
 */
export type AttachStream = AsyncIterable<Uint8Array>;

// ═══════════════════════════════════════════════════════════════════════════
// WP-001 — the full api-types seam (reads + chat + products + discovery).
//
// The runtime TypeScript MIRROR of the signed `contracts/openapi.yaml` — the
// single wire seam every vertical slice (board read, status, chat, brain,
// search, product switch, concierge, onboarding, start-from-intent) imports.
// Every shape below is copied VERBATIM from the OpenAPI components (CF-02: the
// contract is the single source of truth). All stream-event types are
// discriminated unions on a literal `type` field, mirroring the existing event
// types (CF-09; ADR-001). No runtime code — type-only, as the rest of the file.
//
// References:
// - contracts/openapi.yaml (the verbatim source for every shape here).
// - CONTRACT_FIRST_STANDARD CF-02/03/04/09.
// ═══════════════════════════════════════════════════════════════════════════

// ─── Reads ─────────────────────────────────────────────────────────────────

/**
 * Read-time, plain-English status for a change (FR-05). Computed on read, not a
 * stored periodic checkpoint. `needsAttention.reason` is null when the change
 * is idle-but-fine (FR-12 — idle is NOT flagged).
 */
export interface ChangeStatus {
  changeId: string;
  stage: WorkflowStage;
  /** One human-readable sentence/short paragraph of what's happening. */
  headline: string;
  /** The single `NeedsAttention` shape, reused by the board feed too (CF-02 / DRY). */
  needsAttention: NeedsAttention;
}

/** One entity/workflow the agent created for a change (FR-06/07). */
export interface BrainEntity {
  /** e.g. "dna:requirement:<ulid>" */
  id: string;
  /** "requirement" | "workflow" | "design" | "decision" | … */
  kind: string;
  title: string;
  /** The readable fields/content for the detail view (FR-07). */
  detail?: Record<string, unknown>;
}

/** Brain entities of one kind (FR-06). */
export interface BrainGroup {
  kind: string;
  items: BrainEntity[];
}

/** A change's brain entities grouped by kind; `groups: []` is the empty case (FR-06). */
export interface BrainView {
  changeId: string;
  groups: BrainGroup[];
}

// ─── Chat (the one write path; ADR-001/003) ──────────────────────────────────

/** The chat reply stream's error codes (FR-19/20/21). */
export type ChatErrorCode =
  | "SESSION_UNREACHABLE"
  | "SESSION_CHANGE_MISMATCH"
  | "SESSION_BUSY";

/**
 * One SSE event in the chat reply stream (ADR-001). Discriminated on `type`.
 * `state` carries the session lifecycle for the founder (FR-23); `chunk` a
 * reply delta (FR-17); `complete` honestly indicates whether the change was
 * resumed (FR-26); `error` a typed code (FR-19/20/21).
 */
export type ChatStreamEvent =
  | {
      type: "state";
      state:
        | "ready"
        | "resuming"
        | "spawning"
        | "replying"
        | "complete"
        | "interrupted"
        | "failed";
    }
  | { type: "chunk"; text: string }
  | { type: "complete"; resumed: boolean }
  | { type: "error"; code: ChatErrorCode; message: string };

// ─── Products (multi-product; FR-37/38, ADR-009) ─────────────────────────────

/** One Product under the Tenant. `active` marks the current board scope. */
export interface Product {
  /** e.g. "dna:product:<ulid>" */
  productId: string;
  name: string;
  active?: boolean;
}

/** The Tenant's Products with the active one marked (FR-38). */
export interface ProductList {
  products: Product[];
  /** The active Product id, or null when none selected yet. */
  activeProductId: string | null;
}

/**
 * Where a Project's code lives — mapped to `--repo-root` for `sulis-change
 * start` (FR-29/30) and persisted durably (FR-36). The keys are snake_case
 * VERBATIM from `Project.source`; this is the one sanctioned snake_case wire
 * shape in the seam.
 */
export interface ProjectSource {
  /** Repo URL or local path (Project.source.repo). */
  repo: string;
  /** Sub-path within the repo, if any. */
  path: string;
  primary_branch: string;
}

// ─── Discovery — onboarding (cold-start mint; UC-07, ADR-007/008) ─────────────

/** One turn in the cold-start onboarding conversation (UC-07). */
export interface OnboardingRequest {
  /**
   * `search` = begin/continue discovery in the chosen area; `ask` = answer a
   * clarifying question; `confirm` = approve the pending proposal (the
   * consequential act — mint + repo find-or-create — happens ONLY on confirm,
   * FR-N6).
   */
  phase: "search" | "ask" | "confirm";
  /** The folder discovery reads ONLY under (FR-N7). Required on first `search`. */
  chosenArea?: string;
  /** The founder's plain-English answer (for `ask`). */
  message?: string;
  /** The token from the proposal being confirmed (for `confirm`). */
  confirmToken?: string;
  /**
   * The repo branch decision when confirming (FR-35). `find` configures an
   * existing repo; `create` makes a new one — default local-only `git init`
   * (ADR-008). Hosted-remote create is a separately-confirmed choice.
   */
  repoChoice?: {
    mode?: "find" | "create";
    /** Local-only is the safe default (ADR-008). */
    createTarget?: "local" | "hosted-remote";
  };
}

/** One SSE event in the onboarding conversation stream. Discriminated on `type`. */
export type OnboardingStreamEvent =
  | {
      type: "state";
      state:
        | "searching"
        | "asking"
        | "proposing"
        | "confirming"
        | "minting"
        | "complete"
        | "failed";
    }
  | { type: "chunk"; text: string }
  | {
      type: "proposal";
      /**
       * What the agent will mint/create, awaiting the founder's confirm (FR-N6).
       * Nothing is created until a `confirm` turn arrives.
       */
      proposal: {
        confirmToken: string;
        tenant?: string;
        product?: string;
        projects?: Array<{ name?: string; source?: ProjectSource }>;
        repoPlan?:
          | "found-existing"
          | "will-create-local"
          | "will-create-hosted-remote";
        /** True when the entity exists — surfaced, not duplicated (FR-31). */
        alreadyMinted?: boolean;
      };
    }
  | {
      type: "minted";
      /** The entities minted after a confirmed turn (via the spine emitters, FR-32). */
      minted: {
        tenant?: string;
        product?: Product;
        projects?: Array<{ projectId?: string; source?: ProjectSource }>;
      };
    }
  | {
      type: "error";
      code:
        | "DISCOVERY_SCOPE_VIOLATION"
        | "DISCOVERY_CONFIRM_STALE"
        | "REPO_CREATE_FAILED"
        | "MINT_FAILED"
        | "SESSION_UNREACHABLE"
        | "SESSION_BUSY";
      message: string;
    };

// ─── Discovery — start-from-intent (UC-08/10, ADR-007) ────────────────────────

/** Start a change (or an investigation, FR-34) from plain-English intent (UC-08). */
export interface StartFromIntentRequest {
  /**
   * `propose` = classify the intent to a primitive + slug and show the founder
   * what will start; `confirm` = approve it (the change-start act happens ONLY
   * on confirm, FR-N6).
   */
  phase: "propose" | "confirm";
  /** The Product whose Project's repo the change starts against (FR-29). */
  productId?: string;
  /** The founder's plain-English description of the work (for `propose`). */
  intent?: string;
  /**
   * `investigation` marks an explore/look-into request — it still becomes a real
   * change to contain the work (FR-34 / FR-N9), never inline concierge work.
   */
  kind?: "change" | "investigation";
  /** The token from the proposal being confirmed (for `confirm`). */
  confirmToken?: string;
}

/** One SSE event in the start-from-intent stream. Discriminated on `type`. */
export type StartFromIntentStreamEvent =
  | {
      type: "state";
      state:
        | "classifying"
        | "proposing"
        | "confirming"
        | "cloning"
        | "starting"
        | "complete"
        | "failed";
    }
  | { type: "chunk"; text: string }
  | {
      type: "proposal";
      proposal: {
        confirmToken: string;
        /** The resolved change primitive (FR-29). */
        primitive: string;
        slug: string;
        /** True when the Project's repo is absent and must be cloned first (FR-30). */
        willCloneRepo?: boolean;
      };
    }
  | {
      type: "started";
      /** The new change at Recon (FR-29). */
      started: Change;
    }
  | {
      type: "error";
      code:
        | "INTENT_AMBIGUOUS"
        | "START_CONFIRM_STALE"
        | "REPO_UNREACHABLE"
        | "SESSION_UNREACHABLE"
        | "SESSION_BUSY";
      message: string;
    };

// ─── Discovery — concierge (read-only Q&A front door; FR-33/34, ADR-006) ──────

/**
 * One SSE event in the concierge's read-only answer stream (FR-33). Reuses the
 * chat event shapes; `complete` adds an optional `route` hint when the question
 * should become onboarding or a started change (FR-34 — but the concierge does
 * NOT act here; it routes).
 */
export type ConciergeStreamEvent =
  | { type: "state"; state: "thinking" | "replying" | "complete" | "failed" }
  | { type: "chunk"; text: string }
  | {
      type: "complete";
      /**
       * A hint that the founder's intent is consequential and should go to the
       * confirm-gated act endpoint — NOT performed inline (FR-N8 / FR-N9).
       */
      route: "onboarding" | "start-from-intent" | null;
    }
  | { type: "error"; code: "SESSION_UNREACHABLE"; message: string };

// ─── The typed error envelope (all three code categories; CF-03) ─────────────

/**
 * Every error code the seam can return, across all three categories: chat
 * (FR-19/20/21), discovery/onboarding (FR-27..36, FR-N6..N11), and
 * start-from-intent (FR-29/30/34). The verbatim union from the OpenAPI
 * `Error.code` enum.
 */
export type ApiErrorCode =
  | "NOT_FOUND"
  | "SESSION_BUSY"
  | "SESSION_CHANGE_MISMATCH"
  | "SESSION_UNREACHABLE"
  // discovery / onboarding
  | "DISCOVERY_SCOPE_VIOLATION"
  | "DISCOVERY_CONFIRM_STALE"
  | "REPO_CREATE_FAILED"
  // start-from-intent
  | "INTENT_AMBIGUOUS"
  | "START_CONFIRM_STALE"
  | "REPO_UNREACHABLE"
  // settings management surface (WP-001; ADR-019/020/021). NOT_FOUND above is
  // shared (Protocol). These five are the settings-specific Expected/Internal
  // codes so `SettingsErrorCode` is a SUBSET of `ApiErrorCode` — the settings
  // seam REUSES this envelope (CF-03), never redeclares one.
  | "VALIDATION_FAILED"
  | "PATH_NOT_FOUND"
  | "PATH_NOT_A_REPO"
  | "WRITE_FAILED"
  | "IMMUTABLE_IMPLICIT";

/** The typed error envelope (the OpenAPI `Error` schema). */
export interface ApiError {
  error: string;
  code: ApiErrorCode;
}

// ─── Settings (the management surface; WP-001; ADR-019/020/021) ──────────────
//
// The wire shapes for the Settings screen — the products/projects/repo-links
// management tree (read), the create/edit/attach writes, and the typed error
// codes. Per CF-02 these are the single source of truth the producer (WP-006)
// and consumers (WP-007/008/009) import verbatim; none redeclare them.
//
// camelCase on the wire (anti-hardwiring): `RepoLink.primaryBranch` is
// camelCase here; the producer maps it to the snake_case `primary_branch` of
// `Project.source` at the persistence boundary (ADR-020). The snake_case
// `ProjectSource` above remains the ONE sanctioned snake_case wire shape — the
// settings shapes are NOT exceptions.

/**
 * One repo link as the Settings screen shows it (mirrors `Project.source`;
 * ADR-021 local-path-only attach).
 */
export interface RepoLink {
  /** Absolute local path the project points at, or null when unlinked. */
  localPath: string | null;
  primaryBranch: string;
  /** True when localPath exists on disk with a .git dir (ADR-021 read-only check). */
  present: boolean;
}

/** One project node in the Settings tree (ADR-019). */
export interface SettingsProject {
  projectId: string;
  name: string;
  /** null = no repo attached yet. */
  repo: RepoLink | null;
}

/** One product node in the Settings tree, with its projects (ADR-019). */
export interface SettingsProduct {
  productId: string;
  name: string;
  /** false for the synthesised implicit single product (read-only until real; ADR-020). */
  editable: boolean;
  projects: SettingsProject[];
}

/** GET /api/settings — the whole editable store, active entities only (ADR-019/020). */
export interface SettingsTree {
  products: SettingsProduct[];
}

/**
 * Create or edit a product (ADR-020 edit = validated re-save). `productId`
 * present ⇒ edit (upsert by id); absent ⇒ create.
 */
export interface ProductWrite {
  productId?: string;
  name: string;
}

/**
 * Create or edit a project under a product (ADR-020). `projectId` present ⇒
 * edit; `productId` required on create, immutable parent on edit (v1).
 */
export interface ProjectWrite {
  projectId?: string;
  productId: string;
  name: string;
}

/**
 * Attach an existing local folder to a project (ADR-021 local-path-only v1):
 * an absolute path to an EXISTING local folder. No URL, no create.
 */
export interface RepoAttachWrite {
  projectId: string;
  localPath: string;
}

/**
 * The settings error codes, across all three CF-03 categories:
 *   - Protocol: `NOT_FOUND`.
 *   - Expected: `VALIDATION_FAILED`, `PATH_NOT_FOUND`, `PATH_NOT_A_REPO`,
 *     `IMMUTABLE_IMPLICIT`.
 *   - Internal: `WRITE_FAILED`.
 * A SUBSET of `ApiErrorCode` — settings errors travel in the existing
 * `ApiError` envelope, reused not redeclared (CF-03).
 */
export type SettingsErrorCode =
  | "NOT_FOUND"
  | "VALIDATION_FAILED"
  | "PATH_NOT_FOUND"
  | "PATH_NOT_A_REPO"
  | "WRITE_FAILED"
  | "IMMUTABLE_IMPLICIT";
