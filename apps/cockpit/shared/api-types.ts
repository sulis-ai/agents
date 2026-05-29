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
