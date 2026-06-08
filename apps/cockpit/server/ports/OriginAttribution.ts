// WP-P08 — OriginAttribution port (ADR-012).
//
// Change-origin attribution is a domain-owned port. The public face is the
// cockpit's own port; the `git log` / brain / transcript reads are CALLED BY the
// adapter (EXPAND-Create, not SUBSTITUTE-Wrap — parent §2.1, MEA-01). Two
// adapters satisfy ONE contract test:
//
//   - `InferredOriginAttribution` (WP-P09, now) — correlates a file's
//     last-changing commit to a `lifecyclerun` window (→ autonomous) or a
//     conversation turn (→ assisted), else unknown. Every result carries
//     `attribution: "inferred"`.
//   - `RecordedOriginAttribution` (WP-P13, after stamping) — reads the
//     `Sulis-Origin:` commit trailer / sidecar and returns the exact origin
//     with `attribution: "recorded"`. A recorded origin OVERRIDES inference.
//
// Designing the contract once, now, is what lets stamping drop in as a second
// adapter against the SAME contract test — inferred→recorded becomes a swap,
// not a rewrite (ADR-012).

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern blocks escapes out of apps/cockpit/, which import/no-restricted-paths enforces)
import type { Origin } from "../../shared/api-types";

export type { Origin };

/**
 * The one port the cockpit attributes change-origin through.
 *
 *   - `originFor(changeId, path)` → the origin of ONE file.
 *   - `originFor(changeId)`       → the change-level origin (path omitted).
 *
 * Fail-soft: a file with no resolvable commit (or a change with no runs /
 * turns to correlate against) resolves to `{ kind: "unknown", ... }` — NEVER
 * an error. The only error this port surfaces is an unknown change id, which
 * the route maps to a 404 (CF-03).
 */
export interface OriginAttribution {
  originFor(changeId: string, path?: string): Promise<Origin>;
}
