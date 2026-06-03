# fix: frontmatter parser aliases depends_on → dependsOn + strips inline `#` comments

Closes #104.

## Problem

SEA-authored WP frontmatter drifted on two axes:

1. **Key drift** — SEA wrote `depends_on` (snake) while every wpx /
   execution reader queries `dependsOn` (camel). Declared deps silently
   disappeared, list-ready dispatched WP-003 even though its deps
   weren't met.
2. **Inline comments** — the YAML-lite parser only skipped lines whose
   first character was `#`; it did NOT strip trailing inline `# comment`
   on values, so `primitive: create  # placeholder` corrupted the
   parsed value to `create  # placeholder` and downstream validators
   rejected it. Same for commented list items.

## Fix

`_wpxlib.parse_frontmatter`:

- New `_alias_frontmatter_key()` collapses `depends_on` and `depends-on`
  to the canonical `dependsOn` at parse time.
- New `_strip_frontmatter_inline_comment()` strips trailing YAML-form
  comments (whitespace + `#` + end-of-line OR whitespace + comment text)
  from scalars, list items, and inline-list items. A `#` glued to a
  value with no leading whitespace (e.g. `Honest #1`, `WP-#1`) stays
  intact.

plan-work SKILL.md gets a "MUST use camelCase `dependsOn`" callout right
under the WP template so authors emit the canonical spelling; the
parser-side alias is the defensive net.

## Tests

Added five RED-before-fix unit tests in
`tests/unit/test_wpxlib_frontmatter.py`:

- `test_depends_on_snake_case_aliases_to_dependsOn`
- `test_depends_on_snake_case_multiline_list_aliases`
- `test_strips_inline_comment_from_scalar` (covers `Honest #1`)
- `test_strips_inline_comment_from_list_items`
- `test_strips_inline_comment_from_inline_list_items`

Full frontmatter / wpxlib regression: 46 passed.
