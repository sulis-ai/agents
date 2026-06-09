// WP-001 — shared api-types contract test (CF-02/03/04/09; ADR-001).
//
// The shared/api-types.ts file is the runtime TypeScript MIRROR of the signed
// contracts/openapi.yaml — the wire seam every vertical slice imports. This
// test pins that mirror: it constructs ONE example per new wire shape directly
// from the OpenAPI enum/example/description values (the single source of truth,
// CF-02), INCLUDING the error and empty cases (CF-03/04, not happy-path-only).
//
// The real gate is `tsc --noEmit` (the WP's verification): if a shape drifts
// from the contract — a missing field, a wrong enum literal, an invented
// property — these fixtures stop compiling. The runtime `expect`s additionally
// pin the discriminated-union NARROWING on the literal `type` field (CF-09,
// ADR-001 — every stream event is a union on `type`) and re-assert the existing
// anti-hardwiring invariant: no snake_case leaks onto the wire object keys.
//
// References:
// - contracts/openapi.yaml (verbatim source for every shape below).
// - CONTRACT_FIRST_STANDARD CF-02 (single source), CF-03 (errors in contract),
//   CF-04 (stubs include error + empty), CF-09 (structured stream-event schema).

import { describe, it, expect } from "vitest";

import type {
  // Reads
  ChangeStatus,
  BrainEntity,
  BrainGroup,
  BrainView,
  // Chat
  ChatStreamEvent,
  ChatErrorCode,
  // Products
  Product,
  ProductList,
  ProjectSource,
  // Discovery — onboarding
  OnboardingRequest,
  OnboardingStreamEvent,
  // Discovery — start-from-intent
  StartFromIntentRequest,
  StartFromIntentStreamEvent,
  // Discovery — concierge
  ConciergeStreamEvent,
  // The typed error envelope (all three code categories)
  ApiError,
  ApiErrorCode,
  // Settings (the management surface; ADR-019/020/021)
  RepoLink,
  SettingsProject,
  SettingsProduct,
  SettingsTree,
  ProductWrite,
  ProjectWrite,
  RepoAttachWrite,
  SettingsErrorCode,
} from "../../shared/api-types";

import {
  happySettingsTree,
  emptySettingsTree,
  settingsErrorFixtures,
} from "../../shared/__fixtures__/settings.fixtures";

// ── a generic no-snake_case wire-shape assertion (anti-hardwiring) ──────────
// Reuses the established "camelCase on the wire" invariant: every property key
// of a wire object (recursively) must be camelCase, never snake_case. The ONE
// sanctioned exception is ProjectSource.{path,repo,primary_branch}, which the
// contract carries snake_case verbatim from Project.source (FR-36); callers
// pass an allow-set for those keys.
function assertNoSnakeCase(
  value: unknown,
  allow: Set<string> = new Set(),
): void {
  if (Array.isArray(value)) {
    for (const v of value) assertNoSnakeCase(v, allow);
    return;
  }
  if (value && typeof value === "object") {
    for (const [key, v] of Object.entries(value)) {
      if (!allow.has(key)) {
        expect(key).not.toMatch(/_/);
      }
      assertNoSnakeCase(v, allow);
    }
  }
}

describe("shared/api-types — READ shapes (ChangeStatus, Brain*)", () => {
  it("ChangeStatus: a flagged status narrows its needs-attention reason", () => {
    const flagged: ChangeStatus = {
      changeId: "01ABC",
      stage: "implement",
      headline: "The agent is blocked waiting on a decision.",
      needsAttention: { flagged: true, reason: "waiting-on-decision" },
    };
    expect(flagged.needsAttention.flagged).toBe(true);
    expect(flagged.needsAttention.reason).toBe("waiting-on-decision");

    // The not-flagged case carries a null reason (FR-12: idle-but-fine).
    const fine: ChangeStatus = {
      changeId: "01ABC",
      stage: "review",
      headline: "Idle, nothing needs you.",
      needsAttention: { flagged: false, reason: null },
    };
    expect(fine.needsAttention.reason).toBeNull();
    assertNoSnakeCase(flagged);
  });

  it("BrainView: the EMPTY case is groups:[] (FR-06 empty), and a populated group nests entities", () => {
    const empty: BrainView = { changeId: "01ABC", groups: [] };
    expect(empty.groups).toEqual([]);

    const entity: BrainEntity = {
      id: "dna:requirement:01XYZ",
      kind: "requirement",
      title: "A requirement",
      detail: { text: "readable content" },
    };
    const group: BrainGroup = { kind: "requirement", items: [entity] };
    const populated: BrainView = { changeId: "01ABC", groups: [group] };
    expect(populated.groups[0]?.items[0]?.id).toBe("dna:requirement:01XYZ");
    assertNoSnakeCase(populated);
  });
});

describe("shared/api-types — CHAT shapes (ChatStreamEvent union + codes)", () => {
  it("every ChatStreamEvent variant narrows on the literal `type` field (CF-09)", () => {
    const events: ChatStreamEvent[] = [
      { type: "state", state: "ready" },
      { type: "state", state: "resuming" },
      { type: "state", state: "spawning" },
      { type: "state", state: "replying" },
      { type: "state", state: "complete" },
      { type: "state", state: "interrupted" },
      { type: "state", state: "failed" },
      { type: "chunk", text: "a token" },
      { type: "complete", resumed: true },
      { type: "error", code: "SESSION_UNREACHABLE", message: "down" },
    ];
    for (const ev of events) {
      switch (ev.type) {
        case "state":
          expect(typeof ev.state).toBe("string");
          break;
        case "chunk":
          expect(typeof ev.text).toBe("string");
          break;
        case "complete":
          expect(typeof ev.resumed).toBe("boolean");
          break;
        case "error":
          expect(typeof ev.code).toBe("string");
          break;
      }
      assertNoSnakeCase(ev);
    }
  });

  it("the chat error-code union accepts every chat code (CF-03)", () => {
    const codes: ChatErrorCode[] = [
      "SESSION_UNREACHABLE",
      "SESSION_CHANGE_MISMATCH",
      "SESSION_BUSY",
    ];
    for (const code of codes) {
      const ev: ChatStreamEvent = { type: "error", code, message: "x" };
      expect(ev.code).toBe(code);
    }
  });
});

describe("shared/api-types — PRODUCT shapes (Product, ProductList, ProjectSource)", () => {
  it("ProductList marks the active product; ProjectSource carries the contract's snake_case keys verbatim", () => {
    const active: Product = {
      productId: "dna:product:01A",
      name: "Alpha",
      active: true,
    };
    const other: Product = {
      productId: "dna:product:01B",
      name: "Beta",
      active: false,
    };
    const list: ProductList = {
      products: [active, other],
      activeProductId: "dna:product:01A",
    };
    expect(list.products.find((p) => p.active)?.productId).toBe(
      list.activeProductId,
    );

    // The empty/none case: no product selected yet → activeProductId null.
    const none: ProductList = { products: [], activeProductId: null };
    expect(none.activeProductId).toBeNull();

    // ProjectSource is the ONE sanctioned snake_case shape (Project.source, FR-36).
    const source: ProjectSource = {
      repo: "/local/path",
      path: "",
      primary_branch: "main",
    };
    expect(source.primary_branch).toBe("main");
    // The product keys themselves are camelCase; ProjectSource keys are allowed.
    assertNoSnakeCase(list);
    assertNoSnakeCase(source, new Set(["primary_branch"]));
  });
});

describe("shared/api-types — DISCOVERY onboarding shapes", () => {
  it("OnboardingRequest covers the search/ask/confirm turns (the confirm gate is in the contract)", () => {
    const search: OnboardingRequest = {
      phase: "search",
      chosenArea: "/some/folder",
    };
    const ask: OnboardingRequest = { phase: "ask", message: "yes, that one" };
    const confirm: OnboardingRequest = {
      phase: "confirm",
      confirmToken: "tok-1",
      repoChoice: { mode: "create", createTarget: "local" },
    };
    expect(search.phase).toBe("search");
    expect(ask.phase).toBe("ask");
    expect(confirm.phase).toBe("confirm");
    expect(confirm.repoChoice?.createTarget).toBe("local");
  });

  it("OnboardingStreamEvent: every variant narrows on `type`, incl. the proposal→minted pair and an error per code", () => {
    const proposal: OnboardingStreamEvent = {
      type: "proposal",
      proposal: {
        confirmToken: "tok-1",
        tenant: "T",
        product: "P",
        projects: [
          {
            name: "proj",
            source: { repo: "/r", path: "", primary_branch: "main" },
          },
        ],
        repoPlan: "will-create-local",
        alreadyMinted: false,
      },
    };
    const minted: OnboardingStreamEvent = {
      type: "minted",
      minted: {
        tenant: "T",
        product: { productId: "dna:product:01A", name: "Alpha", active: true },
        projects: [
          {
            projectId: "dna:project:01A",
            source: { repo: "/r", path: "", primary_branch: "main" },
          },
        ],
      },
    };
    const events: OnboardingStreamEvent[] = [
      { type: "state", state: "searching" },
      { type: "state", state: "minting" },
      { type: "chunk", text: "agent text" },
      proposal,
      minted,
      {
        type: "error",
        code: "DISCOVERY_SCOPE_VIOLATION",
        message: "out of root",
      },
      { type: "error", code: "DISCOVERY_CONFIRM_STALE", message: "stale" },
      { type: "error", code: "REPO_CREATE_FAILED", message: "git init failed" },
      { type: "error", code: "SESSION_UNREACHABLE", message: "down" },
      { type: "error", code: "SESSION_BUSY", message: "in flight" },
    ];
    for (const ev of events) {
      switch (ev.type) {
        case "proposal":
          expect(ev.proposal.confirmToken).toBe("tok-1");
          assertNoSnakeCase(ev, new Set(["primary_branch"]));
          break;
        case "minted":
          expect(ev.minted.product?.productId).toBe("dna:product:01A");
          assertNoSnakeCase(ev, new Set(["primary_branch"]));
          break;
        case "state":
        case "chunk":
        case "error":
          assertNoSnakeCase(ev);
          break;
      }
    }
  });
});

describe("shared/api-types — DISCOVERY start-from-intent shapes", () => {
  it("StartFromIntentRequest covers propose/confirm with kind change|investigation", () => {
    const propose: StartFromIntentRequest = {
      phase: "propose",
      productId: "dna:product:01A",
      intent: "add a dark mode toggle",
      kind: "change",
    };
    const investigation: StartFromIntentRequest = {
      phase: "propose",
      productId: "dna:product:01A",
      intent: "look into the slow query",
      kind: "investigation",
    };
    const confirm: StartFromIntentRequest = {
      phase: "confirm",
      confirmToken: "tok-2",
    };
    expect(propose.kind).toBe("change");
    expect(investigation.kind).toBe("investigation");
    expect(confirm.phase).toBe("confirm");
  });

  it("StartFromIntentStreamEvent: every variant narrows on `type`, incl. `started` (a Change) and an error per code", () => {
    const started: StartFromIntentStreamEvent = {
      type: "started",
      started: {
        changeId: "01NEW",
        handle: "feat-new",
        slug: "new",
        primitive: "create",
        branch: "change/new",
        worktreePath: "/wt",
        intent: "add a thing",
        baseBranch: "main",
        baseSha: null,
        createdAt: "2026-06-04T00:00:00Z",
        updatedAt: "2026-06-04T00:00:00Z",
        stage: "recon",
        liveness: { status: "not-running" },
        // WP-001 widened fields — fixture defaults.
        needsAttention: { flagged: false, reason: null },
        health: { state: "unknown", reason: "too early to tell" },
        lastActivityAt: null,
      },
    };
    const events: StartFromIntentStreamEvent[] = [
      { type: "state", state: "classifying" },
      { type: "state", state: "cloning" },
      { type: "chunk", text: "agent text" },
      {
        type: "proposal",
        proposal: {
          confirmToken: "tok-2",
          primitive: "create",
          slug: "new",
          willCloneRepo: true,
        },
      },
      started,
      { type: "error", code: "INTENT_AMBIGUOUS", message: "too vague" },
      { type: "error", code: "START_CONFIRM_STALE", message: "stale" },
      { type: "error", code: "REPO_UNREACHABLE", message: "clone failed" },
      { type: "error", code: "SESSION_UNREACHABLE", message: "down" },
      { type: "error", code: "SESSION_BUSY", message: "in flight" },
    ];
    for (const ev of events) {
      if (ev.type === "started") {
        expect(ev.started.stage).toBe("recon");
      }
      if (ev.type === "proposal") {
        expect(ev.proposal.primitive).toBe("create");
      }
    }
  });
});

describe("shared/api-types — DISCOVERY concierge shape", () => {
  it("ConciergeStreamEvent reuses the chat shapes and carries a `route` hint on complete (FR-34)", () => {
    const completeWithRoute: ConciergeStreamEvent = {
      type: "complete",
      route: "start-from-intent",
    };
    expect(completeWithRoute.route).toBe("start-from-intent");

    const events: ConciergeStreamEvent[] = [
      { type: "state", state: "thinking" },
      { type: "state", state: "replying" },
      { type: "chunk", text: "an answer" },
      { type: "complete", route: "onboarding" },
      { type: "complete", route: null },
      { type: "error", code: "SESSION_UNREACHABLE", message: "down" },
    ];
    for (const ev of events) {
      assertNoSnakeCase(ev);
    }
  });
});

describe("shared/api-types — the typed error envelope (all three code categories)", () => {
  it("ApiError.code accepts chat + discovery + start codes (CF-03)", () => {
    const codes: ApiErrorCode[] = [
      "NOT_FOUND",
      "SESSION_BUSY",
      "SESSION_CHANGE_MISMATCH",
      "SESSION_UNREACHABLE",
      "DISCOVERY_SCOPE_VIOLATION",
      "DISCOVERY_CONFIRM_STALE",
      "REPO_CREATE_FAILED",
      "INTENT_AMBIGUOUS",
      "START_CONFIRM_STALE",
      "REPO_UNREACHABLE",
    ];
    for (const code of codes) {
      const err: ApiError = { error: "human-readable", code };
      expect(err.code).toBe(code);
      assertNoSnakeCase(err);
    }
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// WP-001 — Settings wire contract (TDD §5.1; ADR-019/020/021; CF-03/04).
//
// The settings management surface adds the products/projects/repo-links tree
// shapes plus the three error categories. These are camelCase wire shapes —
// the ONE sanctioned snake_case exception (ProjectSource) is NOT among them:
// RepoLink exposes `primaryBranch` (camelCase), the producer maps it to the
// snake_case `primary_branch` of Project.source at the boundary (WP-006).
//
// This block is the WP's named verification
// (settings_shapes_round_trip_happy_error_empty): it pins the happy / empty /
// error fixtures against the new shapes and asserts they serialise/parse
// losslessly. The compile is the real gate (tsc --noEmit): a drifted field or
// invented property stops these fixtures compiling.
// ═══════════════════════════════════════════════════════════════════════════

describe("shared/api-types — SETTINGS wire shapes (ADR-019/020/021)", () => {
  it("settings_shapes_round_trip_happy_error_empty: happy / empty / error fixtures round-trip losslessly (CF-04)", () => {
    // HAPPY — one editable product, one project, one present:true repo.
    const happy: SettingsTree = happySettingsTree;
    expect(happy.products).toHaveLength(1);
    const product = happy.products[0];
    expect(product?.editable).toBe(true);
    const project = product?.projects[0];
    expect(project).toBeDefined();
    const repo: RepoLink | null | undefined = project?.repo;
    expect(repo?.present).toBe(true);
    expect(repo?.localPath).not.toBeNull();
    expect(typeof repo?.primaryBranch).toBe("string");

    // EMPTY — the single implicit product (editable:false, no projects).
    const empty: SettingsTree = emptySettingsTree;
    expect(empty.products).toHaveLength(1);
    expect(empty.products[0]?.editable).toBe(false);
    expect(empty.products[0]?.projects).toEqual([]);

    // ERROR — one ApiError per SettingsErrorCode value (all three categories).
    const errorCodes: SettingsErrorCode[] = [
      "NOT_FOUND",
      "VALIDATION_FAILED",
      "PATH_NOT_FOUND",
      "PATH_NOT_A_REPO",
      "WRITE_FAILED",
      "IMMUTABLE_IMPLICIT",
    ];
    for (const code of errorCodes) {
      const err = settingsErrorFixtures[code];
      expect(err.code).toBe(code);
      expect(typeof err.error).toBe("string");
      assertNoSnakeCase(err);
    }

    // Lossless JSON round-trip for the tree fixtures (the wire is JSON).
    for (const tree of [happy, empty]) {
      const round = JSON.parse(JSON.stringify(tree)) as SettingsTree;
      expect(round).toEqual(tree);
      // No snake_case leaks onto settings wire keys (RepoLink is camelCase).
      assertNoSnakeCase(round);
    }
  });

  it("every SettingsErrorCode member is reachable in the ApiError envelope (CF-03 type-level)", () => {
    // Type-level: a SettingsErrorCode value is assignable to ApiError.code,
    // i.e. SettingsErrorCode ⊆ ApiErrorCode (reuse, not redeclare). If a
    // settings code were missing from ApiErrorCode this stops compiling.
    const asApiCode: (c: SettingsErrorCode) => ApiErrorCode = (c) => c;
    const envelope = (c: SettingsErrorCode): ApiError => ({
      error: "x",
      code: asApiCode(c),
    });
    const codes: SettingsErrorCode[] = [
      "NOT_FOUND",
      "VALIDATION_FAILED",
      "PATH_NOT_FOUND",
      "PATH_NOT_A_REPO",
      "WRITE_FAILED",
      "IMMUTABLE_IMPLICIT",
    ];
    for (const c of codes) {
      expect(envelope(c).code).toBe(c);
    }
  });

  it("the write shapes carry the upsert-by-id invariant (id present ⇒ edit, absent ⇒ create)", () => {
    const create: ProductWrite = { name: "Alpha" };
    const edit: ProductWrite = {
      productId: "dna:product:01A",
      name: "Alpha v2",
    };
    expect(create.productId).toBeUndefined();
    expect(edit.productId).toBe("dna:product:01A");

    const projectCreate: ProjectWrite = {
      productId: "dna:product:01A",
      name: "proj",
    };
    const projectEdit: ProjectWrite = {
      projectId: "dna:project:01A",
      productId: "dna:product:01A",
      name: "proj v2",
    };
    expect(projectCreate.projectId).toBeUndefined();
    expect(projectEdit.projectId).toBe("dna:project:01A");

    // Attach is local-path-only (ADR-021): an absolute path, no URL/create.
    const attach: RepoAttachWrite = {
      projectId: "dna:project:01A",
      localPath: "/Users/founder/code/proj",
    };
    expect(attach.localPath.startsWith("/")).toBe(true);
    assertNoSnakeCase(attach);
  });

  it("SettingsProject.repo is null when no repo is attached yet, and RepoLink.localPath is null when unlinked", () => {
    const unattached: SettingsProject = {
      projectId: "dna:project:01B",
      name: "no-repo",
      repo: null,
    };
    expect(unattached.repo).toBeNull();

    const unlinked: RepoLink = {
      localPath: null,
      primaryBranch: "main",
      present: false,
    };
    expect(unlinked.localPath).toBeNull();
    expect(unlinked.present).toBe(false);

    const productNode: SettingsProduct = {
      productId: "dna:product:01A",
      name: "Alpha",
      editable: true,
      projects: [unattached],
    };
    expect(productNode.projects[0]?.repo).toBeNull();
    assertNoSnakeCase(productNode);
  });
});
