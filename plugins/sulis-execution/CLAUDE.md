# Sulis Execution — DEPRECATED (moved to sulis plugin v0.30.0)

The executor + train + wpx-* CLI tools moved into the `sulis` plugin
at v0.30.0 (2026-05-25). What's left here is the SDK packages only:

- `sdk/python/` — published as `sulis-execution` on PyPI
- `sdk/typescript/` — published as `@sulis-ai/execution` on npm
- `sdk/mcp-server/` — published as `sulis-execution-mcp` on PyPI

These keep their package names because external consumers depend on
them. The SDK may move to a dedicated repo later (`sulis-ai/sulis-
execution-sdk`); that's a separate decision.

## New command names

| Was | Now |
|-----|-----|
| `/sulis-execution:run-wp WP-NNN` | `/sulis:run-wp WP-NNN` |
| `/sulis-execution:run-all` | `/sulis:run-all` |
| `/sulis-execution:retry WP-NNN` | `/sulis:retry WP-NNN` |
| `/sulis-execution:status` | `/sulis:wp-status` (renamed; `/sulis:status` was already taken by the concierge journey status) |
| `/sulis-execution:backfill-code-review` | `/sulis:backfill-code-review` |
| `/sulis-execution:backfill-gates` | `/sulis:backfill-gates` |

## Where each piece lives now

| Was | Now |
|-----|-----|
| `plugins/sulis-execution/agents/executor.md` | `plugins/sulis/agents/executor.md` |
| `plugins/sulis-execution/agents/orchestrator.md` | `plugins/sulis/agents/orchestrator.md` |
| `plugins/sulis-execution/scripts/_wpxlib.py` (3429 LOC) | `plugins/sulis/scripts/_wpxlib.py` |
| `plugins/sulis-execution/scripts/wpx-*` (11 CLIs + sulis-change) | `plugins/sulis/scripts/wpx-*` |
| `plugins/sulis-execution/scripts/tests/` (249 tests) | `plugins/sulis/scripts/tests/` |
| `plugins/sulis-execution/references/lifecycle.md` (2292 LOC) | `plugins/sulis/references/lifecycle.md` |
| `plugins/sulis-execution/references/primitive-scaffolds.md` | `plugins/sulis/references/primitive-scaffolds.md` |
| `plugins/sulis-execution/references/self-heal-budget.md` | `plugins/sulis/references/self-heal-budget.md` |
| `plugins/sulis-execution/docs/research/*` | `plugins/sulis/docs/executor-research/*` |
| `plugins/sulis-execution/E2E_TEST.md` | `plugins/sulis/docs/executor-e2e-test.md` |
| `plugins/sulis-execution/sdk/*` | **STAYS** — published packages |

## What didn't move

- **The SDK packages.** They retain stable package names; external
  consumers depend on `sulis-execution` (PyPI), `@sulis-ai/execution`
  (npm), `sulis-execution-mcp` (PyPI). Moving them would be SemVer-
  breaking.
- **This CHANGELOG.md.** Sealed at v0.25.0 (the deprecation version).
  All future executor changes go in `plugins/sulis/CHANGELOG.md`.

## Removal timeline

This plugin shell is retained as a deprecation marker + SDK distribution
wrapper. Remove (or move SDK to a dedicated repo) when convenient.
