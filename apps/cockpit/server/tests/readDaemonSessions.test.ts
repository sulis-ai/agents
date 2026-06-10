// Daemon-authoritative liveness (readDaemonSessions).
//
// The session-manager daemon OWNS the per-change pty sessions, so it — not the
// signal-0 probe — is the truth about what is running. These tests pin both
// halves of that contract:
//
//   readDaemonLiveSessions — one `status` round-trip over a real AF_UNIX socket;
//     returns a Map keyed by change_id, or `null` for every transport failure
//     (no socket / refused / timeout / malformed reply). `null` ("no authority")
//     is deliberately distinct from an empty Map ("daemon up, zero sessions").
//
//   livenessFromDaemon — the decision: daemon unreachable → fall back to the
//     signal-0 probe; daemon reachable + managing the change → running; daemon
//     reachable + NOT managing it → not-running (no "unknown" guesswork).

import { afterEach, describe, expect, it } from "vitest";
import net from "node:net";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import {
  livenessFromDaemon,
  readDaemonLiveSessions,
  type DaemonSession,
} from "../lib/readDaemonSessions";
import type { Liveness } from "../../shared/api-types";

// A throwaway AF_UNIX server that answers the FIRST framed request line with
// `reply` (newline-delimited JSON, matching the daemon's wire protocol).
function fakeDaemon(
  reply: string | null,
): Promise<{ socketPath: string; close: () => Promise<void> }> {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "daemon-sock-"));
  const socketPath = path.join(dir, "session-manager.sock");
  const server = net.createServer((sock) => {
    sock.on("data", () => {
      if (reply !== null) sock.write(reply + "\n");
      // reply === null → accept + stay silent (exercises the read timeout).
    });
  });
  return new Promise((resolve) => {
    server.listen(socketPath, () => {
      resolve({
        socketPath,
        close: () =>
          new Promise<void>((res) => {
            server.close(() => {
              fs.rmSync(dir, { recursive: true, force: true });
              res();
            });
          }),
      });
    });
  });
}

describe("readDaemonLiveSessions — transport contract", () => {
  const cleanups: Array<() => Promise<void>> = [];
  afterEach(async () => {
    while (cleanups.length) await cleanups.pop()!();
  });

  it("returns null when the socket file does not exist (daemon down)", async () => {
    const missing = path.join(os.tmpdir(), "definitely-no-such.sock");
    expect(await readDaemonLiveSessions(missing)).toBeNull();
  });

  it("maps an ok status reply into a Map keyed by change_id", async () => {
    const reply = JSON.stringify({
      ok: true,
      result: [
        { key: "01CHANGEALIVE", state: "ready", pid: 4242 },
        { key: "01CHANGEQUIET", state: "ready", pid: 4243 },
      ],
    });
    const d = await fakeDaemon(reply);
    cleanups.push(d.close);
    const map = await readDaemonLiveSessions(d.socketPath);
    expect(map).not.toBeNull();
    expect(map!.size).toBe(2);
    expect(map!.get("01CHANGEALIVE")).toEqual({
      key: "01CHANGEALIVE",
      state: "ready",
      pid: 4242,
    });
  });

  it("tolerates a session row with a null pid (managed-without-pid)", async () => {
    const reply = JSON.stringify({
      ok: true,
      result: [{ key: "01NOPID", state: "ready", pid: null }],
    });
    const d = await fakeDaemon(reply);
    cleanups.push(d.close);
    const map = await readDaemonLiveSessions(d.socketPath);
    expect(map!.get("01NOPID")!.pid).toBeNull();
  });

  it("returns null when the daemon replies ok:false", async () => {
    const d = await fakeDaemon(JSON.stringify({ ok: false }));
    cleanups.push(d.close);
    expect(await readDaemonLiveSessions(d.socketPath)).toBeNull();
  });

  it("returns null when the reply is not valid JSON", async () => {
    const d = await fakeDaemon("{ not json");
    cleanups.push(d.close);
    expect(await readDaemonLiveSessions(d.socketPath)).toBeNull();
  });

  it("returns null when the daemon never answers (read timeout)", async () => {
    const d = await fakeDaemon(null);
    cleanups.push(d.close);
    expect(await readDaemonLiveSessions(d.socketPath, 150)).toBeNull();
  });
});

describe("livenessFromDaemon — decision contract", () => {
  const probeFallback: Liveness = { status: "unknown", reason: "no pid recorded" };

  it("daemon unreachable (null) → falls back to the signal-0 probe", () => {
    expect(livenessFromDaemon("01ANY", null, probeFallback)).toEqual(
      probeFallback,
    );
  });

  it("daemon managing the change → running with the daemon's pid", () => {
    const sessions = new Map<string, DaemonSession>([
      ["01LIVE", { key: "01LIVE", state: "ready", pid: 5151 }],
    ]);
    expect(livenessFromDaemon("01LIVE", sessions, probeFallback)).toEqual({
      status: "running",
      pid: 5151,
    });
  });

  it("daemon managing the change but pid null → running with pid 0 sentinel", () => {
    const sessions = new Map<string, DaemonSession>([
      ["01LIVE", { key: "01LIVE", state: "ready", pid: null }],
    ]);
    expect(livenessFromDaemon("01LIVE", sessions, probeFallback)).toEqual({
      status: "running",
      pid: 0,
    });
  });

  it("daemon up but NOT managing the change → not-running (no unknown guess)", () => {
    const sessions = new Map<string, DaemonSession>();
    expect(livenessFromDaemon("01IDLE", sessions, probeFallback)).toEqual({
      status: "not-running",
    });
  });
});
