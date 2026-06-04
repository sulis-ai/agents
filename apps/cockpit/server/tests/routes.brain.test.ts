// WP-006 — GET /api/changes/:id/brain route tests (FR-06/07).
//
// Drives the app through supertest (no real port bind) with a
// FakeChangeStoreReader pointed at a temp worktree that holds a seeded
// `.brain/instances/<domain>/<kind>/*.jsonld` tree (the shape the
// seed-brain-entities-fixture provides in CI). The route composes the
// existing change-lookup (404 for an unknown id) with the new readBrain
// projection — no new port (TDD §2.1). GET-only; reading it starts no
// process (FR-N4) — the read-only gate proves no mutation verb here.
//
//   - 200 + BrainView (groups by kind, empty groups omitted) for a change
//     whose worktree has brain entities.
//   - 200 + { groups: [] } for a change with no brain entities (FR-06).
//   - 404 + { code: "NOT_FOUND" } for an unknown change id.
//   - 405 for a POST (read-only).

import { describe, it, expect } from "vitest";
import request from "supertest";
import { mkdtemp, mkdir, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { createApp } from "../app";
import { FakeChangeStoreReader } from "../adapters/FakeChangeStoreReader";
import type { ChangeStoreRecord } from "../ports/ChangeStoreReader";
import type { BrainView } from "../../shared/api-types";

function record(overrides: Partial<ChangeStoreRecord> = {}): ChangeStoreRecord {
  return {
    changeId: "01ABC",
    handle: "CH-01ABC",
    slug: "demo",
    primitive: "create",
    branch: "change/demo",
    worktreePath: "/tmp/never-used-in-this-test",
    intent: "demo change",
    baseBranch: "main",
    baseSha: "deadbeef",
    createdAt: "2026-05-01T00:00:00Z",
    updatedAt: "2026-05-02T00:00:00Z",
    stage: "design",
    ...overrides,
  };
}

async function seedBrain(worktreeRoot: string): Promise<void> {
  const write = async (
    domain: string,
    kind: string,
    ulid: string,
    body: Record<string, unknown>,
  ) => {
    const dir = join(worktreeRoot, ".brain", "instances", domain, kind);
    await mkdir(dir, { recursive: true });
    await writeFile(join(dir, `${ulid}.jsonld`), JSON.stringify(body), "utf8");
  };
  await write("product-development", "requirement", "01R1", {
    id: "dna:requirement:01R1",
    title: "Board lists changes in stage columns",
  });
  await write("product-development", "requirement", "01R2", {
    id: "dna:requirement:01R2",
    title: "Send a message to a change's agent",
  });
  await write("product-development", "decision", "01D1", {
    id: "dna:decision:01D1",
    decision: "Path A — canonical-as-spec",
  });
}

describe("GET /api/changes/:id/brain (FR-06/07)", () => {
  it("returns 200 + a BrainView grouped by kind for a change with entities", async () => {
    const worktree = await mkdtemp(join(tmpdir(), "cockpit-brain-wt-"));
    await seedBrain(worktree);
    const reader = new FakeChangeStoreReader([
      record({ changeId: "01XYZ", worktreePath: worktree }),
    ]);
    try {
      const app = createApp({
        changeStore: reader,
        sulisStateDir: "/tmp/never",
        claudeProjectsDir: "/tmp/never",
      });
      const res = await request(app).get("/api/changes/01XYZ/brain");
      expect(res.status).toBe(200);
      expect(res.headers["content-type"]).toMatch(/application\/json/);
      const body = res.body as BrainView;
      expect(body.changeId).toBe("01XYZ");
      const group = (kind: string) => body.groups.find((g) => g.kind === kind)!;
      expect(group("requirement").items).toHaveLength(2);
      expect(group("decision").items).toHaveLength(1);
      // Every item carries the fields the detail view needs (FR-07).
      const first = group("requirement").items[0]!;
      expect(first.title.length).toBeGreaterThan(0);
      expect(first.id).toMatch(/^dna:requirement:/);
    } finally {
      await rm(worktree, { recursive: true, force: true });
    }
  });

  it("returns 200 + { groups: [] } for a change with no brain entities", async () => {
    const worktree = await mkdtemp(join(tmpdir(), "cockpit-brain-wt-"));
    const reader = new FakeChangeStoreReader([
      record({ changeId: "01EMPTY", worktreePath: worktree }),
    ]);
    try {
      const app = createApp({
        changeStore: reader,
        sulisStateDir: "/tmp/never",
        claudeProjectsDir: "/tmp/never",
      });
      const res = await request(app).get("/api/changes/01EMPTY/brain");
      expect(res.status).toBe(200);
      const body = res.body as BrainView;
      expect(body.changeId).toBe("01EMPTY");
      expect(body.groups).toEqual([]);
    } finally {
      await rm(worktree, { recursive: true, force: true });
    }
  });

  it("returns 404 + NOT_FOUND for an unknown change id", async () => {
    const reader = new FakeChangeStoreReader([]);
    const app = createApp({
      changeStore: reader,
      sulisStateDir: "/tmp/never",
      claudeProjectsDir: "/tmp/never",
    });
    const res = await request(app).get("/api/changes/does-not-exist/brain");
    expect(res.status).toBe(404);
    const body = res.body as { error: string; code: string };
    expect(body.code).toBe("NOT_FOUND");
    expect(body.error.length).toBeGreaterThan(0);
  });

  it("rejects a POST to the brain route (read-only; 405)", async () => {
    const worktree = await mkdtemp(join(tmpdir(), "cockpit-brain-wt-"));
    const reader = new FakeChangeStoreReader([
      record({ changeId: "01XYZ", worktreePath: worktree }),
    ]);
    try {
      const app = createApp({
        changeStore: reader,
        sulisStateDir: "/tmp/never",
        claudeProjectsDir: "/tmp/never",
      });
      const res = await request(app).post("/api/changes/01XYZ/brain");
      expect(res.status).toBe(405);
    } finally {
      await rm(worktree, { recursive: true, force: true });
    }
  });
});
