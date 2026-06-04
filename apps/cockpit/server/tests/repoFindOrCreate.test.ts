// WP-010 — repo find-or-create tests (FR-35 / FR-N7 / FR-N10 / FR-N11; ADR-008).
//
// repoFindOrCreate is a PURE decision module (no fs/git/process — the actual
// `git init` runs inside the agent session over the bridge, ADR-007). It owns:
//   - the FIND vs CREATE branch (FR-35);
//   - the create-LOCATION default: local-only `git init` (FOUNDER-LOCKED,
//     ADR-008); hosted-remote is a SEPARATELY-confirmed createTarget, never the
//     default;
//   - the repoPlan label the proposal shows (found-existing /
//     will-create-local / will-create-hosted-remote);
//   - the NO-DANGLING-CONFIG rule (FR-N10/N11): a ProjectSource is produced
//     ONLY when the repo is found-or-created AND the outcome is reachable; a
//     FAILED create yields REPO_CREATE_FAILED and NO source.

import { describe, it, expect } from "vitest";

import {
  planRepo,
  resolveRepoSource,
  type RepoChoice,
} from "../lib/discovery/repoFindOrCreate";

const CHOSEN_AREA = "/founder/code/acme-checkout";
const PRIMARY = "main";

describe("planRepo — the FIND vs CREATE branch + locked local-only default", () => {
  it("FIND configures an existing repo from the chosen area, NO creation", () => {
    const choice: RepoChoice = { mode: "find" };
    const plan = planRepo(choice, { chosenArea: CHOSEN_AREA });
    expect(plan.repoPlan).toBe("found-existing");
    expect(plan.willCreate).toBe(false);
  });

  it("CREATE defaults to LOCAL-ONLY git init (founder-locked) when no target given", () => {
    const choice: RepoChoice = { mode: "create" };
    const plan = planRepo(choice, { chosenArea: CHOSEN_AREA });
    expect(plan.repoPlan).toBe("will-create-local");
    expect(plan.willCreate).toBe(true);
    expect(plan.createTarget).toBe("local");
  });

  it("CREATE local-only when target explicitly local", () => {
    const choice: RepoChoice = { mode: "create", createTarget: "local" };
    const plan = planRepo(choice, { chosenArea: CHOSEN_AREA });
    expect(plan.repoPlan).toBe("will-create-local");
    expect(plan.createTarget).toBe("local");
  });

  it("hosted-remote is honoured ONLY when separately + explicitly confirmed", () => {
    const choice: RepoChoice = {
      mode: "create",
      createTarget: "hosted-remote",
    };
    const plan = planRepo(choice, { chosenArea: CHOSEN_AREA });
    expect(plan.repoPlan).toBe("will-create-hosted-remote");
    expect(plan.createTarget).toBe("hosted-remote");
  });

  it("an absent repoChoice defaults to FIND (the safe, non-creating branch)", () => {
    const plan = planRepo(undefined, { chosenArea: CHOSEN_AREA });
    expect(plan.repoPlan).toBe("found-existing");
    expect(plan.willCreate).toBe(false);
  });
});

describe("resolveRepoSource — no dangling config (FR-N10/N11)", () => {
  it("a FOUND repo yields a ProjectSource (persist)", () => {
    const plan = planRepo({ mode: "find" }, { chosenArea: CHOSEN_AREA });
    const result = resolveRepoSource(plan, {
      outcome: "reachable",
      repo: CHOSEN_AREA,
      primaryBranch: PRIMARY,
    });
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.source).toEqual({
        repo: CHOSEN_AREA,
        path: "",
        primary_branch: PRIMARY,
      });
    }
  });

  it("a CONFIRMED + CREATED + reachable local repo yields a ProjectSource", () => {
    const plan = planRepo({ mode: "create" }, { chosenArea: CHOSEN_AREA });
    const result = resolveRepoSource(plan, {
      outcome: "reachable",
      repo: CHOSEN_AREA,
      primaryBranch: PRIMARY,
    });
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.source.repo).toBe(CHOSEN_AREA);
      expect(result.source.primary_branch).toBe(PRIMARY);
    }
  });

  it("a FAILED create yields REPO_CREATE_FAILED and NO source (no dangling config)", () => {
    const plan = planRepo({ mode: "create" }, { chosenArea: CHOSEN_AREA });
    const result = resolveRepoSource(plan, { outcome: "create-failed" });
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.code).toBe("REPO_CREATE_FAILED");
      // The crucial assertion: NOTHING to persist on failure.
      expect((result as { source?: unknown }).source).toBeUndefined();
    }
  });

  it("an unreachable found repo yields a failure and NO source", () => {
    const plan = planRepo({ mode: "find" }, { chosenArea: CHOSEN_AREA });
    const result = resolveRepoSource(plan, { outcome: "unreachable" });
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect((result as { source?: unknown }).source).toBeUndefined();
    }
  });
});
