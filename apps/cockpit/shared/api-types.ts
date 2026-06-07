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
