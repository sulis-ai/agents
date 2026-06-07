// WP-010 — the live-socket transport: a browser WebSocket SocketTransport.
//
// This is the transport WP-008 left as `notYetWiredTransport` for WP-010 to
// replace. A browser cannot open an AF_UNIX socket directly, and the cockpit's
// HTTP server is read-only (GET-only — the read-only-inventory gate), so the
// browser reaches the §2.8 NDJSON socket over a WebSocket bridge: the e2e
// harness (and, in a real deployment, the cockpit's terminal sidecar) runs a
// WS→AF_UNIX proxy that pipes each NDJSON line both ways verbatim. This module
// speaks the SAME §2.13.1 wire the Python socket speaks — one JSON object per
// WebSocket message; requests carry an `id`; responses echo it; a streaming
// response (attach) is many `term` lines then an `end`.
//
// It reuses the WP-007 TerminalBridgeClient unchanged (EP-03 reuse-first): this
// is only the transport seam (request / openStream); all attach/feed decoding
// stays in the port.
//
// WPF-02 (typed client, no raw socket in a component): the component never sees
// this — it consumes the TerminalBridge port; this is wired in at the
// composition seam (createTerminalBridge) per WPF-09.

import type {
  SocketTransport,
  WireResponse,
} from "../../../server/ports/TerminalBridge";

/** Each request gets a unique id so responses (and streaming `term` lines) can
 *  be routed back to their caller over the one multiplexed socket. */
let _nextId = 0;
function nextId(): string {
  _nextId += 1;
  return String(_nextId);
}

/** Resolve the WebSocket constructor (real browser global; injectable for
 *  tests under jsdom, which has no WebSocket). */
type WebSocketCtor = new (url: string) => WebSocket;

/**
 * A SocketTransport over a single WebSocket connection to the WS→AF_UNIX proxy.
 *
 * Lazily connects on first use and reuses the one socket for every request
 * (matching the §2.13.2 decoupling: attach + feed are separate request ids on
 * the SAME connection). Per-id listeners route unary responses and streaming
 * `term`/`end` lines back to their awaiting caller.
 */
export class WebSocketTransport implements SocketTransport {
  private socket: WebSocket | undefined;
  private connecting: Promise<WebSocket> | undefined;
  /** Per-request-id sinks. A unary request resolves once; a stream pushes many. */
  private readonly sinks = new Map<string, (line: WireResponse) => void>();

  constructor(
    private readonly url: string,
    private readonly WebSocketImpl: WebSocketCtor = WebSocket,
  ) {}

  /** Open (or reuse) the one WebSocket, wiring the demultiplexer that fans each
   *  incoming NDJSON line to the sink registered for its `id`. */
  private async connect(): Promise<WebSocket> {
    if (this.socket && this.socket.readyState === this.socket.OPEN) {
      return this.socket;
    }
    if (this.connecting) return this.connecting;

    this.connecting = new Promise<WebSocket>((resolve, reject) => {
      const ws = new this.WebSocketImpl(this.url);
      ws.onopen = () => {
        this.socket = ws;
        resolve(ws);
      };
      ws.onerror = () => {
        reject(new Error(`terminal socket failed to connect: ${this.url}`));
      };
      ws.onclose = () => {
        // Surface a SOCKET_CLOSED to every in-flight sink so streams terminate
        // and unary awaits reject-as-value rather than hang (§2.15 Protocol).
        for (const [, sink] of this.sinks) {
          sink({
            id: "0",
            ok: false,
            error: {
              category: "protocol",
              code: "SOCKET_CLOSED",
              message: "terminal socket closed",
            },
          });
        }
        this.sinks.clear();
        if (this.socket === ws) this.socket = undefined;
        this.connecting = undefined;
      };
      ws.onmessage = (ev: MessageEvent) => {
        const text = typeof ev.data === "string" ? ev.data : String(ev.data);
        // The proxy may batch multiple NDJSON lines into one frame; split.
        for (const raw of text.split("\n")) {
          const line = raw.trim();
          if (!line) continue;
          let obj: WireResponse;
          try {
            obj = JSON.parse(line) as WireResponse;
          } catch {
            continue; // ignore a malformed line rather than wedge the socket
          }
          const sink = this.sinks.get(obj.id);
          if (sink) sink(obj);
        }
      };
    });
    return this.connecting;
  }

  async request(
    method: string,
    params: Record<string, unknown>,
  ): Promise<WireResponse> {
    const ws = await this.connect();
    const id = nextId();
    return new Promise<WireResponse>((resolve) => {
      this.sinks.set(id, (line) => {
        // A unary method has exactly one response line; deregister on arrival.
        this.sinks.delete(id);
        resolve(line);
      });
      ws.send(JSON.stringify({ id, method, params }));
    });
  }

  async *openStream(
    method: string,
    params: Record<string, unknown>,
  ): AsyncIterable<WireResponse> {
    const ws = await this.connect();
    const id = nextId();

    // A bounded async queue: the demux pushes lines in; the generator pulls.
    const queue: WireResponse[] = [];
    let notify: (() => void) | undefined;
    let ended = false;

    this.sinks.set(id, (line) => {
      queue.push(line);
      notify?.();
    });
    ws.send(JSON.stringify({ id, method, params }));

    try {
      while (!ended) {
        if (queue.length === 0) {
          await new Promise<void>((r) => (notify = r));
          notify = undefined;
        }
        while (queue.length > 0) {
          const line = queue.shift()!;
          yield line;
          // The stream terminates on `end` or on an error line (§2.15: an error
          // ends the attach stream; recovery is re-attach).
          if (("end" in line && line.end) || line.ok === false) {
            ended = true;
            break;
          }
        }
      }
    } finally {
      this.sinks.delete(id);
    }
  }
}

/** Read the configured terminal WS endpoint, if any. The cockpit only wires the
 *  live transport when this is set (Vite-standard `import.meta.env.VITE_*`,
 *  matching client/config.ts; or a runtime window global the e2e injects). When
 *  unset, the bridge falls back to the not-yet-wired transport — production-safe
 *  (no live terminal until the WS sidecar is configured). */
export function terminalWsUrl(): string | undefined {
  const fromEnv = (import.meta as { env?: Record<string, string | undefined> })
    .env?.VITE_TERMINAL_WS_URL;
  if (fromEnv) return fromEnv;
  const fromWindow =
    typeof window !== "undefined"
      ? (window as unknown as { __COCKPIT_TERMINAL_WS__?: string })
          .__COCKPIT_TERMINAL_WS__
      : undefined;
  return fromWindow || undefined;
}
