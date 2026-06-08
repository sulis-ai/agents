// WP-P13 — recorded-supersedes-inferred composition (ADR-012).
//
// A thin composing adapter: ask the RECORDED adapter first; if it has a real
// stamp (autonomous / assisted), return it; otherwise fall back to the INFERRED
// adapter. This is the "recorded overrides inferred" precedence rule (ADR-012)
// expressed as one clean seam, so the badge flips inferred → recorded with NO
// UI change (the frontend already keys off `attribution`).
//
// It is itself an `OriginAttribution`, so the route and the whole-change
// `readOrigin` lib consume it exactly as they did the single inferred adapter —
// no route rewrite, no change to `readOrigin` (the swap property, ADR-012).

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern blocks escapes out of apps/cockpit/, which import/no-restricted-paths enforces)
import type { Origin } from "../../shared/api-types";
import type { OriginAttribution } from "../ports/OriginAttribution";

/**
 * Compose two attributions with recorded-wins precedence. A recorded result is
 * "real" when its kind is autonomous or assisted (an actual stamp); a recorded
 * `unknown` means "no stamp here", so we defer to the inferred answer.
 */
export class CompositeOriginAttribution implements OriginAttribution {
  constructor(
    private readonly recorded: OriginAttribution,
    private readonly inferred: OriginAttribution,
  ) {}

  async originFor(changeId: string, path?: string): Promise<Origin> {
    const recorded = await this.recorded.originFor(changeId, path);
    if (recorded.kind !== "unknown") return recorded; // a real stamp wins.
    return this.inferred.originFor(changeId, path);
  }
}
