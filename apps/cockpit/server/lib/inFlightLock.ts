// WP-005 — per-change one-in-flight lock (FR-20, NFR-REL-03; ADR-001 §one-in-flight).
//
// One message per change at a time. The lock is per-change, in-memory, and is
// also a resource bulkhead (TDD §3.2): it bounds the cockpit to one live
// `claude` session per change. `acquire` returns a release handle (or null if
// the change is already streaming → the relay maps that to SESSION_BUSY 409).
// The handle is released on complete / break / fail so the NEXT send (Q10: a
// resend after a broken stream is a NEW message, never a silent duplicate) can
// proceed.
//
// In-memory + single-process is sufficient: the cockpit is localhost,
// single-founder (TDD §3.3). No cross-process coordination is needed.

/** Returned by a successful `acquire`. `release` is idempotent. */
export interface LockHandle {
  /** Free the change so a later send can acquire it again. Idempotent. */
  release(): void;
}

export class InFlightLock {
  private readonly held = new Set<string>();

  /**
   * Acquire the lock for `changeId`. Returns a `LockHandle` if the change was
   * free, or `null` if it is already held (a send is in flight).
   */
  acquire(changeId: string): LockHandle | null {
    if (this.held.has(changeId)) {
      return null;
    }
    this.held.add(changeId);
    let released = false;
    return {
      release: () => {
        if (released) return; // idempotent double-release
        released = true;
        this.held.delete(changeId);
      },
    };
  }

  /** True while a send is in flight for `changeId`. */
  isHeld(changeId: string): boolean {
    return this.held.has(changeId);
  }
}
