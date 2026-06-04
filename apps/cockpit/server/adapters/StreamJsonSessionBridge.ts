// WP-005 — StreamJsonSessionBridge (ADR-002; the ONE process-start site, ADR-003).
//
// The production adapter for the SessionBridge port. It drives the headless
// `claude -p "<prompt>" --output-format stream-json --include-partial-messages`
// interface (the validated mechanism, local-ui-design.md spike 2026-05-26),
// resuming via `--resume`/`--continue` or spawning fresh grounded in the
// change's saved context. The interactive-TUI/pty path is explicitly rejected
// (it is where the earlier attempt churned).
//
// EXPAND-Create, NOT a wrap of the CLI: the public face is the SessionBridge
// port; the CLI is *called by* this adapter. This is the ONLY file in the
// cockpit permitted to start a process (the read-only gate allow-lists it by
// path — ADR-003).
//
// Resume restarts from the persisted transcript; spawn seeds with saved
// context; NEITHER synthesises a completion (FR-24/25/26/N5) — the adapter
// hands the prompt to the agent and streams whatever it produces, mapping each
// stream-json record through the SHARED `streamJsonToEvents` mapper (parity
// with the recorded fixture). On a mid-stream drop it preserves the partial and
// reports `interrupted` (FR-22). A startup timeout bounds the worst case so the
// in-flight lock cannot leak (TDD §3.2); failure ⇒ `unreachable`.
//
// `resolve` and `spawnBridge` are injected so the contract suite exercises the
// adapter with a stubbed child (CI) while `index.ts` wires the real
// `child_process.spawn`. The REAL claude path is the founder-machine
// observation.

import { spawn } from "node:child_process";
import { createInterface } from "node:readline";
import type { Readable } from "node:stream";
import type { EventEmitter } from "node:events";

import type {
  SessionBridge,
  SessionResolution,
  RelaySink,
  RelayOutcome,
} from "../ports/SessionBridge";
import {
  streamJsonToEvent,
  parseStreamJsonLine,
  leadingStateFor,
  resumedFor,
} from "../lib/streamJsonToEvents";

/** The minimal child-process surface this adapter drives. */
export interface BridgeChildHandle {
  /** Emits "close" with an exit code (and may emit "error"). */
  process: EventEmitter;
  /** The child's stdout — NDJSON stream-json lines. */
  stdout: Readable;
  /** Terminate the child (used by the idle/startup watchdog). */
  kill(): void;
}

export interface StreamJsonSessionBridgeOptions {
  /**
   * Resolve the change to a session WITHOUT acting (FR-N4). In production this
   * composes signal-0 liveness + the transcript locator; injected here so the
   * contract suite and the relay control the resolution deterministically.
   */
  resolve(changeId: string): Promise<SessionResolution>;
  /**
   * Start the headless bridge child for the given argv + cwd. In production
   * this is `child_process.spawn("claude", argv, { cwd })`; the contract suite
   * injects a stubbed child. This is the one sanctioned process start.
   */
  spawnBridge(argv: string[], cwd: string): BridgeChildHandle;
  /** Bound the bridge startup so a stuck child can't leak the lock (§3.2). */
  startupTimeoutMs: number;
}

export class StreamJsonSessionBridge implements SessionBridge {
  constructor(private readonly opts: StreamJsonSessionBridgeOptions) {}

  async resolveSession(changeId: string): Promise<SessionResolution> {
    return this.opts.resolve(changeId);
  }

  async relay(
    changeId: string,
    prompt: string,
    sink: RelaySink,
  ): Promise<RelayOutcome> {
    const resolution = await this.opts.resolve(changeId);
    const kind = resolution.kind;
    const argv = buildArgv(prompt, resolution);

    let child: BridgeChildHandle;
    try {
      child = this.opts.spawnBridge(argv, resolution.session.cwd);
    } catch (err) {
      sink.emit({ type: "state", state: "failed" });
      return { kind: "unreachable", detail: describeError(err) };
    }

    // Leading state is honest about resume/spawn (FR-23/26).
    sink.emit({ type: "state", state: leadingStateFor(kind) });

    return await this.consume(child, sink, kind);
  }

  /** Drive the child's stdout to completion, preserving a partial on drop. */
  private async consume(
    child: BridgeChildHandle,
    sink: RelaySink,
    kind: SessionResolution["kind"],
  ): Promise<RelayOutcome> {
    let sawChunk = false;
    let completed = false;
    let startupTimer: NodeJS.Timeout | undefined;

    return await new Promise<RelayOutcome>((resolve) => {
      // Startup watchdog: if no output before the deadline, kill + unreachable.
      startupTimer = setTimeout(() => {
        if (!sawChunk && !completed) {
          child.kill();
          sink.emit({ type: "state", state: "failed" });
          resolve({ kind: "unreachable", detail: "bridge startup timed out" });
        }
      }, this.opts.startupTimeoutMs);

      const lines = createInterface({
        input: child.stdout,
        crlfDelay: Infinity,
      });

      lines.on("line", (line) => {
        const record = parseStreamJsonLine(line);
        if (!record) return;
        if (
          record.type === "result" &&
          (record.is_error || record.subtype === "error")
        ) {
          // An error result mid-stream — surface as interrupted (partial kept).
          return;
        }
        const event = streamJsonToEvent(record, kind);
        if (!event) return;
        if (event.type === "chunk") {
          sawChunk = true;
          if (startupTimer) clearTimeout(startupTimer);
        }
        if (event.type === "complete") completed = true;
        sink.emit(event);
      });

      child.process.on("error", (err: unknown) => {
        if (startupTimer) clearTimeout(startupTimer);
        if (!completed) {
          sink.emit({ type: "state", state: "failed" });
          resolve({ kind: "unreachable", detail: describeError(err) });
        }
      });

      child.process.on("close", (code: number) => {
        if (startupTimer) clearTimeout(startupTimer);
        if (completed) {
          resolve({ kind: "completed", resumed: resumedFor(kind) });
          return;
        }
        if (code === 0 && sawChunk) {
          // Stream closed cleanly but no explicit result — treat as completed.
          sink.emit({ type: "complete", resumed: resumedFor(kind) });
          resolve({ kind: "completed", resumed: resumedFor(kind) });
          return;
        }
        if (sawChunk) {
          // Dropped mid-reply: preserve the partial, mark interrupted (FR-22).
          sink.emit({ type: "state", state: "interrupted" });
          resolve({ kind: "interrupted" });
          return;
        }
        // Never produced anything → unreachable, not delivered (FR-19).
        sink.emit({ type: "state", state: "failed" });
        resolve({
          kind: "unreachable",
          detail: `bridge exited ${code} with no output`,
        });
      });
    });
  }
}

/**
 * Build the headless argv. Always stream-json with partial messages; a
 * resumable session adds `--resume <ref>` (or `--continue` when no explicit
 * ref); a fresh/live session spawns without resume. The prompt is passed via
 * `-p` (headless print mode), NEVER an interactive TUI.
 */
function buildArgv(prompt: string, resolution: SessionResolution): string[] {
  const base = [
    "-p",
    prompt,
    "--output-format",
    "stream-json",
    "--include-partial-messages",
  ];
  if (resolution.kind === "resumable") {
    const ref = resolution.session.lastSessionRef;
    return ref ? [...base, "--resume", ref] : [...base, "--continue"];
  }
  return base;
}

function describeError(err: unknown): string {
  if (err instanceof Error) return err.message;
  return String(err);
}

/**
 * The DEFAULT production `spawnBridge`: start the real headless `claude` child
 * with the cockpit's spawn-not-shell discipline. This is the SINGLE process-
 * start site in the cockpit (ADR-003) — `index.ts` wires the adapter with this
 * so no other file ever calls `spawn`. The read-only gate allow-lists THIS file
 * by path. The REAL claude round-trip is the founder-machine observation; in
 * CI the contract suite injects a stubbed child instead.
 */
export function spawnClaudeBridge(
  argv: string[],
  cwd: string,
): BridgeChildHandle {
  const child = spawn("claude", argv, {
    cwd,
    stdio: ["ignore", "pipe", "ignore"],
  });
  return {
    process: child,
    stdout: child.stdout,
    kill: () => {
      // Terminate the child if the watchdog fires. SIGTERM (not signal 0) is
      // legitimate here: this adapter OWNS the session it started — distinct
      // from the read-only liveness probe (signal 0) elsewhere (NFR-SEC-04).
      child.kill("SIGTERM");
    },
  };
}
