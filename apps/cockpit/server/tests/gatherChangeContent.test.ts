// WP-007 — gatherChangeContent tests (FR-10 content scan).
//
// Proves the folded searchable string covers all three sources — the
// record's labels, the conversation, and the CREATED ENTITIES — so a
// term that appears only in an entity (not the conversation, not the
// title) is still findable (FR-10). Pure; no I/O.

import { describe, it, expect } from "vitest";

import { gatherChangeContent } from "../lib/gatherChangeContent";
import type { ChangeStoreRecord } from "../ports/ChangeStoreReader";
import type {
  BrainView,
  TranscriptMessage,
} from "../../shared/api-types";

function record(overrides: Partial<ChangeStoreRecord> = {}): ChangeStoreRecord {
  return {
    changeId: "01ABC",
    handle: "CH-01ABC",
    slug: "cancel-flow",
    primitive: "create",
    branch: "change/cancel-flow",
    worktreePath: "/tmp/never",
    intent: "Add the cancellation flow",
    baseBranch: "main",
    baseSha: "deadbeef",
    createdAt: "2026-05-01T00:00:00Z",
    updatedAt: "2026-05-02T00:00:00Z",
    stage: "design",
    ...overrides,
  };
}

const emptyBrain = (changeId = "01ABC"): BrainView => ({ changeId, groups: [] });

describe("gatherChangeContent (FR-10)", () => {
  it("includes the record's labels (handle / slug / intent / primitive / branch)", () => {
    const content = gatherChangeContent(record(), [], emptyBrain());
    expect(content).toContain("CH-01ABC");
    expect(content).toContain("cancel-flow");
    expect(content).toContain("Add the cancellation flow");
  });

  it("includes user + assistant + system conversation text", () => {
    const transcript: TranscriptMessage[] = [
      { kind: "user", uuid: "u", timestamp: "t", text: "the marshmallow rollback" },
      {
        kind: "assistant",
        uuid: "a",
        timestamp: "t2",
        blocks: [
          { kind: "tool-use", toolName: "Bash", input: {} },
          { kind: "text", text: "applied the kingfisher patch" },
        ],
      },
      { kind: "system", uuid: "s", timestamp: "t3", subtype: "info", text: "session resumed" },
    ];
    const content = gatherChangeContent(record(), transcript, emptyBrain());
    expect(content).toContain("marshmallow");
    expect(content).toContain("kingfisher");
    expect(content).toContain("resumed");
  });

  it("KEYSTONE (FR-10): includes created-entity title + nested detail text", () => {
    const brain: BrainView = {
      changeId: "01ABC",
      groups: [
        {
          kind: "requirement",
          items: [
            {
              id: "dna:requirement:01",
              kind: "requirement",
              title: "Cancellation reconciliation",
              detail: {
                statement: "the invoice must zarquon-reconcile on cancel",
                acceptance: ["refund issued", "ledger balanced"],
              },
            },
          ],
        },
      ],
    };
    const content = gatherChangeContent(record(), [], brain);
    // A term that appears ONLY in the entity (title + nested detail).
    expect(content).toContain("Cancellation reconciliation");
    expect(content).toContain("zarquon-reconcile");
    expect(content).toContain("ledger balanced");
  });

  it("does not collect object KEYS, only string VALUES (no schema noise)", () => {
    const brain: BrainView = {
      changeId: "01ABC",
      groups: [
        {
          kind: "design",
          items: [
            {
              id: "dna:design:01",
              kind: "design",
              title: "T",
              detail: { uniqueKeyName: "the value text" },
            },
          ],
        },
      ],
    };
    const content = gatherChangeContent(record(), [], brain);
    expect(content).toContain("the value text");
    expect(content).not.toContain("uniqueKeyName");
  });
});
