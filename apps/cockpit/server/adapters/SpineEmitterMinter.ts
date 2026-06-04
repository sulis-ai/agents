// WP-010 (fix-forward) — SpineEmitterMinter: the deterministic server-side mint.
//
// ADR-007 amended: the onboarding MINT and `git init` are deterministic SERVER
// actions, not agent turns. The original confirm→mint delegated the mint to the
// bridge AGENT (a headless `claude -p` that had to hunt for + run the spine
// emitters); live it ran 167s and minted NOTHING. This adapter invokes the
// validated spine-emitter CLIs (`sulis-emit-tenant` / `-product`) + a
// schema-validated Project emit + `git init` DIRECTLY via child_process —
// reliable, fast, and observable.
//
// This is the SECOND sanctioned process-start site in the cockpit (after the
// SessionBridge prod adapter). The read-only gate's per-file process-start rule
// (2b) allow-lists THIS file by path; every other file stays process-free,
// including the onboarding orchestrator (which depends only on the SpineMinter
// port). Entities are written ONLY through the validated adapter (FR-32): no
// freehand entity write — the emitters + emit-project.py validate against the
// vendored schema and reject-on-invalid.
//
// ALL-OR-NOTHING (FR-N11): the three entity emits write into a STAGING brain
// (a temp instances dir); only after all three succeed are the staged entity
// files moved into the real `<sulisStateDir>/.brain/instances`. A failure at
// any step discards the staging dir, so the live graph is left exactly as it
// was — no Product without its Project's source, no dangling Tenant.
//
// IDEMPOTENT (FR-31): the emitters derive deterministic ULIDs from the entity
// names, so a re-mint of the same names overwrites in place and never grows the
// entity count.
//
// Process discipline (mirrors SulisChangeStoreReader): execFile with a string[]
// argv (never a shell string), shell:false, a bounded timeout, and a typed
// failure on non-zero exit / timeout.

import { execFile } from "node:child_process";
import {
  mkdtempSync,
  mkdirSync,
  rmSync,
  writeFileSync,
  existsSync,
  readdirSync,
  renameSync,
  copyFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

import type {
  SpineMinter,
  MintInput,
  MintResult,
  FindOrCreateRepoInput,
} from "../ports/SpineMinter";
import type { RepoOutcome } from "../lib/discovery/repoFindOrCreate";
// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits)
import type { Product } from "../../shared/api-types";

/** The bounded budget for one emitter / git call (a cold python is well under). */
const DEFAULT_TIMEOUT_MS = 30_000;

export interface SpineEmitterMinterOptions {
  /** The spine-emitter scripts dir (resolveEmitterScriptsDir by default). */
  scriptsDir: string;
  /** The active state dir — entities land under `<sulisStateDir>/.brain/instances`. */
  sulisStateDir: string;
  /** Per-call timeout (ms). Defaults to 30s. */
  timeoutMs?: number;
}

/** One captured exec result. */
interface ExecResult {
  ok: boolean;
  stdout: string;
  stderr: string;
}

export class SpineEmitterMinter implements SpineMinter {
  private readonly scriptsDir: string;
  private readonly sulisStateDir: string;
  private readonly timeoutMs: number;

  constructor(opts: SpineEmitterMinterOptions) {
    this.scriptsDir = opts.scriptsDir;
    this.sulisStateDir = opts.sulisStateDir;
    this.timeoutMs = opts.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  }

  /**
   * Find-or-create the repo (FR-35). FIND configures an existing repo (no
   * creation); CREATE runs a real local-only `git init` in the chosen area
   * (ADR-008 founder-locked default). Hosted-remote create is not performed
   * here (a separately-confirmed path); it surfaces as unreachable so the
   * pure module persists no config.
   */
  async findOrCreateRepo(input: FindOrCreateRepoInput): Promise<RepoOutcome> {
    const area = input.chosenArea;
    const mode = input.repoChoice?.mode ?? "find";

    if (mode === "create") {
      const target = input.repoChoice?.createTarget ?? "local";
      if (target !== "local") {
        // Hosted-remote is not the deterministic server path (founder-locked
        // default is local-only). Report unreachable ⇒ no dangling config.
        return { outcome: "unreachable" };
      }
      mkdirSync(area, { recursive: true });
      const init = await this.exec("git", ["init", "--initial-branch=main"], area);
      if (!init.ok || !existsSync(path.join(area, ".git"))) {
        return { outcome: "create-failed" };
      }
      return { outcome: "reachable", repo: area, path: area, primaryBranch: "main" };
    }

    // FIND — the chosen area must exist to be configured.
    if (!existsSync(area)) return { outcome: "unreachable" };
    return { outcome: "reachable", repo: area, path: area, primaryBranch: "main" };
  }

  /**
   * Mint Tenant / Product / Project through the validated emitters into the
   * active brain (FR-32). All-or-nothing (FR-N11) via a staging brain; the
   * staged entities are moved into the real brain only on full success.
   */
  async mint(input: MintInput): Promise<MintResult> {
    const tenantName = input.tenantName.trim() || "Your workspace";
    const productName = input.productName.trim() || "Your product";
    const projectName = (input.projectName || "").trim() || slugify(productName);

    // A temp repo-config dir holds the tenant/product yaml the emitters read.
    // It is sibling-resolved (.sulis/tenant.yaml next to .sulis/products/x.yaml)
    // so the product emitter resolves belongs_to_tenant.
    const configDir = mkdtempSync(path.join(tmpdir(), "spine-cfg-"));
    // The STAGING brain — all three emits write here first (all-or-nothing).
    const stageDir = mkdtempSync(path.join(tmpdir(), "spine-stage-"));
    const stageInstances = path.join(stageDir, ".brain", "instances");

    try {
      const sulisDir = path.join(configDir, ".sulis");
      const productsDir = path.join(sulisDir, "products");
      mkdirSync(productsDir, { recursive: true });
      const tenantYaml = path.join(sulisDir, "tenant.yaml");
      const productYaml = path.join(productsDir, `${slugify(productName)}.yaml`);
      writeFileSync(tenantYaml, `name: ${yamlScalar(tenantName)}\n`);
      writeFileSync(productYaml, `name: ${yamlScalar(productName)}\n`);

      // 1. Tenant.
      const tenant = await this.runEmitter("sulis-emit-tenant", [
        "--from-yaml", tenantYaml,
        "--base-dir", stageInstances,
        "--repo-root", configDir,
      ]);
      if (!tenant.ok) return mintFail(`tenant emit failed: ${tenant.stderr.trim()}`);
      const tenantId = firstEntityId(tenant.stdout);
      if (!tenantId) return mintFail("tenant emit returned no id");

      // 2. Product (resolves belongs_to_tenant from the sibling tenant.yaml).
      const product = await this.runEmitter("sulis-emit-product", [
        "--from-yaml", productYaml,
        "--base-dir", stageInstances,
        "--repo-root", configDir,
      ]);
      if (!product.ok) return mintFail(`product emit failed: ${product.stderr.trim()}`);
      const productId = firstEntityId(product.stdout);
      if (!productId) return mintFail("product emit returned no id");

      // 3. Project (validated emit; carries source + belongs_to_product_ref).
      const sourceJson = JSON.stringify(input.source);
      const projectScript = path.join(spineHelperDir(), "emit-project.py");
      const project = await this.exec(
        "python3",
        [
          projectScript,
          "--scripts-dir", this.scriptsDir,
          "--base-dir", stageInstances,
          "--tenant-id", tenantId,
          "--product-id", productId,
          "--name", projectName,
          "--source-json", sourceJson,
        ],
        configDir,
      );
      if (!project.ok) return mintFail(`project emit failed: ${project.stderr.trim()}`);
      const projectId = firstEntityId(project.stdout);
      if (!projectId) return mintFail("project emit returned no id");

      // ALL succeeded — promote the staged entities into the real brain.
      const realInstances = path.join(this.sulisStateDir, ".brain", "instances");
      promoteStagedEntities(stageInstances, realInstances);

      const mintedProduct: Product = { productId, name: productName };
      return {
        ok: true,
        tenant: tenantName,
        product: mintedProduct,
        project: { projectId, source: input.source },
      };
    } finally {
      rmSync(configDir, { recursive: true, force: true });
      rmSync(stageDir, { recursive: true, force: true });
    }
  }

  /** Run a spine-emitter CLI (a python script under scriptsDir) via python3. */
  private runEmitter(name: string, args: string[]): Promise<ExecResult> {
    const script = path.join(this.scriptsDir, name);
    if (!existsSync(script)) {
      return Promise.resolve({
        ok: false,
        stdout: "",
        stderr: `emitter not found: ${script}`,
      });
    }
    return this.exec("python3", [script, ...args], this.scriptsDir);
  }

  /** execFile with a string[] argv (no shell), bounded timeout, captured I/O. */
  private exec(cmd: string, args: string[], cwd: string): Promise<ExecResult> {
    return new Promise((resolve) => {
      execFile(
        cmd,
        args,
        { cwd, timeout: this.timeoutMs, shell: false },
        (error, stdout, stderr) => {
          if (error) {
            resolve({ ok: false, stdout: stdout ?? "", stderr: stderr || String(error) });
            return;
          }
          resolve({ ok: true, stdout: stdout ?? "", stderr: stderr ?? "" });
        },
      );
    });
  }
}

// ─── pure helpers ────────────────────────────────────────────────────────────

function mintFail(message: string): MintResult {
  return { ok: false, code: "MINT_FAILED", message };
}

/** Parse the first emitted entity id from an emitter's JSON envelope. */
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

/**
 * Move every staged `.jsonld` entity (under `<stage>/<domain>/<kind>/`) into the
 * real brain, preserving the domain/kind layout. The staging step is what makes
 * the mint all-or-nothing: nothing reaches the real brain until all emits pass.
 */
function promoteStagedEntities(stageInstances: string, realInstances: string): void {
  if (!existsSync(stageInstances)) return;
  for (const domain of readdirSync(stageInstances)) {
    const domainDir = path.join(stageInstances, domain);
    for (const kind of readdirSync(domainDir)) {
      const kindDir = path.join(domainDir, kind);
      const destDir = path.join(realInstances, domain, kind);
      mkdirSync(destDir, { recursive: true });
      for (const file of readdirSync(kindDir)) {
        if (!file.endsWith(".jsonld")) continue;
        const from = path.join(kindDir, file);
        const to = path.join(destDir, file);
        try {
          renameSync(from, to);
        } catch {
          // Cross-device rename — fall back to copy (same outcome).
          copyFileSync(from, to);
        }
      }
    }
  }
}

/** Slug from a display name (matches the orchestrator's slugify). */
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

/** The dir holding the bundled spine helper scripts (emit-project.py). */
function spineHelperDir(): string {
  const here = path.dirname(fileURLToPath(import.meta.url));
  return path.join(here, "spine");
}

/**
 * Resolve the spine-emitter scripts dir, mirroring index.ts's helper
 * resolution. Order:
 *   1. `SULIS_EMITTER_SCRIPTS_DIR` env override (tests / CI);
 *   2. the in-repo `plugins/sulis/scripts` (a marketplace checkout);
 *   3. the latest installed plugin cache
 *      (`~/.claude/plugins/cache/.../sulis/<version>/scripts`).
 * Returns the first dir that actually holds `sulis-emit-tenant`, else "".
 */
export function resolveEmitterScriptsDir(): string {
  const override = process.env.SULIS_EMITTER_SCRIPTS_DIR;
  if (override && existsSync(path.join(override, "sulis-emit-tenant"))) {
    return override;
  }

  // In-repo (marketplace checkout): apps/cockpit/server/adapters → repo root.
  const here = path.dirname(fileURLToPath(import.meta.url));
  const repoRoot = path.resolve(here, "..", "..", "..", "..");
  const inRepo = path.join(repoRoot, "plugins", "sulis", "scripts");
  if (existsSync(path.join(inRepo, "sulis-emit-tenant"))) return inRepo;

  // Installed plugin cache — pick the latest version dir that has the emitter.
  const home = process.env.HOME ?? "";
  if (home) {
    const cacheRoot = path.join(home, ".claude", "plugins", "cache");
    const found = latestPluginScriptsDir(cacheRoot);
    if (found) return found;
  }

  return "";
}

/** Find the newest `.../sulis/<version>/scripts` dir holding sulis-emit-tenant. */
function latestPluginScriptsDir(cacheRoot: string): string | null {
  if (!existsSync(cacheRoot)) return null;
  const candidates: string[] = [];
  // Layout: <cacheRoot>/<marketplace>/sulis/<version>/scripts/sulis-emit-tenant
  for (const marketplace of safeReaddir(cacheRoot)) {
    const sulisDir = path.join(cacheRoot, marketplace, "sulis");
    for (const version of safeReaddir(sulisDir)) {
      const scripts = path.join(sulisDir, version, "scripts");
      if (existsSync(path.join(scripts, "sulis-emit-tenant"))) {
        candidates.push(scripts);
      }
    }
  }
  if (candidates.length === 0) return null;
  // Newest version string last (lexical sort is adequate for semver-ish dirs).
  candidates.sort();
  return candidates[candidates.length - 1] ?? null;
}

function safeReaddir(dir: string): string[] {
  try {
    return readdirSync(dir);
  } catch {
    return [];
  }
}
