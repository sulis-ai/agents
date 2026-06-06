// WP-P09 — the pure origin correlation (ADR-012).
//
// Given a file's last-changing commit, the change's autonomous runs, and its
// conversation turns, decide the file's `Origin`. This is a PURE function — no
// I/O, no clock, no git, no fs — so it is testable in isolation (DoD Blue) and
// the same logic backs both the route and the contract test.
//
// Precedence (ADR-012):
//   1. A RECORDED trailer present on the commit → defer to recorded (P13).
//      Correlation is the fallback only; recorded overrides inferred.
//   2. The commit falls inside a `lifecyclerun` window (or its message carries
//      that run's id), OR the commit author is a bot/relay → autonomous.
//   3. The commit timestamp is near a conversation turn → assisted.
//   4. Neither → unknown, with a plain-English reason (never a guess).
//
// Every inferred result carries `attribution: "inferred"` — the honesty flag
// (TDD §3.3). The recorded short-circuit carries `attribution: "recorded"`.

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern blocks escapes out of apps/cockpit/, which import/no-restricted-paths enforces)
import type { Origin } from "../../../shared/api-types";

/** A file's last-changing commit, as read via the ONE git site (gitShow.ts). */
export interface CommitFacts {
  /** Author name/email line (e.g. "Sulis Bot <bot@sulis.ai>"). */
  author: string;
  /** Commit timestamp, ISO 8601. */
  at: string;
  /** Full commit message (subject + body + trailers). */
  message: string;
}

/** One autonomous run (a `lifecyclerun`) to correlate a commit against. */
export interface RunFacts {
  runId: string;
  /** Run timestamp, ISO 8601. */
  at: string;
  outcome: string;
  workflow: string | null;
  confidence: number | null;
}

/** One conversation turn to correlate a commit against. */
export interface TurnFacts {
  conversationId: string;
  /** 1-based turn index within the conversation. */
  turn: number;
  /** Turn timestamp, ISO 8601. */
  at: string;
  summary: string | null;
}

export interface CorrelateInput {
  commit: CommitFacts;
  runs: RunFacts[];
  turns: TurnFacts[];
}

export interface CorrelateOptions {
  /**
   * How close (ms) a commit must be to a run's `at` to count as that run's
   * commit. Autonomous runs commit shortly after the run completes, so a wide
   * window is appropriate. Default 1 hour.
   */
  runWindowMs?: number;
  /**
   * How close (ms) a commit must be to a turn's `at` to count as that turn's
   * commit. A turn's commit lands within the turn, so a tighter window than the
   * run window. Default 15 minutes.
   */
  turnWindowMs?: number;
}

const DEFAULT_RUN_WINDOW_MS = 60 * 60 * 1000; // 1 hour
const DEFAULT_TURN_WINDOW_MS = 15 * 60 * 1000; // 15 minutes

/** The `Sulis-Origin:` commit trailer (ADR-013). Recorded overrides inferred. */
const RECORDED_TRAILER = /^Sulis-Origin:\s*(.+)$/im;

/** Author signals that mark a commit as bot/relay-authored (→ autonomous). */
const BOT_AUTHOR = /\b(bot|\[bot\]|sulis[- ]?(bot|executor|agent)|noreply)\b/i;

function parseMs(iso: string): number | null {
  const ms = Date.parse(iso);
  return Number.isFinite(ms) ? ms : null;
}

/**
 * Parse a recorded `Sulis-Origin:` trailer into an Origin, or null if absent /
 * unparseable. Shape (ADR-013/CF-11):
 *   `Sulis-Origin: autonomous; run=<ulid>; confidence=<0..1>`
 *   `Sulis-Origin: assisted; conversation=<id>; turn=<n>`
 */
function recordedFromTrailer(message: string): Origin | null {
  const m = RECORDED_TRAILER.exec(message);
  if (m === null) return null;
  const value = m[1]!.trim();
  const fields = new Map<string, string>();
  let kind = "";
  for (const part of value.split(";")) {
    const seg = part.trim();
    if (seg === "") continue;
    const eq = seg.indexOf("=");
    if (eq === -1) {
      if (kind === "") kind = seg; // the leading bare token is the kind
      continue;
    }
    fields.set(seg.slice(0, eq).trim(), seg.slice(eq + 1).trim());
  }

  if (kind === "autonomous") {
    const runId = fields.get("run") ?? "";
    if (runId === "") return null;
    const confRaw = fields.get("confidence");
    const conf = confRaw !== undefined ? Number.parseFloat(confRaw) : NaN;
    return {
      kind: "autonomous",
      run: { runId, workflow: null, outcome: "" },
      confidence: Number.isFinite(conf) ? conf : null,
      attribution: "recorded",
    };
  }
  if (kind === "assisted") {
    const conversationId = fields.get("conversation") ?? "";
    if (conversationId === "") return null;
    const turn = Number.parseInt(fields.get("turn") ?? "", 10);
    return {
      kind: "assisted",
      conversation: {
        conversationId,
        turn: Number.isFinite(turn) ? turn : 0,
        summary: null,
      },
      attribution: "recorded",
    };
  }
  return null;
}

/** Find the run whose `at` is nearest the commit and within `windowMs`. */
function nearestRun(
  commitMs: number,
  runs: RunFacts[],
  windowMs: number,
): RunFacts | null {
  let best: RunFacts | null = null;
  let bestDelta = Number.POSITIVE_INFINITY;
  for (const run of runs) {
    const runMs = parseMs(run.at);
    if (runMs === null) continue;
    const delta = Math.abs(commitMs - runMs);
    if (delta <= windowMs && delta < bestDelta) {
      best = run;
      bestDelta = delta;
    }
  }
  return best;
}

/** A run whose id appears verbatim in the commit message (a strong signal). */
function runNamedInMessage(message: string, runs: RunFacts[]): RunFacts | null {
  for (const run of runs) {
    if (run.runId !== "" && message.includes(run.runId)) return run;
  }
  return null;
}

/** Find the turn whose `at` is nearest the commit and within `windowMs`. */
function nearestTurn(
  commitMs: number,
  turns: TurnFacts[],
  windowMs: number,
): TurnFacts | null {
  let best: TurnFacts | null = null;
  let bestDelta = Number.POSITIVE_INFINITY;
  for (const turn of turns) {
    const turnMs = parseMs(turn.at);
    if (turnMs === null) continue;
    const delta = Math.abs(commitMs - turnMs);
    if (delta <= windowMs && delta < bestDelta) {
      best = turn;
      bestDelta = delta;
    }
  }
  return best;
}

/** The newest run by `at` (the best guess for a bot commit with no window). */
function mostRecentRun(runs: RunFacts[]): RunFacts | null {
  let best: RunFacts | null = null;
  let bestMs = Number.NEGATIVE_INFINITY;
  for (const run of runs) {
    const runMs = parseMs(run.at);
    if (runMs !== null && runMs > bestMs) {
      best = run;
      bestMs = runMs;
    }
  }
  return best;
}

function autonomousFrom(run: RunFacts): Origin {
  return {
    kind: "autonomous",
    run: { runId: run.runId, workflow: run.workflow, outcome: run.outcome },
    confidence: run.confidence,
    attribution: "inferred",
  };
}

function assistedFrom(turn: TurnFacts): Origin {
  return {
    kind: "assisted",
    conversation: {
      conversationId: turn.conversationId,
      turn: turn.turn,
      summary: turn.summary,
    },
    attribution: "inferred",
  };
}

function unknown(reason: string): Origin {
  return { kind: "unknown", reason, attribution: "inferred" };
}

/**
 * Correlate one file's last-changing commit to an `Origin`. Pure: same input →
 * same output, no I/O. See the file header for the precedence rules.
 */
export function correlate(
  input: CorrelateInput,
  opts: CorrelateOptions = {},
): Origin {
  const { commit, runs, turns } = input;
  const runWindowMs = opts.runWindowMs ?? DEFAULT_RUN_WINDOW_MS;
  const turnWindowMs = opts.turnWindowMs ?? DEFAULT_TURN_WINDOW_MS;

  // 1. Recorded trailer wins (ADR-012). Correlation is the fallback only.
  const recorded = recordedFromTrailer(commit.message);
  if (recorded !== null) return recorded;

  const commitMs = parseMs(commit.at);
  if (commitMs === null) {
    return unknown("the commit has no readable timestamp to correlate");
  }

  // 2. Autonomous — a run named in the message is the strongest signal; else a
  //    run whose window the commit falls inside.
  const namedRun = runNamedInMessage(commit.message, runs);
  if (namedRun !== null) return autonomousFrom(namedRun);

  // A commit inside a run window is autonomous (the run IS the autonomous act).
  const windowRun = nearestRun(commitMs, runs, runWindowMs);
  if (windowRun !== null) return autonomousFrom(windowRun);

  // 3. Assisted — a turn the commit lands near.
  const turn = nearestTurn(commitMs, turns, turnWindowMs);
  if (turn !== null) return assistedFrom(turn);

  // A bot/relay-authored commit with no matching run window is still
  // autonomous-by-author (the WP's OR-signal) — but only when there ARE runs to
  // attribute it to; with no runs at all, "autonomous" would be a guess.
  if (BOT_AUTHOR.test(commit.author) && runs.length > 0) {
    const fallbackRun = mostRecentRun(runs);
    if (fallbackRun !== null) return autonomousFrom(fallbackRun);
  }

  // 4. Neither — honest unknown (never a guess).
  if (runs.length === 0 && turns.length === 0) {
    return unknown("no autonomous runs or chat turns recorded for this change");
  }
  return unknown("the commit didn't line up with any run or chat turn");
}
