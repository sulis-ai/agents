# ADR-001 — One widened WP-id matcher, defined once, reused by every caller

> **Change:** CH-5DMB1N · extend · `unique-wp-ids`
> **Status:** accepted
> **Date:** 2026-06-10

## Context

WP ids are gaining a change-handle prefix: `{CH-HANDLE}-WP-NNN` (e.g.
`CH-5DMB1N-WP-001`), alongside the retained legacy bare `WP-NNN` and the
existing source-tagged `WP-{SOURCE}-{NNN}`. Today the recognition that a string
is a WP id is open-coded as `startswith("WP-")` (and a `removeprefix("wp-")` for
the branch-suffix) in **five** call sites:

1. `_wpxlib.py:parse_index_md` row-filter (~L1801) — drops non-WP rows
2. `_wpxlib.py:_normalise_wp_reference` (~L1730) — full-id detection
3. `_wpxlib.py:_branch_name` (~L1990) — NNN suffix for branch naming
4. `_wpxlib.py:resolve_wp_branch` (~L2218) — NNN suffix for branch resolution
5. `_p_ver_rubric.py` (~L111) — filename filter that skips WP files in a fixture dir

Widening each site independently is the precise mechanism by which a matcher and
its validators drift. The codebase already learned this lesson once: `#60`/EP-03
drove the `validate_wp_index_header` ↔ `parse_index_md` shared-regex
(`_WP_TABLE_HEADER_RE`, `CANONICAL_WP_INDEX_HEADER`) so the lint and the parser
can never disagree about what a WP table header is.

## Decision

Define the widened WP-id recognition **once** in `_wpxlib.py` — a single
module-level regex plus a thin predicate/extractor surface — and have all five
sites consume it. The surface is the minimum the callers need:

- **`is_wp_id(s: str) -> bool`** — does this string name a Work Package id?
  Recognises all three shapes (`CH-…-WP-NNN`, `WP-NNN`, `WP-{SOURCE}-{NNN}`).
  Consumed by sites 1, 2, and (as a filename variant) 5.
- **`wp_nnn_suffix(s: str) -> str`** — the lowercased `wp-NNN` tail used to
  compose and resolve branches. Consumed by sites 3 and 4. For a prefixed id it
  strips the `CH-<HANDLE>-` prefix; for a bare/source-tagged id it returns the
  existing tail unchanged. This is what keeps the #283 per-change branch scheme
  clean — without it, `removeprefix("wp-")` is a no-op on `ch-5dmb1n-wp-001`
  and the branch would carry a doubled, leaked id
  (`wp/{scope}/wp-ch-5dmb1n-wp-001-{slug}`).

The single regex is the source of truth; the predicate and extractor are thin
readers over it, exactly as `validate_wp_index_header` reads `_WP_TABLE_HEADER_RE`.

This is **EXPAND-Create at the abstraction level** — extracting the shared
primitive EP-03 mandates — *not* SUBSTITUTE-Wrap: no layer is placed over
internal code; the existing call sites are edited in place to consume the new
predicate.

## Alternatives considered

- **Widen each `startswith` independently (rejected).** Five copies of the same
  recognition rule that can drift apart — the exact failure `#60`/EP-03 fixed
  for the table-header regex. A new id shape (e.g. a future scheme) would have
  to be threaded through five sites by hand, and a missed site fails *silently*
  (a dropped row, a mis-named branch). Rejected as a known anti-pattern in this
  codebase.
- **A regex per concern (one for rows, one for refs, one for branches)
  (rejected).** Still multi-source; the shapes they accept can diverge. The
  whole point is a single accepted-shape definition.
- **Parse the id into a structured object (`WPId` dataclass) (rejected for
  now).** Heavier than the callers need — they only ask "is this a WP id?" and
  "what's the NNN tail?". A full parse is YAGNI for this change; the predicate +
  extractor is the boring, sufficient surface. Can be revisited if a future
  caller needs the handle component in isolation.

## Consequences

- All five sites read one definition; adding or retiring an id shape is a
  one-line regex edit, validated by the shared tests.
- The branch scheme from #283 stays clean and per-change-namespaced because
  `wp_nnn_suffix` strips the handle prefix before composing the branch.
- The matcher's accepted-shapes set is itself a test target (the both-shapes
  regression guard), so back-compat cannot regress unnoticed.
