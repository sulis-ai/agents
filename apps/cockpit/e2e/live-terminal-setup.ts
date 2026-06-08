// WP-010 — live-terminal e2e global setup.
//
// The live-terminal round-trip needs its OWN isolated environment so it never
// collides with a developer's running cockpit (the v1 RED run reused a live
// dev server on the default ports and read the real ~/.sulis state). This setup:
//
//   1. Seeds a dedicated change record + worktree (reuses the WP-016 seeder,
//      but under its own state/projects dirs) so /api/changes lists exactly the
//      one change the e2e drives. The seed + handoff are IDEMPOTENT and called
//      by BOTH globalSetup AND the server wrapper (run-terminal-server.ts), so
//      the boot order (Playwright starts webServers + globalSetup in a
//      version-dependent order) cannot leave the server without its handoff —
//      mirrors the WP-016 ensureSeeded() pattern.
//   2. Starts the WS→AF_UNIX terminal proxy (terminal-proxy.ts) bound to the
//      seeded change id, on a dedicated port. The proxy is a live process, so it
//      is started ONLY in globalSetup (once), not in the server wrapper.
//   3. The client webServer is given VITE_TERMINAL_WS_URL (a fixed proxy-port
//      URL — config-level, no handoff dependency) so createTerminalBridge wires
//      the live WebSocketTransport.
//
// Teardown stops the proxy and removes the temp dirs.

import { writeFile, rm, mkdir, realpath, mkdtemp } from "node:fs/promises";
import { readFileSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { seed } from "./fixtures/seed";
import { startTerminalProxy, type TerminalProxyHandle } from "./terminal-proxy";

/** Dedicated handoff path (distinct from the WP-016 smoke handoff). */
export const TERMINAL_HANDOFF_PATH = join(
  tmpdir(),
  "cockpit-e2e-terminal-handoff.json",
);

/** The dedicated WS proxy port (distinct from any cockpit dev/e2e port). Kept in
 *  sync with VITE_TERMINAL_WS_URL in live-terminal.config.ts. */
export const TERMINAL_PROXY_PORT = 5185;

export interface TerminalHandoff {
  stateDir: string;
  projectsDir: string;
  worktree: string;
  changeId: string;
  handle: string;
  terminalWsUrl: string;
  proxyCwd: string;
}

let proxy: TerminalProxyHandle | undefined;

/** Idempotent: seed the fixture + write the handoff if it does not yet exist;
 *  otherwise return the existing one. Called by globalSetup AND the server
 *  wrapper so neither boot order leaves the server without its state dirs. The
 *  proxy is NOT started here — only the seed + handoff (the server wrapper needs
 *  only the state dirs; the proxy is a live process owned by globalSetup). */
export async function ensureTerminalSeeded(): Promise<TerminalHandoff> {
  if (existsSync(TERMINAL_HANDOFF_PATH)) {
    return readTerminalHandoff();
  }
  const fx = await seed();
  const proxyCwd = await realpath(
    await mkdtemp(join(tmpdir(), "cockpit-e2e-pty-")),
  );
  await mkdir(proxyCwd, { recursive: true });

  const handoff: TerminalHandoff = {
    stateDir: fx.stateDir,
    projectsDir: fx.projectsDir,
    worktree: fx.worktree,
    changeId: fx.changeId,
    handle: fx.handle,
    terminalWsUrl: `ws://127.0.0.1:${TERMINAL_PROXY_PORT}`,
    proxyCwd,
  };
  await writeFile(
    TERMINAL_HANDOFF_PATH,
    JSON.stringify(handoff, null, 2),
    "utf8",
  );
  return handoff;
}

export default async function globalSetup(): Promise<void> {
  const handoff = await ensureTerminalSeeded();
  // Start the live proxy (once) bound to the seeded change id.
  proxy = await startTerminalProxy({
    port: TERMINAL_PROXY_PORT,
    changeId: handoff.changeId,
    cwd: handoff.proxyCwd,
  });
}

export function readTerminalHandoff(): TerminalHandoff {
  return JSON.parse(
    readFileSync(TERMINAL_HANDOFF_PATH, "utf8"),
  ) as TerminalHandoff;
}

export async function globalTeardown(): Promise<void> {
  try {
    await proxy?.stop();
  } catch {
    /* best-effort proxy shutdown */
  }
  try {
    if (existsSync(TERMINAL_HANDOFF_PATH)) {
      const h = readTerminalHandoff();
      await rm(h.stateDir, { recursive: true, force: true });
      await rm(h.projectsDir, { recursive: true, force: true });
      await rm(h.worktree, { recursive: true, force: true });
      await rm(h.proxyCwd, { recursive: true, force: true });
      await rm(TERMINAL_HANDOFF_PATH, { force: true });
    }
  } catch {
    /* nothing to clean if setup failed */
  }
}
