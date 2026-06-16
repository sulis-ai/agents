// WP-005 — SpineSettingsAdapter: the single sanctioned SettingsStore writer
// (TDD §2.1/§6/§7; ADR-019/020/021).
//
// This is the ONLY new process-start site in the change (ADR-019) — the
// read-only gate allow-lists THIS file by path, exactly as SpineEmitterMinter
// is. It implements the domain-owned `SettingsStore` port (WP-002) by driving
// the validated Python helpers (WP-004) into the brain instance store. It NEVER
// hand-builds a schema entity (ADR-007): every write goes through a helper that
// validates against the vendored schema and rejects-on-invalid.
//
//   readTree        → list-entities.py (active allow-list), projected to the
//                     SettingsTree wire shape.
//   upsertProduct   → create: sulis-emit-product (deterministic ULID from name);
//                     edit (id): edit-product.py.
//   upsertProject   → create: emit-project.py; edit (id): edit-project.py.
//   removeProduct/  → set-entity-status.py --status deleted (a FIELD mutation;
//   removeProject     the .jsonld file stays on disk — ADR-020, never a delete).
//   attachRepo      → existsSync(localPath) read-only check, then edit-project.py
//                     --source-json (the gate-fix path that lets attach/unlink
//                     mutate Project.source through the validated upsert).
//   unlinkRepo      → edit-project.py --source-json with the empty-link shape.
//
// Process discipline mirrors SpineEmitterMinter: execFile with a string[] argv
// (never a shell string), shell:false, a bounded DEFAULT_TIMEOUT_MS (30s), and a
// typed `WRITE_FAILED` on non-zero exit / timeout (never an opaque throw).
//
// SECURITY — path-confinement (CONCERN-1, gate fix). Request-controlled segments
// (the entity ids the router passes through) are validated against the dna id
// pattern BEFORE any helper runs, and the extracted ULID is checked for
// traversal (`..`, `/`, `\`, leading separators). The resolved instance path is
// asserted to stay under the adapter's base dir. A `../`-laden id is rejected
// with a typed error and nothing is read or written outside base_dir.

import { execFile } from "node:child_process";
import {
  mkdtempSync,
  rmSync,
  writeFileSync,
  mkdirSync,
  existsSync,
} from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

import type {
  SettingsStore,
  SettingsTree,
  ProductWrite,
  ProjectWrite,
  RepoAttachWrite,
  SettingsProduct,
  SettingsProject,
} from "../ports/SettingsStore";
import { SettingsStoreError } from "../ports/SettingsStore";
import { activeSortedByName } from "./settingsActiveSort";

/** The bounded budget for one helper call (a cold python is well under). */
const DEFAULT_TIMEOUT_MS = 30_000;

/** The brain domains each kind lives under (mirrors readProducts/resolveProjectRepo). */
const PRODUCT_DOMAIN = "product-development";
const PROJECT_DOMAIN = "foundation";

/** The default tenant a fresh-brain product/project hangs off. Matches
 *  SpineEmitterMinter's "Your workspace" so the deterministic tenant ULID is
 *  identical across mint surfaces. */
const DEFAULT_TENANT_NAME = "Your workspace";

/** The default primary branch a freshly-attached repo reports (ADR-021). */
const DEFAULT_PRIMARY_BRANCH = "main";

/** The empty-link `Project.source` shape unlink persists (TDD §3.4). */
const EMPTY_SOURCE = { repo: "", path: "", primary_branch: "" };

/** The id patterns the schemas enforce — Crockford-base32 ULID (ADR-020). The
 *  adapter validates request-controlled ids against these BEFORE any helper
 *  runs (path-confinement, CONCERN-1). */
const PRODUCT_ID_RE = /^dna:product:[0-9A-HJKMNP-TV-Z]{26}$/;
const PROJECT_ID_RE = /^dna:project:[0-9A-HJKMNP-TV-Z]{26}$/;
/** A change id is the bare Crockford-base32 ULID (the cockpit's `changeId`). */
const CHANGE_ULID_RE = /^[0-9A-HJKMNP-TV-Z]{26}$/;

/** A structured log entry the adapter emits per write (and on a write error). */
export type SettingsLogEntry = Record<string, unknown>;

export interface SpineSettingsAdapterOptions {
  /** The vendored adapter scripts dir (`_entity_adapter_local.py` lives here). */
  scriptsDir: string;
  /** The brain instances dir: `<state>/.brain/instances`. */
  baseDir: string;
  /** The change store dir: `<state>/changes`. Used to compose a Change entity
   *  for a change that has no brain record yet (per-change product assignment). */
  changesDir?: string;
  /** Override for the bundled spine helper dir (tests inject a stub here). */
  spineDir?: string;
  /** Per-call timeout (ms). Defaults to 30s. */
  timeoutMs?: number;
  /** Sink for the per-write structured log line. Defaults to a JSON line on
   *  stderr. Injected by tests to assert the audit trail. */
  log?: (entry: SettingsLogEntry) => void;
}

/** Default log sink: one JSON line per entry on stderr (fail-soft — a logging
 *  failure must never break a write). */
function defaultLog(entry: SettingsLogEntry): void {
  try {
    process.stderr.write(`${JSON.stringify(entry)}\n`);
  } catch {
    /* logging is best-effort; never throw out of the write path */
  }
}

/** One captured exec result. */
interface ExecResult {
  ok: boolean;
  stdout: string;
  stderr: string;
}

/** A brain entity as read back from `list-entities.py`. */
type BrainEntity = Record<string, unknown>;

export class SpineSettingsAdapter implements SettingsStore {
  private readonly scriptsDir: string;
  private readonly baseDir: string;
  private readonly changesDir: string;
  private readonly spineDir: string;
  private readonly timeoutMs: number;
  private readonly log: (entry: SettingsLogEntry) => void;

  constructor(opts: SpineSettingsAdapterOptions) {
    this.scriptsDir = opts.scriptsDir;
    this.baseDir = path.resolve(opts.baseDir);
    // Default the change store to the sibling of the brain home
    // (`<state>/changes` next to `<state>/.brain/instances`).
    this.changesDir =
      opts.changesDir ?? path.resolve(opts.baseDir, "..", "..", "changes");
    this.spineDir = opts.spineDir ?? defaultSpineDir();
    this.timeoutMs = opts.timeoutMs ?? DEFAULT_TIMEOUT_MS;
    this.log = opts.log ?? defaultLog;
  }

  // ─── change → product assignment ──────────────────────────────────────────

  /**
   * Assign a change to a Product by setting `for_product` on its brain Change
   * entity (the authoritative link the board scopes by). Drives the sanctioned
   * `set-change-product.py` helper — a validated read-modify-save, composing a
   * Change entity from the change's record when none exists yet. The product id
   * is validated against the ULID pattern BEFORE the helper runs (path-
   * confinement parity with the settings writes). Returns the saved id + link.
   */
  async assignChangeProduct(
    changeId: string,
    productId: string,
  ): Promise<{ id: string; forProduct: string }> {
    if (!CHANGE_ULID_RE.test(changeId)) {
      throw new SettingsStoreError("VALIDATION_FAILED", "invalid change id");
    }
    if (!PRODUCT_ID_RE.test(productId)) {
      throw new SettingsStoreError("VALIDATION_FAILED", "invalid product id");
    }
    const stdout = await this.runHelper(
      this.spineScript("set-change-product.py"),
      [
        "--base-dir", this.baseDir,
        "--change-id", changeId,
        "--for-product", productId,
        "--changes-dir", this.changesDir,
      ],
    );
    let id = `dna:change:${changeId}`;
    try {
      const parsed = JSON.parse(stdout) as { data?: { id?: unknown } };
      if (typeof parsed.data?.id === "string") id = parsed.data.id;
    } catch {
      /* the helper already succeeded (runHelper unwraps non-zero); keep the
         derived id if the envelope shape ever drifts. */
    }
    this.logWrite("assign-change-product", { changeId, productId });
    return { id, forProduct: productId };
  }

  // ─── reads ─────────────────────────────────────────────────────────────

  async readTree(): Promise<SettingsTree> {
    const rawProducts = await this.listEntities(PRODUCT_DOMAIN, "product");
    const rawProjects = await this.listEntities(PROJECT_DOMAIN, "project");

    // ADVISORY 3: `list-entities.py`'s `sys_status == "active"` allow-list is
    // the AUTHORITATIVE active filter (it runs in Python, the single write
    // surface). The `activeSortedByName` pass below is the SAME allow-list
    // (shared WP-002 primitive) applied again as sort + belt-and-braces, so a
    // future status-rule change is not made in only one place — the two layers
    // agree by construction. `status` here is the entity's `sys_status`.
    const projectRows = rawProjects.map(toProjectRow);
    const productRows = rawProducts.map((p) => toProductRow(p, projectRows));

    const products = activeSortedByName(productRows).map((row) => ({
      productId: row.productId,
      name: row.name,
      editable: row.editable,
      projects: activeSortedByName(row.projectRows).map(rowToSettingsProject),
    }));

    return { products };
  }

  // ─── product writes ──────────────────────────────────────────────────────

  async upsertProduct(input: ProductWrite): Promise<SettingsProduct> {
    const name = input.name.trim();
    this.assertName(name, "product");

    if (input.productId !== undefined) {
      this.assertId(input.productId, PRODUCT_ID_RE, "product");
      await this.runHelper(this.spineScript("edit-product.py"), [
        "--base-dir", this.baseDir,
        "--domain", PRODUCT_DOMAIN,
        "--id", input.productId,
        "--name", name,
      ]);
      this.logWrite("edit-product", { productId: input.productId });
    } else {
      await this.mintProduct(name);
      this.logWrite("create-product", { name });
    }

    return this.requireProductInTree(input.productId, name);
  }

  async removeProduct(productId: string): Promise<void> {
    this.assertId(productId, PRODUCT_ID_RE, "product");
    await this.setStatus(PRODUCT_DOMAIN, "product", productId, "deleted");
    this.logWrite("remove-product", { productId });
  }

  // ─── project writes ──────────────────────────────────────────────────────

  async upsertProject(input: ProjectWrite): Promise<SettingsProject> {
    const name = input.name.trim();
    this.assertName(name, "project");

    if (input.projectId !== undefined) {
      this.assertId(input.projectId, PROJECT_ID_RE, "project");
      await this.runHelper(this.spineScript("edit-project.py"), [
        "--base-dir", this.baseDir,
        "--domain", PROJECT_DOMAIN,
        "--id", input.projectId,
        "--name", name,
      ]);
      this.logWrite("edit-project", { projectId: input.projectId });
      return this.requireProject(input.projectId);
    }

    this.assertId(input.productId, PRODUCT_ID_RE, "product");
    const tenantId = await this.tenantOf(input.productId);
    const stdout = await this.runHelper(this.spineScript("emit-project.py"), [
      "--base-dir", this.baseDir,
      "--tenant-id", tenantId,
      "--product-id", input.productId,
      "--name", name,
      "--source-json", JSON.stringify(EMPTY_SOURCE),
    ]);
    const projectId = firstEntityId(stdout);
    if (!projectId) {
      throw new SettingsStoreError(
        "WRITE_FAILED",
        "project emit returned no id",
      );
    }
    this.logWrite("create-project", { projectId, productId: input.productId });
    return this.requireProject(projectId);
  }

  async removeProject(projectId: string): Promise<void> {
    this.assertId(projectId, PROJECT_ID_RE, "project");
    await this.setStatus(PROJECT_DOMAIN, "project", projectId, "deleted");
    this.logWrite("remove-project", { projectId });
  }

  // ─── repo link ────────────────────────────────────────────────────────────

  async attachRepo(input: RepoAttachWrite): Promise<SettingsProject> {
    this.assertId(input.projectId, PROJECT_ID_RE, "project");

    // ADR-021 + ADVISORY 4: resolve to absolute and reject relative / traversal
    // paths BEFORE any disk read or write — we only ever record the path, never
    // write into the founder's folder.
    if (!path.isAbsolute(input.localPath)) {
      throw new SettingsStoreError(
        "PATH_NOT_FOUND",
        `localPath must be an absolute path: ${input.localPath}`,
      );
    }
    const localPath = path.resolve(input.localPath);
    if (localPath.split(path.sep).includes("..")) {
      // path.resolve already collapses `..`; this is defence-in-depth in case a
      // platform leaves a literal `..` segment (e.g. an odd separator).
      throw new SettingsStoreError(
        "PATH_NOT_FOUND",
        `localPath must not contain traversal segments: ${input.localPath}`,
      );
    }

    // Read-only against disk (existsSync) — the ONLY disk access to the
    // founder's folder (ADR-021). A missing path is a typed PATH_NOT_FOUND with
    // no write.
    if (!existsSync(localPath)) {
      throw new SettingsStoreError(
        "PATH_NOT_FOUND",
        `path ${localPath} does not exist`,
      );
    }

    // Record the local attach in Project.source through the validated upsert —
    // local attach uses the path as the repo, matching SpineEmitterMinter's
    // FIND branch (`repo: area`). A folder without .git still attaches with
    // present:false (computed at read time).
    const source = JSON.stringify({
      repo: localPath,
      path: localPath,
      primary_branch: DEFAULT_PRIMARY_BRANCH,
    });
    await this.editProjectSource(input.projectId, source);
    this.logWrite("attach-repo", { projectId: input.projectId, localPath });
    return this.requireProject(input.projectId);
  }

  async unlinkRepo(projectId: string): Promise<SettingsProject> {
    this.assertId(projectId, PROJECT_ID_RE, "project");
    await this.editProjectSource(projectId, JSON.stringify(EMPTY_SOURCE));
    this.logWrite("unlink-repo", { projectId });
    return this.requireProject(projectId);
  }

  // ─── internals ────────────────────────────────────────────────────────────

  /** Edit ONLY Project.source through the validated upsert (the gate-fix path). */
  private editProjectSource(projectId: string, sourceJson: string): Promise<string> {
    return this.runHelper(this.spineScript("edit-project.py"), [
      "--base-dir", this.baseDir,
      "--domain", PROJECT_DOMAIN,
      "--id", projectId,
      "--source-json", sourceJson,
    ]);
  }

  /** Mint a fresh Product via the validated `sulis-emit-product` CLI. Writes a
   *  temp `.sulis/tenant.yaml` + `.sulis/products/{slug}.yaml` (the emitter
   *  resolves belongs_to_tenant from the sibling tenant.yaml), exactly as
   *  SpineEmitterMinter does. Idempotent: deterministic ULID from the name. */
  private async mintProduct(name: string): Promise<void> {
    const configDir = mkdtempSync(path.join(tmpdir(), "spine-settings-cfg-"));
    try {
      const sulisDir = path.join(configDir, ".sulis");
      const productsDir = path.join(sulisDir, "products");
      mkdirSync(productsDir, { recursive: true });
      writeFileSync(
        path.join(sulisDir, "tenant.yaml"),
        `name: ${yamlScalar(DEFAULT_TENANT_NAME)}\n`,
      );
      const productYaml = path.join(productsDir, `${slugify(name)}.yaml`);
      writeFileSync(productYaml, `name: ${yamlScalar(name)}\n`);

      await this.runEmitter("sulis-emit-product", [
        "--from-yaml", productYaml,
        "--base-dir", this.baseDir,
        "--repo-root", configDir,
      ]);
    } finally {
      rmSync(configDir, { recursive: true, force: true });
    }
  }

  /** Resolve a Product's `belongs_to_tenant` by reading it back from the active
   *  store. `belongs_to_tenant` is a schema-required field, so an active product
   *  always carries it; a missing product (or a corrupt entity without the ref)
   *  is a typed NOT_FOUND rather than a silent default. */
  private async tenantOf(productId: string): Promise<string> {
    const products = await this.listEntities(PRODUCT_DOMAIN, "product");
    const match = products.find((p) => p.id === productId);
    const ref = match?.belongs_to_tenant;
    if (typeof ref === "string" && ref.length > 0) return ref;
    throw new SettingsStoreError(
      "NOT_FOUND",
      `product ${productId} not found (cannot resolve its tenant)`,
    );
  }

  /** Soft-delete / lifecycle status mutation via set-entity-status.py. */
  private setStatus(
    domain: string,
    kind: string,
    id: string,
    status: string,
  ): Promise<string> {
    return this.runHelper(this.spineScript("set-entity-status.py"), [
      "--base-dir", this.baseDir,
      "--domain", domain,
      "--kind", kind,
      "--id", id,
      "--status", status,
    ]);
  }

  /** Walk `{base}/{domain}/{kind}/*.jsonld` for ACTIVE entities via the
   *  validated read helper. */
  private async listEntities(domain: string, kind: string): Promise<BrainEntity[]> {
    const stdout = await this.runHelper(this.spineScript("list-entities.py"), [
      "--base-dir", this.baseDir,
      "--domain", domain,
      "--kind", kind,
    ]);
    try {
      const parsed = JSON.parse(stdout) as {
        ok?: boolean;
        data?: { entities?: BrainEntity[] };
      };
      return parsed.ok === true ? (parsed.data?.entities ?? []) : [];
    } catch {
      return [];
    }
  }

  private async requireProject(projectId: string): Promise<SettingsProject> {
    const tree = await this.readTree();
    for (const product of tree.products) {
      const project = product.projects.find((pr) => pr.projectId === projectId);
      if (project) return project;
    }
    throw new SettingsStoreError(
      "NOT_FOUND",
      `project ${projectId} not found after write`,
    );
  }

  /** Re-read the tree and return the product just written. On create the id is
   *  unknown until mint, so we fall back to matching by (active) name. */
  private async requireProductInTree(
    productId: string | undefined,
    name: string,
  ): Promise<SettingsProduct> {
    const tree = await this.readTree();
    const match =
      productId !== undefined
        ? tree.products.find((p) => p.productId === productId)
        : tree.products.find((p) => p.name === name);
    if (!match) {
      throw new SettingsStoreError(
        "NOT_FOUND",
        `product ${productId ?? name} not found after write`,
      );
    }
    return match;
  }

  /** Run a bundled spine helper (a python script) argv-only; non-zero exit /
   *  timeout / a non-ok envelope maps to a typed WRITE_FAILED. Returns stdout. */
  private async runHelper(script: string, args: string[]): Promise<string> {
    const result = await this.exec("python3", [
      script,
      "--scripts-dir", this.scriptsDir,
      ...args,
    ]);
    return this.unwrap(result, script);
  }

  /** Run a vendored emitter CLI (under scriptsDir) argv-only. */
  private async runEmitter(name: string, args: string[]): Promise<string> {
    const script = path.join(this.scriptsDir, name);
    const result = await this.exec("python3", [script, ...args]);
    return this.unwrap(result, name);
  }

  /** Map an ExecResult to stdout or a typed WRITE_FAILED. A helper emits a
   *  `{"ok": false}` envelope on a schema reject (exit 1) — also WRITE_FAILED.
   *
   *  SECURITY (CWE-209): the raw helper stderr can carry absolute filesystem
   *  paths, tracebacks, and internal exception text. It is logged server-side
   *  (the audit trail) but NEVER returned to the client — the client message is
   *  a fixed, opaque string so no internal detail leaks over the HTTP envelope. */
  private unwrap(result: ExecResult, label: string): string {
    if (!result.ok) {
      const detail = result.stderr.trim() || result.stdout.trim();
      this.log({
        evt: "settings-write-error",
        op: path.basename(label),
        detail,
      });
      throw new SettingsStoreError(
        "WRITE_FAILED",
        "the settings write failed — see the server log for details",
      );
    }
    return result.stdout;
  }

  /** execFile with a string[] argv (no shell), bounded timeout, captured I/O. */
  private exec(cmd: string, args: string[]): Promise<ExecResult> {
    return new Promise((resolve) => {
      execFile(
        cmd,
        args,
        { timeout: this.timeoutMs, shell: false },
        (error, stdout, stderr) => {
          if (error) {
            resolve({
              ok: false,
              stdout: stdout ?? "",
              stderr: stderr || String(error),
            });
            return;
          }
          resolve({ ok: true, stdout: stdout ?? "", stderr: stderr ?? "" });
        },
      );
    });
  }

  /** Absolute path of a bundled spine helper. */
  private spineScript(name: string): string {
    return path.join(this.spineDir, name);
  }

  /** Emit one structured audit line per successful write op. Fail-soft. */
  private logWrite(op: string, fields: SettingsLogEntry): void {
    this.log({ evt: "settings-write", op, ...fields });
  }

  /**
   * Validate a request-controlled display name. Empty (after trim) is a typed
   * VALIDATION_FAILED. A LEADING HYPHEN is also rejected: the python helper's
   * argparse would read `--name -Foo` as a flag (exit 2 → an opaque
   * WRITE_FAILED), so we reject it up front with a clear, founder-readable
   * message instead of letting it fail obscurely downstream.
   */
  private assertName(name: string, kind: string): void {
    if (!name) {
      throw new SettingsStoreError(
        "VALIDATION_FAILED",
        `a non-empty ${kind} name is required`,
      );
    }
    if (name.startsWith("-")) {
      throw new SettingsStoreError(
        "VALIDATION_FAILED",
        `a ${kind} name cannot start with a hyphen: ${name}`,
      );
    }
  }

  /**
   * Validate a request-controlled entity id (CONCERN-1 path-confinement). The
   * id MUST match the schema's dna pattern, its extracted ULID MUST carry no
   * traversal (`..`, `/`, `\`, leading separator), and the resolved on-disk
   * instance path MUST stay under base_dir. Rejection is a typed
   * `VALIDATION_FAILED` BEFORE any helper runs — nothing escapes base_dir.
   */
  private assertId(id: string, pattern: RegExp, kind: string): void {
    if (typeof id !== "string" || !pattern.test(id)) {
      throw new SettingsStoreError(
        "VALIDATION_FAILED",
        `invalid ${kind} id (must match ${pattern.source}): ${id}`,
      );
    }
    const ulid = id.split(":").pop() ?? "";
    if (
      ulid.length === 0 ||
      ulid.includes("..") ||
      ulid.includes("/") ||
      ulid.includes("\\") ||
      ulid.startsWith(path.sep)
    ) {
      throw new SettingsStoreError(
        "VALIDATION_FAILED",
        `invalid ${kind} id segment: ${id}`,
      );
    }
    const domain = kind === "product" ? PRODUCT_DOMAIN : PROJECT_DOMAIN;
    const resolved = path.resolve(this.baseDir, domain, kind, `${ulid}.jsonld`);
    const confine = path.resolve(this.baseDir, domain, kind) + path.sep;
    if (!resolved.startsWith(confine)) {
      throw new SettingsStoreError(
        "VALIDATION_FAILED",
        `${kind} id resolves outside base_dir: ${id}`,
      );
    }
  }
}

// ─── pure helpers ────────────────────────────────────────────────────────────

/** A product entity → a sortable/projectable row (status mirrors sys_status). */
interface ProductRow {
  productId: string;
  name: string;
  editable: boolean;
  status: string;
  projectRows: ProjectRow[];
}

/** A project entity → a sortable/projectable row. */
interface ProjectRow {
  projectId: string;
  productId: string;
  name: string;
  status: string;
  repo: { localPath: string; primaryBranch: string } | null;
}

/** Read a string field off an untyped brain entity, falling back when absent or
 *  non-string. Extracted at the 2-consumer threshold (both row mappers below
 *  read id/name/status/ref this way) so the coercion lives once (EP-03). */
function strField(entity: BrainEntity, key: string, fallback = ""): string {
  const value = entity[key];
  return typeof value === "string" ? value : fallback;
}

function toProjectRow(entity: BrainEntity): ProjectRow {
  const ref = strField(entity, "belongs_to_product_ref");
  const productId = ref.startsWith("dna:product:") ? ref : `dna:product:${ref}`;
  return {
    projectId: strField(entity, "id"),
    productId,
    name: strField(entity, "name"),
    status: strField(entity, "sys_status", "active"),
    repo: parseRepo(entity.source),
  };
}

function toProductRow(entity: BrainEntity, allProjects: ProjectRow[]): ProductRow {
  const productId = strField(entity, "id");
  return {
    productId,
    name: strField(entity, "name"),
    editable: true,
    status: strField(entity, "sys_status", "active"),
    projectRows: allProjects.filter((pr) => pr.productId === productId),
  };
}

function rowToSettingsProject(row: ProjectRow): SettingsProject {
  return {
    projectId: row.projectId,
    name: row.name,
    repo: row.repo
      ? {
          localPath: row.repo.localPath,
          primaryBranch: row.repo.primaryBranch,
          present: existsSync(path.join(row.repo.localPath, ".git")),
        }
      : null,
  };
}

/** Project.source is a JSON-encoded `{repo, path, primary_branch}` string. An
 *  empty path (the unlink shape) yields a null repo link. */
function parseRepo(
  source: unknown,
): { localPath: string; primaryBranch: string } | null {
  if (typeof source !== "string" || source.length === 0) return null;
  try {
    const parsed = JSON.parse(source) as {
      path?: unknown;
      primary_branch?: unknown;
    };
    const localPath = typeof parsed.path === "string" ? parsed.path : "";
    if (localPath.length === 0) return null;
    const primaryBranch =
      typeof parsed.primary_branch === "string" && parsed.primary_branch.length > 0
        ? parsed.primary_branch
        : DEFAULT_PRIMARY_BRANCH;
    return { localPath, primaryBranch };
  } catch {
    return null;
  }
}

/** Parse the first emitted entity id from a helper's JSON envelope. */
function firstEntityId(stdout: string): string | null {
  try {
    const parsed = JSON.parse(stdout) as {
      ok?: boolean;
      data?: { id?: string; entities?: Array<{ id?: string }> };
    };
    if (parsed.ok !== true || !parsed.data) return null;
    if (typeof parsed.data.id === "string") return parsed.data.id;
    const id = parsed.data.entities?.[0]?.id;
    return typeof id === "string" ? id : null;
  } catch {
    return null;
  }
}

/** Slug from a display name (matches SpineEmitterMinter's slugify). */
function slugify(name: string): string {
  return (
    name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "product"
  );
}

/** Quote a yaml scalar so a name with `:` / leading spaces stays one value. */
function yamlScalar(value: string): string {
  return JSON.stringify(value);
}

/** The dir holding the bundled spine helper scripts (edit/list/status/emit). */
function defaultSpineDir(): string {
  const here = path.dirname(fileURLToPath(import.meta.url));
  return path.join(here, "spine");
}
