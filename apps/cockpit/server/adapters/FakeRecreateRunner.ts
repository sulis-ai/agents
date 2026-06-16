// WP-004 — In-memory FakeRecreateRunner (TDD §3, §4.3; WPB-03, MEA-09).
//
// The serving-path resolver (`resolveContractWorktree`) and the route
// tests inject this fake instead of the real `SulisChangeRecreator` so
// they don't pay the cost of (and the flakiness of) spawning the real
// CLI. It is a real adapter shape implementing the RecreateRunner port —
// NOT an ad-hoc mock (MEA-09: an in-memory adapter validates behaviour; a
// mock only validates a call signature).
//
// It serves a configured outcome and records every change_id it was
// called with (ADR-001 — the seam is keyed by the unique id, not the
// handle). An optional `onRecreate` hook lets a test reproduce the real
// CLI's side effect of materialising the worktree on disk, so the
// resolver can then resolve the now-present root — proving recreate
// happens BEFORE the render-path resolution.

import type { RecreateOutcome, RecreateRunner } from "../ports/RecreateRunner";

export type FakeRecreateRunnerHooks = {
  /**
   * Invoked just before the configured outcome is returned, on every
   * recreate call. A test wires this to e.g. `mkdir` the worktree so a
   * subsequent resolve sees it present — mirroring the real CLI's effect.
   */
  onRecreate?: (changeId: string) => Promise<void> | void;
};

export class FakeRecreateRunner implements RecreateRunner {
  /** Every change_id passed to `recreate`, in call order. */
  readonly calls: string[] = [];

  private readonly outcome: RecreateOutcome;
  private readonly hooks: FakeRecreateRunnerHooks;

  constructor(outcome: RecreateOutcome, hooks: FakeRecreateRunnerHooks = {}) {
    this.outcome = outcome;
    this.hooks = hooks;
  }

  /**
   * The argument the most recent `recreate` call carried, or `undefined`
   * if it has not been called yet. Lets a test pin the carried key (the
   * unique change_id, never the handle — HD-004) without indexing `calls`.
   */
  get lastArg(): string | undefined {
    return this.calls[this.calls.length - 1];
  }

  async recreate(changeId: string): Promise<RecreateOutcome> {
    this.calls.push(changeId);
    if (this.hooks.onRecreate) {
      await this.hooks.onRecreate(changeId);
    }
    return this.outcome;
  }
}
