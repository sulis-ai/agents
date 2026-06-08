// WP-P05 — GET /api/changes/:id/provenance route tests (ADR-011).
//
// Drives the app through supertest (no real port bind) with a
// FakeChangeStoreReader pointed at a temp worktree that holds a seeded
// `.brain/instances/<domain>/<kind>/*.jsonld` tree. The route composes the
// existing change-lookup (404 for an unknown id) with the new readProvenance
// projection — no new port (ADR-011, EP-03). GET-only; reading it starts no
// process (NFR-SEC-05 parity) — the read-only gate proves no mutation here.
//
//   - 200 + ProvenanceView (digest + run-log + coverage) for a populated brain.
//   - 200 + empty dashboard (digest all-zero, empty lenses) for an empty brain.
//   - 200 + FocusedTrace for the `?focus=<reqId>` variant.
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
import type { ProvenanceView, FocusedTrace } from "../../shared/api-types";

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
    kind: string,
    ulid: string,
    body: Record<string, unknown>,
  ) => {
    const dir = join(
      worktreeRoot,
      ".brain",
      "instances",
      "product-development",
      kind,
    );
    await mkdir(dir, { recursive: true });
    await writeFile(join(dir, `${ulid}.jsonld`), JSON.stringify(body), "utf8");
  };
  await write("opportunity", "OPP1", {
    id: "dna:opportunity:OPP1",
    title: "Founders lose track of what the agent did",
  });
  await write("requirement", "REQ1", {
    id: "dna:requirement:REQ1",
    title: "Show a digest",
    source: "dna:opportunity:OPP1",
  });
  await write("design", "DES1", {
    id: "dna:design:DES1",
    title: "Provenance read projection",
    satisfies: ["dna:requirement:REQ1"],
    decisions: ["dna:decision:DEC1"],
  });
  await write("decision", "DEC1", {
    id: "dna:decision:DEC1",
    title: "Compose readBrain",
  });
  await write("testresult", "TR1", {
    id: "dna:testresult:TR1",
    title: "Digest passes",
    outcome: "pass",
    verifies: ["dna:requirement:REQ1"],
  });
  await write("lifecyclerun", "RUN1", {
    id: "dna:lifecyclerun:RUN1",
    step_name: "faithful-generation-harness",
    at: "2026-06-02T00:00:00Z",
    outcome: "completed",
    confidence: 0.88,
    _final_verdict: "partial-unattributed",
    _step_runs: [{ step: "observe-manifest", outcome: "completed" }],
    _gaps: [{ claim: "rule-3 ...", reason: "no docs source supports it" }],
    _self_critique: "REFUSED to bind rule-3 to an org-scoped source.",
  });
}

function app(reader: FakeChangeStoreReader) {
  return createApp({
    changeStore: reader,
    sulisStateDir: "/tmp/never",
    claudeProjectsDir: "/tmp/never",
  });
}

describe("GET /api/changes/:id/provenance (ADR-011)", () => {
  it("returns 200 + a ProvenanceView (digest + run-log + coverage) for a populated brain", async () => {
    const worktree = await mkdtemp(join(tmpdir(), "cockpit-prov-wt-"));
    await seedBrain(worktree);
    const reader = new FakeChangeStoreReader([
      record({ changeId: "01XYZ", worktreePath: worktree }),
    ]);
    try {
      const res = await request(app(reader)).get(
        "/api/changes/01XYZ/provenance",
      );
      expect(res.status).toBe(200);
      expect(res.headers["content-type"]).toMatch(/application\/json/);
      const body = res.body as ProvenanceView;
      expect(body.changeId).toBe("01XYZ");
      expect(body.digest.did).toBe(1);
      expect(body.digest.covered).toEqual({ verified: 1, total: 1 });
      expect(body.digest.decided).toBe(1);
      expect(body.digest.flagged.count).toBe(1);
      expect(body.digest.flagged.selfCritique).toContain("REFUSED");
      expect(body.runLog).toHaveLength(1);
      expect(body.runLog[0]!.steps).toHaveLength(1);
      expect(body.coverage.map((c) => c.axis).sort()).toEqual([
        "how",
        "tested",
        "what",
        "why",
      ]);
    } finally {
      await rm(worktree, { recursive: true, force: true });
    }
  });

  it("returns 200 + an empty dashboard for a change with no brain entities", async () => {
    const worktree = await mkdtemp(join(tmpdir(), "cockpit-prov-wt-"));
    const reader = new FakeChangeStoreReader([
      record({ changeId: "01EMPTY", worktreePath: worktree }),
    ]);
    try {
      const res = await request(app(reader)).get(
        "/api/changes/01EMPTY/provenance",
      );
      expect(res.status).toBe(200);
      const body = res.body as ProvenanceView;
      expect(body).toEqual({
        changeId: "01EMPTY",
        digest: {
          did: 0,
          covered: { verified: 0, total: 0 },
          decided: 0,
          flagged: { count: 0, topGap: null, selfCritique: null },
        },
        runLog: [],
        coverage: [],
      });
    } finally {
      await rm(worktree, { recursive: true, force: true });
    }
  });

  it("returns 200 + a FocusedTrace for the ?focus=<reqId> variant", async () => {
    const worktree = await mkdtemp(join(tmpdir(), "cockpit-prov-wt-"));
    await seedBrain(worktree);
    const reader = new FakeChangeStoreReader([
      record({ changeId: "01XYZ", worktreePath: worktree }),
    ]);
    try {
      const res = await request(app(reader)).get(
        "/api/changes/01XYZ/provenance?focus=dna:requirement:REQ1",
      );
      expect(res.status).toBe(200);
      const body = res.body as FocusedTrace;
      expect(body.requirementId).toBe("dna:requirement:REQ1");
      expect(body.why).toContainEqual({
        id: "dna:opportunity:OPP1",
        title: "Founders lose track of what the agent did",
      });
      expect(body.how.some((h) => h.kind === "design")).toBe(true);
      expect(body.tested.some((t) => t.outcome === "pass")).toBe(true);
    } finally {
      await rm(worktree, { recursive: true, force: true });
    }
  });

  it("returns 404 for the ?focus= variant when the requirement is unknown", async () => {
    const worktree = await mkdtemp(join(tmpdir(), "cockpit-prov-wt-"));
    await seedBrain(worktree);
    const reader = new FakeChangeStoreReader([
      record({ changeId: "01XYZ", worktreePath: worktree }),
    ]);
    try {
      const res = await request(app(reader)).get(
        "/api/changes/01XYZ/provenance?focus=dna:requirement:NOPE",
      );
      expect(res.status).toBe(404);
      const body = res.body as { code: string };
      expect(body.code).toBe("NOT_FOUND");
    } finally {
      await rm(worktree, { recursive: true, force: true });
    }
  });

  it("returns 404 + NOT_FOUND for an unknown change id", async () => {
    const reader = new FakeChangeStoreReader([]);
    const res = await request(app(reader)).get(
      "/api/changes/does-not-exist/provenance",
    );
    expect(res.status).toBe(404);
    const body = res.body as { error: string; code: string };
    expect(body.code).toBe("NOT_FOUND");
    expect(body.error.length).toBeGreaterThan(0);
  });

  it("rejects a POST to the provenance route (read-only; 405)", async () => {
    const worktree = await mkdtemp(join(tmpdir(), "cockpit-prov-wt-"));
    const reader = new FakeChangeStoreReader([
      record({ changeId: "01XYZ", worktreePath: worktree }),
    ]);
    try {
      const res = await request(app(reader)).post(
        "/api/changes/01XYZ/provenance",
      );
      expect(res.status).toBe(405);
    } finally {
      await rm(worktree, { recursive: true, force: true });
    }
  });
});
