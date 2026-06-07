// WP-007 — TerminalBridge: the cockpit's typed socket-client port for the
// terminal path (contract §2.13.5; TDD §1.5; ADR-003).
//
// This is the ONE place in the cockpit that talks to the §2.8 socket for the
// terminal path (WPF-02 — data behind a typed client, never a raw socket in a
// component). It sits ALONGSIDE the chat path's bridge, never replacing it:
// the chat content model (offset event log) and the terminal content model
// (raw byte scrollback) are two independent seams (§2.11.2). It mirrors the
// existing port pattern (ChangeStoreReader sits behind an adapter) — the port
// is the interface, the socket transport is the swappable dependency:
//
//   - the real adapter speaks the Unix-domain socket (a later WP wires it);
//   - the contract test supplies a fixture-replay transport over WP-001's
//     recorded byte fixtures (WPF-03 mock-first) — so the port reaches `done`
//     against the recorded contract mock with no live socket (WP-010 proves
//     it end-to-end against the live socket).
//
// What the port does (contract §2.13.5):
//   - open(changeId)            → get-or-spawn a pty-mode session;
//   - attach(changeId)          → AsyncIterable<Uint8Array> (snapshot→live);
//   - attachResults(changeId)   → AsyncIterable<AttachResult> (errors-as-values);
//   - feed(changeId, bytes)     → { written };
//   - resize(changeId, r, c)    → void;
//   - detach(changeId)          → void (leaves the session running, §2.12.3).
//
// It decodes the base64 `term.data` → Uint8Array (the inverse of the socket's
// encoding) and surfaces the §2.15 errors as TYPED, narrowable result values
// the component renders — never thrown opaque (WPF).

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern blocks escapes OUT of apps/cockpit/, which import/no-restricted-paths enforces)
import type {
  AttachResult,
  FeedAck,
  TermFrame,
  TermPhase,
  TerminalError,
  TerminalOpenResult,
} from "../../shared/api-types";

export type {
  AttachResult,
  FeedAck,
  TermFrame,
  TerminalError,
  TerminalOpenResult,
};

// ── The wire shape (§2.13.1) ──────────────────────────────────────────────
//
// One JSON object per line; requests carry an `id` + `method` + `params`;
// responses echo the `id`. A streaming response (attach) is many `term` lines
// then an `end`. An error response carries `ok:false` + a three-category
// `error`. These mirror the recorded fixtures verbatim.

/** A single response line off the socket (§2.13.1). */
export type WireResponse =
  | { id: string; ok: true; result?: Record<string, unknown> }
  | { id: string; ok: true; term: TermFrame }
  | { id: string; ok: true; end: true }
  | {
      id: string;
      ok: false;
      error: { category: string; code: string; message: string };
    };

/**
 * The socket transport the port talks through — the swappable dependency
 * (mirrors how ChangeStoreReader sits behind an adapter). The real
 * implementation speaks the Unix-domain socket; the contract test supplies a
 * fixture-replay transport. Two methods, matching the two §2.13.1 response
 * shapes: a unary request/response (open/feed/resize/detach) and a streaming
 * response (attach — one request id, many `term` lines, terminated by `end`).
 */
export interface SocketTransport {
  /** Issue a unary request; resolve with its single response line. */
  request(
    method: string,
    params: Record<string, unknown>,
  ): Promise<WireResponse>;

  /**
   * Issue a streaming request; yield each response line lazily as it arrives.
   * MUST NOT collect the whole stream before yielding (the attach stream is
   * unbounded — it runs until detach/close).
   */
  openStream(
    method: string,
    params: Record<string, unknown>,
  ): AsyncIterable<WireResponse>;
}

/**
 * The typed terminal port surface (contract §2.13.5). A consumer (the
 * `<LiveTerminal/>` of WP-008) talks to exactly this — never to the socket.
 */
export interface TerminalBridge {
  /** Get-or-spawn a pty-mode session for the change (idempotent). */
  open(changeId: string): Promise<TerminalOpenResult>;
  /** Snapshot bytes first, then live bytes — until detach or close. */
  attach(changeId: string): AsyncIterable<Uint8Array>;
  /** Write keystroke bytes to the live PTY; resolve with the byte count. */
  feed(changeId: string, data: Uint8Array): Promise<FeedAck>;
  /** Tell the PTY its size (TIOCSWINSZ) so TUIs render correctly (§2.13.3). */
  resize(changeId: string, rows: number, cols: number): Promise<void>;
  /** Detach this viewer; LEAVES THE SESSION RUNNING (§2.12.3). */
  detach(changeId: string): Promise<void>;
}

// ── base64 ⇄ bytes (the inverse of the socket's encoding, §2.13.1) ─────────
//
// ISOMORPHIC (WP-010): this port runs in BOTH the Node test harness (vitest /
// jsdom) AND the real browser bundle (the cockpit imports TerminalBridgeClient
// into the client). `Buffer` is a Node-only global — using it broke the live
// browser round-trip with `ReferenceError: Buffer is not defined`. These two
// helpers use the platform-neutral `atob`/`btoa` (available in both browsers and
// modern Node) so the same port serves both the recorded-fixture replay and the
// live WebSocket transport.

/** Decode a base64 `term.data` field to raw bytes (browser + Node). */
function decodeTermData(b64: string): Uint8Array {
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

/** Encode keystroke bytes to the base64 `feed` `data` field (browser + Node). */
function encodeFeedData(bytes: Uint8Array): string {
  let binary = "";
  for (let i = 0; i < bytes.length; i += 1)
    binary += String.fromCharCode(bytes[i]!);
  return btoa(binary);
}

/** Narrow a raw wire error object to the typed §2.15 TerminalError. */
function toTerminalError(raw: {
  category: string;
  code: string;
  message: string;
}): TerminalError {
  // The wire categories/codes are the §2.15 enums; cast at the trust boundary
  // (the recorded fixtures + the live socket both emit exactly these).
  return {
    category: raw.category as TerminalError["category"],
    code: raw.code as TerminalError["code"],
    message: raw.message,
  };
}

/**
 * The socket-client implementation of {@link TerminalBridge}. Construct it
 * with a {@link SocketTransport}; the same client serves the live socket and
 * the recorded-fixture replay (the contract mock).
 */
export class TerminalBridgeClient implements TerminalBridge {
  constructor(private readonly transport: SocketTransport) {}

  /**
   * Issue a unary request and return its `result` object, throwing a typed
   * {@link TerminalBridgeError} on a §2.15 error. The single owner of the
   * unwrap-or-throw convention for the four unary methods — they all narrow
   * the same three-category error the same way, so it lives here once.
   */
  private async unaryOrThrow(
    method: string,
    params: Record<string, unknown>,
  ): Promise<Record<string, unknown>> {
    const response = await this.transport.request(method, params);
    if (!response.ok) {
      throw new TerminalBridgeError(toTerminalError(response.error));
    }
    return ("result" in response ? response.result : {}) ?? {};
  }

  async open(changeId: string): Promise<TerminalOpenResult> {
    const result = await this.unaryOrThrow("open", {
      key: changeId,
      spec: { io_mode: "pty" },
    });
    return {
      key: String(result.key ?? changeId),
      ioMode: "pty",
      viewerCount: Number(result.viewer_count ?? 0),
    };
  }

  /**
   * The byte stream (the common path: pipe straight into xterm.js
   * `Terminal.write()`). Yields decoded snapshot then live bytes. An error
   * surfaces as a thrown {@link TerminalBridgeError} ONLY for callers that opt
   * into the throwing variant; the error-as-value variant is `attachResults`.
   * Most consumers use `attachResults` so errors are rendered, not thrown.
   */
  async *attach(changeId: string): AsyncIterable<Uint8Array> {
    for await (const result of this.attachResults(changeId)) {
      if (!result.ok) {
        throw new TerminalBridgeError(result.error);
      }
      yield result.bytes;
    }
  }

  /**
   * The component-facing attach surface: each emission is a typed
   * {@link AttachResult} — a decoded byte chunk (with phase) or a narrowable
   * error value. Lazy: yields per `term` line, never buffering the whole
   * stream (matches the streaming side, Performance §). The `end` line
   * terminates the stream silently.
   */
  async *attachResults(changeId: string): AsyncIterable<AttachResult> {
    const stream = this.transport.openStream("attach", { key: changeId });
    for await (const line of stream) {
      if (!line.ok) {
        yield { ok: false, error: toTerminalError(line.error) };
        // An error terminates the attach stream (§2.15 recovery is re-attach).
        return;
      }
      if ("end" in line) {
        return;
      }
      if ("term" in line) {
        yield {
          ok: true,
          bytes: decodeTermData(line.term.data),
          phase: line.term.phase as TermPhase,
        };
      }
      // A bare `ok:true` with no term/end (e.g. an ack interleaved on the
      // same id) carries no bytes — skip it.
    }
  }

  async feed(changeId: string, data: Uint8Array): Promise<FeedAck> {
    const result = await this.unaryOrThrow("feed", {
      key: changeId,
      data: encodeFeedData(data),
      encoding: "base64",
    });
    return { written: Number(result.written ?? 0) };
  }

  async resize(changeId: string, rows: number, cols: number): Promise<void> {
    await this.unaryOrThrow("resize", { key: changeId, rows, cols });
  }

  async detach(changeId: string): Promise<void> {
    // Detach leaves the session running (§2.12.3) — the ack is enough.
    await this.unaryOrThrow("detach", { key: changeId });
  }
}

/**
 * The thrown form of a {@link TerminalError}, for the rare caller that uses
 * the throwing `attach`/`open`/`feed`/`resize`/`detach` path rather than the
 * error-as-value `attachResults`. It carries the typed error so a catch site
 * can still narrow on `.terminalError.code`.
 */
export class TerminalBridgeError extends Error {
  constructor(readonly terminalError: TerminalError) {
    super(`${terminalError.code}: ${terminalError.message}`);
    this.name = "TerminalBridgeError";
  }
}
