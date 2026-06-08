// WP-007 — searchChanges: the pure search/filter predicate (FR-10/11/12).
//
// The single content+stage+needs-attention filter the search route drives.
// It is PURE: the route gathers each change's searchable content (the
// conversation text + the created-entity text) and its attention verdict,
// then passes them in. searchChanges decides which changes survive the
// active filters — it does NO I/O and re-implements NOTHING from WP-004
// (the route feeds it the `needsAttention` verdict; searchChanges only
// reads `verdict.flagged`).
//
// The keystone case (FR-10): a term that appears ONLY in a change's
// conversation (not its handle/intent/stage) still matches — search hits
// CONTENT, not just labels.

import { describe, it, expect } from "vitest";

import {
  searchChanges,
  type SearchableChange,
} from "../lib/searchChanges";
import type { ChangeStoreRecord } from "../ports/ChangeStoreReader";
import type { AttentionVerdict } from "../lib/needsAttention";

function record(overrides: Partial<ChangeStoreRecord> = {}): ChangeStoreRecord {
  return {
    changeId: "01ABC",
    handle: "CH-01ABC",
    slug: "demo",
    primitive: "create",
    branch: "change/demo",
    worktreePath: "/tmp/never",
    intent: "demo change",
    baseBranch: "main",
    baseSha: "deadbeef",
    createdAt: "2026-05-01T00:00:00Z",
    updatedAt: "2026-05-02T00:00:00Z",
    stage: "design",
    ...overrides,
  };
}

const NOT_FLAGGED: AttentionVerdict = { flagged: false, reason: null };
const FLAGGED: AttentionVerdict = { flagged: true, reason: "blocked" };

function item(
  overrides: Partial<ChangeStoreRecord> = {},
  content = "",
  attention: AttentionVerdict = NOT_FLAGGED,
): SearchableChange {
  return { record: record(overrides), content, attention };
}

describe("searchChanges (FR-10/11/12)", () => {
  it("returns every change when no filters are active (the unfiltered board)", () => {
    const items = [
      item({ changeId: "01A" }),
      item({ changeId: "01B" }),
    ];
    const out = searchChanges(items, {});
    expect(out.map((r) => r.changeId)).toEqual(["01A", "01B"]);
  });

  it("KEYSTONE (FR-10): matches a term that appears ONLY in the conversation, not the title", () => {
    const items = [
      // The term "marshmallow" is nowhere in handle/intent/slug — only in
      // the conversation content the route gathered.
      item(
        { changeId: "01HIT", handle: "CH-01HIT", intent: "Refactor the auth flow" },
        "we discussed the marshmallow rollback strategy at length",
      ),
      item(
        { changeId: "01MISS", handle: "CH-01MISS", intent: "Unrelated work" },
        "nothing relevant here",
      ),
    ];
    const out = searchChanges(items, { q: "marshmallow" });
    expect(out.map((r) => r.changeId)).toEqual(["01HIT"]);
  });

  it("matches a term that appears ONLY in a created entity's text (FR-10 content scan)", () => {
    const items = [
      item(
        { changeId: "01ENT", handle: "CH-01ENT", intent: "Build the thing" },
        // entity text folded into content by the route (a requirement title etc.)
        "Requirement: the cancellation invoice must reconcile",
      ),
      item({ changeId: "01NO" }, "unrelated"),
    ];
    const out = searchChanges(items, { q: "reconcile" });
    expect(out.map((r) => r.changeId)).toEqual(["01ENT"]);
  });

  it("still matches the handle/intent (the route folds labels into content too)", () => {
    // The route gathers `content` = conversation + entity text + the
    // record's own labels (handle/intent/slug). searchChanges sees only
    // the folded `content`, so a label hit arrives as a content hit.
    const items = [
      item(
        { changeId: "01H", handle: "CH-LOGIN", intent: "Fix login redirect" },
        "CH-LOGIN Fix login redirect",
      ),
      item(
        { changeId: "01O", handle: "CH-OTHER", intent: "Something else" },
        "CH-OTHER Something else",
      ),
    ];
    expect(searchChanges(items, { q: "login" }).map((r) => r.changeId)).toEqual([
      "01H",
    ]);
  });

  it("matches case-insensitively and trims the query", () => {
    const items = [item({ changeId: "01C" }, "The DataBase migration")];
    expect(searchChanges(items, { q: "  database  " }).map((r) => r.changeId)).toEqual([
      "01C",
    ]);
  });

  it("a whitespace-only query is treated as no query (returns all)", () => {
    const items = [item({ changeId: "01A" }), item({ changeId: "01B" })];
    expect(searchChanges(items, { q: "   " })).toHaveLength(2);
  });

  it("filters to the requested stages (FR-11), keeping any of several", () => {
    const items = [
      item({ changeId: "01R", stage: "recon" }),
      item({ changeId: "01D", stage: "design" }),
      item({ changeId: "01S", stage: "ship" }),
    ];
    const out = searchChanges(items, { stage: ["design", "ship"] });
    expect(out.map((r) => r.changeId)).toEqual(["01D", "01S"]);
  });

  it("an empty stage list is treated as no stage filter (FR-11)", () => {
    const items = [
      item({ changeId: "01R", stage: "recon" }),
      item({ changeId: "01D", stage: "design" }),
    ];
    expect(searchChanges(items, { stage: [] })).toHaveLength(2);
  });

  it("filters to needs-attention only (FR-12): keeps flagged, drops idle-but-fine", () => {
    const items = [
      item({ changeId: "01FLAG" }, "", FLAGGED),
      item({ changeId: "01IDLE" }, "", NOT_FLAGGED),
    ];
    const out = searchChanges(items, { needsAttention: true });
    expect(out.map((r) => r.changeId)).toEqual(["01FLAG"]);
  });

  it("needsAttention=false is treated as no attention filter (FR-12)", () => {
    const items = [
      item({ changeId: "01FLAG" }, "", FLAGGED),
      item({ changeId: "01IDLE" }, "", NOT_FLAGGED),
    ];
    expect(searchChanges(items, { needsAttention: false })).toHaveLength(2);
  });

  it("composes all three filters (q AND stage AND needs-attention)", () => {
    const items = [
      // matches q + stage + attention → kept
      item({ changeId: "01KEEP", stage: "design" }, "rollback plan", FLAGGED),
      // matches q + stage but NOT attention → dropped
      item({ changeId: "01A", stage: "design" }, "rollback plan", NOT_FLAGGED),
      // matches q + attention but wrong stage → dropped
      item({ changeId: "01B", stage: "recon" }, "rollback plan", FLAGGED),
      // wrong q → dropped
      item({ changeId: "01C", stage: "design" }, "unrelated", FLAGGED),
    ];
    const out = searchChanges(items, {
      q: "rollback",
      stage: ["design"],
      needsAttention: true,
    });
    expect(out.map((r) => r.changeId)).toEqual(["01KEEP"]);
  });

  it("preserves input order of the surviving changes", () => {
    const items = [
      item({ changeId: "01_1", stage: "design" }),
      item({ changeId: "01_2", stage: "recon" }),
      item({ changeId: "01_3", stage: "design" }),
    ];
    const out = searchChanges(items, { stage: ["design"] });
    expect(out.map((r) => r.changeId)).toEqual(["01_1", "01_3"]);
  });

  it("returns the underlying records (so the route can shape them to the wire Change)", () => {
    const items = [item({ changeId: "01X", handle: "CH-01X" })];
    const out = searchChanges(items, {});
    expect(out[0]).toMatchObject({ changeId: "01X", handle: "CH-01X" });
  });
});
