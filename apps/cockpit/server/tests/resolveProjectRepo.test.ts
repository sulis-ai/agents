// WP-011 — resolveProjectRepo (FR-29/30): productId → Project repo (read-only).
//
// The production resolver start-from-intent uses to find the Product's Project
// repo (the route's default `resolveProject`). It reads the on-disk brain's
// Project entities and reports the full source + whether the working copy is
// present (else clone-first, FR-30). This pins:
//   - a Project with a source.path that has a .git ⇒ present:true;
//   - a Project whose path is absent ⇒ present:false (the route clones first);
//   - an unknown product / empty brain ⇒ null (the route refuses cleanly).

import { describe, it, expect, afterEach } from "vitest";
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { resolveProjectRepo } from "../lib/products/resolveProjectRepo";

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

/** Seed a `dna:project` entity carrying the given source under the brain. */
function seedProject(
  stateDir: string,
  productRef: string,
  source: { repo: string; path: string; primary_branch: string },
): void {
  const dir = join(stateDir, ".brain", "instances", "product-development", "project");
  mkdirSync(dir, { recursive: true });
  writeFileSync(
    join(dir, "p1.jsonld"),
    JSON.stringify({
      "@id": "dna:project:p1",
      belongs_to_product_ref: productRef,
      source: JSON.stringify(source),
    }),
  );
}

describe("resolveProjectRepo", () => {
  it("resolves a Product's Project repo + reports present:true when the path has a .git", async () => {
    const stateDir = tmp("rpr-state-");
    const repo = tmp("rpr-repo-");
    mkdirSync(join(repo, ".git"), { recursive: true }); // a present working copy
    seedProject(stateDir, "dna:product:acme", {
      repo: "git@github.com:acme/checkout.git",
      path: repo,
      primary_branch: "main",
    });

    const resolved = await resolveProjectRepo({
      sulisStateDir: stateDir,
      productId: "dna:product:acme",
    });
    expect(resolved).not.toBeNull();
    expect(resolved?.repo).toBe("git@github.com:acme/checkout.git");
    expect(resolved?.path).toBe(repo);
    expect(resolved?.primaryBranch).toBe("main");
    expect(resolved?.present).toBe(true);
  });

  it("reports present:false when the Project path is absent (so the route clones first, FR-30)", async () => {
    const stateDir = tmp("rpr-state-");
    seedProject(stateDir, "dna:product:acme", {
      repo: "git@github.com:acme/checkout.git",
      path: "/nope/not/here",
      primary_branch: "main",
    });
    const resolved = await resolveProjectRepo({
      sulisStateDir: stateDir,
      productId: "dna:product:acme",
    });
    expect(resolved?.present).toBe(false);
  });

  it("matches a bare-ULID belongs_to_product_ref against the full product id", async () => {
    const stateDir = tmp("rpr-state-");
    const repo = tmp("rpr-repo-");
    mkdirSync(join(repo, ".git"), { recursive: true });
    // The entity carries the BARE ulid; the query carries the full id.
    seedProject(stateDir, "01ACMEULID", {
      repo: repo,
      path: repo,
      primary_branch: "main",
    });
    const resolved = await resolveProjectRepo({
      sulisStateDir: stateDir,
      productId: "dna:product:01ACMEULID",
    });
    expect(resolved).not.toBeNull();
    expect(resolved?.repo).toBe(repo);
  });

  it("returns null for an unknown product / empty brain (the route refuses cleanly)", async () => {
    const stateDir = tmp("rpr-state-");
    const resolved = await resolveProjectRepo({
      sulisStateDir: stateDir,
      productId: "dna:product:nope",
    });
    expect(resolved).toBeNull();
  });
});
