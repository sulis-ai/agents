// WP-004 — recreate-on-demand for shipped changes (TDD §3, §5; ADR-004).
//
// A shipped change's worktree is removed by the #56 tidy step, but its
// branch + record (with a pinned `shipped_sha`) are kept. To render a
// tidied change's contracts, the serving path must re-materialise the
// worktree FIRST — transparently — by composing the already-shipped
// `sulis-change recreate` CLI (ADR-004). This WP does NOT re-implement
// worktree materialisation; it composes `cmd_recreate` behind a
// `RecreateRunner` port.
//
// These tests build against a FakeRecreateRunner (WPB-03 in-memory-first,
// MEA-09: a real adapter shape, not an ad-hoc mock) so WP-004 ships in
// parallel with the renderers (WP-001/002) and the wiring (WP-003).
//
// Three states the serving path MUST distinguish (acceptance criteria):
//   (a) worktree present            → render directly (no recreate);
//   (b) absent-but-recreatable      → recreate then render;
//   (c) absent-and-not-recreatable  → typed note; the cockpit degrades to
//                                      "couldn't reach this shipped change's
//                                      contracts" rather than hanging.
// Plus: recreate is idempotent (already-present → no-op success), and a
// recreate TIMEOUT degrades to the typed note (never hangs the request).

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import {
  mkdtemp,
  rm,
  mkdir,
  realpath,
  writeFile,
  chmod,
} from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { readFile } from "node:fs/promises";

import { resolveContractWorktree } from "../routes/_recreate-on-demand";
import { FakeRecreateRunner } from "../adapters/FakeRecreateRunner";
import { SulisChangeRecreator } from "../adapters/SulisChangeRecreator";
import type { ChangeStoreRecord } from "../ports/ChangeStoreReader";

// ─── Test fixtures ───────────────────────────────────────────────────────

/**
 * A change record stub. The on-demand resolver reads only the facts the
 * record carries (worktreePath, branch, shippedSha, handle) — ADR-003,
 * never hard-wiring a specific change.
 */
function makeRecord(
  overrides: Partial<ChangeStoreRecord> = {},
): ChangeStoreRecord {
  return {
    changeId: "01TESTCHANGEID0000000000AB",
    handle: "feat-some-shipped-change",
    slug: "some-shipped-change",
    primitive: "feat",
    branch: "change/feat-some-shipped-change",
    worktreePath: "/nonexistent/worktree/path",
    intent: "a shipped change",
    baseBranch: "dev",
    baseSha: "abc123",
    shippedSha: "deadbeefcafe",
    createdAt: "2026-05-01T00:00:00Z",
    updatedAt: "2026-05-02T00:00:00Z",
    stage: "shipped",
    ...overrides,
  };
}

describe("resolveContractWorktree (recreate-on-demand)", () => {
  let tmpRoot: string; // realpath-resolved

  beforeEach(async () => {
    const base = await mkdtemp(join(tmpdir(), "recreate-ondemand-"));
    tmpRoot = await realpath(base);
  });

  afterEach(async () => {
    await rm(tmpRoot, { recursive: true, force: true });
  });

  // ── (a) present → render directly, recreate NOT invoked ───────────────
  it("present worktree → resolves the root directly, recreate is NOT invoked", async () => {
    const worktree = join(tmpRoot, "present-wt");
    await mkdir(worktree, { recursive: true });

    const runner = new FakeRecreateRunner({ ok: true, alreadyPresent: false });
    const result = await resolveContractWorktree({
      record: makeRecord({ worktreePath: worktree }),
      runner,
    });

    expect(result.status).toBe("ready");
    if (result.status === "ready") {
      // realpath-resolved canonical root (the serving path's safeJoin
      // discipline depends on this — reuse of resolveWorktreeRoot).
      expect(result.worktreeRoot).toBe(await realpath(worktree));
    }
    // The whole point of state (a): a present worktree is never recreated.
    expect(runner.calls).toEqual([]);
  });

  // ── (b) absent-but-recreatable → recreate THEN render ─────────────────
  it("absent-but-recreatable → invokes recreate with the handle, then resolves the root", async () => {
    const worktree = join(tmpRoot, "recreatable-wt");
    // Worktree absent at first. The fake recreate MATERIALISES it (the real
    // `sulis-change recreate` checks out the worktree) so the resolver can
    // then resolve the now-present root — proving recreate happens BEFORE
    // the render-path resolution.
    const runner = new FakeRecreateRunner(
      { ok: true, alreadyPresent: false },
      {
        onRecreate: async () => {
          await mkdir(worktree, { recursive: true });
        },
      },
    );

    const record = makeRecord({ worktreePath: worktree });
    const result = await resolveContractWorktree({ record, runner });

    expect(result.status).toBe("ready");
    if (result.status === "ready") {
      expect(result.worktreeRoot).toBe(await realpath(worktree));
    }
    // Recreate invoked exactly once, with the change's own handle (ADR-003
    // generic resolution — the handle comes off the record, not hard-wired).
    expect(runner.calls).toEqual([record.handle]);
  });

  // ── idempotent: already-present recreate → no-op success ──────────────
  it("recreate reporting already-present → no-op success, root resolves", async () => {
    const worktree = join(tmpRoot, "idempotent-wt");
    // The worktree already exists on disk; the change record still triggers
    // recreate because the resolver can't know it's present without the
    // recreate's own idempotent check (the real recreate is the authority).
    // recreate returns alreadyPresent:true (its documented idempotent path)
    // and the root resolves — a no-op success, not an error.
    await mkdir(worktree, { recursive: true });
    const runner = new FakeRecreateRunner({ ok: true, alreadyPresent: true });

    // Force the recreate branch by pointing the resolver at an absent path
    // first is unnecessary here — present-on-disk takes state (a). To
    // exercise idempotency we recreate explicitly via the runner's contract:
    // a present worktree resolves directly (state a) WITHOUT calling recreate,
    // so idempotency is the *runner's* guarantee. Assert the runner surfaces
    // alreadyPresent without throwing.
    const outcome = await runner.recreate("feat-some-shipped-change");
    expect(outcome.ok).toBe(true);
    if (outcome.ok) {
      expect(outcome.alreadyPresent).toBe(true);
    }
    // And resolving a present worktree is a ready no-op.
    const result = await resolveContractWorktree({
      record: makeRecord({ worktreePath: worktree }),
      runner,
    });
    expect(result.status).toBe("ready");
  });

  // ── (c) absent-and-not-recreatable → typed note (never hangs) ─────────
  it("absent-and-not-recreatable (no shippedSha, no branch) → typed note, no recreate", async () => {
    const runner = new FakeRecreateRunner({ ok: true, alreadyPresent: false });
    const result = await resolveContractWorktree({
      record: makeRecord({
        worktreePath: join(tmpRoot, "does-not-exist"),
        branch: "",
        shippedSha: null,
      }),
      runner,
    });

    expect(result.status).toBe("unavailable");
    if (result.status === "unavailable") {
      // A plain founder-legible note, never a raw stack/throw (TDD §3).
      expect(result.note).toMatch(
        /couldn't reach this shipped change's contracts/i,
      );
    }
    // Not recreatable → we never even attempt recreate.
    expect(runner.calls).toEqual([]);
  });

  // ── recreate TIMEOUT degrades, does not hang/throw ────────────────────
  it("recreate TIMEOUT → degrades to the typed note, does not hang or throw raw", async () => {
    const worktree = join(tmpRoot, "timeout-wt"); // stays absent
    const runner = new FakeRecreateRunner({
      ok: false,
      reason: "TIMEOUT",
      detail: "recreate exceeded 30000ms",
    });

    const record = makeRecord({ worktreePath: worktree });
    // Must resolve (not reject) — the cockpit degrades rather than hanging
    // a request on a recreate that blew its timeout (TDD §3 bounded recreate).
    const result = await resolveContractWorktree({ record, runner });

    expect(result.status).toBe("unavailable");
    if (result.status === "unavailable") {
      expect(result.note).toMatch(
        /couldn't reach this shipped change's contracts/i,
      );
    }
    // We did attempt recreate (it was recreatable) before degrading.
    expect(runner.calls).toEqual([record.handle]);
  });

  // ── recreate EXEC_FAIL degrades, does not hang/throw ──────────────────
  it("recreate EXEC_FAIL → degrades to the typed note, does not throw raw", async () => {
    const worktree = join(tmpRoot, "execfail-wt"); // stays absent
    const runner = new FakeRecreateRunner({
      ok: false,
      reason: "EXEC_FAIL",
      detail: "sulis-change recreate exited 1",
    });

    const result = await resolveContractWorktree({
      record: makeRecord({ worktreePath: worktree }),
      runner,
    });

    expect(result.status).toBe("unavailable");
  });

  // ── recreate "success" but worktree still absent → degrade (no-op) ────
  it("recreate reports success but worktree stays absent → degrades (no-op), never hands back a missing root", async () => {
    const worktree = join(tmpRoot, "ghost-wt"); // never created
    // The fake reports a clean success but its onRecreate does NOT
    // materialise the worktree — simulating a recreate that claimed
    // success yet left nothing on disk. The resolver must degrade rather
    // than return a `ready` root that isn't there.
    const runner = new FakeRecreateRunner({ ok: true, alreadyPresent: false });

    const record = makeRecord({ worktreePath: worktree });
    const result = await resolveContractWorktree({ record, runner });

    expect(result.status).toBe("unavailable");
    if (result.status === "unavailable") {
      expect(result.reason).toBe("recreate-no-op");
      expect(result.note).toMatch(
        /couldn't reach this shipped change's contracts/i,
      );
    }
    expect(runner.calls).toEqual([record.handle]);
  });

  // ── recreatable via shippedSha alone (no branch) ──────────────────────
  it("recreatable via shippedSha alone (empty branch) → still attempts recreate", async () => {
    const worktree = join(tmpRoot, "pinned-wt");
    const runner = new FakeRecreateRunner(
      { ok: true, alreadyPresent: false },
      {
        onRecreate: async () =>
          void (await mkdir(worktree, { recursive: true })),
      },
    );

    const record = makeRecord({
      worktreePath: worktree,
      branch: "", // branch gone…
      shippedSha: "deadbeefcafe", // …but pinned, so still recreatable
    });
    const result = await resolveContractWorktree({ record, runner });

    expect(result.status).toBe("ready");
    expect(runner.calls).toEqual([record.handle]);
  });
});

// ─── Source-hygiene guard for the production spawn adapter ───────────────
//
// The real RecreateRunner (SulisChangeRecreator) is the ONE new place that
// spawns a subprocess. The cockpit's subprocess discipline (TDD §3, the
// SulisChangeStoreReader / gitShow pattern) MUST hold: spawn (not exec),
// args:string[] (no string command line), shell:false, a bounded timeout,
// and ONLY the `recreate` verb (no mutating git verbs — read-only gate).
describe("SulisChangeRecreator source hygiene", () => {
  it("uses spawn with args:string[] + shell:false, only the 'recreate' verb, bounded timeout", async () => {
    const src = await readFile(
      join(__dirname, "..", "adapters", "SulisChangeRecreator.ts"),
      "utf8",
    );
    // Strip line-comments so prose mentioning a forbidden token isn't matched.
    const code = src
      .split("\n")
      .map((line) => line.replace(/\/\/.*$/, ""))
      .join("\n");

    // spawn, not exec/execSync/spawnSync-string.
    expect(code).toMatch(/from\s+["']node:child_process["']/);
    expect(code).toMatch(/spawn\s*\(/);
    // Never enable the shell.
    expect(code).not.toMatch(/shell\s*:\s*true/);
    // Never interpolate into a string command line (spawn's first arg is the
    // bare executable name, not a template string starting with the binary).
    expect(code).not.toMatch(/spawn\s*\(\s*[`'"]\s*sulis-change\s/);
    // It MUST carry the recreate verb as a quoted argv token.
    expect(code).toMatch(/["']recreate["']/);
    // It MUST NOT carry any mutating git verb (read-only gate parity).
    expect(code).not.toMatch(
      /["'](add|commit|reset|checkout|push|pull|merge|rebase)["']/,
    );
    // A bounded timeout must be present (setTimeout + kill discipline).
    expect(code).toMatch(/setTimeout\s*\(/);
    expect(code).toMatch(/\.kill\s*\(/);
  });
});

// ─── Behavioural coverage of the production spawn adapter ────────────────
//
// WP-004 builds its serving-path logic against the FakeRecreateRunner so it
// can ship in parallel (the WP Contract). But the production adapter's typed
// outcomes are themselves behaviour worth pinning, so we drive it against a
// REAL ephemeral fake `sulis-change` script (no mocks at the subprocess
// boundary — MEA-09, the gitShow.test.ts pattern). This proves the spawn,
// the argv passing, the exit-code → typed-outcome mapping, the
// already-present sniff, and the bounded timeout, without depending on the
// real shipped CLI.
describe("SulisChangeRecreator behaviour (against a real fake CLI)", () => {
  let dir: string;

  beforeEach(async () => {
    dir = await realpath(await mkdtemp(join(tmpdir(), "recreator-bin-")));
  });

  afterEach(async () => {
    await rm(dir, { recursive: true, force: true });
  });

  /** Write an executable fake `sulis-change` that behaves as scripted. */
  async function writeFakeCli(body: string): Promise<string> {
    const path = join(dir, "sulis-change");
    await writeFile(path, `#!/usr/bin/env bash\n${body}\n`, "utf8");
    await chmod(path, 0o755);
    return path;
  }

  it("clean exit (fresh materialisation) → { ok: true, alreadyPresent: false }", async () => {
    const binPath = await writeFakeCli(`echo "recreated worktree"; exit 0`);
    const outcome = await new SulisChangeRecreator({ binPath }).recreate(
      "feat-x",
    );
    expect(outcome.ok).toBe(true);
    if (outcome.ok) expect(outcome.alreadyPresent).toBe(false);
  });

  it("clean exit with 'already exists' marker → { ok: true, alreadyPresent: true }", async () => {
    const binPath = await writeFakeCli(
      `echo "worktree already exists"; exit 0`,
    );
    const outcome = await new SulisChangeRecreator({ binPath }).recreate(
      "feat-x",
    );
    expect(outcome.ok).toBe(true);
    if (outcome.ok) expect(outcome.alreadyPresent).toBe(true);
  });

  it("non-zero exit → { ok: false, reason: 'EXEC_FAIL' } carrying stderr", async () => {
    const binPath = await writeFakeCli(`echo "boom" >&2; exit 3`);
    const outcome = await new SulisChangeRecreator({ binPath }).recreate(
      "feat-x",
    );
    expect(outcome.ok).toBe(false);
    if (!outcome.ok) {
      expect(outcome.reason).toBe("EXEC_FAIL");
      expect(outcome.detail).toMatch(/boom/);
    }
  });

  it("missing binary → { ok: false, reason: 'SPAWN_FAIL' }", async () => {
    const outcome = await new SulisChangeRecreator({
      binPath: join(dir, "does-not-exist"),
    }).recreate("feat-x");
    expect(outcome.ok).toBe(false);
    if (!outcome.ok) expect(outcome.reason).toBe("SPAWN_FAIL");
  });

  it("exceeding the timeout → { ok: false, reason: 'TIMEOUT' }, child killed", async () => {
    const binPath = await writeFakeCli(`sleep 5; exit 0`);
    const outcome = await new SulisChangeRecreator({
      binPath,
      timeoutMs: 50,
    }).recreate("feat-x");
    expect(outcome.ok).toBe(false);
    if (!outcome.ok) expect(outcome.reason).toBe("TIMEOUT");
  });
});
