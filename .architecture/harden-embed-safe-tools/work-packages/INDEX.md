# Work Package Index — harden-embed-safe-tools (embed L1+L2 into the governed action-surface)

> **TDD:** [../TDD.md](../TDD.md) · **ARCH:** [../ARCH.yaml](../ARCH.yaml)
> **Change:** CH-522P6P · `harden` · tier M · base SHA 2da4d842
> **Scope:** embed the shipped L1 (safe-fetch) + L2 (scoped file-tools) into
> the harness — Phases 1–3 buildable backend, Phases 4–5 doc/config. Decisions
> D1–D8 LOCKED upstream.
> **Total WPs:** 5
>
> **Three largely-independent tracks** (joinable at t=0):
> - **MCP server:** WP-001 (standalone — wraps existing functions)
> - **Resolver → governance:** WP-002 → WP-003 (resolver feeds the hook)
> - **Resolver → backstop:** WP-002 → WP-004 (resolver feeds the sandbox recipe)
> - **Standard:** WP-005 (after WP-003 + WP-004 — describes their rules)
>
> **Critical path:** WP-002 → WP-003 → WP-005 (3 serial). WP-001 + WP-002
> both joinable at t=0. **Peak parallelism:** 2 (WP-001 ∥ WP-002).
>
> **Scenario coverage (SC-E1..E6 automated):** E1→WP-001, E2/E3/E4→WP-003,
> E5→WP-002, E6→WP-005. **Deferred-labelled:** E7 (testable half→WP-003;
> sandbox half→attested), E8/E9→WP-004 (consumer-config / attested).

## Status Summary

| Status | Count |
|---|---|
| pending | 5 |
| in_progress | 0 |
| done | 0 |
| blocked | 0 |

## WP Table

| ID | Title | Primitive | Status | Depends On | Blocks |
|---|---|---|---|---|---|
| WP-001 | safe-tools MCP server — wrap safe_fetch/safe_search/scoped_file as denyable MCP identities | create | pending | — | — |
| WP-002 | write-roots resolver — add brain root + sandbox-config emit, one source for L2+L3 | abstract | pending | — | WP-003, WP-004 |
| WP-003 | PreToolUse hook + permission deny-rules — block the unsafe path (locus ii) | create | pending | WP-002 | — |
| WP-004 | sandbox-enable recipe — document the locus-iii backstop consuming the resolver roots | document | pending | WP-002 | — |
| WP-005 | governed-action-surface standard (D8 2-axis) + locus-honesty test + quality nudge | document | pending | WP-003, WP-004 | — |

## WP Detail (extra columns — second table, non-canonical header)

| ID | Kind | Group | Scenarios satisfied | Verification artifact | Token (in/out) |
|---|---|---|---|---|---|
| WP-001 | backend | EXPAND | SC-E1 | tests/unit/test_safe_tools_mcp_contract.py | 11k / 9k |
| WP-002 | backend | REORGANISE | SC-E5 | tests/unit/test_write_roots_resolver.py | 10k / 8k |
| WP-003 | backend | EXPAND | SC-E2, SC-E3, SC-E4, SC-E7 (testable half) | tests/unit/test_safe_tools_hook.py | 13k / 11k |
| WP-004 | docs | REINFORCE | SC-E8, SC-E9 (deferred-attested) | (na — doc/config; asserted via SC-E5 + SC-E6) | 7k / 6k |
| WP-005 | docs | REINFORCE | SC-E6 | tests/unit/test_locus_honesty.py | 9k / 8k |
