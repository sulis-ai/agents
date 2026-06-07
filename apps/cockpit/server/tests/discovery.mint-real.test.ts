// WP-010 (fix-forward) — REAL deterministic server-side mint (FR-32/36/N11/31).
//
// THE failure this pins: the original confirm→mint delegated the mint to the
// bridge AGENT (a headless `claude -p` that had to hunt for + run the spine
// emitters). Live, it ran 167s and minted NOTHING — yet the recorded-bridge
// integration test passed because it STUBBED the bridge. The stub proved a
// prompt was relayed, not that a graph was minted.
//
// This test drives the REAL SpineEmitterMinter adapter (the deterministic
// server-side mint) against a TEMP SULIS_STATE_DIR + the vendored spine-emitter
// CLIs, and asserts REAL entities land on disk:
//   - a Tenant, a Product, and a Project jsonld actually exist in the temp brain
//     after a confirm (the thing that failed live);
//   - the Project carries source = {repo, path, primary_branch} (FR-36);
//   - the entities are readable by the cockpit's OWN reader (readProducts) — the
//     same reader the board uses — so onboarding actually populates the app;
//   - ALL-OR-NOTHING: an emit failure leaves NO partial graph (FR-N11);
//   - IDEMPOTENT: a re-confirm with the same names does not duplicate (FR-31).
//
// It needs the vendored emitter scripts (tenant/product) + python3. When the
// scripts can't be resolved (a bare checkout with no plugin cache), the suite
// skips with a clear message rather than failing vacuously.

import { describe, it, expect, beforeAll, afterEach } from "vitest";
import { mkdtempSync, rmSync, existsSync, readdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { execFileSync } from "node:child_process";

import {
  SpineEmitterMinter,
  resolveEmitterScriptsDir,
} from "../adapters/SpineEmitterMinter";
import { readProducts } from "../lib/products/readProducts";
import type { ProjectSource } from "../../shared/api-types";

// Real-subprocess budget. Each mint cold-starts python3 THREE times (tenant,
// product, project); the idempotent case does it twice (six spawns). Vitest's
// 5s default per-test timeout cannot cover that even in isolation — and under
// the full parallel `vitest run` (CI's constrained CPU, every fork competing
// for cores) the cold spawns are slower still, so the 5s default is a
// deterministic failure there. We give these REAL tests a generous per-test
// budget (the emitters themselves are bounded at 30s each inside the adapter)
// without weakening any assertion. The fork pool is also CPU-capped (see
// vitest.config.ts) so these spawns are not starved by the rest of the suite.
// Flake #8.
const REAL_SUBPROCESS_TIMEOUT_MS = 120_000;

// ── resolve the vendored emitter scripts (skip cleanly if unavailable) ───────
let scriptsDir: string | null = null;
let havePython = false;
beforeAll(() => {
  scriptsDir = resolveEmitterScriptsDir();
  try {
    execFileSync("python3", ["--version"], { stdio: "ignore" });
    havePython = true;
  } catch {
    havePython = false;
  }
});

// Each test gets its own temp state dir + repo so runs never collide.
const cleanups: string[] = [];
afterEach(() => {
  while (cleanups.length > 0) {
    const dir = cleanups.pop();
    if (dir) rmSync(dir, { recursive: true, force: true });
  }
});

function tmp(prefix: string): string {
  const dir = mkdtempSync(join(tmpdir(), prefix));
  cleanups.push(dir);
  return dir;
}

/** Count `.jsonld` files of one kind across every brain domain. */
function countKind(stateDir: string, kind: string): number {
  const instances = join(stateDir, ".brain", "instances");
  if (!existsSync(instances)) return 0;
  let n = 0;
  for (const domain of readdirSync(instances)) {
    const kindDir = join(instances, domain, kind);
    if (!existsSync(kindDir)) continue;
    n += readdirSync(kindDir).filter((f) => f.endsWith(".jsonld")).length;
  }
  return n;
}

const SOURCE: ProjectSource = {
  repo: "",
  path: "",
  primary_branch: "main",
};

describe("SpineEmitterMinter — the REAL deterministic server-side mint", { timeout: REAL_SUBPROCESS_TIMEOUT_MS }, () => {
  it("mints a real Tenant + Product + Project into the temp brain on confirm (FR-32/36)", async () => {
    if (!scriptsDir || !havePython) {
      // eslint-disable-next-line no-console
      console.warn("skipping: vendored emitter scripts or python3 unavailable");
      return;
    }
    const stateDir = tmp("mint-state-");
    const repo = tmp("mint-repo-");
    const minter = new SpineEmitterMinter({
      scriptsDir,
      sulisStateDir: stateDir,
    });

    const result = await minter.mint({
      tenantName: "Acme Checkout",
      productName: "Acme Checkout",
      projectName: "acme-checkout",
      chosenArea: repo,
      source: { ...SOURCE, repo, path: repo },
    });

    expect(result.ok).toBe(true);

    // REAL entities exist on disk — the thing that failed live.
    expect(countKind(stateDir, "tenant")).toBe(1);
    expect(countKind(stateDir, "product")).toBe(1);
    expect(countKind(stateDir, "project")).toBe(1);

    // The cockpit's OWN reader sees the minted Product (no implicit fallback).
    const { list } = await readProducts({ sulisStateDir: stateDir });
    expect(list.products.length).toBe(1);
    expect(list.products[0]?.name).toBe("Acme Checkout");
    expect(list.products[0]?.productId).not.toBe("dna:product:implicit-single");

    // The Project carries source = {repo, path, primary_branch} (FR-36): the
    // roll-up keys on source.path, so a regression here would orphan changes.
    if (result.ok) {
      expect(result.project.source.repo).toBe(repo);
      expect(result.project.source.path).toBe(repo);
      expect(result.project.source.primary_branch).toBe("main");
    }
  });

  it("is IDEMPOTENT — a re-confirm with the same names does not duplicate (FR-31)", async () => {
    if (!scriptsDir || !havePython) return;
    const stateDir = tmp("mint-state-");
    const repo = tmp("mint-repo-");
    const minter = new SpineEmitterMinter({ scriptsDir, sulisStateDir: stateDir });

    const input = {
      tenantName: "Acme Checkout",
      productName: "Acme Checkout",
      projectName: "acme-checkout",
      chosenArea: repo,
      source: { ...SOURCE, repo, path: repo },
    };

    await minter.mint(input);
    await minter.mint(input); // same names again

    // Deterministic ULIDs ⇒ the second mint overwrites, never grows the count.
    expect(countKind(stateDir, "tenant")).toBe(1);
    expect(countKind(stateDir, "product")).toBe(1);
    expect(countKind(stateDir, "project")).toBe(1);
  });

  it("ALL-OR-NOTHING — an emit failure leaves NO partial graph (FR-N11)", async () => {
    if (!scriptsDir || !havePython) return;
    const stateDir = tmp("mint-state-");
    const repo = tmp("mint-repo-");
    // Point the minter at a bogus scripts dir so the FIRST emit (tenant) fails:
    // nothing must be written anywhere under the state dir.
    const minter = new SpineEmitterMinter({
      scriptsDir: join(repo, "does-not-exist"),
      sulisStateDir: stateDir,
    });

    const result = await minter.mint({
      tenantName: "Acme Checkout",
      productName: "Acme Checkout",
      projectName: "acme-checkout",
      chosenArea: repo,
      source: { ...SOURCE, repo, path: repo },
    });

    expect(result.ok).toBe(false);
    // No dangling graph — neither a tenant, a product, nor a project survives.
    expect(countKind(stateDir, "tenant")).toBe(0);
    expect(countKind(stateDir, "product")).toBe(0);
    expect(countKind(stateDir, "project")).toBe(0);
  });

  it("a CREATE branch runs a real `git init` in the chosen area (deterministic, server-side)", async () => {
    if (!scriptsDir || !havePython) return;
    const stateDir = tmp("mint-state-");
    const repo = tmp("mint-repo-");
    const minter = new SpineEmitterMinter({ scriptsDir, sulisStateDir: stateDir });

    const outcome = await minter.findOrCreateRepo({
      chosenArea: repo,
      repoChoice: { mode: "create", createTarget: "local" },
    });

    expect(outcome.outcome).toBe("reachable");
    // `git init` produced a real .git in the chosen area (local-only, ADR-008).
    expect(existsSync(join(repo, ".git"))).toBe(true);
  });
});
