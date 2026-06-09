// WP-002 — readTestsState.ts unit tests (BR-10 / BR-11).
//
// Best-effort read of the change's recorded CI/test state. The cockpit
// reads it; it never writes one. The recorded signal is a small JSON
// sidecar inside the change's own worktree at `.sulis/ci-state.json`
// (the same sidecar discipline `session.json` already uses), shape
// `{ "state": "green" | "red" }`. The reader resolves it to:
//   - "green" / "red" when the sidecar records that state,
//   - "unknown" on every other path: no sidecar, malformed JSON, an
//     unexpected/absent `state` value, a gone worktree.
//
// Read-only + never-throws (BR-11): a board must never 500 because one
// change's test-state sidecar is missing or garbage.

import { describe, it, expect } from "vitest";
import { mkdtemp, rm, mkdir, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { readTestsState } from "../lib/readTestsState";

async function makeWorktree(): Promise<string> {
  return await mkdtemp(join(tmpdir(), "wt-tests-"));
}

async function seedCiState(wt: string, body: string): Promise<void> {
  const dir = join(wt, ".sulis");
  await mkdir(dir, { recursive: true });
  await writeFile(join(dir, "ci-state.json"), body, "utf8");
}

describe("readTestsState (BR-10)", () => {
  it("reads green from the recorded sidecar", async () => {
    const wt = await makeWorktree();
    try {
      await seedCiState(wt, JSON.stringify({ state: "green" }));
      expect(await readTestsState(wt)).toBe("green");
    } finally {
      await rm(wt, { recursive: true, force: true });
    }
  });

  it("reads red from the recorded sidecar", async () => {
    const wt = await makeWorktree();
    try {
      await seedCiState(wt, JSON.stringify({ state: "red" }));
      expect(await readTestsState(wt)).toBe("red");
    } finally {
      await rm(wt, { recursive: true, force: true });
    }
  });
});

describe("readTestsState — unknown on absence/garbage (BR-11)", () => {
  it("no .sulis sidecar → unknown", async () => {
    const wt = await makeWorktree();
    try {
      expect(await readTestsState(wt)).toBe("unknown");
    } finally {
      await rm(wt, { recursive: true, force: true });
    }
  });

  it("malformed JSON → unknown (never throws)", async () => {
    const wt = await makeWorktree();
    try {
      await seedCiState(wt, "{ not json");
      expect(await readTestsState(wt)).toBe("unknown");
    } finally {
      await rm(wt, { recursive: true, force: true });
    }
  });

  it("an unexpected state value → unknown", async () => {
    const wt = await makeWorktree();
    try {
      await seedCiState(wt, JSON.stringify({ state: "purple" }));
      expect(await readTestsState(wt)).toBe("unknown");
    } finally {
      await rm(wt, { recursive: true, force: true });
    }
  });

  it("a missing state field → unknown", async () => {
    const wt = await makeWorktree();
    try {
      await seedCiState(wt, JSON.stringify({ other: 1 }));
      expect(await readTestsState(wt)).toBe("unknown");
    } finally {
      await rm(wt, { recursive: true, force: true });
    }
  });

  it("a non-existent worktree → unknown (never throws)", async () => {
    expect(await readTestsState("/tmp/does-not-exist-wp002-tests")).toBe(
      "unknown",
    );
  });
});
