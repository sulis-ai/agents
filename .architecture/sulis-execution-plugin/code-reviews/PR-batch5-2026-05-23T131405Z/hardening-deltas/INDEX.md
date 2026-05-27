# Hardening Delta Index — Code Review PR-batch5-2026-05-23T131405Z

**Supersedes:** [PR-batch5-2026-05-23T124318Z/hardening-deltas](../../PR-batch5-2026-05-23T124318Z/hardening-deltas/INDEX.md)

**Status:** No drafts produced by this review.

## Why

All three findings from the prior review (HD-010 CRITICAL, HD-011 medium,
HD-012 high) have been addressed in the working tree before commit. The
prior review's drafts at `../PR-batch5-2026-05-23T124318Z/hardening-deltas/`
remain on disk for traceability; they are now historical artifacts (the
fixes they prescribed are landed in this same diff that this review
verifies).

## Verification of Resolution

| Prior finding | Resolved in | Test backing |
|---|---|---|
| HD-010 (CRITICAL — data loss) | `scripts/_wpxlib.py:2222-2371`, `scripts/wpx-train:105, 1843-1851, 1881, 1897` | `test_mark_gates_complete_preserves_bundle_and_deploy_fields` + 2 tightened existing tests |
| HD-011 (medium — phase_descriptions drift) | `scripts/_wpxlib.py:2146-2163` | `test_phase_descriptions_covers_every_non_terminal_phase` + `test_phase_descriptions_has_no_dead_keys_outside_phases` |
| HD-012 (high — SDK lag) | `sdk/sulis-execution.openapi.yaml`, `sdk/python/sulis_execution/{types,resources/train}.py`, `sdk/typescript/src/{types,resources/train}.ts`, `sdk/mcp-server/tests/test_server.py` | 6 new SDK tests + 1 MCP tool count assertion + `tsc --noEmit` clean |

## Watch List (not deltas — observational)

- `_TRAIN_RECORD_SCALAR_KEYS` is now load-bearing schema (future field
  additions must update this tuple). Candidate for a future REORGANISE
  WP that promotes it to a typed dataclass.
- `_wpxlib.find_wp_merge_sha` has an inline YAML-lite parser that
  duplicates the new `read_train_run_record` logic. Candidate for a
  REORGANISE-Refactor WP.
