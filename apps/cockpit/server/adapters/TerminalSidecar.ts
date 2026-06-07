// WP-002 — the production terminal sidecar bridge (browser WS ↔ AF_UNIX).
//
// The first-class cockpit-server sibling of e2e/terminal-proxy.ts's `bridge()`:
// a real cockpit feature, not the e2e harness. It accepts a browser WebSocket on
// the cockpit's existing HTTP server (riding the same 127.0.0.1 port, so the
// bind invariant covers it for free) and pipes each NDJSON line VERBATIM to a
// fresh AF_UNIX connection on the session-manager host's socket — one socket
// connection per WS — rewriting `open` to inject the resolved provider+cwd.
//
// SHAPE: modelled exactly on the proven `terminal-proxy.ts` `bridge()` (NDJSON
// line buffer, per-WS socket, open-rewrite, lifecycle parity). Reuse-first
// (EP-03 / CP): no second transport, no parallel engine, no new packages (`ws`
// is already a dependency).
//
// INDEPENDENCE (founder directive — MUST): this bridge has ZERO dependency on
// the chat relay (routes/chat.ts) or the chat's SessionBridge. It is the
// terminal's OWN bridge — its own module, attached to the http server's
// `upgrade` event. The chat path is reworked separately; this stays decoupled.
//
// READ-ONLY GATE (ADR-010): this module registers NO `app.post` and starts NO
// process. It attaches a WebSocket upgrade handler to the existing HTTP server
// and opens an AF_UNIX `connect()` per WS — neither is a write-verb route nor a
// process start. The GET-only HTTP surface is preserved (WP-005 allow-lists
// this file for the WS-attachment exception; the host spawn is WP-001/WP-004).

import { connect, type Socket } from "node:net";
import type { IncomingMessage, Server } from "node:http";
import type { Duplex } from "node:stream";

import { WebSocketServer, type WebSocket } from "ws";

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (the shared NDJSON framer, also used by e2e/terminal-proxy.ts; the rule blocks escapes OUT of apps/cockpit/, which import/no-restricted-paths enforces)
import { createNdjsonLineFramer } from "../../shared/ndjsonLineFramer";

/** The session spec the sidecar resolves a change to: the cockpit client sends
 *  only `{io_mode:"pty"}`; the sidecar supplies provider+cwd (it owns the
 *  change→worktree mapping, the client must not know it — WP-007). */
export interface SpecResolution {
  provider: string;
  cwd: string;
}

/** Resource ceilings (TDD §3.4). Conservative, localhost-tuned defaults; the
 *  composition seam passes the frozen CONFIG values (WP-004). */
export interface TerminalSidecarCaps {
  /** Reject new WS upgrades past this many concurrent connections. */
  maxConnections: number;
  /** Reject an `attach` past this many open attachments on one WS. */
  maxAttachmentsPerConnection: number;
}

export interface CreateTerminalSidecarOptions {
  /** The AF_UNIX socket path the session-manager host serves (per-run temp). */
  socketPath: string;
  /** Resolve a change id → its provider+cwd. Returns `null` for an unknown id.
   *  Reuses the change-store reader (TDD §2.4) — no second resolution path. */
  resolveChange: (changeId: string) => Promise<SpecResolution | null>;
  /** The one allowed browser origin(s) for the upgrade handshake (TDD §3.2). */
  originAllowList: string[];
  /** Resource ceilings (TDD §3.4). */
  caps: TerminalSidecarCaps;
}

/** WebSocket close codes used at the handshake / cap boundaries. 1008 = policy
 *  violation (the §6455 code for "received a message that violates policy"). */
const WS_POLICY_VIOLATION = 1008;

/** The path the terminal WS endpoint lives at on the shared HTTP server. */
const TERMINAL_WS_PATH = "/terminal";

export interface TerminalSidecar {
  /** Wire the WS endpoint to an HTTP server's `upgrade` event. */
  attach(httpServer: Server): void;
  /** Tear down the WS server (and every live bridge connection). Idempotent. */
  close(): Promise<void>;
}

/**
 * Build the terminal sidecar. Call `attach(httpServer)` after `listen()` to
 * wire the `/terminal` WS endpoint to the server's `upgrade` event; call
 * `close()` on graceful shutdown.
 */
export function createTerminalSidecar(
  opts: CreateTerminalSidecarOptions,
): TerminalSidecar {
  // `noServer: true`: we own the upgrade handshake so we can validate Origin +
  // path + caps BEFORE completing it (a refused upgrade opens no socket).
  const wss = new WebSocketServer({ noServer: true });
  // A no-op error handler so a transient WS-server error never crashes the
  // process (parity with terminal-proxy.ts); per-bridge socket errors are
  // handled in `bridge()`.
  wss.on("error", () => {});

  let attachedServer: Server | undefined;
  let onUpgrade: ((req: IncomingMessage, socket: Duplex, head: Buffer) => void) | undefined;
  let openConnections = 0;

  /** Origin gate (TDD §3.2): accept only the cockpit's own client origin. A
   *  mismatched / absent Origin → refuse the upgrade, no socket opened. */
  function originAllowed(req: IncomingMessage): boolean {
    const origin = req.headers.origin;
    return typeof origin === "string" && opts.originAllowList.includes(origin);
  }

  /** Resolve the changeId the WS is opened for from its connection URL
   *  (`/terminal?changeId=…`). The first `open`'s key binds the host-side guard
   *  (ADR-010 §3.3); the URL gives us the identity up front for the caps + logs. */
  function changeIdFromUrl(req: IncomingMessage): string | undefined {
    if (!req.url) return undefined;
    const url = new URL(req.url, "http://127.0.0.1");
    return url.searchParams.get("changeId") ?? undefined;
  }

  attachedServer = undefined;

  function attach(httpServer: Server): void {
    attachedServer = httpServer;
    onUpgrade = (req: IncomingMessage, socket: Duplex, head: Buffer): void => {
      // Only claim our own path; leave other upgrade paths (none today) alone.
      const path = req.url ? new URL(req.url, "http://127.0.0.1").pathname : "";
      if (path !== TERMINAL_WS_PATH) return;

      // Origin gate (TDD §3.2) — refuse the handshake outright on mismatch.
      if (!originAllowed(req)) {
        socket.write("HTTP/1.1 403 Forbidden\r\n\r\n");
        socket.destroy();
        return;
      }

      // Concurrent-connection cap (TDD §3.4) — refuse past the ceiling.
      if (openConnections >= opts.caps.maxConnections) {
        socket.write("HTTP/1.1 503 Service Unavailable\r\n\r\n");
        socket.destroy();
        return;
      }

      const changeId = changeIdFromUrl(req);
      wss.handleUpgrade(req, socket, head, (ws) => {
        openConnections += 1;
        bridge(ws, changeId);
      });
    };
    httpServer.on("upgrade", onUpgrade);
  }

  /**
   * Bridge one browser WebSocket to its OWN fresh AF_UNIX connection. Each WS
   * gets a dedicated `connect(socketPath)` so request ids never cross-talk
   * between tabs (§2.13.2, the proven shape). The bridge rewrites `open` to
   * carry the resolved provider+cwd and forwards every other method verbatim.
   */
  function bridge(ws: WebSocket, changeId: string | undefined): void {
    const sock: Socket = connect(opts.socketPath);
    const framer = createNdjsonLineFramer();
    let attachments = 0;
    // Serialise outbound writes per connection. The `open` rewrite is ASYNC
    // (it awaits `resolveChange`), but every other method takes the sync path —
    // so a naive fire-and-forget could write a later `attach` to the socket
    // BEFORE an earlier still-resolving `open`, reordering the NDJSON wire and
    // breaking the session. Chaining each message through this tail promise
    // preserves browser→socket order regardless of per-message async cost.
    let writeChain: Promise<void> = Promise.resolve();

    // socket → browser: forward each NDJSON line as a WS text message, verbatim
    // (byte-for-byte, including base64 `term.data` — the bridge does not decode).
    // The shared framer re-assembles complete lines across split/batched reads.
    sock.on("data", (chunk: Buffer) => {
      for (const line of framer.push(chunk)) {
        if (ws.readyState === ws.OPEN) ws.send(line);
      }
    });
    sock.on("close", () => {
      if (ws.readyState === ws.OPEN) ws.close();
    });
    sock.on("error", () => {
      if (ws.readyState === ws.OPEN) ws.close();
    });

    // browser → socket: forward each WS message as one NDJSON line, rewriting
    // `open` to inject the resolved provider+cwd (the sidecar's change→spec job)
    // and enforcing the per-connection attachment cap before relaying `attach`.
    ws.on("message", (data) => {
      const text = typeof data === "string" ? data : data.toString();
      // Append to the per-connection write chain so messages reach the socket
      // in arrival order even when an earlier `open` is still resolving.
      writeChain = writeChain.then(() => relay(text));
    });
    ws.on("close", () => sock.end());
    ws.on("error", () => sock.destroy());

    /** Transform-and-forward one inbound WS message. Async because the `open`
     *  rewrite resolves the change→spec; non-open methods take the sync path. */
    async function relay(text: string): Promise<void> {
      let outbound = text;
      try {
        const req = JSON.parse(text) as {
          method?: string;
          params?: { key?: string; spec?: Record<string, unknown> };
        };

        // Per-connection attachment cap (TDD §3.4) — refuse past the ceiling
        // without opening another attachment on the host.
        if (req.method === "attach") {
          if (attachments >= opts.caps.maxAttachmentsPerConnection) {
            if (ws.readyState === ws.OPEN) {
              ws.close(WS_POLICY_VIOLATION, "attachment cap reached");
            }
            return;
          }
          attachments += 1;
        }
        if (req.method === "detach" && attachments > 0) attachments -= 1;

        if (req.method === "open") {
          // The connection's identity is the changeId it was opened for (URL),
          // falling back to the open's own `key` so the host's first-open guard
          // still binds (ADR-010 §3.3).
          const key = changeId ?? req.params?.key;
          const spec = key ? await opts.resolveChange(key) : null;
          if (spec) {
            req.params = req.params ?? {};
            req.params.spec = {
              provider: spec.provider,
              cwd: spec.cwd,
              ...(req.params.spec ?? {}),
            };
            outbound = JSON.stringify(req);
          }
        }
      } catch {
        // Not JSON we can rewrite — forward verbatim.
      }
      if (!sock.destroyed) {
        sock.write(outbound.endsWith("\n") ? outbound : outbound + "\n");
      }
    }

    // Decrement the live-connection counter exactly once when this WS ends.
    ws.once("close", () => {
      openConnections = Math.max(0, openConnections - 1);
    });
  }

  let closed = false;
  async function close(): Promise<void> {
    if (closed) return;
    closed = true;
    if (attachedServer && onUpgrade) {
      attachedServer.off("upgrade", onUpgrade);
    }
    for (const client of wss.clients) client.close();
    await new Promise<void>((resolve) => wss.close(() => resolve()));
  }

  return { attach, close };
}
