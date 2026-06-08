// WP-007 — the `ensureDaemon` / stable-socket presence contract (Node binding).
//
// The Node half of the CONTRACT_FIRST seam documented in
// `plugins/sulis/scripts/_session_manager/DAEMON_CONTRACT.md` (TDD §5, ADR-001).
// Both views start the shared session-manager daemon through this contract
// before connecting: this module is the cockpit's caller (WP-007); the Python
// `daemon_client.py` (WP-002) is the desktop launcher's sibling binding over the
// same wire. The two bindings are byte-for-byte interchangeable from the
// daemon's perspective.
//
// What this module owns is the CALLER side of the presence contract:
//
//   - `resolveDefaultSocket` / the stable socket location, env-overridable
//     (`SULIS_SESSION_MANAGER_SOCKET`).
//   - `daemonIsLive` — the liveness probe: connect + a `status` round-trip that
//     must return `ok:true`, with a short timeout so a dead socket fails fast.
//   - `ensureDaemon` — probe-first, spawn-at-most-once, race-tolerant start. If
//     no daemon answers, spawn one DETACHED and wait for `READY`; if a peer
//     caller wins the singleton race, poll until its daemon answers.
//
// The flock singleton arbitration itself is the DAEMON's job (WP-003); the
// caller contract here is the matching half — never assume a spawn won, always
// re-confirm liveness, and tolerate a peer having started the daemon instead.
//
// INDEPENDENCE (founder directive, MUST; ADR-003): this module imports the Node
// stdlib + the in-tree shared NDJSON framer ONLY. No chat relay (routes/chat.ts),
// no chat SessionBridge, no `platform` communication service, no engine
// internals — it speaks the engine's §2.13 NDJSON wire as a plain socket client.
// The terminal daemon is terminal-only.
//
// READ-ONLY GATE (ADR-010, re-pointed by WP-007): this is the ONE sanctioned
// process-start site the terminal composition introduces (the spawn MOVED here
// from index.ts's retired `startSessionManagerHost`). It is allow-listed BY PATH
// in `tests/read-only-inventory.test.ts` — the gate follows the spawn.

import { spawn } from "node:child_process";
import { connect } from "node:net";
import { existsSync, mkdirSync } from "node:fs";
import { homedir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (the shared NDJSON framer, also used by TerminalSidecar.ts + e2e/terminal-proxy.ts; the rule blocks escapes OUT of apps/cockpit/, which import/no-restricted-paths enforces)
import { createNdjsonLineFramer } from "../../shared/ndjsonLineFramer";

/** The env override seam for the stable socket — mirrors the existing
 *  `SULIS_SESSION_MANAGER_HOST` injection used by the cockpit + CI/e2e. */
const ENV_SOCKET_OVERRIDE = "SULIS_SESSION_MANAGER_SOCKET";

/** The token in a spawn argv that {@link ensureDaemon} replaces with the
 *  resolved socket path (so an injected command names the socket without
 *  re-spelling it) — parity with `daemon_client.py`'s `_SOCKET_TOKEN`. */
const SOCKET_TOKEN = "{socket}";

/**
 * Resolve the absolute path to the bundled Python daemon entrypoint
 * `plugins/sulis/scripts/session_manager_daemon.py` (WP-003). Mirrors the
 * existing `resolveHelperPath`/`resolveHostPath` resolution in index.ts: the
 * repo root is three levels up from this file's package
 * (`apps/cockpit/server/lib/ → apps/cockpit/server → apps/cockpit → apps → root`
 * is four; the helper resolution in index.ts is from `server/`, three up — this
 * file is one level deeper, so four up).
 */
function resolveDaemonEntrypoint(): string {
  const here = path.dirname(fileURLToPath(import.meta.url));
  const repoRoot = path.resolve(here, "..", "..", "..", "..");
  return path.join(
    repoRoot,
    "plugins",
    "sulis",
    "scripts",
    "session_manager_daemon.py",
  );
}

/**
 * The stable daemon socket path. `~/.sulis/session-manager.sock` by default,
 * overridable by `SULIS_SESSION_MANAGER_SOCKET` (the test/CI/e2e injection seam,
 * mirroring the existing `SULIS_SESSION_MANAGER_HOST` override). Always absolute.
 *
 * Resolved at call time (not snapshotted) so a test setting the env var before a
 * boot sees its value — the Node analogue of `daemon_client.resolve_default_socket`.
 */
export function resolveDefaultSocket(): string {
  const override = process.env[ENV_SOCKET_OVERRIDE];
  if (override !== undefined && override.length > 0) {
    return override;
  }
  return path.join(homedir(), ".sulis", "session-manager.sock");
}

/**
 * The daemon was spawned but did not become live within `readyTimeoutMs`.
 *
 * This is the contract's INTERNAL category (CF-03): the daemon exists but is
 * broken, distinct from "no daemon present" (which {@link ensureDaemon} heals by
 * spawning). Callers log + escalate; retrying unchanged repeats it. The Node
 * sibling of `daemon_client.DaemonStartError`.
 */
export class DaemonStartError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "DaemonStartError";
  }
}

/** Connect and run one `status` round-trip; resolve true iff it returns
 *  `ok:true`. Any transport failure (missing socket, refused connect, timeout,
 *  malformed reply) maps to false — the contract's Protocol/Expected categories
 *  both mean "not live → the caller should (re)start". The short timeout makes a
 *  dead-but-present socket file fail fast instead of blocking. */
function statusProbe(socketPath: string, timeoutMs: number): Promise<boolean> {
  return new Promise<boolean>((resolve) => {
    const framer = createNdjsonLineFramer();
    let settled = false;
    const sock = connect(socketPath);

    const done = (live: boolean): void => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      sock.destroy();
      resolve(live);
    };

    const timer = setTimeout(() => done(false), timeoutMs);
    sock.setTimeout(timeoutMs, () => done(false));

    sock.on("connect", () => {
      sock.write(
        JSON.stringify({ id: "live", method: "status", params: {} }) + "\n",
      );
    });
    sock.on("data", (chunk: Buffer) => {
      for (const line of framer.push(chunk)) {
        try {
          const reply = JSON.parse(line) as { ok?: unknown };
          done(reply.ok === true);
        } catch {
          done(false);
        }
        return; // only the first framed line matters
      }
    });
    sock.on("error", () => done(false));
    sock.on("close", () => done(false));
  });
}

/**
 * True iff a daemon serves `socketPath`: connect succeeds AND a `status` request
 * returns `ok:true` (`DAEMON_CONTRACT.md` § Liveness). Fails fast on a dead or
 * absent socket — the connect+read is bounded by `timeoutMs` so a stale socket
 * file never blocks the caller. The Node sibling of `daemon_client.daemon_is_live`.
 */
export async function daemonIsLive(
  socketPath: string = resolveDefaultSocket(),
  timeoutMs = 1_000,
): Promise<boolean> {
  if (!existsSync(socketPath)) return false;
  return statusProbe(socketPath, timeoutMs);
}

/** Options for {@link ensureDaemon}. */
export interface EnsureDaemonOptions {
  /** python executable to launch the daemon with (default `python3`). */
  python?: string;
  /** How long to wait for a live daemon after spawning before raising
   *  {@link DaemonStartError} (ms, default 30_000). */
  readyTimeoutMs?: number;
  /** The argv to launch; the literal `"{socket}"` token in it is replaced with
   *  the resolved socket path. When omitted it defaults to the real daemon
   *  entrypoint (WP-003): `python session_manager_daemon.py --socket <path>
   *  --lock <path>.lock`. Injecting it keeps this binding testable against a
   *  fake daemon and independent of WP-003's entrypoint (parity with
   *  `daemon_client.ensure_daemon`'s `spawn_command`). */
  spawnCommand?: string[];
}

/** The default argv to launch the real daemon (WP-003). The socket token is
 *  filled in by {@link ensureDaemon}. The `--lock` co-locates beside the socket
 *  so an INJECTED socket (tests/e2e) gets an isolated lock+socket pair for free,
 *  while the stable default socket yields the stable lock — preserving the
 *  singleton. (The daemon defaults `--lock` to `~/.sulis/session-manager.lock`;
 *  naming it beside the socket here is the boring, explicit isolation seam.) */
function defaultSpawnCommand(python: string): string[] {
  const entry = resolveDaemonEntrypoint();
  const lockToken = `${SOCKET_TOKEN}.lock`;
  return [python, entry, "--socket", SOCKET_TOKEN, "--lock", lockToken];
}

/** Substitute the socket token in the spawn argv with the resolved path. */
function materialiseCommand(
  spawnCommand: string[],
  socketPath: string,
): string[] {
  const lockPath = `${socketPath}.lock`;
  return spawnCommand.map((part) =>
    part === SOCKET_TOKEN
      ? socketPath
      : part.replace(`${SOCKET_TOKEN}.lock`, lockPath).replace(SOCKET_TOKEN, socketPath),
  );
}

const sleep = (ms: number): Promise<void> =>
  new Promise((r) => setTimeout(r, ms));

/** Poll the liveness probe until the socket answers or the deadline passes — the
 *  race-loser's path (`DAEMON_CONTRACT.md` § Idempotent ensure): a caller whose
 *  spawn lost the singleton race waits here for the winner's daemon. */
async function pollUntilLive(
  socketPath: string,
  deadline: number,
  probeTimeoutMs: number,
): Promise<boolean> {
  while (Date.now() < deadline) {
    if (await daemonIsLive(socketPath, probeTimeoutMs)) return true;
    await sleep(50);
  }
  return daemonIsLive(socketPath, probeTimeoutMs);
}

// Process-local arbitration: concurrent `ensureDaemon` callers WITHIN one
// process (e.g. several parallel boots in a test) collapse to a single
// probe→spawn critical section per socket, so they yield one spawn rather than
// each racing a launch. Cross-process arbitration is the daemon's `fcntl.flock`
// (ADR-001, WP-003): a launch that loses the flock exits 0 and the caller polls.
// The two together give the "at most one daemon" guarantee end to end. This is
// the Node analogue of `daemon_client`'s per-socket `threading.Lock`.
const spawnChains = new Map<string, Promise<string>>();

/**
 * Return `socketPath` with a live daemon serving it. Probe-first,
 * spawn-at-most-once, race-tolerant (`DAEMON_CONTRACT.md` § Idempotent ensure):
 *
 *   1. If a daemon already answers the `status` probe → return immediately,
 *      spawn nothing.
 *   2. Otherwise spawn the daemon DETACHED (`detached: true` + `unref()` — it
 *      survives this caller's exit), wait for the `READY <socket>` handshake,
 *      confirm liveness, and return.
 *   3. If the spawn lost the singleton race (the process exited before READY
 *      because a peer's flock won), POLL the socket until the winner answers,
 *      then return.
 *
 * Concurrent callers therefore yield AT MOST ONE serving daemon and all return
 * the same `socketPath`. The Node sibling of `daemon_client.ensure_daemon`.
 *
 * Raises {@link DaemonStartError} if, after spawning, no live daemon answers
 * within `readyTimeoutMs` (the daemon is broken — Internal, not absent).
 */
export async function ensureDaemon(
  socketPath: string = resolveDefaultSocket(),
  opts: EnsureDaemonOptions = {},
): Promise<string> {
  const python = opts.python ?? "python3";
  const readyTimeoutMs = opts.readyTimeoutMs ?? 30_000;
  const probeTimeoutMs = Math.min(1_000, readyTimeoutMs);

  // 1. Warm path: a daemon already serves the socket (no critical section).
  if (await daemonIsLive(socketPath, probeTimeoutMs)) return socketPath;

  // Serialise the probe→spawn critical section across in-process callers so
  // concurrent boots collapse to one spawn. A caller that joins an in-flight
  // chain returns its result; otherwise it starts (and registers) the chain.
  const inFlight = spawnChains.get(socketPath);
  if (inFlight !== undefined) return inFlight;

  const chain = spawnAndWait(socketPath, {
    python,
    spawnCommand: opts.spawnCommand,
    probeTimeoutMs,
    readyTimeoutMs,
  }).finally(() => {
    spawnChains.delete(socketPath);
  });
  spawnChains.set(socketPath, chain);
  return chain;
}

/** Spawn the daemon detached, wait for READY, confirm liveness (the cold-start
 *  body of {@link ensureDaemon}, run under the per-socket in-process chain). */
async function spawnAndWait(
  socketPath: string,
  args: {
    python: string;
    spawnCommand?: string[];
    probeTimeoutMs: number;
    readyTimeoutMs: number;
  },
): Promise<string> {
  const { python, spawnCommand, probeTimeoutMs, readyTimeoutMs } = args;
  const deadline = Date.now() + readyTimeoutMs;

  // Double-check under the chain: a peer may have just brought the daemon up.
  if (await daemonIsLive(socketPath, probeTimeoutMs)) return socketPath;

  // Ensure the socket's parent dir exists (0o700) before the daemon binds there.
  const parent = path.dirname(path.resolve(socketPath));
  mkdirSync(parent, { recursive: true, mode: 0o700 });

  const command = materialiseCommand(
    spawnCommand ?? defaultSpawnCommand(python),
    socketPath,
  );
  const [cmd, ...argv] = command;
  if (cmd === undefined) {
    throw new DaemonStartError("empty spawn command");
  }

  // 2. Spawn detached. stdout is piped only to read the READY line; the daemon
  // is a new session leader (`detached: true` + `unref()`) so it outlives this
  // caller — the Node analogue of Python's `start_new_session=True`.
  const ready = await new Promise<boolean>((resolve) => {
    const proc = spawn(cmd, argv, {
      detached: true,
      stdio: ["ignore", "pipe", "ignore"],
    });
    let settled = false;
    const framer = createNdjsonLineFramer();

    const finish = (value: boolean): void => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      // Release our hold on the pipe; the detached daemon keeps running. unref()
      // lets THIS process exit independently of the daemon.
      proc.stdout?.removeAllListeners();
      proc.unref();
      resolve(value);
    };

    const timer = setTimeout(
      () => finish(false),
      Math.max(0, deadline - Date.now()),
    );

    proc.stdout?.on("data", (chunk: Buffer) => {
      // READY is a single line on stdout; the daemon may print it un-framed
      // (no trailing object), so also check the raw chunk.
      if (chunk.toString().includes("READY")) {
        finish(true);
        return;
      }
      framer.push(chunk); // drain so backpressure never stalls the daemon
    });
    proc.on("error", () => finish(false));
    proc.on("exit", () => {
      // The process exited before READY. For a race-loser this is the normal
      // "another daemon won, I exited 0" path — finish false so the caller polls
      // the live socket below.
      finish(false);
    });
  });

  if (ready && (await daemonIsLive(socketPath, probeTimeoutMs))) {
    return socketPath;
  }

  // 3. Either we did not see READY (lost the singleton race, or a slow start) or
  // READY came but the probe has not caught up — poll until the socket answers.
  if (await pollUntilLive(socketPath, deadline, probeTimeoutMs)) {
    return socketPath;
  }

  throw new DaemonStartError(
    `daemon did not become live at ${JSON.stringify(socketPath)} within ` +
      `${readyTimeoutMs}ms (spawn argv: ${JSON.stringify(command)})`,
  );
}
