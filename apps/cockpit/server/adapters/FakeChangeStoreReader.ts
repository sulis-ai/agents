// WP-003 — In-memory FakeChangeStoreReader (TDD §14.1, ADR-008).
//
// The lib-level WPs (WP-006..WP-009) and the route WP (WP-010) inject
// this fake instead of the real adapter so they don't pay the cost of
// shelling out to Python on every test. The contract test runs against
// both — if a behaviour holds for the fake but not the adapter (or
// vice versa), the boundary parity guarantee ADR-008 relies on has
// broken.
//
// The fake takes records pre-shaped (camelCase, overlay applied). It
// does not simulate state.json + change.json composition — it serves
// what it is given.

import type {
  ChangeStoreReader,
  ChangeStoreRecord,
  WorkflowStage,
} from "../ports/ChangeStoreReader";

export class FakeChangeStoreReader implements ChangeStoreReader {
  private readonly records: ChangeStoreRecord[];

  constructor(records: ChangeStoreRecord[]) {
    // Sort once at construction, most-recent-first by createdAt. This
    // matches the live adapter's behaviour and means listAllChanges()
    // can return the array directly without re-sorting on every call.
    this.records = [...records].sort((a, b) =>
      a.createdAt < b.createdAt ? 1 : a.createdAt > b.createdAt ? -1 : 0,
    );
  }

  async listAllChanges(): Promise<ChangeStoreRecord[]> {
    return [...this.records];
  }

  async readChangeRecord(changeId: string): Promise<ChangeStoreRecord | null> {
    const found = this.records.find((r) => r.changeId === changeId);
    return found ? { ...found } : null;
  }

  async readChangeStage(changeId: string): Promise<WorkflowStage | null> {
    const found = this.records.find((r) => r.changeId === changeId);
    return found ? found.stage : null;
  }
}
