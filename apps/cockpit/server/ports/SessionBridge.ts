// WP-005 — SessionBridge port (TDD §2.1/§2.2, ADR-002).
//
// The one new domain-owned port this change introduces: the seam to the
// local `claude` session. EXPAND-Create, NOT a SUBSTITUTE-Wrap of the
// `claude` CLI — the public face is THIS interface (the cockpit owns it);
// the CLI is *called by* the adapter (ADR-002). The change store, recreate
// runner, and transcript locator already follow this hexagonal shape; the
// session bridge must too.
//
// The port carries resolve-then-deliver as two explicit operations so the
// safety guards (binding ADR-004, lock ADR-003, timeouts §3.2) sit at the
// relay seam, not scattered into the adapter:
//
//   resolveSession(changeId)  — side-effect-free; which path applies
//                               (live | resumable | fresh), WITHOUT acting
//                               (FR-N4). Reuses signal-0 liveness + the
//                               transcript locator.
//   relay(changeId, prompt, sink)  — the single act. Resumes / spawns as
//                               the resolution dictates, then streams
//                               lifecycle + chunk events to the sink.
//
// Two adapters sit behind it: `StreamJsonSessionBridge` (production — drives
// headless `claude -p --output-format stream-json`) and
// `RecordedSessionBridge` (a recorded real stream-json session replayed for
// tests — MEA-09, not a mock). Both satisfy `session-bridge.contract.test.ts`.

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern is intended to block escapes out of apps/cockpit/, which `import/no-restricted-paths` already enforces correctly)
import type { ChatStreamEvent } from "../../shared/api-types";

export type { ChatStreamEvent };

/**
 * A reference to a session the bridge can act on. The fields below are the
 * IDENTITY the binding guard (ADR-004, `lib/sessionBinding.ts`) checks
 * against the requested change BEFORE any process start: `changeId` must
 * equal the requested change, and `cwd` must equal the change's
 * `worktreePath`. Carried by identity, never inferred from position.
 */
export interface SessionRef {
  /** The session record's `change_id` (session.json). */
  changeId: string;
  /** The session's working directory (must equal the change's worktreePath). */
  cwd: string;
  /**
   * The transcript the session resumes from, when resuming. Absent for a
   * `fresh` resolution and for a `live` session that is already attached.
   */
  lastSessionRef?: string;
}

/**
 * Which delivery path `resolveSession` decided, WITHOUT acting (FR-N4). The
 * relay binds the carried `session` BEFORE acting, so a mis-bound request is
 * refused with zero bytes (ADR-004).
 *
 *   - `live`      — a live session is present; use it.
 *   - `resumable` — no live session, but a prior transcript exists; resume.
 *   - `fresh`     — never had a session; spawn grounded in saved context.
 */
export type SessionResolution =
  | { kind: "live"; session: SessionRef }
  | { kind: "resumable"; session: SessionRef }
  | { kind: "fresh"; session: SessionRef };

/**
 * The sink the bridge streams events into during `relay`. The relay route
 * adapts this onto the SSE response; tests adapt it onto an array. Keeping
 * the sink an interface (not the raw `res`) is what lets the contract suite
 * exercise `relay` with no HTTP server.
 */
export interface RelaySink {
  /** Emit one stream event (state / chunk / complete / error). */
  emit(event: ChatStreamEvent): void;
}

/**
 * The terminal outcome of one `relay`, returned AFTER the stream closes.
 * Mirrors the last `state` the sink saw, so the route can decide the HTTP
 * disposition (delivered vs refused vs broken) and the structured log line.
 *
 *   - `completed`   — the reply finished cleanly; `resumed` is honest about
 *                     whether the change was resumed (FR-26).
 *   - `interrupted` — the stream dropped mid-reply; the partial is preserved
 *                     and marked interrupted (FR-22).
 *   - `unreachable` — the session could not be started; NOT marked delivered
 *                     (FR-19 / FR-N3) → SESSION_UNREACHABLE.
 *   - `mismatch`    — binding failed; zero bytes, no process touched
 *                     (FR-21 / FR-N2) → SESSION_CHANGE_MISMATCH.
 */
export type RelayOutcome =
  | { kind: "completed"; resumed: boolean }
  | { kind: "interrupted" }
  | { kind: "unreachable"; detail: string }
  | { kind: "mismatch"; detail: string };

/**
 * The domain-owned seam to the local `claude` session (ADR-002). One
 * production adapter (`StreamJsonSessionBridge`) and one recorded fixture
 * adapter (`RecordedSessionBridge`) implement it; the relay route depends on
 * this interface, never on an adapter.
 */
export interface SessionBridge {
  /**
   * Decide which delivery path applies for `changeId` WITHOUT acting
   * (side-effect-free; FR-N4). Starts no process, sends no signal other than
   * the signal-0 liveness probe, writes nothing. Returns the resolution +
   * the carried session identity the binding guard checks.
   */
  resolveSession(changeId: string): Promise<SessionResolution>;

  /**
   * Deliver `prompt` to the resolved session for `changeId` and stream the
   * reply into `sink`. The relay route runs bind → lock BEFORE calling this;
   * the adapter performs the resume/spawn and the streaming. Emits
   * `state` → `chunk*` → `complete` on success (ADR-001); on a mid-stream
   * drop, preserves the partial and emits `interrupted`; never synthesises a
   * completion (FR-N5). On resume, `complete.resumed` is `true`.
   */
  relay(
    changeId: string,
    prompt: string,
    sink: RelaySink,
  ): Promise<RelayOutcome>;
}
