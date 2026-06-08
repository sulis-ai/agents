// WP-008 — products route + Product-scoped board/search (FR-37, FR-38, ADR-009).
//
// Drives the app through supertest (no real port bind). Seeds the Tenant's
// Products + Projects into a temp brain and the matching changes into a
// FakeChangeStoreReader, then asserts:
//   - GET /api/products lists the Products, marks one active.
//   - GET /api/changes?product=<id> returns ONLY that Product's changes
//     (server-side roll-up; no other Product's change leaks).
//   - GET /api/search?product=<id> honours the same scope.
//   - the single-Product trivial case returns all changes.
//
// DECISION (ADR-009 builder's choice): the `?product=` query-param variant —
// the seam stays all-GET, the read-only gate needs NO change, there is no
// POST /api/products/active. The active Product is the client's UI scope,
// passed as a query param on each read; the roll-up is server-side either way.
//
// The change→Project→Product roll-up keys on the change's worktree path
// falling under a Project's `source.path` (`change → Project → Product`); a
// change under no known Project rolls up to the single implicit Product.

import { describe, it, expect } from "vitest";
import request from "supertest";
import { mkdtemp, mkdir, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { createApp } from "../app";
import { FakeChangeStoreReader } from "../adapters/FakeChangeStoreReader";
import type { ChangeStoreRecord } from "../ports/ChangeStoreReader";

const ACME_ULID = "01ACME00000000000000000000";
const HELP_ULID = "01HELP00000000000000000000";
const ACME = `dna:product:${ACME_ULID}`;
const HELP = `dna:product:${HELP_ULID}`;

function record(overrides: Partial<ChangeStoreRecord> = {}): ChangeStoreRecord {
  return {
    changeId: "01ABC",
    handle: "CH-01ABC",
    slug: "demo",
    primitive: "create",
    branch: "change/demo",
    worktreePath: "/tmp/x",
    intent: "demo change",
    baseBranch: "main",
    baseSha: "deadbeef",
    createdAt: "2026-05-01T00:00:00Z",
    updatedAt: "2026-05-01T00:00:00Z",
    stage: "specify",
    ...overrides,
  };
}

async function seedEntity(
  stateDir: string,
  domain: string,
  kind: string,
  ulid: string,
  body: Record<string, unknown>,
): Promise<void> {
  const d = join(stateDir, ".brain", "instances", domain, kind);
  await mkdir(d, { recursive: true });
  await writeFile(join(d, `${ulid}.jsonld`), JSON.stringify(body), "utf8");
}

/**
 * Seed two Products, each with one Project whose source.path roots the
 * worktrees of that Product's changes. Returns the two repo roots so the
 * change records can be placed under them.
 */
async function seedTwoProducts(stateDir: string): Promise<{
  acmeRoot: string;
  helpRoot: string;
}> {
  const acmeRoot = join(stateDir, "repos", "acme");
  const helpRoot = join(stateDir, "repos", "help");

  await seedEntity(stateDir, "product-development", "product", ACME_ULID, {
    id: ACME,
    name: "Acme Checkout",
    sys_status: "active",
  });
  await seedEntity(stateDir, "product-development", "product", HELP_ULID, {
    id: HELP,
    name: "Helpdesk",
    sys_status: "active",
  });
  await seedEntity(stateDir, "foundation", "project", "01ACMEPROJ0000000000000000", {
    id: "dna:project:01ACMEPROJ0000000000000000",
    name: "acme-app",
    belongs_to_product_ref: ACME_ULID,
    source: JSON.stringify({ repo: acmeRoot, path: acmeRoot, primary_branch: "main" }),
    sys_status: "active",
  });
  await seedEntity(stateDir, "foundation", "project", "01HELPPROJ0000000000000000", {
    id: "dna:project:01HELPPROJ0000000000000000",
    name: "help-app",
    belongs_to_product_ref: HELP_ULID,
    source: JSON.stringify({ repo: helpRoot, path: helpRoot, primary_branch: "main" }),
    sys_status: "active",
  });
  return { acmeRoot, helpRoot };
}

describe("GET /api/products (FR-38)", () => {
  it("lists the Tenant's Products with one marked active", async () => {
    const tmpState = await mkdtemp(join(tmpdir(), "cockpit-state-"));
    try {
      await seedTwoProducts(tmpState);
      const app = createApp({
        changeStore: new FakeChangeStoreReader([]),
        sulisStateDir: tmpState,
        claudeProjectsDir: "/tmp/never",
      });
      const res = await request(app).get("/api/products");
      expect(res.status).toBe(200);
      const body = res.body as {
        products: Array<{ productId: string; name: string; active?: boolean }>;
        activeProductId: string | null;
      };
      expect(body.products.map((p) => p.name).sort()).toEqual([
        "Acme Checkout",
        "Helpdesk",
      ]);
      const active = body.products.filter((p) => p.active);
      expect(active).toHaveLength(1);
      expect(body.activeProductId).toBe(active[0]?.productId);
    } finally {
      await rm(tmpState, { recursive: true, force: true });
    }
  });

  it("returns one implicit Product (active) when the brain has none — the single-Product trivial case", async () => {
    const tmpState = await mkdtemp(join(tmpdir(), "cockpit-state-"));
    try {
      const app = createApp({
        changeStore: new FakeChangeStoreReader([]),
        sulisStateDir: tmpState,
        claudeProjectsDir: "/tmp/never",
      });
      const res = await request(app).get("/api/products");
      expect(res.status).toBe(200);
      const body = res.body as {
        products: Array<{ productId: string; active?: boolean }>;
        activeProductId: string | null;
      };
      expect(body.products).toHaveLength(1);
      expect(body.products[0]?.active).toBe(true);
      expect(body.activeProductId).toBe(body.products[0]?.productId);
    } finally {
      await rm(tmpState, { recursive: true, force: true });
    }
  });
});

describe("GET /api/changes?product= — server-side roll-up (FR-37)", () => {
  it("returns ONLY the active Product's changes; no other Product's change leaks", async () => {
    const tmpState = await mkdtemp(join(tmpdir(), "cockpit-state-"));
    try {
      const { acmeRoot, helpRoot } = await seedTwoProducts(tmpState);
      const reader = new FakeChangeStoreReader([
        record({ changeId: "01A1", worktreePath: join(acmeRoot, "01A1", "worktree"), createdAt: "2026-05-10T00:00:00Z" }),
        record({ changeId: "01H1", worktreePath: join(helpRoot, "01H1", "worktree"), createdAt: "2026-05-09T00:00:00Z" }),
        record({ changeId: "01A2", worktreePath: join(acmeRoot, "01A2", "worktree"), createdAt: "2026-05-08T00:00:00Z" }),
      ]);
      const app = createApp({
        changeStore: reader,
        sulisStateDir: tmpState,
        claudeProjectsDir: "/tmp/never",
      });

      const acme = await request(app).get(`/api/changes?product=${encodeURIComponent(ACME)}`);
      expect(acme.status).toBe(200);
      expect((acme.body as Array<{ changeId: string }>).map((c) => c.changeId).sort()).toEqual(["01A1", "01A2"]);

      const help = await request(app).get(`/api/changes?product=${encodeURIComponent(HELP)}`);
      expect(help.status).toBe(200);
      const helpIds = (help.body as Array<{ changeId: string }>).map((c) => c.changeId);
      expect(helpIds).toEqual(["01H1"]);
      // The switch: no Acme change appears in the Helpdesk scope (FR-37).
      expect(helpIds.some((id) => id.startsWith("01A"))).toBe(false);
    } finally {
      await rm(tmpState, { recursive: true, force: true });
    }
  });

  it("returns all changes for the single-Product trivial case (no ?product=)", async () => {
    const tmpState = await mkdtemp(join(tmpdir(), "cockpit-state-"));
    try {
      const reader = new FakeChangeStoreReader([
        record({ changeId: "01AAA", createdAt: "2026-05-10T00:00:00Z" }),
        record({ changeId: "01BBB", createdAt: "2026-05-01T00:00:00Z" }),
      ]);
      const app = createApp({
        changeStore: reader,
        sulisStateDir: tmpState,
        claudeProjectsDir: "/tmp/never",
      });
      const res = await request(app).get("/api/changes");
      expect(res.status).toBe(200);
      expect((res.body as Array<{ changeId: string }>).map((c) => c.changeId).sort()).toEqual(["01AAA", "01BBB"]);
    } finally {
      await rm(tmpState, { recursive: true, force: true });
    }
  });
});

describe("GET /api/search?product= — search stays within the active Product (FR-37/38)", () => {
  it("a search never surfaces another Product's change", async () => {
    const tmpState = await mkdtemp(join(tmpdir(), "cockpit-state-"));
    try {
      const { acmeRoot, helpRoot } = await seedTwoProducts(tmpState);
      const reader = new FakeChangeStoreReader([
        record({ changeId: "01A1", intent: "checkout flow work", worktreePath: join(acmeRoot, "01A1", "worktree"), createdAt: "2026-05-10T00:00:00Z" }),
        record({ changeId: "01H1", intent: "checkout flow work", worktreePath: join(helpRoot, "01H1", "worktree"), createdAt: "2026-05-09T00:00:00Z" }),
      ]);
      const app = createApp({
        changeStore: reader,
        sulisStateDir: tmpState,
        claudeProjectsDir: "/tmp/never",
      });
      // Both changes match "checkout" by content, but the search is scoped to Acme.
      const res = await request(app).get(`/api/search?product=${encodeURIComponent(ACME)}&q=checkout`);
      expect(res.status).toBe(200);
      const ids = (res.body as { results: Array<{ changeId: string }> }).results.map((c) => c.changeId);
      expect(ids).toEqual(["01A1"]);
      expect(ids).not.toContain("01H1");
    } finally {
      await rm(tmpState, { recursive: true, force: true });
    }
  });
});
