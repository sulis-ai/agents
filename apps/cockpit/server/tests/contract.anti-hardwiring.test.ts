// WP-003 — anti-hard-wiring acceptance (RELEASE GATE · MUST · ADR-003 / TDD §4.4).
//
// The trust property of the whole feature: open the cockpit, walk EVERY
// in-flight change, and confirm each surfaces its OWN data + UI contracts —
// resolution is generic, never hard-wired to a specific change. This is an
// automated encoding of the founder's explicit release-acceptance walk
// (multiple changes in the fixture, each resolving to its own artifacts).
//
// It also pins the security shape-guard at the serving boundary: a malformed
// change handle (the argparse flag-confusion vector) must yield a typed
// failure WITHOUT ever spawning recreate.

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import request from "supertest";
import { mkdtemp, rm, writeFile, mkdir, realpath } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { createApp } from "../app";
import { FakeChangeStoreReader } from "../adapters/FakeChangeStoreReader";
import { FakeRecreateRunner } from "../adapters/FakeRecreateRunner";
import type { ChangeStoreRecord } from "../ports/ChangeStoreReader";

function record(overrides: Partial<ChangeStoreRecord> = {}): ChangeStoreRecord {
  return {
    changeId: "01ABC",
    handle: "feat-demo",
    slug: "demo",
    primitive: "create",
    branch: "change/demo",
    worktreePath: "/tmp/never",
    intent: "demo",
    baseBranch: "main",
    baseSha: "deadbeef",
    shippedSha: null,
    createdAt: "2026-05-01T00:00:00Z",
    updatedAt: "2026-05-01T00:00:00Z",
    stage: "design",
    ...overrides,
  };
}

/** Seed a change's own worktree with artifacts that NAME the change, so we
 *  can prove each change resolves to ITS OWN artifacts (not a shared one). */
async function seedFor(worktree: string, label: string): Promise<void> {
  await mkdir(worktree, { recursive: true });
  await writeFile(
    join(worktree, "CONTRACT.html"),
    `<!doctype html><title>${label}</title><h1>Contract for ${label}</h1>`,
    "utf8",
  );
  await writeFile(
    join(worktree, "UI.html"),
    `<!doctype html><title>${label} UI</title><h1>UI for ${label}</h1>`,
    "utf8",
  );
  await writeFile(
    join(worktree, "CONTRACT.manifest.json"),
    JSON.stringify({
      data_contract: { format: "servicespec", name: label, contracts: [] },
      contract_html: join(worktree, "CONTRACT.html"),
      ui_contract: "present",
      path: join(worktree, "UI.html"),
    }),
    "utf8",
  );
}

describe("anti-hard-wiring acceptance (walk every change → own contracts)", () => {
  let tmpRoot: string;

  beforeEach(async () => {
    tmpRoot = await realpath(await mkdtemp(join(tmpdir(), "anti-hardwire-")));
  });
  afterEach(async () => {
    await rm(tmpRoot, { recursive: true, force: true });
  });

  it("every in-flight change surfaces ITS OWN data + UI contracts (no change is hard-wired)", async () => {
    // Three distinct changes, each with its own worktree + artifacts.
    const specs = [
      {
        id: "01ALPHA000000000000000000A",
        handle: "feat-alpha",
        label: "alpha",
      },
      { id: "01BETA0000000000000000000B", handle: "fix-beta", label: "beta" },
      {
        id: "01GAMMA000000000000000000C",
        handle: "chore-gamma",
        label: "gamma",
      },
    ];
    const records: ChangeStoreRecord[] = [];
    for (const s of specs) {
      const wt = join(tmpRoot, s.label);
      await seedFor(wt, s.label);
      records.push(
        record({
          changeId: s.id,
          handle: s.handle,
          worktreePath: wt,
          slug: s.label,
        }),
      );
    }

    const reader = new FakeChangeStoreReader(records);
    const runner = new FakeRecreateRunner({ ok: true, alreadyPresent: true });
    const app = createApp({
      changeStore: reader,
      recreateRunner: runner,
      sulisStateDir: "/tmp/never",
      claudeProjectsDir: "/tmp/never",
    });

    // Walk EVERY change. Each must resolve to ITS OWN artifacts.
    for (const s of specs) {
      const data = await request(app).get(`/api/changes/${s.id}/contract/data`);
      expect(data.status).toBe(200);
      expect(data.text).toContain(`Contract for ${s.label}`);
      // Crucially: it must NOT contain another change's label.
      for (const other of specs) {
        if (other.label !== s.label) {
          expect(data.text).not.toContain(`Contract for ${other.label}`);
        }
      }

      const ui = await request(app).get(`/api/changes/${s.id}/contract/ui`);
      expect(ui.status).toBe(200);
      expect(ui.text).toContain(`UI for ${s.label}`);
    }
  });

  it("shape-guard: a malformed handle (leading '-') yields a typed failure and NEVER spawns recreate", async () => {
    // The worktree is absent → the serving path would normally try recreate.
    // But the handle is a flag-confusion shape, so the guard must reject it
    // BEFORE any spawn.
    const runner = new FakeRecreateRunner({ ok: true, alreadyPresent: false });
    const rec = record({
      changeId: "01MALFORMED00000000000000A",
      handle: "-rf", // flag-confusion vector
      worktreePath: join(tmpRoot, "absent-wt"),
      shippedSha: "deadbeefcafe", // would be recreatable IF the handle were safe
      stage: "shipped",
    });
    const reader = new FakeChangeStoreReader([rec]);
    const app = createApp({
      changeStore: reader,
      recreateRunner: runner,
      sulisStateDir: "/tmp/never",
      claudeProjectsDir: "/tmp/never",
    });

    const res = await request(app).get(
      "/api/changes/01MALFORMED00000000000000A/contract",
    );

    // Typed failure surfaced to the client; never a raw 500, never a spawn.
    expect(res.status).toBe(200);
    const body = res.body as { status: string; note?: string };
    expect(body.status).toBe("unavailable");
    // The guard refused to spawn on the malformed handle.
    expect(runner.calls).toEqual([]);
  });
});
