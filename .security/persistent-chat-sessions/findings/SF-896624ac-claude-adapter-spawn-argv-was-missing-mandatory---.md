---
id: SF-896624ac
severity: CONCERN
signature: 896624ac8d69
source_wp: WP-009
detected_at: 2026-06-05T16:34:43Z
primitive: ADAPTER-ARGV
---

## Summary

Claude adapter spawn argv was missing mandatory --verbose flag; real claude died with STDIN_BROKEN until WP-009's observed-done gate caught it (fixed + regression-pinned)

## Evidence

```
{
  "observed": "First real-claude run of the demo (WP-009 observed-done gate) died mid-turn: error {category:protocol, code:STDIN_BROKEN}, zero chunks.",
  "reproduction": "printf '{\"type\":\"user\",\"message\":{\"role\":\"user\",\"content\":\"say hi in 3 words\"}}\\n' | claude -p --input-format stream-json --output-format stream-json --include-partial-messages --dangerously-skip-permissions",
  "child_stderr": "Error: When using --print, --output-format=stream-json requires --verbose",
  "claude_version": "2.1.165",
  "root_cause": "_session_manager/adapters/claude.py _BASE_ARGV omitted --verbose, which the claude CLI mandates with -p + --output-format=stream-json; the child exits 1 before any output, surfaced by the manager as STDIN_BROKEN.",
  "why_units_missed_it": "WP-003/008 unit + contract tests decode RECORDED stream-json fixtures and never spawn the real binary, so spawn_argv correctness against the live CLI was unverified until WP-009's observed-done gate ran it for real.",
  "fix_applied": "Added --verbose to _BASE_ARGV (one token) + pinned it with a regression assertion in tests/unit/test_claude_adapter.py::test_spawn_argv_streaming_flags. Re-ran observed-done: live streaming + memory + warm-second-turn all proven."
}
```

## Suggested fix

Fixed in WP-009: added --verbose to _BASE_ARGV and pinned via test_spawn_argv_streaming_flags. Captured here so WP-003's adapter authoring learns the real-binary requirement and future provider adapters validate spawn_argv against the live CLI, not only recorded fixtures.

## Cross-references

- Source WP: WP-009
- Auto-draft WP: WP-AUTO-896624ac (created by this Step 11 run)
- Duplicate observations: none yet
