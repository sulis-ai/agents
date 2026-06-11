// WP-003 — GET /api/changes/:id/contract{,/data,/ui} route tests
// (TDD §2.1, §4.3; ADR-001 read-only, ADR-003 generic, ADR-004 recreate).
//
// Three GET-only endpoints serve the rendered artifacts the renderers
// (WP-001/002) write into a change's worktree, resolved generically by
// `:id` via the existing ChangeStoreReader port + the WP-004 recreate-on-
// demand resolver:
//
//   GET /api/changes/:id/contract       → ContractAvailability summary
//                                          (the links read this to decide
//                                          present / none / unavailable).
//   GET /api/changes/:id/contract/data  → serves CONTRACT.html (text/html).
//   GET /api/changes/:id/contract/ui    → serves UI.html (text/html) when
//                                          present; a typed JSON note when
//                                          the change has no UI contract
//                                          (NOT a broken link).
//
// The cockpit CONSUMES the shared CONTRACT.manifest.json + serves the files;
// it never parses contracts itself (ADR-001). Built against a manifest
// fixture (CF-05) + the FakeRecreateRunner (MEA-09) so it needs neither the
// real renderers nor the real recreate CLI.

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
    handle: "feat-demo-change",
    slug: "demo",
    primitive: "create",
    branch: "change/demo",
    worktreePath: "/tmp/wt-default",
    intent: "demo change",
    baseBranch: "main",
    baseSha: "deadbeef",
    shippedSha: null,
    createdAt: "2026-05-01T00:00:00Z",
    updatedAt: "2026-05-01T00:00:00Z",
    stage: "design",
    ...overrides,
  };
}

const CONTRACT_HTML =
  "<!doctype html><title>Contract</title><h1>What it does</h1>";
const UI_HTML = "<!doctype html><title>UI</title><h1>Visual preview</h1>";

/** Seed a worktree dir with rendered artifacts + a shared manifest. */
async function seedRendered(
  worktree: string,
  opts: { ui: "present" | "none" } = { ui: "present" },
): Promise<void> {
  await writeFile(join(worktree, "CONTRACT.html"), CONTRACT_HTML, "utf8");
  const manifest: Record<string, unknown> = {
    data_contract: {
      format: "servicespec",
      name: "Platforms",
      contracts: [{ path: join(worktree, "spec.json"), format: "servicespec" }],
    },
    contract_html: join(worktree, "CONTRACT.html"),
  };
  if (opts.ui === "present") {
    await writeFile(join(worktree, "UI.html"), UI_HTML, "utf8");
    manifest.ui_contract = "present";
    manifest.path = join(worktree, "UI.html");
  } else {
    manifest.ui_contract = "none";
    manifest.note =
      "No UI contract for this change — it carries no visual contract.";
  }
  await writeFile(
    join(worktree, "CONTRACT.manifest.json"),
    JSON.stringify(manifest, null, 2),
    "utf8",
  );
}

function makeApp(reader: FakeChangeStoreReader, runner: FakeRecreateRunner) {
  return createApp({
    changeStore: reader,
    recreateRunner: runner,
    sulisStateDir: "/tmp/never",
    claudeProjectsDir: "/tmp/never",
  });
}

describe("GET /api/changes/:id/contract endpoints", () => {
  let tmpRoot: string;

  beforeEach(async () => {
    tmpRoot = await realpath(await mkdtemp(join(tmpdir(), "routes-contract-")));
  });
  afterEach(async () => {
    await rm(tmpRoot, { recursive: true, force: true });
  });

  // ── summary ──────────────────────────────────────────────────────────
  it("summary: reports data + ui contract availability when present", async () => {
    const wt = join(tmpRoot, "present-wt");
    await mkdir(wt, { recursive: true });
    await seedRendered(wt, { ui: "present" });

    const reader = new FakeChangeStoreReader([
      record({ changeId: "01AAA", worktreePath: wt }),
    ]);
    const runner = new FakeRecreateRunner({ ok: true, alreadyPresent: true });
    const res = await request(makeApp(reader, runner)).get(
      "/api/changes/01AAA/contract",
    );

    expect(res.status).toBe(200);
    const body = res.body as {
      status: string;
      dataContract: { format: string; name: string } | null;
      uiContract: { status: string };
    };
    expect(body.status).toBe("ready");
    expect(body.dataContract?.format).toBe("servicespec");
    expect(body.uiContract.status).toBe("present");
  });

  it("summary: ui_contract none surfaces a note (not a broken link)", async () => {
    const wt = join(tmpRoot, "no-ui-wt");
    await mkdir(wt, { recursive: true });
    await seedRendered(wt, { ui: "none" });

    const reader = new FakeChangeStoreReader([
      record({ changeId: "01BBB", worktreePath: wt }),
    ]);
    const runner = new FakeRecreateRunner({ ok: true, alreadyPresent: true });
    const res = await request(makeApp(reader, runner)).get(
      "/api/changes/01BBB/contract",
    );

    expect(res.status).toBe(200);
    const body = res.body as {
      status: string;
      uiContract: { status: string; note?: string };
    };
    expect(body.status).toBe("ready");
    expect(body.uiContract.status).toBe("none");
    expect(body.uiContract.note).toMatch(/no ui contract/i);
  });

  // ── data ─────────────────────────────────────────────────────────────
  it("data: serves the rendered CONTRACT.html when present", async () => {
    const wt = join(tmpRoot, "data-wt");
    await mkdir(wt, { recursive: true });
    await seedRendered(wt, { ui: "present" });

    const reader = new FakeChangeStoreReader([
      record({ changeId: "01CCC", worktreePath: wt }),
    ]);
    const runner = new FakeRecreateRunner({ ok: true, alreadyPresent: true });
    const res = await request(makeApp(reader, runner)).get(
      "/api/changes/01CCC/contract/data",
    );

    expect(res.status).toBe(200);
    expect(res.headers["content-type"]).toMatch(/text\/html/);
    expect(res.text).toContain("What it does");
  });

  // ── ui ───────────────────────────────────────────────────────────────
  it("ui: serves the rendered UI.html when present", async () => {
    const wt = join(tmpRoot, "ui-present-wt");
    await mkdir(wt, { recursive: true });
    await seedRendered(wt, { ui: "present" });

    const reader = new FakeChangeStoreReader([
      record({ changeId: "01DDD", worktreePath: wt }),
    ]);
    const runner = new FakeRecreateRunner({ ok: true, alreadyPresent: true });
    const res = await request(makeApp(reader, runner)).get(
      "/api/changes/01DDD/contract/ui",
    );

    expect(res.status).toBe(200);
    expect(res.headers["content-type"]).toMatch(/text\/html/);
    expect(res.text).toContain("Visual preview");
  });

  it("ui: returns a typed JSON note (not a broken link) when there is no UI contract", async () => {
    const wt = join(tmpRoot, "ui-none-wt");
    await mkdir(wt, { recursive: true });
    await seedRendered(wt, { ui: "none" });

    const reader = new FakeChangeStoreReader([
      record({ changeId: "01EEE", worktreePath: wt }),
    ]);
    const runner = new FakeRecreateRunner({ ok: true, alreadyPresent: true });
    const res = await request(makeApp(reader, runner)).get(
      "/api/changes/01EEE/contract/ui",
    );

    // A note, served as JSON, NOT a 404/broken link — the founder sees
    // "no UI contract for this change", not an error.
    expect(res.status).toBe(200);
    expect(res.headers["content-type"]).toMatch(/application\/json/);
    const body = res.body as { uiContract: string; note: string };
    expect(body.uiContract).toBe("none");
    expect(body.note).toMatch(/no ui contract/i);
  });

  // ── recreate-on-demand for a tidied (shipped) change ───────────────────
  it("recreates a tidied worktree on demand, then serves the contract", async () => {
    const wt = join(tmpRoot, "tidied-wt"); // absent at first
    // The fake recreate MATERIALISES the worktree + artifacts (mirrors the
    // real `sulis-change recreate`), so the serving path can then read them.
    const runner = new FakeRecreateRunner(
      { ok: true, alreadyPresent: false },
      {
        onRecreate: async () => {
          await mkdir(wt, { recursive: true });
          await seedRendered(wt, { ui: "present" });
        },
      },
    );
    const rec = record({
      changeId: "01FFF",
      worktreePath: wt,
      shippedSha: "deadbeefcafe", // recreatable
      stage: "shipped",
    });
    const reader = new FakeChangeStoreReader([rec]);

    const res = await request(makeApp(reader, runner)).get(
      "/api/changes/01FFF/contract/data",
    );

    expect(res.status).toBe(200);
    expect(res.text).toContain("What it does");
    // Recreate was invoked exactly once, with the change's OWN unique id
    // (ADR-001 — the seam is keyed by change_id, off the record, never
    // hard-wired nor the non-unique handle).
    expect(runner.calls).toEqual([rec.changeId]);
  });

  it("degrades to a typed note when the worktree is gone and not recreatable", async () => {
    const runner = new FakeRecreateRunner({ ok: true, alreadyPresent: false });
    const rec = record({
      changeId: "01GGG",
      worktreePath: join(tmpRoot, "missing-wt"),
      branch: "",
      shippedSha: null, // not recreatable
      stage: "shipped",
    });
    const reader = new FakeChangeStoreReader([rec]);

    const res = await request(makeApp(reader, runner)).get(
      "/api/changes/01GGG/contract",
    );

    expect(res.status).toBe(200);
    const body = res.body as { status: string; note?: string };
    expect(body.status).toBe("unavailable");
    expect(body.note).toMatch(
      /couldn't reach this shipped change's contracts/i,
    );
    // Not recreatable → never even attempted a spawn.
    expect(runner.calls).toEqual([]);
  });

  // ── unknown change ─────────────────────────────────────────────────────
  it("returns 404 NOT_FOUND for an unknown change id", async () => {
    const reader = new FakeChangeStoreReader([]);
    const runner = new FakeRecreateRunner({ ok: true, alreadyPresent: false });
    const res = await request(makeApp(reader, runner)).get(
      "/api/changes/missing/contract",
    );
    expect(res.status).toBe(404);
    expect((res.body as { code: string }).code).toBe("NOT_FOUND");
  });

  // ── read-only invariant: non-GET methods rejected ──────────────────────
  it("preserves the read-only invariant: POST to a contract endpoint is 405", async () => {
    const wt = join(tmpRoot, "ro-wt");
    await mkdir(wt, { recursive: true });
    await seedRendered(wt, { ui: "present" });
    const reader = new FakeChangeStoreReader([
      record({ changeId: "01HHH", worktreePath: wt }),
    ]);
    const runner = new FakeRecreateRunner({ ok: true, alreadyPresent: true });
    const res = await request(makeApp(reader, runner)).post(
      "/api/changes/01HHH/contract/data",
    );
    expect(res.status).toBe(405);
  });
});
