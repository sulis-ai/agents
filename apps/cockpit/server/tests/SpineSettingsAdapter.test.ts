// WP-005 — SpineSettingsAdapter integration test (TDD §6, §7; ADR-019/020/021).
//
// Outside-in (WPB-08): this is the REAL integration test for the only new
// process-start site in the change. It drives the actual validated Python
// helpers (emit / edit / set-status / list) into a `mkdtemp` brain — NO mocks
// (WPB-03 / MEA-09). It asserts the disk-safety invariant the WP owns: after
// removeProject + unlinkRepo, a sentinel file (and `.git`) planted in a mock
// "founder folder" still exist on disk (ADR-020).
//
// The named Red cases (WP Definition of Done):
//   - create_writes_valid_jsonld
//   - edit_overwrites_in_place_no_count_growth
//   - remove_sets_sys_status_deleted_file_remains
//   - unlink_clears_source_disk_untouched
//   - attach_missing_path_is_PATH_NOT_FOUND
//   - write_failure_maps_to_WRITE_FAILED
//   - bootstrap_from_empty_brain
//   - sentinel_file_survives_remove_and_unlink
//
// Plus the MANDATORY security guard (path-traversal hardening, CONCERN-1):
//   - traversal_domain_or_id_is_rejected_no_escape
//
// Skips cleanly (not vacuously) when python3 or the vendored adapter scripts
// are unavailable (a bare checkout), matching emit-helpers.test.ts.

import { describe, it, expect, beforeAll, afterEach } from "vitest";
import {
  mkdtempSync,
  rmSync,
  existsSync,
  readdirSync,
  writeFileSync,
  mkdirSync,
  readFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { execFileSync } from "node:child_process";

import { SpineSettingsAdapter } from "../adapters/SpineSettingsAdapter";
import { SettingsStoreError } from "../ports/SettingsStore";

// Repo-root-relative anchors (this file is five levels under the repo root).
const HERE = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = join(HERE, "..", "..", "..", "..");
const SCRIPTS_DIR = join(REPO_ROOT, "plugins", "sulis", "scripts");

const PRODUCT_DOMAIN = "product-development";
const PROJECT_DOMAIN = "foundation";

// ── availability gate ──────────────────────────────────────────────────────
let havePython = false;
let haveAdapter = false;
beforeAll(() => {
  try {
    execFileSync("python3", ["--version"], { stdio: "ignore" });
    havePython = true;
  } catch {
    havePython = false;
  }
  haveAdapter = existsSync(join(SCRIPTS_DIR, "_entity_adapter_local.py"));
});

function unavailable(): boolean {
  if (!havePython || !haveAdapter) {
    // eslint-disable-next-line no-console
    console.warn(
      "skipping: python3 or the vendored adapter scripts unavailable",
    );
    return true;
  }
  return false;
}

// ── temp lifecycle ─────────────────────────────────────────────────────────
const cleanups: string[] = [];
afterEach(() => {
  while (cleanups.length > 0) {
    const dir = cleanups.pop();
    if (dir) rmSync(dir, { recursive: true, force: true });
  }
});

/** A fresh `<state>/.brain/instances` dir for one test. */
function tmpBrain(): string {
  const dir = mkdtempSync(join(tmpdir(), "wp005-brain-"));
  cleanups.push(dir);
  return join(dir, ".brain", "instances");
}

/** A fresh mock "founder folder" (optionally a git repo). */
function tmpFolder(withGit: boolean): string {
  const dir = mkdtempSync(join(tmpdir(), "wp005-folder-"));
  cleanups.push(dir);
  if (withGit) mkdirSync(join(dir, ".git"), { recursive: true });
  return dir;
}

function makeAdapter(base: string): SpineSettingsAdapter {
  return new SpineSettingsAdapter({
    scriptsDir: SCRIPTS_DIR,
    baseDir: base,
  });
}

/** Count `.jsonld` files of one kind in a domain. */
function countKind(base: string, domain: string, kind: string): number {
  const dir = join(base, domain, kind);
  if (!existsSync(dir)) return 0;
  return readdirSync(dir).filter((f) => f.endsWith(".jsonld")).length;
}

/** Read a stored entity back from disk by its id. */
function readEntityById(
  base: string,
  domain: string,
  kind: string,
  id: string,
): Record<string, unknown> {
  const ulid = id.split(":").pop() as string;
  return JSON.parse(
    readFileSync(join(base, domain, kind, `${ulid}.jsonld`), "utf8"),
  );
}

describe("SpineSettingsAdapter (real temp brain, no mocks)", { timeout: 60_000 }, () => {
  it("create_writes_valid_jsonld — upsertProduct (no id) mints a valid .jsonld", async () => {
    if (unavailable()) return;
    const base = tmpBrain();
    const adapter = makeAdapter(base);

    const product = await adapter.upsertProduct({ name: "Acme" });
    expect(product.productId).toMatch(/^dna:product:[0-9A-HJKMNP-TV-Z]{26}$/);
    expect(product.name).toBe("Acme");

    // A valid .jsonld is on disk with the active status.
    expect(countKind(base, PRODUCT_DOMAIN, "product")).toBe(1);
    const stored = readEntityById(base, PRODUCT_DOMAIN, "product", product.productId);
    expect(stored.id).toBe(product.productId);
    expect(stored.sys_status).toBe("active");

    // It surfaces through readTree.
    const tree = await adapter.readTree();
    expect(tree.products.map((p) => p.productId)).toContain(product.productId);
  });

  it("edit_overwrites_in_place_no_count_growth — upsert with id overwrites, never grows the tree", async () => {
    if (unavailable()) return;
    const base = tmpBrain();
    const adapter = makeAdapter(base);

    const created = await adapter.upsertProduct({ name: "Acme" });
    expect(countKind(base, PRODUCT_DOMAIN, "product")).toBe(1);

    const edited = await adapter.upsertProduct({
      productId: created.productId,
      name: "Acme Renamed",
    });
    expect(edited.productId).toBe(created.productId);
    expect(edited.name).toBe("Acme Renamed");

    // Same id ⇒ overwrite in place; the file count is unchanged (FR-31).
    expect(countKind(base, PRODUCT_DOMAIN, "product")).toBe(1);
    const stored = readEntityById(base, PRODUCT_DOMAIN, "product", created.productId);
    expect(stored.name).toBe("Acme Renamed");
  });

  it("edit_project_with_id_renames_in_place — upsertProject with id overwrites the project name", async () => {
    if (unavailable()) return;
    const base = tmpBrain();
    const adapter = makeAdapter(base);

    const product = await adapter.upsertProduct({ name: "Acme" });
    const created = await adapter.upsertProject({
      productId: product.productId,
      name: "Web",
    });
    expect(countKind(base, PROJECT_DOMAIN, "project")).toBe(1);

    const edited = await adapter.upsertProject({
      projectId: created.projectId,
      productId: product.productId,
      name: "Web Renamed",
    });
    expect(edited.projectId).toBe(created.projectId);
    expect(edited.name).toBe("Web Renamed");
    // Same id ⇒ overwrite in place; no count growth.
    expect(countKind(base, PROJECT_DOMAIN, "project")).toBe(1);
  });

  it("remove_sets_sys_status_deleted_file_remains — removeProduct soft-deletes; the file stays", async () => {
    if (unavailable()) return;
    const base = tmpBrain();
    const adapter = makeAdapter(base);

    const product = await adapter.upsertProduct({ name: "Acme" });
    const ulid = product.productId.split(":").pop() as string;
    const filePath = join(base, PRODUCT_DOMAIN, "product", `${ulid}.jsonld`);
    expect(existsSync(filePath)).toBe(true);

    await adapter.removeProduct(product.productId);

    // The FILE still exists (soft-delete is a field mutation, never a file
    // delete — ADR-020) and now carries sys_status:"deleted".
    expect(existsSync(filePath)).toBe(true);
    const stored = readEntityById(base, PRODUCT_DOMAIN, "product", product.productId);
    expect(stored.sys_status).toBe("deleted");

    // It is gone from the next readTree (the active allow-list filter).
    const tree = await adapter.readTree();
    expect(tree.products.map((p) => p.productId)).not.toContain(product.productId);
  });

  it("unlink_clears_source_disk_untouched — unlinkRepo clears Project.source; the founder folder is untouched", async () => {
    if (unavailable()) return;
    const base = tmpBrain();
    const adapter = makeAdapter(base);

    const product = await adapter.upsertProduct({ name: "Acme" });
    const project = await adapter.upsertProject({
      productId: product.productId,
      name: "Web",
    });

    const folder = tmpFolder(false);
    const sentinel = join(folder, "PRECIOUS.txt");
    writeFileSync(sentinel, "do not delete");

    await adapter.attachRepo({ projectId: project.projectId, localPath: folder });
    const unlinked = await adapter.unlinkRepo(project.projectId);

    expect(unlinked.repo).toBeNull();
    // The Project.source on disk is the empty-link shape.
    const stored = readEntityById(base, PROJECT_DOMAIN, "project", project.projectId);
    const parsedSource = JSON.parse(stored.source as string) as { path: string };
    expect(parsedSource.path).toBe("");

    // The founder's folder and its sentinel are untouched (disk safety).
    expect(existsSync(folder)).toBe(true);
    expect(existsSync(sentinel)).toBe(true);
  });

  it("attach_missing_path_is_PATH_NOT_FOUND — attaching a non-existent folder raises PATH_NOT_FOUND, no write", async () => {
    if (unavailable()) return;
    const base = tmpBrain();
    const adapter = makeAdapter(base);

    const product = await adapter.upsertProduct({ name: "Acme" });
    const project = await adapter.upsertProject({
      productId: product.productId,
      name: "Web",
    });

    const before = readEntityById(base, PROJECT_DOMAIN, "project", project.projectId);

    await expect(
      adapter.attachRepo({
        projectId: project.projectId,
        localPath: "/nonexistent/wp005/missing-folder",
      }),
    ).rejects.toMatchObject({ code: "PATH_NOT_FOUND" });

    // No write happened — the project's source is byte-identical to before.
    const after = readEntityById(base, PROJECT_DOMAIN, "project", project.projectId);
    expect(after.source).toEqual(before.source);
  });

  it("write_failure_maps_to_WRITE_FAILED — a helper non-zero exit maps to a typed WRITE_FAILED", async () => {
    if (unavailable()) return;
    const base = tmpBrain();
    // Point the adapter's spine helpers at a temp dir holding a stub
    // edit-product.py that exits non-zero — the real failure path, no mock of
    // the adapter's own code. (We still need a real product to edit.)
    const realAdapter = makeAdapter(base);
    const product = await realAdapter.upsertProduct({ name: "Acme" });

    const fakeSpine = mkdtempSync(join(tmpdir(), "wp005-fakespine-"));
    cleanups.push(fakeSpine);
    writeFileSync(
      join(fakeSpine, "edit-product.py"),
      'import sys\nsys.stderr.write("boom")\nsys.exit(7)\n',
    );

    const adapter = new SpineSettingsAdapter({
      scriptsDir: SCRIPTS_DIR,
      baseDir: base,
      spineDir: fakeSpine,
    });

    await expect(
      adapter.upsertProduct({ productId: product.productId, name: "X" }),
    ).rejects.toMatchObject({ code: "WRITE_FAILED" });
  });

  it("bootstrap_from_empty_brain — empty brain → add product → project → attach → readTree persists", async () => {
    if (unavailable()) return;
    const base = tmpBrain();
    const adapter = makeAdapter(base);

    // Empty brain: readTree is empty.
    expect((await adapter.readTree()).products).toHaveLength(0);

    const product = await adapter.upsertProduct({ name: "Acme" });
    const project = await adapter.upsertProject({
      productId: product.productId,
      name: "Web",
    });
    const folder = tmpFolder(true); // a real git repo this time
    await adapter.attachRepo({ projectId: project.projectId, localPath: folder });

    // A FRESH adapter over the same brain (simulating a reload) sees it all.
    const reloaded = makeAdapter(base);
    const tree = await reloaded.readTree();
    const acme = tree.products.find((p) => p.productId === product.productId);
    expect(acme).toBeDefined();
    expect(acme?.name).toBe("Acme");
    const web = acme?.projects.find((pr) => pr.projectId === project.projectId);
    expect(web).toBeDefined();
    expect(web?.repo?.localPath).toBe(folder);
    expect(web?.repo?.present).toBe(true); // .git present
  });

  it("sentinel_file_survives_remove_and_unlink — the founder's folder is never touched", async () => {
    if (unavailable()) return;
    const base = tmpBrain();
    const adapter = makeAdapter(base);

    // Plant a sentinel file + .git in a mock founder folder.
    const founder = tmpFolder(true);
    const sentinel = join(founder, "PRECIOUS.txt");
    writeFileSync(sentinel, "the founder's irreplaceable work");
    const gitDir = join(founder, ".git");
    expect(existsSync(sentinel)).toBe(true);
    expect(existsSync(gitDir)).toBe(true);

    const product = await adapter.upsertProduct({ name: "Acme" });
    const project = await adapter.upsertProject({
      productId: product.productId,
      name: "Web",
    });
    await adapter.attachRepo({ projectId: project.projectId, localPath: founder });

    // The two operations that could conceivably touch disk: unlink + remove.
    // (Unlink first while the project is still active — once soft-deleted it is
    // filtered out of the active tree; the disk-safety invariant is what this
    // test pins, and it must hold for BOTH writes.)
    await adapter.unlinkRepo(project.projectId);
    await adapter.removeProject(project.projectId);

    // INVARIANT (ADR-020): the sentinel and .git STILL exist on disk.
    expect(existsSync(founder)).toBe(true);
    expect(existsSync(sentinel)).toBe(true);
    expect(readFileSync(sentinel, "utf8")).toBe(
      "the founder's irreplaceable work",
    );
    expect(existsSync(gitDir)).toBe(true);
  });

  it("empty_name_is_VALIDATION_FAILED — a blank product/project name is rejected with no write", async () => {
    if (unavailable()) return;
    const base = tmpBrain();
    const adapter = makeAdapter(base);

    await expect(adapter.upsertProduct({ name: "   " })).rejects.toMatchObject({
      code: "VALIDATION_FAILED",
    });
    const product = await adapter.upsertProduct({ name: "Acme" });
    await expect(
      adapter.upsertProject({ productId: product.productId, name: "" }),
    ).rejects.toMatchObject({ code: "VALIDATION_FAILED" });

    // Only the one real product exists; the blank writes never landed.
    expect(countKind(base, PRODUCT_DOMAIN, "product")).toBe(1);
    expect(countKind(base, PROJECT_DOMAIN, "project")).toBe(0);
  });

  it("edit_nonexistent_product_maps_to_WRITE_FAILED — a helper non-ok envelope (no such id) surfaces as WRITE_FAILED", async () => {
    if (unavailable()) return;
    const base = tmpBrain();
    const adapter = makeAdapter(base);

    // A well-formed but unminted id: the real edit-product.py runs, find_by_id
    // returns None, the helper emits {"ok": false} and exits non-zero — the
    // adapter maps that to a typed WRITE_FAILED (the real failure path).
    const ghostId = `dna:product:${"01HZZZZZZZZZZZZZZZZZZZG010".slice(0, 26)}`;
    await expect(
      adapter.upsertProduct({ productId: ghostId, name: "Ghost" }),
    ).rejects.toMatchObject({ code: "WRITE_FAILED" });
  });

  it("traversal_domain_or_id_is_rejected_no_escape — a ../-laden id is rejected, no read/write escapes base_dir", async () => {
    // MANDATORY FIX 2 (security CONCERN-1) — request-controlled segments must
    // not contain traversal. A `../`-laden id is rejected BEFORE any helper
    // runs, and nothing is read or written outside base_dir.
    if (unavailable()) return;
    const base = tmpBrain();
    const adapter = makeAdapter(base);

    // An id whose ULID segment carries traversal — both the dna pattern check
    // and the segment guard must reject it.
    const evilId = "dna:product:../../../../etc/passwd";
    await expect(adapter.removeProduct(evilId)).rejects.toBeInstanceOf(
      SettingsStoreError,
    );
    await expect(
      adapter.upsertProduct({ productId: evilId, name: "X" }),
    ).rejects.toBeInstanceOf(SettingsStoreError);

    // A bare-path traversal attempt on a project id is likewise rejected.
    const evilProjectId = "dna:project:..%2f..%2f..%2fescape";
    await expect(adapter.removeProject(evilProjectId)).rejects.toBeInstanceOf(
      SettingsStoreError,
    );

    // No entity files were created anywhere under base.
    expect(countKind(base, PRODUCT_DOMAIN, "product")).toBe(0);
    expect(countKind(base, PROJECT_DOMAIN, "project")).toBe(0);
  });
});

// ── Hardening follow-ups (CH-01KTPD) ───────────────────────────────────────
describe("SpineSettingsAdapter — hardening follow-ups", { timeout: 60_000 }, () => {
  // A well-formed-but-nonexistent product id (passes the pattern, has no entity)
  // — editing it makes the helper fail, exercising the WRITE_FAILED path.
  const MISSING_PRODUCT_ID = "dna:product:01HZZZZZZZZZZZZZZZZZZZG010";

  // #4 — a leading-hyphen name is rejected up front (pure validation, no python).
  it("rejects a product name starting with a hyphen (VALIDATION_FAILED)", async () => {
    const adapter = makeAdapter(tmpBrain());
    await expect(
      adapter.upsertProduct({ name: "-Acme" }),
    ).rejects.toMatchObject({ code: "VALIDATION_FAILED" });
  });

  it("rejects a project name starting with a hyphen (VALIDATION_FAILED)", async () => {
    const adapter = makeAdapter(tmpBrain());
    await expect(
      adapter.upsertProject({ productId: MISSING_PRODUCT_ID, name: "-Proj" }),
    ).rejects.toMatchObject({ code: "VALIDATION_FAILED" });
  });

  // #5 — a successful write emits one structured audit log line.
  it("emits a structured per-write log line on create (audit trail)", async () => {
    if (unavailable()) return;
    const entries: Record<string, unknown>[] = [];
    const adapter = new SpineSettingsAdapter({
      scriptsDir: SCRIPTS_DIR,
      baseDir: tmpBrain(),
      log: (e) => entries.push(e),
    });

    await adapter.upsertProduct({ name: "Logged Co" });

    const writes = entries.filter((e) => e.evt === "settings-write");
    expect(writes.length).toBeGreaterThanOrEqual(1);
    expect(writes.some((e) => e.op === "create-product")).toBe(true);
  });

  // #6 — a write failure returns an OPAQUE client message; the raw helper detail
  // (paths / tracebacks) goes only to the server-side log (CWE-209).
  it("WRITE_FAILED is opaque to the client; raw detail goes to the log", async () => {
    if (unavailable()) return;
    const entries: Record<string, unknown>[] = [];
    const adapter = new SpineSettingsAdapter({
      scriptsDir: SCRIPTS_DIR,
      baseDir: tmpBrain(),
      log: (e) => entries.push(e),
    });

    let caught: SettingsStoreError | undefined;
    try {
      await adapter.upsertProduct({ productId: MISSING_PRODUCT_ID, name: "Ghost" });
    } catch (e) {
      caught = e as SettingsStoreError;
    }

    expect(caught).toBeInstanceOf(SettingsStoreError);
    expect(caught?.code).toBe("WRITE_FAILED");
    // The client-facing message is fixed + opaque — no filesystem path, no
    // traceback, no scripts dir leaking through.
    expect(caught?.message).not.toContain("/");
    expect(caught?.message).not.toContain("Traceback");
    expect(caught?.message).not.toContain(SCRIPTS_DIR);
    // The full detail still reached the server-side log (the audit trail).
    const errs = entries.filter((e) => e.evt === "settings-write-error");
    expect(errs.length).toBeGreaterThanOrEqual(1);
    expect(String(errs[0]?.detail ?? "")).not.toBe("");
  });
});

// ── change → product un-assign (clearChangeProduct) — WP-003 ────────────────
describe("SpineSettingsAdapter.clearChangeProduct (real helper, no mocks)", {
  timeout: 60_000,
}, () => {
  const CHANGE_ULID = "01CHG0000000000000000000AA";
  const PRODUCT_ID = "dna:product:01ACME00000000000000000000";

  /** A fresh `<state>/changes` dir holding one seeded `<ulid>/change.json`. */
  function tmpChangesWithRecord(ulid: string): string {
    const dir = mkdtempSync(join(tmpdir(), "wp003-changes-"));
    cleanups.push(dir);
    const recDir = join(dir, ulid);
    mkdirSync(recDir, { recursive: true });
    writeFileSync(
      join(recDir, "change.json"),
      JSON.stringify({
        change_id: ulid,
        handle: "CH-0000AA",
        slug: "unassign-me",
        intent: "a change to un-assign from a product",
        primitive: "feat",
        created_at: "2026-06-16T00:00:00Z",
        branch: `change/feat-${ulid}`,
      }),
    );
    return dir;
  }

  function changeEntityPath(base: string, ulid: string): string {
    return join(base, PRODUCT_DOMAIN, "change", `${ulid}.jsonld`);
  }

  it("clears for_product back to null and emits a structured log line", async () => {
    if (unavailable()) return;
    const base = tmpBrain();
    const changesDir = tmpChangesWithRecord(CHANGE_ULID);
    const entries: Record<string, unknown>[] = [];
    const adapter = new SpineSettingsAdapter({
      scriptsDir: SCRIPTS_DIR,
      baseDir: base,
      changesDir,
      log: (e) => entries.push(e),
    });

    // Assign first so there is a link to clear (compose path from change.json).
    await adapter.assignChangeProduct(CHANGE_ULID, PRODUCT_ID);
    expect(
      JSON.parse(readFileSync(changeEntityPath(base, CHANGE_ULID), "utf8"))
        .for_product,
    ).toBe(PRODUCT_ID);

    // Clear it.
    const result = await adapter.clearChangeProduct(CHANGE_ULID);
    expect(result).toEqual({
      id: `dna:change:${CHANGE_ULID}`,
      forProduct: null,
    });

    // The on-disk entity now has NO link — "unassigned" is the absence of the
    // key (the schema types for_product as an optional string), not a null.
    expect(
      JSON.parse(readFileSync(changeEntityPath(base, CHANGE_ULID), "utf8")),
    ).not.toHaveProperty("for_product");

    // A structured audit line was emitted for the clear.
    const writes = entries.filter((e) => e.evt === "settings-write");
    expect(writes.some((e) => e.op === "clear-change-product")).toBe(true);
  });

  it("rejects a malformed change id with VALIDATION_FAILED before any helper runs", async () => {
    const adapter = new SpineSettingsAdapter({
      scriptsDir: SCRIPTS_DIR,
      baseDir: tmpBrain(),
    });
    await expect(
      adapter.clearChangeProduct("../../etc/passwd"),
    ).rejects.toMatchObject({ code: "VALIDATION_FAILED" });
  });
});
