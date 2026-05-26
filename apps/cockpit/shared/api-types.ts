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
  | "ship";

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
