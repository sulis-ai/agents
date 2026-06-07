// WP-010 — the e2e WS→AF_UNIX terminal proxy (the live-socket bridge).
//
// A browser cannot open an AF_UNIX socket, and the cockpit's HTTP server is
// read-only (the read-only-inventory gate). So the browser reaches the §2.8
// NDJSON socket over a WebSocket: this proxy accepts the browser's WebSocket and
// pipes each NDJSON line VERBATIM to/from the real AF_UNIX socket served by the
// REAL SessionManager (terminal-backend.py). Playwright drives the cockpit UI
// against this proxy — the full round-trip through the real interface + the real
// socket + a real pty child (MEA-09).
//
// This lives in e2e/ (excluded from the read-only gate) and is harness-only: it
// is NOT part of the production cockpit server. (A real deployment would run an
// equivalent terminal sidecar; that is out of THIS WP's scope — WP-010 proves
// the round-trip, it does not ship the production sidecar.)
//
// Lifetime: startTerminalProxy() spawns the Python backend, waits for its READY
// line, then opens a WS server on the requested port. Returns a stop() that
// tears both down. run-server.ts starts it; globalTeardown is not required (the
// Playwright webServer process exit reaps it), but stop() is exposed for tests.

import { spawn, type ChildProcess } from "node:child_process";
import { connect, type Socket } from "node:net";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

import { WebSocketServer, type WebSocket } from "ws";

const here = dirname(fileURLToPath(import.meta.url));

export interface TerminalProxyHandle {
  /** The ws:// URL the cockpit client connects to (VITE_TERMINAL_WS_URL). */
  url: string;
  /** Tear down the WS server + the Python backend. Idempotent. */
  stop: () => Promise<void>;
}

export interface StartTerminalProxyOptions {
  /** WS port to listen on (dedicated, so it never collides with a real run). */
  port: number;
  /** The change id the seeded pty session is opened under. */
  changeId: string;
  /** Working dir for the pty child (defaults to a fresh temp dir). */
  cwd?: string;
  /** python executable (defaults to python3). */
  python?: string;
}

/** Spawn the Python backend and wait for its `READY <socket>` line. */
function startBackend(
  opts: Required<Pick<StartTerminalProxyOptions, "changeId" | "cwd">> & {
    python: string;
    socketPath: string;
  },
): Promise<ChildProcess> {
  return new Promise((resolve, reject) => {
    const proc = spawn(
      opts.python,
      [
        join(here, "terminal-backend.py"),
        "--socket",
        opts.socketPath,
        "--change-id",
        opts.changeId,
        "--cwd",
        opts.cwd,
      ],
      { stdio: ["ignore", "pipe", "pipe"] },
    );
    let ready = false;
    const timer = setTimeout(() => {
      if (!ready) reject(new Error("terminal-backend.py did not become READY"));
    }, 30_000);
    proc.stdout.on("data", (chunk: Buffer) => {
      if (chunk.toString().includes("READY")) {
        ready = true;
        clearTimeout(timer);
        resolve(proc);
      }
    });
    proc.stderr.on("data", (chunk: Buffer) => {
      // Surface backend errors to the Playwright stdout pipe for debugging.
      // eslint-disable-next-line no-console -- e2e harness diagnostics
      console.error(`[terminal-backend] ${chunk.toString().trimEnd()}`);
    });
    proc.on("exit", (code) => {
      if (!ready) {
        clearTimeout(timer);
        reject(new Error(`terminal-backend.py exited early (code ${code})`));
      }
    });
  });
}

/** The session spec the proxy resolves a change to — exactly what a production
 *  terminal sidecar does: it knows the change→worktree→provider mapping; the
 *  cockpit client only sends `{io_mode:"pty"}` (it must not know provider/cwd,
 *  WP-007). The proxy injects provider+cwd so the §2.13.1 `open` is a complete
 *  get-or-spawn (idempotent against the pre-seeded session). */
interface SpecResolution {
  provider: string;
  cwd: string;
}

/**
 * Bridge one browser WebSocket to its own AF_UNIX connection to the backend.
 * Each WS gets a fresh socket connection so request ids never cross-talk between
 * tabs (mirrors the real per-connection model, §2.13.2).
 *
 * The proxy rewrites `open` requests to carry the resolved provider+cwd (the
 * cockpit client deliberately sends only `{io_mode:"pty"}`); every other method
 * is forwarded verbatim.
 */
function bridge(ws: WebSocket, socketPath: string, spec: SpecResolution): void {
  const sock: Socket = connect(socketPath);
  let buf = "";

  // socket → browser: forward each NDJSON line as a WS text message.
  sock.on("data", (chunk: Buffer) => {
    buf += chunk.toString("utf8");
    let nl: number;
    while ((nl = buf.indexOf("\n")) !== -1) {
      const line = buf.slice(0, nl);
      buf = buf.slice(nl + 1);
      if (line.trim() && ws.readyState === ws.OPEN) ws.send(line);
    }
  });
  sock.on("close", () => {
    if (ws.readyState === ws.OPEN) ws.close();
  });
  sock.on("error", () => {
    if (ws.readyState === ws.OPEN) ws.close();
  });

  // browser → socket: forward each WS message as one NDJSON line, injecting the
  // resolved provider+cwd into `open` params (the sidecar's change→spec job).
  ws.on("message", (data) => {
    const text = typeof data === "string" ? data : data.toString();
    let outbound = text;
    try {
      const req = JSON.parse(text) as {
        method?: string;
        params?: { spec?: Record<string, unknown> };
      };
      if (req.method === "open") {
        req.params = req.params ?? {};
        req.params.spec = {
          provider: spec.provider,
          cwd: spec.cwd,
          ...(req.params.spec ?? {}),
        };
        outbound = JSON.stringify(req);
      }
    } catch {
      // Not JSON we can rewrite — forward verbatim.
    }
    sock.write(outbound.endsWith("\n") ? outbound : outbound + "\n");
  });
  ws.on("close", () => sock.end());
  ws.on("error", () => sock.destroy());
}

/** Start the backend + the WS proxy. Resolves once both are accepting. */
export async function startTerminalProxy(
  opts: StartTerminalProxyOptions,
): Promise<TerminalProxyHandle> {
  const python = opts.python ?? "python3";
  const cwd = opts.cwd ?? mkdtempSync(join(tmpdir(), "wp010-pty-"));
  const socketDir = mkdtempSync(join(tmpdir(), "wp010-sock-"));
  const socketPath = join(socketDir, "terminal.sock");

  const backend = await startBackend({
    changeId: opts.changeId,
    cwd,
    python,
    socketPath,
  });

  const wss = new WebSocketServer({ host: "127.0.0.1", port: opts.port });
  wss.on("connection", (ws) =>
    bridge(ws, socketPath, { provider: "pty", cwd }),
  );

  // Bind: resolve on `listening`, REJECT on `error` (e.g. EADDRINUSE from a
  // leaked prior run) rather than letting the unhandled `error` event crash the
  // whole process. A rejection fails globalSetup loudly + cleanly, and we reap
  // the backend so we never leak it.
  await new Promise<void>((resolve, reject) => {
    const onError = (err: Error) => {
      backend.kill("SIGKILL");
      reject(
        new Error(
          `terminal proxy could not bind ws://127.0.0.1:${opts.port}: ${err.message}`,
        ),
      );
    };
    wss.once("error", onError);
    wss.once("listening", () => {
      wss.off("error", onError);
      // Keep a no-op error handler so a later transient error never crashes the
      // process; bridge connections handle their own socket errors.
      wss.on("error", () => {});
      resolve();
    });
  });

  let stopped = false;
  const stop = async (): Promise<void> => {
    if (stopped) return;
    stopped = true;
    await new Promise<void>((resolve) => wss.close(() => resolve()));
    backend.kill("SIGTERM");
  };

  return { url: `ws://127.0.0.1:${opts.port}`, stop };
}
