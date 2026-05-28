# Code Review (batch gate): WP-008 — keystone remediation

> **Timestamp:** 2026-05-28T183710Z
> **Target:** train-2026-05-28T183603Z (batch_size=1, WP-008); merge `4c1cbf6` on `change/create-release-train`
> **Outcome:** Ready to merge (PASS)

## At a glance

WP-008 is a focused remediation whose entire diff closes the four findings from the WP-001 keystone review (PR-1fd6d60). The per-WP review already ran the full three-lens pass on this exact code and returned PASS / 0 findings. This batch gate (solo WP — no cross-WP composition surface) confirms the merged tip is green and the four prior findings are genuinely closed.

## Verdict

`PASS` per CR-06. No critical/high; Build Verification empty; all four prior findings (CR-WP001-01..04) closed and verified by the suite.

## Findings closure (vs PR-1fd6d60)

| Prior finding | Severity | Status in WP-008 |
|---|---|---|
| CR-WP001-01 — tier map omits 13 of 22 primitives; docstring overclaim | high | **CLOSED** — all 22 primitives map non-None (founder-approved defaults; `test_tier_for_primitive_all_22_primitives_mapped` passes); docstring + README table now accurate. |
| CR-WP001-02 — newline injection in raw scalar fields → forged `tier` | medium | **CLOSED** — `_reject_unsafe_scalar` raises ValueError on `\n` in change_id/primitive/tier and `:` in change_id/primitive; the forged `tier: major` payload now raises, no file written. |
| CR-WP001-03 — block-scalar/quote/comment grammar undocumented for bash re-implementer | medium | **CLOSED** — `.changesets/README.md` gains a "Rules for re-implementers" section. |
| CR-WP001-04 — low items (README-table not conformance-tested, misnamed test, next_version doc) | low | **CLOSED** — table↔map conformance test added; test renamed/folded to full-coverage; next_version strict-triple raise documented. |

## Build Verification (CR-01)

- pytest `tests/unit/test_changeset.py` → **50 passed** (19 → 50; 31 net-new).
- `ruff check` → clean. `mypy _changeset.py` → clean.
- Founder-decision spot check: 22 vocabulary primitives all resolve non-None; `admin` → None; samples delete→minor, move→patch, secure→minor, document→patch, replace→minor, generate→minor, deprecate→patch.

## Methodology — CR-08

- [✓] CR-01 mechanical baseline ran on merged tip `4c1cbf6` (pytest/ruff/mypy clean).
- [✓] CR-02 full three-lens parallel review satisfied by the per-WP pass on identical code (`.architecture/release-train/code-reviews/PR-feat-wp-008-2026-05-28T183302Z/`, verdict PASS, 0 findings). Batch_size=1 → no cross-WP composition surface; a second parallel pass on the identical diff would add no signal. Recorded as a deliberate proportionality call.
- [✓] CR-06 verdict computed: PASS (no critical/high; Build Verification empty).
- [✓] Findings-closure verified against the prior review (table above).

## Cross-reference
- Drives-from: `.architecture/release-train/code-reviews/PR-1fd6d60-2026-05-28T171158Z/` (the keystone review that raised the four findings).
- Per-WP full review: `.architecture/release-train/code-reviews/PR-feat-wp-008-2026-05-28T183302Z/`.
