// WP-002 — readRigorForStage.ts unit tests (BR-12 / BR-11 / MUC-4).
//
// Best-effort, read-only, never-throws (mirrors detectOpenBlocker). Encodes
// the per-stage required-artifact rule (BR-12):
//   - Specify / Design → a spec exists (.specifications/<project>/SRD.md).
//   - Implement        → a design OR plan exists (.architecture/<project>/
//                        TDD.md OR a work-packages/ dir).
//   - Review / Ship    → tests exist alongside the code (a *.test.* file or
//                        a tests/ dir somewhere outside the architecture +
//                        specification trees).
//   - Recon            → no required artifact (never off-track on rigor).
//
// Returns { ok, missing, determinable }:
//   - dir readable + rule resolves → determinable:true, ok per the rule.
//   - worktree gone / unreadable / rule can't resolve → { ok:true,
//     missing:null, determinable:false } (can't prove drift ⇒ don't flag
//     off-track on absence alone; this feeds the FR-31 unknown read).
//   - path containment (MUC-4): reads stay inside the change's own worktree
//     via safeJoin; a containment violation fails soft to determinable:false.

import { describe, it, expect } from "vitest";
import { mkdtemp, rm, mkdir, writeFile, symlink } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { readRigorForStage } from "../lib/readRigorForStage";

async function makeWorktree(): Promise<string> {
  return await mkdtemp(join(tmpdir(), "wt-rigor-"));
}

async function seedSpec(wt: string): Promise<void> {
  const dir = join(wt, ".specifications", "demo");
  await mkdir(dir, { recursive: true });
  await writeFile(join(dir, "SRD.md"), "# spec", "utf8");
}

async function seedTdd(wt: string): Promise<void> {
  const dir = join(wt, ".architecture", "demo");
  await mkdir(dir, { recursive: true });
  await writeFile(join(dir, "TDD.md"), "# design", "utf8");
}

async function seedWorkPackages(wt: string): Promise<void> {
  const dir = join(wt, ".architecture", "demo", "work-packages");
  await mkdir(dir, { recursive: true });
  await writeFile(join(dir, "WP-001.md"), "# plan", "utf8");
}

async function seedTests(wt: string): Promise<void> {
  const dir = join(wt, "src");
  await mkdir(dir, { recursive: true });
  await writeFile(join(dir, "thing.test.ts"), "// a test", "utf8");
}

describe("readRigorForStage — Specify/Design require a spec", () => {
  it("spec present → ok, determinable", async () => {
    const wt = await makeWorktree();
    try {
      await seedSpec(wt);
      const r = await readRigorForStage(wt, "specify");
      expect(r).toEqual({ ok: true, missing: null, determinable: true });
    } finally {
      await rm(wt, { recursive: true, force: true });
    }
  });

  it("design stage with a spec → ok", async () => {
    const wt = await makeWorktree();
    try {
      await seedSpec(wt);
      const r = await readRigorForStage(wt, "design");
      expect(r.ok).toBe(true);
      expect(r.determinable).toBe(true);
    } finally {
      await rm(wt, { recursive: true, force: true });
    }
  });

  it("specify with NO spec → off-track on rigor (ok:false, missing names spec)", async () => {
    const wt = await makeWorktree();
    try {
      // empty worktree — no .specifications dir
      const r = await readRigorForStage(wt, "specify");
      expect(r.ok).toBe(false);
      expect(r.missing).toBe("spec");
      expect(r.determinable).toBe(true);
    } finally {
      await rm(wt, { recursive: true, force: true });
    }
  });
});

describe("readRigorForStage — Implement requires a design or plan", () => {
  it("a TDD design present → ok", async () => {
    const wt = await makeWorktree();
    try {
      await seedTdd(wt);
      const r = await readRigorForStage(wt, "implement");
      expect(r).toEqual({ ok: true, missing: null, determinable: true });
    } finally {
      await rm(wt, { recursive: true, force: true });
    }
  });

  it("a work-packages plan present → ok", async () => {
    const wt = await makeWorktree();
    try {
      await seedWorkPackages(wt);
      const r = await readRigorForStage(wt, "implement");
      expect(r.ok).toBe(true);
      expect(r.determinable).toBe(true);
    } finally {
      await rm(wt, { recursive: true, force: true });
    }
  });

  it("implement with neither design nor plan → off-track, missing names design", async () => {
    const wt = await makeWorktree();
    try {
      const r = await readRigorForStage(wt, "implement");
      expect(r.ok).toBe(false);
      expect(r.missing).toBe("design");
      expect(r.determinable).toBe(true);
    } finally {
      await rm(wt, { recursive: true, force: true });
    }
  });
});

describe("readRigorForStage — Review/Ship require tests alongside code", () => {
  it("a *.test.* file present → ok", async () => {
    const wt = await makeWorktree();
    try {
      await seedTests(wt);
      const r = await readRigorForStage(wt, "review");
      expect(r.ok).toBe(true);
      expect(r.determinable).toBe(true);
    } finally {
      await rm(wt, { recursive: true, force: true });
    }
  });

  it("ship with no tests in the tree → off-track, missing names tests", async () => {
    const wt = await makeWorktree();
    try {
      // a code file but no test file
      await mkdir(join(wt, "src"), { recursive: true });
      await writeFile(join(wt, "src", "thing.ts"), "// code", "utf8");
      const r = await readRigorForStage(wt, "ship");
      expect(r.ok).toBe(false);
      expect(r.missing).toBe("tests");
      expect(r.determinable).toBe(true);
    } finally {
      await rm(wt, { recursive: true, force: true });
    }
  });
});

describe("readRigorForStage — Recon has no required artifact (BR-12)", () => {
  it("recon → ok (never off-track on rigor), nothing missing, but NOT determinable", async () => {
    // Recon has no required-for-stage artifact, so rigor can never pull it
    // off-track (ok:true, missing:null). But there is no positive rigor
    // signal to determine either — so determinable:false. That is the
    // honest read: absent tests on a Recon change ⇒ the FR-31 unknown
    // health, not a false on-track (BR-12 note).
    const wt = await makeWorktree();
    try {
      const r = await readRigorForStage(wt, "recon");
      expect(r).toEqual({ ok: true, missing: null, determinable: false });
    } finally {
      await rm(wt, { recursive: true, force: true });
    }
  });

  it("shipped (terminal) → no required artifact: ok, not determinable", async () => {
    const wt = await makeWorktree();
    try {
      const r = await readRigorForStage(wt, "shipped");
      expect(r.ok).toBe(true);
      expect(r.missing).toBeNull();
      expect(r.determinable).toBe(false);
    } finally {
      await rm(wt, { recursive: true, force: true });
    }
  });
});

describe("readRigorForStage — best-effort / never-throw (BR-11)", () => {
  it("non-existent worktree → determinable:false, never throws", async () => {
    const r = await readRigorForStage("/tmp/does-not-exist-wp002-rigor", "implement");
    expect(r).toEqual({ ok: true, missing: null, determinable: false });
  });

  it("a worktree that is a file, not a dir → determinable:false (can't resolve)", async () => {
    const tmp = await mkdtemp(join(tmpdir(), "wt-rigor-file-"));
    const fakeWt = join(tmp, "not-a-dir");
    try {
      await writeFile(fakeWt, "i am a file", "utf8");
      const r = await readRigorForStage(fakeWt, "specify");
      expect(r.determinable).toBe(false);
      expect(r.ok).toBe(true);
    } finally {
      await rm(tmp, { recursive: true, force: true });
    }
  });
});

describe("readRigorForStage — path containment (MUC-4)", () => {
  it("a symlinked .specifications escaping the worktree is not followed (fails soft to determinable:false or ignores it)", async () => {
    const wt = await makeWorktree();
    const outside = await mkdtemp(join(tmpdir(), "outside-spec-"));
    try {
      // Seed a real spec OUTSIDE the worktree, then symlink the worktree's
      // .specifications at it. safeJoin must refuse to read the escaped
      // target — the rigor read must NOT pick up the outside spec.
      const outsideSpecDir = join(outside, "demo");
      await mkdir(outsideSpecDir, { recursive: true });
      await writeFile(join(outsideSpecDir, "SRD.md"), "# outside spec", "utf8");
      await symlink(outside, join(wt, ".specifications"));

      const r = await readRigorForStage(wt, "specify");
      // The escaped spec must not count as rigor-satisfied. Either the
      // containment guard refuses the read (determinable:false) or it
      // treats the escape as "no readable spec" (ok:false). Never ok:true.
      expect(r.ok === true && r.determinable === true).toBe(false);
    } finally {
      await rm(wt, { recursive: true, force: true });
      await rm(outside, { recursive: true, force: true });
    }
  });
});
