# Polish Rule Catalogue

The rules the scanner applies, per category, with severity + rationale.

## Documentation completeness (per plugin)

For each `plugins/<name>/` directory:

| Rule | Severity | Check |
|---|---|---|
| DC-001 | concern | `README.md` exists at plugin root |
| DC-002 | advisory | `CHANGELOG.md` exists IF plugin.json version > 1.0.0 OR multiple historical versions detectable |
| DC-003 | advisory | `LICENSE` or `LICENSE.md` exists at plugin root |
| DC-004 | advisory | plugin.json has `keywords` field with ≥3 entries |
| DC-005 | advisory | README.md has at least one `##` heading (not just a title) |

DC-001 is `concern`, not `high`, because legacy plugins often shipped
without README. Founders see "needs attention" not "❌ failed."

## Tech-debt density (per file)

Scan source files (`.py` / `.js` / `.ts` / `.jsx` / `.tsx` / `.go` /
`.rb`) for tech-debt markers:

- `TODO`
- `FIXME`
- `HACK`
- `XXX`
- `TEMPORARY`
- `WORKAROUND`

| Rule | Severity | Check |
|---|---|---|
| TD-001 | concern | Tech-debt density > 5% of total comments per file |
| TD-002 | advisory | Single file has > 20 tech-debt markers |

Density = (tech-debt-marker count) / (total comment lines). Files
with no comments have density 0.

5% is the threshold from `sulis-security:codebase-assess` CQ-04
(technical debt). Above that is "high concentration."

## File hygiene (per file)

| Rule | Severity | Check |
|---|---|---|
| FH-001 | advisory | Trailing whitespace on >5 lines |
| FH-002 | advisory | Mixed line endings (CRLF + LF in same file) |
| FH-003 | advisory | File doesn't end with newline |

Single trailing-whitespace finding is too noisy; only flag if >5 lines
(otherwise editors handle it transparently).

## Per-finding signature

Each finding has a stable signature for baseline-dedup:

- `docs-completeness::{plugin}::{rule}` (e.g., `docs-completeness::sulis-builder::DC-001`)
- `tech-debt-density::{file}::{rule}` (e.g., `tech-debt-density::plugins/sea/scripts/probe.py::TD-001`)
- `file-hygiene::{file}::{rule}` (e.g., `file-hygiene::plugins/x/y.py::FH-001`)

## Allowlist mechanism

`.checkup/{project}/check-polish-allowlist.md`:

```
# Legacy plugin without README — intentional
docs-completeness::sulis-platform-sdk::DC-001: small SDK, README in main repo

# Pinned TODO density — by-design future-work tracker
tech-debt-density::plugins/foo/bar.py::TD-001: TODO comments track feature backlog
```

Same `signature: reason` format as sibling skills.

## Why scope intentionally narrower than SEA's TDD

SEA's TDD specified tier 7 as perf/a11y/UX. Each of those requires the
founder to pick a STANDARD first:

- Performance: which latency budget? p95 < 200ms? p99 < 500ms?
  Per-endpoint or global?
- Accessibility: WCAG 2.1 AA? AAA? Specific country regs (UK PSBAR,
  EU EN 301 549)?
- UX: which design system? component library?

Without those choices, an "audit" can't be more than checklist
matching against a default — which may not match the founder's
business. v1 ships the basics where the standard is universal
(README is README, line endings are line endings); the rest waits for
upstream design.

## Adding a new rule

To extend the catalogue:

1. Add a function to `scripts/scanner.py` that returns
   `list[Finding]`
2. Add the rule to this document (severity + signature pattern)
3. Test against the marketplace + a fixture

## What this catalogue does NOT cover

Per SKILL.md "What this skill catches vs misses":
- Performance budgets
- Accessibility audits
- UX consistency / design-system adherence
- API doc completeness (beyond README presence)
- Translation / localisation
- SEO / metadata

These require dedicated skills when the founder has picked the
relevant standards.
