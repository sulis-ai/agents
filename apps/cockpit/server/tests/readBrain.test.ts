// WP-006 — readBrain(worktreeRoot, changeId) tests (FR-06/07).
//
// readBrain composes a read-only view of the entities the agent created
// for a change: it walks the change worktree's `.brain/instances/<domain>/
// <kind>/<ULID>.jsonld` tree, parses each entity, GROUPS by kind, omits
// empty groups, and returns a BrainView. An absent/empty `.brain` yields
// the empty case `{ changeId, groups: [] }` (FR-06). Each BrainEntity
// carries enough detail for the readable detail view (FR-07): a title
// (resolved from title / name / a decision-like field / the id) and the
// full parsed object as `detail`.
//
// Pure read over the on-disk brain — no process start, no write (the
// same seam discipline as the transcript/status reads).

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtemp, mkdir, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { readBrain } from "../lib/readBrain";
import type { BrainView } from "../../shared/api-types";

let root: string;

async function writeEntity(
  domain: string,
  kind: string,
  ulid: string,
  body: Record<string, unknown>,
): Promise<void> {
  const dir = join(root, ".brain", "instances", domain, kind);
  await mkdir(dir, { recursive: true });
  await writeFile(join(dir, `${ulid}.jsonld`), JSON.stringify(body), "utf8");
}

beforeEach(async () => {
  root = await mkdtemp(join(tmpdir(), "cockpit-brain-"));
});

afterEach(async () => {
  await rm(root, { recursive: true, force: true });
});

describe("readBrain (FR-06/07)", () => {
  it("groups entities by kind and stamps the changeId", async () => {
    await writeEntity("product-development", "requirement", "01AAA", {
      id: "dna:requirement:01AAA",
      title: "Board lists changes in stage columns",
    });
    await writeEntity("product-development", "requirement", "01BBB", {
      id: "dna:requirement:01BBB",
      title: "Send a message to a change's agent",
    });
    await writeEntity("product-development", "decision", "01CCC", {
      id: "dna:decision:01CCC",
      title: "Path A — canonical-as-spec",
    });

    const view: BrainView = await readBrain(root, "01XYZ");

    expect(view.changeId).toBe("01XYZ");
    const group = (kind: string) => view.groups.find((g) => g.kind === kind)!;
    expect(group("requirement").items).toHaveLength(2);
    expect(group("decision").items).toHaveLength(1);
  });

  it("returns the empty case {groups:[]} when there is no .brain", async () => {
    const view = await readBrain(root, "01EMPTY");
    expect(view).toEqual({ changeId: "01EMPTY", groups: [] });
  });

  it("returns the empty case when .brain/instances exists but holds no entities", async () => {
    await mkdir(join(root, ".brain", "instances"), { recursive: true });
    const view = await readBrain(root, "01EMPTY2");
    expect(view.groups).toEqual([]);
  });

  it("carries the kind and id derived from the entity for the detail view", async () => {
    await writeEntity("product-development", "design", "01DDD", {
      id: "dna:design:01DDD",
      state: "draft",
      satisfies: ["dna:requirement:01AAA"],
    });
    const view = await readBrain(root, "01XYZ");
    const design = view.groups.find((g) => g.kind === "design")!;
    const item = design.items[0]!;
    expect(item.id).toBe("dna:design:01DDD");
    expect(item.kind).toBe("design");
    // The full parsed object is available for the readable detail (FR-07).
    expect(item.detail).toMatchObject({ state: "draft" });
  });

  it("resolves a human title from title, then name, then a decision-like field, else the id", async () => {
    await writeEntity("product-development", "requirement", "01TTT", {
      id: "dna:requirement:01TTT",
      title: "Has an explicit title",
    });
    await writeEntity("product-development", "scenario", "01NNN", {
      id: "dna:scenario:01NNN",
      name: "Named, not titled",
    });
    await writeEntity("product-development", "decision", "01KKK", {
      id: "dna:decision:01KKK",
      decision: "The chosen path is X",
    });
    await writeEntity("product-development", "workflow", "01III", {
      id: "dna:workflow:01III",
    });

    const view = await readBrain(root, "01XYZ");
    const title = (kind: string) =>
      view.groups.find((g) => g.kind === kind)!.items[0]!.title;

    expect(title("requirement")).toBe("Has an explicit title");
    expect(title("scenario")).toBe("Named, not titled");
    expect(title("decision")).toContain("The chosen path is X");
    // No title/name/decision → falls back to the id (never empty).
    expect(title("workflow")).toBe("dna:workflow:01III");
  });

  it("skips non-entity sidecars like .journal.md and never throws on them", async () => {
    const dir = join(
      root,
      ".brain",
      "instances",
      "product-development",
      "lifecyclerun",
    );
    await mkdir(dir, { recursive: true });
    await writeFile(join(dir, "01RUN.journal.md"), "# a journal\n", "utf8");
    await writeFile(
      join(dir, "01RUN.jsonld"),
      JSON.stringify({ id: "dna:lifecyclerun:01RUN" }),
      "utf8",
    );

    const view = await readBrain(root, "01XYZ");
    const run = view.groups.find((g) => g.kind === "lifecyclerun")!;
    // Only the .jsonld is counted; the .journal.md is ignored.
    expect(run.items).toHaveLength(1);
    expect(run.items[0]!.id).toBe("dna:lifecyclerun:01RUN");
  });

  it("merges the same kind across different domains into one group", async () => {
    await writeEntity("foundation", "workflow", "01WA", {
      id: "dna:workflow:01WA",
      title: "Foundation workflow",
    });
    await writeEntity("product-development", "workflow", "01WB", {
      id: "dna:workflow:01WB",
      title: "Product workflow",
    });
    const view = await readBrain(root, "01XYZ");
    const workflows = view.groups.filter((g) => g.kind === "workflow");
    expect(workflows).toHaveLength(1);
    expect(workflows[0]!.items).toHaveLength(2);
  });

  it("hides soft-deleted entities (sys_status not active) — ADR-020 invariant", async () => {
    await writeEntity("product-development", "product", "01ACTIVE", {
      id: "dna:product:01ACTIVE",
      name: "Live product",
      sys_status: "active",
    });
    await writeEntity("product-development", "product", "01GONE", {
      id: "dna:product:01GONE",
      name: "Removed product",
      sys_status: "deleted",
    });
    await writeEntity("product-development", "product", "01LEGACY", {
      // legacy entity with no sys_status → still active (absence ≠ deleted).
      id: "dna:product:01LEGACY",
      name: "Legacy product",
    });

    const view = await readBrain(root, "01XYZ");
    const products = view.groups.find((g) => g.kind === "product");
    const ids = (products?.items ?? []).map((i) => i.id).sort();

    // The soft-deleted one is gone; active + legacy remain.
    expect(ids).toEqual(["dna:product:01ACTIVE", "dna:product:01LEGACY"]);
  });

  it("tolerates a malformed entity file without failing the whole read", async () => {
    await writeEntity("product-development", "requirement", "01GOOD", {
      id: "dna:requirement:01GOOD",
      title: "Good one",
    });
    const dir = join(
      root,
      ".brain",
      "instances",
      "product-development",
      "requirement",
    );
    await writeFile(join(dir, "01BAD.jsonld"), "{ not json", "utf8");

    const view = await readBrain(root, "01XYZ");
    const reqs = view.groups.find((g) => g.kind === "requirement")!;
    // The good entity still surfaces; the malformed one is skipped.
    expect(reqs.items).toHaveLength(1);
    expect(reqs.items[0]!.id).toBe("dna:requirement:01GOOD");
  });
});
