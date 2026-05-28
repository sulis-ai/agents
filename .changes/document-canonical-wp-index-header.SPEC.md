# SPEC — document: canonical WP INDEX header + decompose-time lint

> Change: `change/document-canonical-wp-index-header` (CH-01KSQM / 01KSQM3DMEYS8Z1M9EF94ASRB0)
> Primitive: `document`
> Resolves: GitHub issue #60

## Context — the bug

`/sulis:plan-work` (engineering-architect) produced a WP INDEX.md whose
table header began `| WP | Title | kind | Primitive | ... |`. The
`wpx-index` / `parse_index_md` tooling detects WP tables via a regex that
requires the header to literally begin `| ID | Title |`
(`_WP_TABLE_HEADER_RE`). So the table was **invisible** to the run-all
loop: flip-status + list-ready failed with "Could not find WP table in
INDEX.md (no | ID | header)", and the loop could not flip statuses or
compute eligibility.

Latent second bug: a `kind` column AND a `Primitive` column both alias to
canonical `primitive` in `resolve_wp_columns` (`WP_COLUMN_ALIASES`:
`primitive = {primitive, kind}`), first-match-wins — so the loop would
read the kind ("backend") as the primitive.

## The fix

1. **Emit the canonical header** wherever the WP INDEX template lives —
   the `/sulis:plan-work` skill (`plugins/sulis/skills/plan-work/SKILL.md`)
   and the engineering-architect agent's INDEX template
   (`plugins/sulis/agents/engineering-architect.md`, and any template file
   it points at). Canonical form:
   `| ID | Title | Primitive | Status | Depends On | Blocks | ... |`.
   First column MUST be `ID` (not `WP`). Do NOT emit a separate `kind`
   column that duplicates `Primitive` (it aliases to the same canonical
   column and silently wins first-match).
2. **Add a decompose-time lint that fails loudly** — extend `wpx-index`
   (`plugins/sulis/scripts/wpx-index`) with a `lint` subcommand (or
   extend the existing validation path) that checks the INDEX header
   matches `_WP_TABLE_HEADER_RE` and exits non-zero with a clear message
   when it doesn't. This converts a silent mid-run-all failure into a
   surgical decompose-time error. Wire it where decompose validation
   already runs if such a hook exists; otherwise expose it as a
   standalone `wpx-index lint <INDEX.md>`.

Search first (EP-03): if `wpx-index` already has a validate/check path,
extend it rather than adding a parallel one.

## Definition of Done (Red → Green → Blue)

**RED** — tests first (column/index tests live in
`plugins/sulis/scripts/tests/unit/test_wpx_index_columns.py` and the
wpx-index integration tests):
1. A non-canonical header (`| WP | Title | kind | Primitive | ... |`) is
   **rejected** by the new lint with a non-zero exit + a message naming
   the expected header. (Fails against current code — no lint exists.)
2. The canonical header (`| ID | Title | Primitive | Status | Depends On
   | Blocks |`) **passes** the lint.
3. (Guard) `parse_index_md` / `resolve_wp_columns` on a canonical INDEX
   reads `primitive` correctly (no `kind`-wins-first ambiguity, because
   the canonical template has no `kind` column).

**GREEN** — implement the lint + fix the template/skill so they emit the
canonical header.

**BLUE** — refactor; ensure the lint reuses the existing
`_WP_TABLE_HEADER_RE` (single source of truth, no second regex). Add a
one-line note in the plan-work skill pointing at the lint so a future
decompose runs it.

## Acceptance criteria
- [ ] plan-work skill + engineering-architect INDEX template emit
      `| ID | Title | Primitive | Status | Depends On | Blocks |` (ID
      first; no duplicate `kind` column).
- [ ] `wpx-index` has a loud lint that rejects a non-canonical header
      (non-zero exit, clear message) and passes the canonical one, reusing
      `_WP_TABLE_HEADER_RE`.
- [ ] Tests cover reject + pass + correct primitive parse.
- [ ] Full scripts suite green; no new lint/type errors.

## Out of scope
- Changing the canonical column set itself (keep what `_WP_TABLE_HEADER_RE`
  + `resolve_wp_columns` already expect).
- #61, #63, #62 — separate changes.
