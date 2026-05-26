// WP-003 — Contract test + failure-mode tests for SulisChangeStoreReader.
//
// The adapter is the one place in the cockpit that shells out (TDD §9,
// §13.3; ADR-008). The tests run against the *real* WP-002 Python
// helper at plugins/sulis/scripts/sulis-list-changes by:
//
//   1. Creating a temp directory.
//   2. Seeding change.json + state.json files inside <temp>/changes/<id>/.
//   3. Setting SULIS_STATE_DIR on the spawned helper (the helper
//      honours this env var; the cockpit doesn't see SULIS_STATE_DIR
//      anywhere else).
//
// Per MEA-09: no mocks for the change-store boundary. Real subprocess,
// real fixtures.

import { describe, it, expect, beforeAll, afterEach } from "vitest";
import { promises as fs } from "node:fs";
import fsSync from "node:fs";
import os from "node:os";
import path from "node:path";

import {
  runContract,
  type ContractFixture,
} from "./change-store-reader.contract.test";
import {
  SulisChangeStoreReader,
  ChangeStoreReaderError,
} from "../adapters/SulisChangeStoreReader";

// Resolve the helper path once. The worktree may sit alongside the
// repo (e.g. /Users/.../wp-003-worktree) or be the repo itself; either
// way the helper lives at plugins/sulis/scripts/sulis-list-changes
// inside this worktree.
function helperPath(): string {
  // The repo root is the parent of apps/. Use __dirname which points
  // at server/tests/.
  const here = path.dirname(new URL(import.meta.url).pathname);
  // here = .../apps/cockpit/server/tests
  // repo root = .../
  const repoRoot = path.resolve(here, "..", "..", "..", "..");
  return path.join(repoRoot, "plugins", "sulis", "scripts", "sulis-list-changes");
}

// Seed a temp SULIS_STATE_DIR with the given fixtures.
async function seedStateDir(
  stateDir: string,
  fixtures: ContractFixture[],
): Promise<void> {
  for (const fx of fixtures) {
    const dir = path.join(stateDir, "changes", fx.changeId);
    await fs.mkdir(dir, { recursive: true });
    const record = {
      change_id: fx.changeId,
      handle: fx.handle,
      slug: fx.slug,
      primitive: fx.primitive,
      branch: fx.branch,
      worktree_path: fx.worktreePath,
      intent: fx.intent,
      base_branch: fx.baseBranch,
      base_sha: fx.baseSha,
      created_at: fx.createdAt,
      stage: fx.seedStage,
    };
    await fs.writeFile(
      path.join(dir, "change.json"),
      JSON.stringify(record, null, 2) + "\n",
      "utf8",
    );
    if (fx.liveStage !== undefined) {
      const state = {
        change_id: fx.changeId,
        stage: fx.liveStage,
        updated_at: fx.createdAt,
        stage_history: [{ stage: fx.liveStage, at: fx.createdAt }],
      };
      await fs.writeFile(
        path.join(dir, "state.json"),
        JSON.stringify(state, null, 2) + "\n",
        "utf8",
      );
    }
  }
}

const tempDirs: string[] = [];

async function mkTempStateDir(): Promise<string> {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), "wp003-state-"));
  tempDirs.push(dir);
  return dir;
}

beforeAll(() => {
  // Verify the WP-002 helper actually exists; the adapter test cannot
  // run without it.
  expect(fsSync.existsSync(helperPath())).toBe(true);
});

runContract("SulisChangeStoreReader", {
  setup: async (fixtures) => {
    const stateDir = await mkTempStateDir();
    await seedStateDir(stateDir, fixtures);
    return new SulisChangeStoreReader({
      helperPath: helperPath(),
      sulisStateDir: stateDir,
    });
  },
  teardown: async () => {
    while (tempDirs.length > 0) {
      const d = tempDirs.pop();
      if (d) {
        await fs.rm(d, { recursive: true, force: true });
      }
    }
  },
});

// ─── Failure-mode tests (TDD §13.3, §13.6) ─────────────────────────────

describe("SulisChangeStoreReader — spawn failure (EXEC_FAIL)", () => {
  it("throws ChangeStoreReaderError with code 'EXEC_FAIL' for a bogus helperPath", async () => {
    const stateDir = await mkTempStateDir();
    const reader = new SulisChangeStoreReader({
      helperPath: "/nonexistent/path/to/sulis-list-changes",
      sulisStateDir: stateDir,
    });
    let err: unknown;
    try {
      await reader.listAllChanges();
    } catch (e) {
      err = e;
    }
    expect(err).toBeInstanceOf(ChangeStoreReaderError);
    expect((err as ChangeStoreReaderError).code).toBe("EXEC_FAIL");
  });

  afterEachCleanup();
});

describe("SulisChangeStoreReader — timeout (TIMEOUT)", () => {
  it("throws ChangeStoreReaderError with code 'TIMEOUT' when the helper exceeds timeoutMs", async () => {
    // Stand up a tiny stub helper that sleeps for 500ms — well above
    // the test's 50ms timeout. Sleep in pure shell so we don't rely
    // on Python's startup time.
    const stubDir = await mkTempStateDir();
    const stub = path.join(stubDir, "slow-helper.sh");
    await fs.writeFile(
      stub,
      "#!/bin/sh\nsleep 0.5\necho '[]'\n",
      "utf8",
    );
    await fs.chmod(stub, 0o755);

    const reader = new SulisChangeStoreReader({
      helperPath: stub,
      sulisStateDir: stubDir,
      timeoutMs: 50,
    });

    let err: unknown;
    try {
      await reader.listAllChanges();
    } catch (e) {
      err = e;
    }
    expect(err).toBeInstanceOf(ChangeStoreReaderError);
    expect((err as ChangeStoreReaderError).code).toBe("TIMEOUT");
  });

  afterEachCleanup();
});

describe("SulisChangeStoreReader — malformed JSON (PARSE_ERROR)", () => {
  it("throws ChangeStoreReaderError with code 'PARSE_ERROR' when the helper emits non-JSON stdout", async () => {
    // Stand up a stub helper that exits 0 but prints non-JSON. The
    // adapter's parse step must convert that to a typed PARSE_ERROR
    // rather than letting JSON.parse's SyntaxError leak out.
    const stubDir = await mkTempStateDir();
    const stub = path.join(stubDir, "garbage-helper.sh");
    await fs.writeFile(
      stub,
      "#!/bin/sh\necho 'not json at all'\n",
      "utf8",
    );
    await fs.chmod(stub, 0o755);

    const reader = new SulisChangeStoreReader({
      helperPath: stub,
      sulisStateDir: stubDir,
    });

    let err: unknown;
    try {
      await reader.listAllChanges();
    } catch (e) {
      err = e;
    }
    expect(err).toBeInstanceOf(ChangeStoreReaderError);
    expect((err as ChangeStoreReaderError).code).toBe("PARSE_ERROR");
  });

  afterEachCleanup();
});

describe("SulisChangeStoreReader — source inventory (TDD §13.3)", () => {
  it("uses spawn (not exec); never shell:true", async () => {
    const adapterSrc = path.resolve(
      path.dirname(new URL(import.meta.url).pathname),
      "..",
      "adapters",
      "SulisChangeStoreReader.ts",
    );
    const src = await fs.readFile(adapterSrc, "utf8");
    // The adapter MUST NOT use shell:true or any exec() shape.
    expect(src).not.toMatch(/shell:\s*true/);
    expect(src).not.toMatch(/\bexec\s*\(/);
    expect(src).not.toMatch(/\bexecSync\s*\(/);
    expect(src).not.toMatch(/\bexecFile\s*\(/);
    // It MUST use spawn.
    expect(src).toMatch(/\bspawn\s*\(/);
  });
});

// Helper: register an afterEach cleanup inside any describe block.
// Called from inside a `describe()` so the hook is scoped to that suite.
function afterEachCleanup(): void {
  afterEach(async () => {
    while (tempDirs.length > 0) {
      const d = tempDirs.pop();
      if (d) {
        await fs.rm(d, { recursive: true, force: true });
      }
    }
  });
}
