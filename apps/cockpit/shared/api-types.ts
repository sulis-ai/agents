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
  | { status: "unknown"; reason: string };

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
  needsAttention: {
    flagged: boolean;
    reason: "blocked" | "waiting-on-decision" | "stopped-mid-reply" | null;
  };
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
  | "REPO_UNREACHABLE";

/** The typed error envelope (the OpenAPI `Error` schema). */
export interface ApiError {
  error: string;
  code: ApiErrorCode;
}
