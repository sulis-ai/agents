// WP-005 (fix-forward) — the two LIVE round-trip bugs, pinned by regression.
//
// The recorded-fixture contract suite (session-bridge.streamjson.test.ts) is
// green because it injects a synthetic child that emits output instantly. It
// could NOT catch two faults that only bite a REAL `claude` over a real socket
// — both made EVERY live chat fail with SESSION_UNREACHABLE on any machine:
//
//   Bug 1 — startup watchdog far too short. index.ts wired
//     `startupTimeoutMs: CONFIG.gitTimeoutMs` (~5 s). A cold headless
//     `claude -p --output-format stream-json --include-partial-messages`
//     legitimately takes ~5–9 s to FIRST output (measured live: ~3.5 s
//     time-to-first-token + a 3 s stdin stall, bug 2). The 5 s watchdog fired
//     right as the agent woke ⇒ kill ⇒ unreachable. Fix: a DEDICATED
//     `chatBridgeStartupTimeoutMs` (≥45 s), never `gitTimeoutMs`.
//
//   Bug 2 — child stdin left open ⇒ 3 s stall. The prompt is passed via `-p`,
//     so the child needs NO stdin; if stdin is open/inherited, real `claude`
//     logs `Warning: no stdin data received in 3s, proceeding without it` —
//     dead time that pushed first output past the watchdog. Fix: spawn with
//     stdin IGNORED (immediate EOF). The live stall isn't unit-observable, so
//     we pin it two ways: (a) a source-hygiene assertion on the spawn stdio
//     config, and (b) a behavioural proof against a real fake `claude` on PATH
//     that records whether its stdin reached EOF immediately.

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import {
  mkdtemp,
  rm,
  realpath,
  writeFile,
  chmod,
  readFile,
} from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

import { CONFIG } from "../config";
import { spawnClaudeBridge } from "../adapters/StreamJsonSessionBridge";

const HERE = dirname(fileURLToPath(import.meta.url));
const SERVER_DIR = join(HERE, "..");

// ─── Bug 1: the prod bridge startup budget is the dedicated value ──────────
describe("WP-005 bug 1 — chat-bridge startup budget is NOT gitTimeoutMs", () => {
  it("CONFIG exposes a dedicated chatBridgeStartupTimeoutMs ≥ 45 s", () => {
    expect(CONFIG.chatBridgeStartupTimeoutMs).toBeGreaterThanOrEqual(45_000);
  });

  it("the bridge budget is distinct from the git-operation budget", () => {
    // The whole point: a cold model start legitimately exceeds a git op's
    // budget, so the two must never be the same knob.
    expect(CONFIG.chatBridgeStartupTimeoutMs).not.toBe(CONFIG.gitTimeoutMs);
    expect(CONFIG.chatBridgeStartupTimeoutMs).toBeGreaterThan(
      CONFIG.gitTimeoutMs,
    );
  });

  it("index.ts wires chatBridgeStartupTimeoutMs (NOT gitTimeoutMs) into the prod bridge", async () => {
    // Source-hygiene guard: the production wiring is the regression surface.
    // The contract suite injects startupTimeoutMs directly, so only this
    // assertion proves the prod adapter receives the dedicated budget.
    const src = await readFile(join(SERVER_DIR, "index.ts"), "utf8");
    expect(src).toMatch(/startupTimeoutMs:\s*CONFIG\.chatBridgeStartupTimeoutMs/);
    expect(src).not.toMatch(/startupTimeoutMs:\s*CONFIG\.gitTimeoutMs/);
  });
});

// ─── Bug 2: the prod spawn closes the child's stdin ────────────────────────
describe("WP-005 bug 2 — spawnClaudeBridge closes/ignores the child stdin", () => {
  it("source-hygiene: stdio[0] is 'ignore' (immediate EOF, no 3 s stall)", async () => {
    const src = await readFile(
      join(SERVER_DIR, "adapters", "StreamJsonSessionBridge.ts"),
      "utf8",
    );
    // The stdio array passed to spawn must close stdin. Match the canonical
    // form `stdio: ["ignore", ...]` (stdin position = "ignore").
    const stdioMatch = src.match(/stdio:\s*\[\s*"(\w+)"/);
    expect(stdioMatch, "spawn call must pass an explicit stdio array").not.toBe(
      null,
    );
    expect(stdioMatch?.[1]).toBe("ignore");
  });

  describe("behavioural: a real fake claude sees stdin EOF immediately", () => {
    let dir: string;
    let originalPath: string | undefined;

    beforeEach(async () => {
      dir = await realpath(await mkdtemp(join(tmpdir(), "wp005-claude-")));
      originalPath = process.env.PATH;
      // Prepend the fake-bin dir so spawn("claude", …) resolves to our stub.
      process.env.PATH = `${dir}:${originalPath ?? ""}`;
    });

    afterEach(async () => {
      process.env.PATH = originalPath;
      await rm(dir, { recursive: true, force: true });
    });

    it("does not stall on stdin — first read hits EOF immediately, no 3 s wait", async () => {
      // The fake `claude` times its FIRST stdin read (with a 2 s ceiling) and
      // records the elapsed ms. This is the real-world discriminator:
      //   - stdin CLOSED (stdio[0]="ignore") ⇒ read hits EOF in ~single-digit
      //     ms ⇒ no stall;
      //   - stdin OPEN-but-idle (inherited/piped, the bug) ⇒ read BLOCKS until
      //     the timeout — exactly the "Warning: no stdin data received in 3s"
      //     dead time that pushed first output past the startup watchdog.
      // It then emits valid stream-json so the adapter records a completed
      // reply. The assertion: the read did NOT stall (≪ the real 3 s warning).
      const sentinel = join(dir, "stdin-block-ms");
      const fakeClaude = join(dir, "claude");
      await writeFile(
        fakeClaude,
        [
          "#!/usr/bin/env bash",
          "set -uo pipefail",
          "start=$(date +%s%N)",
          "IFS= read -t 2 -r _line < /dev/stdin || true",
          "end=$(date +%s%N)",
          `echo $(( (end - start) / 1000000 )) > "${sentinel}"`,
          // Minimal valid stream-json so the adapter records a completed reply.
          `printf '%s\\n' '{\"type\":\"system\",\"subtype\":\"init\"}'`,
          `printf '%s\\n' '{\"type\":\"stream_event\",\"event\":{\"type\":\"content_block_delta\",\"delta\":{\"text\":\"hi\"}}}'`,
          `printf '%s\\n' '{\"type\":\"result\",\"subtype\":\"success\"}'`,
          "exit 0",
        ].join("\n") + "\n",
        "utf8",
      );
      await chmod(fakeClaude, 0o755);

      const handle = spawnClaudeBridge(["-p", "hello"], dir);

      await new Promise<void>((resolve, reject) => {
        handle.process.on("close", () => resolve());
        handle.process.on("error", (err) => reject(err));
        // Drain stdout so the pipe doesn't backpressure the child.
        handle.stdout.resume();
      });

      const blockedMs = Number((await readFile(sentinel, "utf8")).trim());
      // Closed stdin returns at EOF near-instantly; an open-idle stdin would
      // block ~2000 ms here (≈ the real 3 s claude stall). 500 ms is a wide
      // margin that still fails loudly if stdin is ever left open again.
      expect(blockedMs).toBeLessThan(500);
    });
  });
});
