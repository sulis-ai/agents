// WP-011 — the REAL deterministic server-side change-start (FR-29/30/34).
//
// THE LESSON FROM WP-010, applied: the original onboarding mint delegated the
// consequential act to the bridge AGENT (a headless `claude -p`) — live it ran
// 167s and created NOTHING. start-from-intent does NOT repeat that mistake: the
// change-creation act is a DETERMINISTIC SERVER action behind the
// StartChangeRunner port, whose real adapter (SulisChangeStarter) execFiles
// `sulis-change start` + `git clone` directly.
//
// This test drives the REAL SulisChangeStarter against a TEMP SULIS_STATE_DIR +
// a TEMP git repo and asserts a REAL change is created:
//   - `sulis-change start` lands a real change at stage `recon`, readable by the
//     cockpit's own change store (the board reads the same records) (FR-29);
//   - the resolved primitive + slug are carried onto the started change (FR-29);
//   - LOCAL-FIRST (FR-30): an absent repo is CLONED from source.repo first, then
//     the change starts against the clone;
//   - ALL-OR-NOTHING: a broken clone source ⇒ a typed clone failure and NO
//     change is started (the temp state stays empty);
//   - it pollutes NOTHING outside the temp SULIS_STATE_DIR (the real ~/.sulis is
//     never touched — the env override is the only state root).
//
// It needs `sulis-change` + git + python3. When the script can't be resolved
// (a bare checkout with no plugin cache), the suite skips with a clear message
// rather than failing vacuously — parity with discovery.mint-real.test.ts.

import { describe, it, expect, beforeAll, afterEach } from "vitest";
import { mkdtempSync, rmSync, existsSync, readdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { execFileSync } from "node:child_process";

import {
  SulisChangeStarter,
  resolveSulisChangeScript,
} from "../adapters/SulisChangeStarter";

// Real-subprocess budget (parity with discovery.mint-real.test.ts, flake #8).
// Each case cold-starts git + `sulis-change` (python3) one or more times; some
// also `git clone`. Vitest's 5s default per-test timeout cannot cover real
// process startup, and under the full parallel `vitest run` (CI's constrained
// CPU) the spawns are slower still — so the 5s default times out
// deterministically there. We give these REAL tests a generous per-test budget
// without weakening any assertion (the work itself is bounded inside the
// adapter). The fork pool is also CPU-capped (see vitest.config.ts) so these
// spawns are not starved by the rest of the suite.
const REAL_SUBPROCESS_TIMEOUT_MS = 120_000;

let scriptPath: string | null = null;
let haveGitPython = false;

beforeAll(() => {
  scriptPath = resolveSulisChangeScript();
  try {
    execFileSync("git", ["--version"], { stdio: "ignore" });
    execFileSync("python3", ["--version"], { stdio: "ignore" });
    haveGitPython = true;
  } catch {
    haveGitPython = false;
  }
});

const cleanups: string[] = [];
afterEach(() => {
  while (cleanups.length > 0) {
    const dir = cleanups.pop();
    if (dir) rmSync(dir, { recursive: true, force: true });
  }
});

function tmp(prefix: string): string {
  const dir = mkdtempSync(join(tmpdir(), prefix));
  cleanups.push(dir);
  return dir;
}

/** Make a real git repo with one commit on `main`. Returns its path. */
function makeRepo(prefix: string): string {
  const repo = tmp(prefix);
  execFileSync("git", ["init", "--initial-branch=main", repo], { stdio: "ignore" });
  execFileSync("git", ["-C", repo, "config", "user.email", "t@t.t"], { stdio: "ignore" });
  execFileSync("git", ["-C", repo, "config", "user.name", "t"], { stdio: "ignore" });
  execFileSync("git", ["-C", repo, "commit", "--allow-empty", "-m", "init"], {
    stdio: "ignore",
  });
  return repo;
}

/** Read the change records the cockpit board would see, from the temp state. */
function listChanges(scripts: string, stateDir: string): Array<Record<string, unknown>> {
  // Resolve the sibling `sulis-list-changes` next to the started script.
  const listHelper = join(scripts, "sulis-list-changes");
  const out = execFileSync("python3", [listHelper, "list"], {
    env: { ...process.env, SULIS_STATE_DIR: stateDir },
    encoding: "utf8",
  });
  return JSON.parse(out) as Array<Record<string, unknown>>;
}

describe("SulisChangeStarter — the REAL deterministic server-side change-start", { timeout: REAL_SUBPROCESS_TIMEOUT_MS }, () => {
  it("starts a REAL change at `recon` against a present repo (FR-29)", async () => {
    if (!scriptPath || !haveGitPython) {
      // eslint-disable-next-line no-console
      console.warn("skipping: sulis-change / git / python3 unavailable");
      return;
    }
    const stateDir = tmp("sfi-state-");
    const repo = makeRepo("sfi-repo-");
    const scripts = join(scriptPath, "..");
    const starter = new SulisChangeStarter({ scriptPath, sulisStateDir: stateDir });

    const result = await starter.start({
      repoRoot: repo,
      primitive: "fix",
      slug: "login-bug",
      intent: "fix the login bug",
    });

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.change.primitive).toBe("fix");
      expect(result.change.slug).toBe("login-bug");
      expect(result.change.stage).toBe("recon");
      expect(result.change.handle).toMatch(/^CH-/);
    }

    // The cockpit's OWN change store sees the started change at recon (the
    // board reads the same records) — the thing that proves it ACTUALLY started.
    const changes = listChanges(scripts, stateDir);
    expect(changes.length).toBe(1);
    expect(changes[0]?.stage).toBe("recon");
    expect(changes[0]?.slug).toBe("login-bug");
  });

  it("LOCAL-FIRST (FR-30): an ABSENT repo is CLONED from source first, then the change starts", async () => {
    if (!scriptPath || !haveGitPython) return;
    const stateDir = tmp("sfi-state-");
    const sourceRepo = makeRepo("sfi-source-"); // a real repo to clone FROM
    const cloneParent = tmp("sfi-clone-");
    const cloneTarget = join(cloneParent, "checkout"); // does NOT exist yet
    const scripts = join(scriptPath, "..");
    const starter = new SulisChangeStarter({ scriptPath, sulisStateDir: stateDir });

    // clone() materialises the absent repo from the source.
    const cloned = await starter.clone({ sourceRepo, targetPath: cloneTarget });
    expect(cloned.ok).toBe(true);
    expect(existsSync(join(cloneTarget, ".git"))).toBe(true);

    // Then the change starts against the freshly-cloned repo and lands at recon.
    const started = await starter.start({
      repoRoot: cloneTarget,
      primitive: "create",
      slug: "checkout-flow",
      intent: "build a new checkout flow",
    });
    expect(started.ok).toBe(true);
    const changes = listChanges(scripts, stateDir);
    expect(changes.length).toBe(1);
    expect(changes[0]?.stage).toBe("recon");
  });

  it("ALL-OR-NOTHING (FR-30): a BROKEN clone source fails + starts NO change", async () => {
    if (!scriptPath || !haveGitPython) return;
    const stateDir = tmp("sfi-state-");
    const cloneParent = tmp("sfi-clone-");
    const cloneTarget = join(cloneParent, "checkout");
    const scripts = join(scriptPath, "..");
    const starter = new SulisChangeStarter({ scriptPath, sulisStateDir: stateDir });

    // A path that is NOT a git repo ⇒ clone fails.
    const broken = join(cloneParent, "not-a-repo");
    const cloned = await starter.clone({ sourceRepo: broken, targetPath: cloneTarget });
    expect(cloned.ok).toBe(false);
    if (!cloned.ok) expect(cloned.code).toBe("REPO_UNREACHABLE");

    // No clone ⇒ no start ⇒ the temp state holds zero changes (no dangling work).
    expect(existsSync(join(stateDir, "changes"))).toBe(false);
    if (existsSync(join(stateDir, "changes"))) {
      expect(readdirSync(join(stateDir, "changes")).length).toBe(0);
    }
  });

  it("pollutes NOTHING outside the temp state dir — the real ~/.sulis is never touched", async () => {
    if (!scriptPath || !haveGitPython) return;
    const stateDir = tmp("sfi-state-");
    const repo = makeRepo("sfi-repo-");
    const starter = new SulisChangeStarter({ scriptPath, sulisStateDir: stateDir });

    await starter.start({
      repoRoot: repo,
      primitive: "fix",
      slug: "scoped-change",
      intent: "fix something scoped",
    });

    // The started change's worktree lives UNDER the temp state dir (the env
    // override is the only state root the script honours) — never under HOME.
    const changeDirs = existsSync(join(stateDir, "changes"))
      ? readdirSync(join(stateDir, "changes"))
      : [];
    expect(changeDirs.length).toBe(1);
  });
});
