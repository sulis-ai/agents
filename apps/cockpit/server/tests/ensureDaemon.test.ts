// WP-007 — the `ensureDaemon` / stable-socket presence contract (Node binding).
//
// Contract: `plugins/sulis/scripts/_session_manager/DAEMON_CONTRACT.md` + TDD
// §2.2/§5 (the CONTRACT_FIRST producer/consumer seam) + ADR-001 (shared daemon:
// singleton via flock, stable socket, on-demand start). This is the Node sibling
// of the Python `daemon_client.py` binding (WP-002): the cockpit's caller. The
// two bindings are byte-for-byte interchangeable from the daemon's perspective.
//
// Verification posture (MEA-09, no mocks): every test drives a REAL detached
// process over a REAL AF_UNIX socket. The process is a *fake daemon* — a tiny
// Node stdlib script that answers the contract's `status` liveness probe with
// `ok:true` and prints the `READY <socket>` handshake, exactly as the real
// daemon (WP-003) does. Spawning is INJECTED (`spawnCommand`) so this binding is
// tested against a fake daemon and proven independent of the real entrypoint.
// The fake records every launch by appending a byte to a counter file — that
// counter is the literal proof of the singleton / idempotent-ensure guarantees,
// the exact shape the Python WP-002 suite uses.
//
// INDEPENDENCE (founder directive, MUST; ADR-003): the binding imports the Node
// stdlib + the shared NDJSON framer ONLY — never the chat relay (routes/chat.ts),
// the chat SessionBridge, or the platform communication service. The last test
// codifies that as an import-graph assertion so it cannot regress silently.

import { describe, it, expect, afterEach, beforeEach } from "vitest";
import {
  existsSync,
  mkdtempSync,
  rmSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname } from "node:path";

import {
  ensureDaemon,
  daemonIsLive,
  resolveDefaultSocket,
  DaemonStartError,
} from "../lib/ensureDaemon";

// Bounded wait for a process assertion — long enough never to flake on a loaded
// CI runner, short enough that a real hang fails fast (mirrors the Python suite).
const WAIT_MS = 8_000;

// ─── the fake daemon: a real detached Node process honouring the contract ─────
//
// A real program, not a mock (the way `fake_claude_child` is for the pty path).
// It binds the contract's AF_UNIX socket, answers the `status` liveness probe
// with a framed `ok:true` line, prints `READY <socket>`, and — critically —
// records every launch so a test can assert exactly one spawn. It deliberately
// does NOT take the flock (the flock is the *daemon's* job, WP-003); WP-007 owns
// and proves the *caller* contract: probe-first, spawn-once, race-tolerant.
const FAKE_DAEMON_SOURCE = String.raw`
const net = require("node:net");
const fs = require("node:fs");

const args = process.argv.slice(2);
function argOf(name, fallback) {
  const i = args.indexOf(name);
  return i >= 0 && i + 1 < args.length ? args[i + 1] : fallback;
}
const socketPath = argOf("--socket");
const counter = argOf("--counter");
const bindDelayMs = Number.parseInt(argOf("--bind-delay", "0"), 10);

// Record this launch (append a byte) BEFORE binding, so a launch that races and
// loses the bind is still counted — the assertion is "how many processes were
// started", which is the singleton property under test.
fs.appendFileSync(counter, "x");

const server = net.createServer((sock) => {
  let buf = "";
  sock.on("data", (chunk) => {
    buf += chunk.toString("utf8");
    let idx;
    while ((idx = buf.indexOf("\n")) >= 0) {
      const line = buf.slice(0, idx);
      buf = buf.slice(idx + 1);
      let req;
      try {
        req = JSON.parse(line);
      } catch {
        continue;
      }
      const resp =
        req.method === "status"
          ? { id: req.id, ok: true, result: [] }
          : {
              id: req.id,
              ok: false,
              error: { category: "expected", code: "UNKNOWN_METHOD" },
            };
      sock.write(JSON.stringify(resp) + "\n");
    }
  });
  sock.on("error", () => {});
});

function bindAndServe() {
  server.on("error", (err) => {
    // Another launcher won the socket — losing the bind race is normal for a
    // non-flock fake. Exit 0; the winner serves. (The real daemon uses flock.)
    if (err && err.code === "EADDRINUSE") process.exit(0);
    process.exit(1);
  });
  server.listen(socketPath, () => {
    process.stdout.write("READY " + socketPath + "\n");
  });
}

if (bindDelayMs > 0) setTimeout(bindAndServe, bindDelayMs);
else bindAndServe();

// Stay alive so the socket keeps answering for the test's duration.
setTimeout(() => process.exit(0), 3600_000);
`;

// A fake daemon that NEVER prints READY and never binds — the DaemonStartError
// (Internal category) path: spawned, but broken / absent the handshake.
const SILENT_DAEMON_SOURCE = String.raw`
setTimeout(() => process.exit(0), 3600_000);
`;

let tmp: string;

beforeEach(() => {
  tmp = mkdtempSync(join(tmpdir(), "wp007-ensure-"));
});

afterEach(() => {
  if (tmp && existsSync(tmp)) rmSync(tmp, { recursive: true, force: true });
});

/** Short AF_UNIX socket path (macOS bounds the path at ~104 bytes). */
function socketPathFor(): string {
  return join(tmp, "d.sock");
}

function writeFakeDaemon(source = FAKE_DAEMON_SOURCE): string {
  const script = join(tmp, "fake-daemon.cjs");
  writeFileSync(script, source);
  return script;
}

/** The injected argv `ensureDaemon` runs to start a (fake) daemon. The
 *  placeholder `{socket}` mirrors how the real call substitutes the socket. */
function spawnCommandFor(
  script: string,
  counter: string,
  bindDelayMs = 0,
): string[] {
  const cmd = [
    process.execPath,
    script,
    "--socket",
    "{socket}",
    "--counter",
    counter,
  ];
  if (bindDelayMs > 0) cmd.push("--bind-delay", String(bindDelayMs));
  return cmd;
}

function spawnCount(counter: string): number {
  return existsSync(counter) ? statSync(counter).size : 0;
}

describe("WP-007 ensureDaemon — the Node daemon-presence binding (DAEMON_CONTRACT)", () => {
  it("test_resolveDefaultSocket — the stable socket, env-overridable", () => {
    const prev = process.env.SULIS_SESSION_MANAGER_SOCKET;
    try {
      delete process.env.SULIS_SESSION_MANAGER_SOCKET;
      // Default: ~/.sulis/session-manager.sock (absolute, ends with the name).
      expect(resolveDefaultSocket()).toMatch(
        /\.sulis[/\\]session-manager\.sock$/,
      );
      // The override seam (mirrors SULIS_SESSION_MANAGER_HOST) wins when set.
      process.env.SULIS_SESSION_MANAGER_SOCKET = "/tmp/override.sock";
      expect(resolveDefaultSocket()).toBe("/tmp/override.sock");
    } finally {
      if (prev === undefined) delete process.env.SULIS_SESSION_MANAGER_SOCKET;
      else process.env.SULIS_SESSION_MANAGER_SOCKET = prev;
    }
  });

  it("test_daemonIsLive_false_when_nothing_serves — a dead socket reports dead, fast (not a hang)", async () => {
    const socketPath = socketPathFor();
    expect(existsSync(socketPath)).toBe(false);
    const start = Date.now();
    expect(await daemonIsLive(socketPath)).toBe(false);
    // A dead socket must fail fast (short connect timeout), never block on the
    // OS default connect timeout.
    expect(Date.now() - start).toBeLessThan(WAIT_MS);
  });

  it("test_ensureDaemon_cold_start_then_warm_is_noop — cold start spawns exactly once; the warm call spawns nothing", async () => {
    const socketPath = socketPathFor();
    const counter = join(tmp, "spawns");
    const cmd = spawnCommandFor(writeFakeDaemon(), counter);

    const returned = await ensureDaemon(socketPath, {
      spawnCommand: cmd,
      readyTimeoutMs: WAIT_MS,
    });
    expect(returned).toBe(socketPath);
    expect(await daemonIsLive(socketPath)).toBe(true);
    expect(spawnCount(counter)).toBe(1);

    // Warm: the daemon already answers, so ensureDaemon must NOT spawn again.
    const returned2 = await ensureDaemon(socketPath, {
      spawnCommand: cmd,
      readyTimeoutMs: WAIT_MS,
    });
    expect(returned2).toBe(socketPath);
    expect(spawnCount(counter)).toBe(1);
  });

  it("test_concurrent_ensureDaemon_yields_one_spawn — N racers cold-start exactly one daemon; losers poll until it answers (ADR-001 singleton)", async () => {
    const socketPath = socketPathFor();
    const counter = join(tmp, "spawns");
    // A bind delay widens the race window so the race is real.
    const cmd = spawnCommandFor(writeFakeDaemon(), counter, 400);

    const n = 6;
    const results = await Promise.all(
      Array.from({ length: n }, () =>
        ensureDaemon(socketPath, { spawnCommand: cmd, readyTimeoutMs: WAIT_MS }),
      ),
    );

    expect(results).toHaveLength(n);
    expect(results.every((r) => r === socketPath)).toBe(true);
    expect(await daemonIsLive(socketPath)).toBe(true);
    expect(spawnCount(counter)).toBe(1);
  });

  it("test_ensureDaemon_raises_DaemonStartError_when_no_READY — a spawned-but-broken daemon is Internal, not absent", async () => {
    const socketPath = socketPathFor();
    const counter = join(tmp, "spawns");
    const script = writeFakeDaemon(SILENT_DAEMON_SOURCE);
    const cmd = spawnCommandFor(script, counter);

    await expect(
      ensureDaemon(socketPath, { spawnCommand: cmd, readyTimeoutMs: 1_500 }),
    ).rejects.toBeInstanceOf(DaemonStartError);
  });

  it("test_module_is_terminal_only — the binding imports no chat relay / SessionBridge / platform (independence, MUST; ADR-003)", async () => {
    const here = dirname(fileURLToPath(import.meta.url));
    const moduleSrc = await readFile(
      join(here, "..", "lib", "ensureDaemon.ts"),
      "utf8",
    );
    // The import-graph note codified (the Node analogue of the Python WP-002
    // AST-import assertion): scan only the module's `import`/`require`
    // STATEMENTS — prose comments may legitimately describe what is NOT imported
    // (the independence note itself names chat/platform to forbid them). A
    // forbidden dependency in an actual import line is the regression this
    // catches.
    const importLines = moduleSrc
      .split("\n")
      .filter((l) => /^\s*import\b/.test(l) || /\brequire\s*\(/.test(l));
    const imports = importLines.join("\n");
    expect(imports).not.toMatch(/routes\/chat/);
    expect(imports).not.toMatch(/SessionBridge/);
    expect(imports).not.toMatch(/StreamJsonSessionBridge/);
    // No `platform` communication-service import (the cockpit's platform client).
    expect(imports).not.toMatch(/platform/i);
  });
});
