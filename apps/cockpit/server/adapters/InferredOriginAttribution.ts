// WP-P09 — InferredOriginAttribution adapter (ADR-012).
//
// The inferred side of the `OriginAttribution` port. For one file it:
//   1. reads the file's last-changing commit via the ONE git site
//      (`gitLogLastCommit` in gitShow.ts — no new spawn),
//   2. reads the change's autonomous runs via `readBrain` (the `lifecyclerun`
//      entities), and its conversation turns via the transcript locator/parser
//      + `groupTurns`,
//   3. hands all three to the PURE `correlate` (no I/O there).
//
// Every result it produces is `attribution: "inferred"` (the honesty flag —
// TDD §3.3), EXCEPT a recorded trailer the correlate short-circuits to
// `"recorded"` (recorded overrides inferred — ADR-012; the recorded ADAPTER is
// WP-P13, but a stamped commit read through inference still reports the truth).
//
// Fail-soft throughout: a file with no resolvable commit, a change with no
// runs/turns, an absent brain or transcript dir — all resolve to a plain-English
// `unknown`, NEVER an error (DoD Green: "missing commit/run/turn → unknown").

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern blocks escapes out of apps/cockpit/, which import/no-restricted-paths enforces)
import type { BrainEntity, Origin } from "../../shared/api-types";
import type { OriginAttribution } from "../ports/OriginAttribution";
import {
  correlate,
  type RunFacts,
  type TurnFacts,
} from "../lib/originAttribution/correlate";
import { gitLogLastCommit, type GitLastCommit } from "../lib/gitShow";
import { groupTurns, type TurnItem } from "../../shared/groupTurns";
import { locateTranscripts } from "../lib/locateTranscripts";
import { parseTranscripts } from "../lib/parseTranscripts";
import { readBrain } from "../lib/readBrain";

/** The reads the adapter needs, injected so tests can stub git/brain/turns. */
export interface InferredOriginDeps {
  /** Realpath-resolved worktree root for the change. */
  worktreeRoot: string;
  /** Where Claude Code stores session transcripts (`~/.claude/projects`). */
  claudeProjectsDir: string;
  /** The worktree path AS RECORDED (pre-realpath) — for transcript locating. */
  recordedWorktreePath: string;
  /** Override the git subprocess timeout. */
  gitTimeoutMs?: number;
  /** Correlation windows / clock-free overrides (tests). */
  runWindowMs?: number;
  turnWindowMs?: number;
}

function strField(detail: Record<string, unknown>, key: string): string | null {
  const v = detail[key];
  return typeof v === "string" && v.length > 0 ? v : null;
}

function numField(
  detail: Record<string, unknown>,
  key: string,
): number | null {
  const v = detail[key];
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

/** Project the change's `lifecyclerun` entities into RunFacts for correlate. */
function runsFromBrain(entities: BrainEntity[]): RunFacts[] {
  const runs: RunFacts[] = [];
  for (const e of entities) {
    if (e.kind !== "lifecyclerun") continue;
    const d = e.detail ?? {};
    const at = strField(d, "at") ?? strField(d, "valid_from");
    if (at === null) continue;
    runs.push({
      runId: strField(d, "_run_id") ?? e.id,
      at,
      outcome: strField(d, "outcome") ?? "",
      workflow: strField(d, "_workflow"),
      confidence: numField(d, "confidence"),
    });
  }
  return runs;
}

/**
 * Project the change's conversation turns into TurnFacts. The conversation id
 * is the transcript file's stem (the Claude Code session id); each turn's index
 * is its 1-based position; its `at` is the turn's timestamp; its summary is the
 * turn's first sentences (the plain-English carry — full Haiku summaries are the
 * chat surface's concern, not origin inference).
 */
function turnsFromMessages(
  messages: Parameters<typeof groupTurns>[0],
  conversationId: string,
): TurnFacts[] {
  const items = groupTurns(messages).filter(
    (i): i is TurnItem => i.type === "turn",
  );
  return items.map((t, idx) => ({
    conversationId,
    turn: idx + 1,
    at: t.timestamp,
    summary: firstSentences(t.said),
  }));
}

/** The first ~2 sentences of a turn's prose (plain-English carry). */
function firstSentences(text: string): string | null {
  const t = text.replace(/\s+/g, " ").trim();
  if (t === "") return null;
  const parts = t.match(/[^.!?]+[.!?]+(\s|$)/g);
  if (!parts || parts.length === 0) {
    return t.length > 240 ? `${t.slice(0, 237)}…` : t;
  }
  const out = parts.slice(0, 2).join("").trim();
  return out || t.slice(0, 237);
}

export class InferredOriginAttribution implements OriginAttribution {
  constructor(private readonly deps: InferredOriginDeps) {}

  async originFor(changeId: string, path?: string): Promise<Origin> {
    // Change-level origin: with no path we have no single commit to read.
    // Honest unknown — the per-file list (readOrigin) is the meaningful view.
    if (path === undefined || path === "") {
      return {
        kind: "unknown",
        reason:
          "origin is attributed per file; ask for a specific file's origin",
        attribution: "inferred",
      };
    }

    let commit: GitLastCommit | null;
    try {
      commit = await gitLogLastCommit({
        cwd: this.deps.worktreeRoot,
        relativePath: path,
        ...(this.deps.gitTimeoutMs !== undefined
          ? { timeoutMs: this.deps.gitTimeoutMs }
          : {}),
      });
    } catch {
      // A git failure (e.g. timeout) is fail-soft for origin: unknown, never 500.
      commit = null;
    }
    if (commit === null) {
      return {
        kind: "unknown",
        reason: "no commit has touched this file yet",
        attribution: "inferred",
      };
    }

    const [runs, turns] = await Promise.all([
      this.readRuns(changeId),
      this.readTurns(),
    ]);

    return correlate(
      { commit, runs, turns },
      {
        ...(this.deps.runWindowMs !== undefined
          ? { runWindowMs: this.deps.runWindowMs }
          : {}),
        ...(this.deps.turnWindowMs !== undefined
          ? { turnWindowMs: this.deps.turnWindowMs }
          : {}),
      },
    );
  }

  /** The change's autonomous runs (fail-soft: absent brain → []). */
  private async readRuns(changeId: string): Promise<RunFacts[]> {
    try {
      const brain = await readBrain(this.deps.worktreeRoot, changeId);
      return runsFromBrain(brain.groups.flatMap((g) => g.items));
    } catch {
      return [];
    }
  }

  /** The change's conversation turns (fail-soft: no transcripts → []). */
  private async readTurns(): Promise<TurnFacts[]> {
    try {
      const paths = await locateTranscripts(
        this.deps.recordedWorktreePath,
        this.deps.claudeProjectsDir,
      );
      if (paths.length === 0) return [];
      const messages = await parseTranscripts(paths);
      // The conversation id is the first transcript's file stem (the session id).
      const stem = paths[0]!.split("/").pop()?.replace(/\.jsonl$/, "") ?? "";
      return turnsFromMessages(messages, stem);
    } catch {
      return [];
    }
  }
}
