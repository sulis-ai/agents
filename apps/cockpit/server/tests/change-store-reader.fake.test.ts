// WP-003 — Contract test against FakeChangeStoreReader.
//
// The fake satisfies the same ChangeStoreReader contract as the real
// adapter without spawning subprocesses. Lib-level WPs (WP-006..WP-009)
// + the route WP (WP-010) consume the fake in their tests; this file is
// the proof the fake stays compliant with the port.

import { runContract, type ContractFixture } from "./change-store-reader.contract.test";
import { FakeChangeStoreReader } from "../adapters/FakeChangeStoreReader";
import type { ChangeStoreRecord } from "../ports/ChangeStoreReader";

function recordsFromFixtures(fixtures: ContractFixture[]): ChangeStoreRecord[] {
  return fixtures.map((fx) => ({
    changeId: fx.changeId,
    handle: fx.handle,
    slug: fx.slug,
    primitive: fx.primitive,
    branch: fx.branch,
    worktreePath: fx.worktreePath,
    intent: fx.intent,
    baseBranch: fx.baseBranch,
    baseSha: fx.baseSha,
    createdAt: fx.createdAt,
    // The fake takes pre-shaped records — the overlay is baked in.
    updatedAt: fx.liveStage ? `${fx.createdAt}` : fx.createdAt,
    stage: (fx.liveStage ?? fx.seedStage) as ChangeStoreRecord["stage"],
  }));
}

runContract("FakeChangeStoreReader", {
  setup: async (fixtures) => {
    return new FakeChangeStoreReader(recordsFromFixtures(fixtures));
  },
});
