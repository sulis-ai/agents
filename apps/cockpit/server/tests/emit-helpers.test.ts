// WP-004 — validated Python edit/status/list entity helpers (ADR-020).
//
// These four helpers own the read-modify-validate-save (and the read-back)
// against the brain instance store so the TypeScript SpineSettingsAdapter
// (WP-005) never hand-builds a schema entity (ADR-007 discipline):
//
//   - edit-product.py      — validated re-save of a product's `name` (every
//                            other field preserved); same id, overwrites in
//                            place, never mints a second entity (FR-31).
//   - edit-project.py      — same for a project (source +
//                            belongs_to_product_ref preserved).
//   - set-entity-status.py — soft-delete via `sys_status` (NEVER a file
//                            delete — ADR-020).
//   - list-entities.py     — walk {base}/{domain}/{kind}/*.jsonld, return the
//                            ACTIVE entities as JSON.
//
// Outside-in (WPB-08): this is the integration test, driven against the REAL
// `_entity_adapter_local` surface over a `mkdtemp` brain — no mocks (WPB-03).
// Each helper is a standalone validated CLI mirroring `emit-project.py`; it is
// invoked argv-only via `python3` (shell:false), the same way
// `SpineEmitterMinter` drives `emit-project.py`.
//
// The four named Red cases (WP Definition of Done):
//   - edit_product_resave_overwrites_in_place
//   - edit_rejects_invalid_writes_nothing
//   - set_status_deleted_keeps_file_on_disk
//   - list_entities_returns_active_only
//
// Skips cleanly (not vacuously) when python3 or the vendored adapter scripts
// are unavailable (a bare checkout), matching discovery.mint-real.test.ts.

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
import { execFileSync, execFile } from "node:child_process";

// Repo-root-relative anchors. This test file lives at
// apps/cockpit/server/tests/ — five levels under the repo root.
const HERE = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = join(HERE, "..", "..", "..", "..");
// The validated adapter + schemas the helpers import (the same `--scripts-dir`
// SpineEmitterMinter passes to emit-project.py).
const SCRIPTS_DIR = join(REPO_ROOT, "plugins", "sulis", "scripts");
// The four helpers under test.
const SPINE_DIR = join(
  REPO_ROOT,
  "apps",
  "cockpit",
  "server",
  "adapters",
  "spine",
);

const PRODUCT_DOMAIN = "product-development";
const PROJECT_DOMAIN = "foundation";

// A valid 26-char Crockford ULID-shaped suffix for deterministic seed ids.
const PRODUCT_ULID = "01HZZZZZZZZZZZZZZZZZZZZP01";
const PRODUCT_ULID_26 = "01HZZZZZZZZZZZZZZZZZZZZP010".slice(0, 26);
const PROJECT_ULID_26 = "01HZZZZZZZZZZZZZZZZZZZQ010".slice(0, 26);
const TENANT_ULID_26 = "01HZZZZZZZZZZZZZZZZZZZT010".slice(0, 26);

const PRODUCT_ID = `dna:product:${PRODUCT_ULID_26}`;
const PROJECT_ID = `dna:project:${PROJECT_ULID_26}`;
const TENANT_ID = `dna:tenant:${TENANT_ULID_26}`;

void PRODUCT_ULID; // documentation of the id shape; the 26-char value is used.

// ── availability gate ─────────────────────────────────────────────────────
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

// ── temp brain lifecycle ──────────────────────────────────────────────────
const cleanups: string[] = [];
afterEach(() => {
  while (cleanups.length > 0) {
    const dir = cleanups.pop();
    if (dir) rmSync(dir, { recursive: true, force: true });
  }
});

function tmpBrain(): string {
  const dir = mkdtempSync(join(tmpdir(), "wp004-brain-"));
  cleanups.push(dir);
  return join(dir, ".brain", "instances");
}

/** Path of a seeded entity's on-disk .jsonld file. */
function entityPath(
  base: string,
  domain: string,
  kind: string,
  id: string,
): string {
  const ulid = id.split(":").pop() as string;
  return join(base, domain, kind, `${ulid}.jsonld`);
}

/** Seed a valid entity directly to disk (the layout the adapter reads). */
function seed(
  base: string,
  domain: string,
  kind: string,
  entity: Record<string, unknown>,
): string {
  const path = entityPath(base, domain, kind, entity.id as string);
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, JSON.stringify(entity, null, 2));
  return path;
}

function seedProduct(
  base: string,
  overrides: Record<string, unknown> = {},
): string {
  return seed(base, PRODUCT_DOMAIN, "product", {
    id: PRODUCT_ID,
    name: "Original Name",
    belongs_to_tenant: TENANT_ID,
    state: "active",
    sys_status: "active",
    ...overrides,
  });
}

function seedProject(
  base: string,
  overrides: Record<string, unknown> = {},
): string {
  return seed(base, PROJECT_DOMAIN, "project", {
    id: PROJECT_ID,
    name: "original-project",
    belongs_to_tenant: TENANT_ID,
    belongs_to_product_ref: PRODUCT_ID,
    type: "application",
    source: JSON.stringify({ repo: "/x", path: "/x", primary_branch: "main" }),
    version_files: ["package.json"],
    branch_policy: "trunk",
    state: "active",
    sys_status: "active",
    ...overrides,
  });
}

/** Count `.jsonld` files of one kind in a domain. */
function countKind(base: string, domain: string, kind: string): number {
  const dir = join(base, domain, kind);
  if (!existsSync(dir)) return 0;
  return readdirSync(dir).filter((f) => f.endsWith(".jsonld")).length;
}

/** Read a seeded entity back from disk. */
function readEntity(
  base: string,
  domain: string,
  kind: string,
  id: string,
): Record<string, unknown> {
  return JSON.parse(readFileSync(entityPath(base, domain, kind, id), "utf8"));
}

interface RunResult {
  ok: boolean;
  stdout: string;
  stderr: string;
}

/** Run a spine helper argv-only via python3 (no shell), capturing I/O. */
function runHelper(script: string, args: string[]): Promise<RunResult> {
  return new Promise((resolve) => {
    execFile(
      "python3",
      [join(SPINE_DIR, script), "--scripts-dir", SCRIPTS_DIR, ...args],
      { timeout: 30_000 },
      (err, stdout, stderr) => {
        resolve({ ok: !err, stdout: stdout ?? "", stderr: stderr ?? "" });
      },
    );
  });
}

describe(
  "WP-004 validated edit/status/list helpers (ADR-020)",
  { timeout: 60_000 },
  () => {
    it("edit_product_resave_overwrites_in_place", async () => {
      if (unavailable()) return;
      const base = tmpBrain();
      seedProduct(base);
      expect(countKind(base, PRODUCT_DOMAIN, "product")).toBe(1);

      const r = await runHelper("edit-product.py", [
        "--base-dir",
        base,
        "--domain",
        PRODUCT_DOMAIN,
        "--id",
        PRODUCT_ID,
        "--name",
        "Renamed Product",
      ]);
      expect(r.ok).toBe(true);

      // Same id ⇒ overwrites in place; the file count is unchanged (FR-31).
      expect(countKind(base, PRODUCT_DOMAIN, "product")).toBe(1);
      const after = readEntity(base, PRODUCT_DOMAIN, "product", PRODUCT_ID);
      expect(after.name).toBe("Renamed Product");
      // Every other required field is preserved.
      expect(after.belongs_to_tenant).toBe(TENANT_ID);
      expect(after.state).toBe("active");
      expect(after.sys_status).toBe("active");
    });

    it("edit_rejects_invalid_writes_nothing", async () => {
      if (unavailable()) return;
      const base = tmpBrain();
      // Seed a project, then attempt an edit that would drop a required field by
      // setting an invalid value the schema rejects (empty version_files via a
      // status helper isn't the edit path — instead force an invalid name type
      // by clearing belongs_to_product_ref is allowed; the schema-invalid case
      // is editing `name` while corrupting source to a non-string). The helper
      // must validate BEFORE writing: nothing changes on disk and exit != 0.
      seedProject(base);
      const before = readEntity(base, PROJECT_DOMAIN, "project", PROJECT_ID);

      const r = await runHelper("edit-project.py", [
        "--base-dir",
        base,
        "--domain",
        PROJECT_DOMAIN,
        "--id",
        PROJECT_ID,
        // A project name is required to be a string; pass --branch-policy to an
        // invalid enum value to force a schema rejection.
        "--name",
        "renamed",
        "--branch-policy",
        "not-a-real-policy",
      ]);
      expect(r.ok).toBe(false); // non-zero exit on schema failure

      // Nothing was written: the on-disk entity is byte-identical to the seed.
      const after = readEntity(base, PROJECT_DOMAIN, "project", PROJECT_ID);
      expect(after).toEqual(before);
      expect(countKind(base, PROJECT_DOMAIN, "project")).toBe(1);
    });

    it("set_status_deleted_keeps_file_on_disk", async () => {
      if (unavailable()) return;
      const base = tmpBrain();
      const path = seedProduct(base);
      expect(existsSync(path)).toBe(true);

      const r = await runHelper("set-entity-status.py", [
        "--base-dir",
        base,
        "--domain",
        PRODUCT_DOMAIN,
        "--kind",
        "product",
        "--id",
        PRODUCT_ID,
        "--status",
        "deleted",
      ]);
      expect(r.ok).toBe(true);

      // The file STILL exists (soft-delete is a field mutation, ADR-020) — never
      // a file delete — and carries sys_status:"deleted".
      expect(existsSync(path)).toBe(true);
      expect(countKind(base, PRODUCT_DOMAIN, "product")).toBe(1);
      const after = readEntity(base, PRODUCT_DOMAIN, "product", PRODUCT_ID);
      expect(after.sys_status).toBe("deleted");
    });

    it("edit_project_source_json_overwrites_source_preserving_other_fields", async () => {
      // MANDATORY FIX 1 (composition CONCERN) — the port's attachRepo/unlinkRepo
      // mutate Project.source, but edit-project.py originally exposed only --name
      // / --branch-policy. It is extended with an optional --source-json routed
      // through the SAME validated _entity_edit upsert, so the adapter never
      // hand-builds an entity (ADR-007). This Red case proves the source edit.
      if (unavailable()) return;
      const base = tmpBrain();
      seedProject(base);
      const before = readEntity(base, PROJECT_DOMAIN, "project", PROJECT_ID);
      expect(before.source).toBe(
        JSON.stringify({ repo: "/x", path: "/x", primary_branch: "main" }),
      );

      const newSource = JSON.stringify({
        repo: "/home/founder/acme",
        path: "/home/founder/acme",
        primary_branch: "main",
      });
      const r = await runHelper("edit-project.py", [
        "--base-dir",
        base,
        "--domain",
        PROJECT_DOMAIN,
        "--id",
        PROJECT_ID,
        "--source-json",
        newSource,
      ]);
      expect(r.ok).toBe(true);

      // Same id ⇒ overwrites in place (no count growth); source replaced; every
      // other field preserved via {**existing, **changes}.
      expect(countKind(base, PROJECT_DOMAIN, "project")).toBe(1);
      const after = readEntity(base, PROJECT_DOMAIN, "project", PROJECT_ID);
      expect(after.source).toBe(newSource);
      expect(after.name).toBe(before.name);
      expect(after.belongs_to_product_ref).toBe(PRODUCT_ID);
      expect(after.belongs_to_tenant).toBe(TENANT_ID);
      expect(after.sys_status).toBe("active");
    });

    it("edit_project_source_json_only_does_not_require_name", async () => {
      // The adapter's attach/unlink edits ONLY source — it must not be forced to
      // restate the name. --name becomes optional when --source-json is given.
      if (unavailable()) return;
      const base = tmpBrain();
      seedProject(base);

      const r = await runHelper("edit-project.py", [
        "--base-dir",
        base,
        "--domain",
        PROJECT_DOMAIN,
        "--id",
        PROJECT_ID,
        "--source-json",
        JSON.stringify({ repo: "", path: "", primary_branch: "" }),
      ]);
      expect(r.ok).toBe(true);
      const after = readEntity(base, PROJECT_DOMAIN, "project", PROJECT_ID);
      // Unlink shape persisted; name untouched.
      expect(after.source).toBe(
        JSON.stringify({ repo: "", path: "", primary_branch: "" }),
      );
      expect(after.name).toBe("original-project");
    });

    it("list_entities_returns_active_only", async () => {
      if (unavailable()) return;
      const base = tmpBrain();
      // One active product, one soft-deleted product.
      seedProduct(base, { id: PRODUCT_ID, name: "Active One" });
      const deletedId = `dna:product:${"01HZZZZZZZZZZZZZZZZZZZD010".slice(0, 26)}`;
      seedProduct(base, {
        id: deletedId,
        name: "Deleted One",
        sys_status: "deleted",
      });
      expect(countKind(base, PRODUCT_DOMAIN, "product")).toBe(2);

      const r = await runHelper("list-entities.py", [
        "--base-dir",
        base,
        "--domain",
        PRODUCT_DOMAIN,
        "--kind",
        "product",
      ]);
      expect(r.ok).toBe(true);

      const payload = JSON.parse(r.stdout) as {
        ok: boolean;
        data: {
          entities: Array<{ id: string; name: string; sys_status: string }>;
        };
      };
      expect(payload.ok).toBe(true);
      const ids = payload.data.entities.map((e) => e.id);
      expect(ids).toContain(PRODUCT_ID);
      expect(ids).not.toContain(deletedId); // the deleted entity is omitted
      expect(
        payload.data.entities.every((e) => e.sys_status === "active"),
      ).toBe(true);
    });
  },
);
