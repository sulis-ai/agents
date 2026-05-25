# Operator → Founder Translation Table

For founder mode (`--raw` not set). Each heuristic name + technical
phrasing maps to a plain-English equivalent. Apply at output time per
founder-facing-conventions.md Rule 4.

## Heuristic-name translation

| Operator term | Founder term |
|---|---|
| `naming-clarity` | "Hard-to-read names" |
| `kitchen-sink-file` | "Files doing too many jobs" |
| `jargon-density` | "Domain jargon a new person would struggle with" |
| `magic-method-name` | "Names that don't say what they do" |
| `over-abbreviated` | "Names that are too short to be clear" |
| `over-long` | "Names that are awkwardly long" |
| `unexplained-acronym` | "Acronyms with no glossary entry" |
| `low-doc-coverage` | "Modules with no top-line explanation" |

## Identifier presentation

Identifiers always parenthetical to the founder-readable label, never
the headline.

| Operator headline | Founder headline |
|---|---|
| `_wpxlib.py is a kitchen sink` | "The work-package-lib file is doing too many jobs (`_wpxlib.py`)" |
| `proc_d → process_deploy` | "The function `proc_d` could be `process_deploy` — it would explain itself" |
| `WP-AUTO-018 named ambiguously` | "The observability-adapter task name is unclear (`WP-AUTO-018`)" |

## File-path presentation

| Format | Use when |
|---|---|
| Bare path in monospace (`observability_adapter.py`) | Per-finding location reference (parenthetical or "File:" line) |
| Translated description ("the observability adapter file") | Headline / sentence subject |
| Never: full absolute path | Founders don't need `/Users/iain/...`; relative paths from project root only |

## Verdict-strength wording

| Heuristic verdict | Founder verdict |
|---|---|
| `pass` (0 findings) | "Clear — nothing needs attention." |
| `mostly_pass` (1-5 advisory findings) | "Mostly clear — a few things worth tidying when convenient." |
| `partial` (6-20 findings OR ≥1 concern-severity) | "Getting messy — some things need attention." |
| `fail` (>20 findings OR ≥1 high-severity) | "Hard to read — worth focused cleanup before adding more." |

Note: verdict strength is based on finding count AND severity. A single
"file is 8,000 LOC" finding can fail the whole audit; ten "name could be
clearer" advisories can stay at "mostly clear."

## Severity translation

| Operator severity | Founder phrasing |
|---|---|
| `high` | "needs attention" |
| `concern` | "worth fixing" |
| `advisory` | "worth tidying when convenient" |
| `info` | "for your information" |

## Domain vocabulary — what NOT to flag

The audit respects the project's established vocabulary. If found, the
following terms are NOT flagged as jargon:

- Terms in `plugins/sea/references/boring-code.md`
- Terms in any project-level `GLOSSARY.md` (top-level or `.specifications/{project}/`)
- Terms in `plugins/sulis/references/founder-english.md`'s glossary section
  (if present)
- Per-project vocabulary in `references/check-readability-vocabulary.md`
  (per-project allow-list — author this if the audit flags too many
  legitimate terms; one term per line)

The audit reports which vocabulary sources it consulted, so the founder
knows what was treated as established.

## What NOT to translate

Some operator terms have no good founder equivalent and ARE the
founder vocabulary now (because the founder uses them every day in
this marketplace):

- `inbox` — already founder-vocab; don't translate
- `checkup` — already founder-vocab; don't translate
- `PR` — universal abbreviation; explain on first use, then use bare
- `codebase` — universal; don't translate

The translation table is for code-internal terms that operators
recognise but founders don't. It is NOT for marketplace-level concepts
the founder has learned by using the marketplace.
