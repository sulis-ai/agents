# Context Discovery Protocol

> **Status:** Active — v0.1.0

The scan catalogue used by `/sulis:discover-context` and `/sulis:refresh-context`.
Defines what to look for, where to look, and how to present findings.

This protocol is **folder-structure-agnostic** by design. Real projects don't
follow one convention — some use `architecture/`, some `docs/architecture/`,
some scatter ADRs across `decisions/`, `adr/`, or `docs/adr/`. The protocol
matches by *purpose*, not by hard-coded paths.

---

## Scan Catalogue

The discovery skill walks the entire project tree once and matches files
against this catalogue. Multiple matches per file are allowed (a
`CONTRIBUTING.md` can be both "convention" and "documentation index").

### Purpose 1 — Architecture Documentation

What the system *is* — components, boundaries, dependencies, high-level design.

| Glob pattern | Why it matches |
|---|---|
| `**/ARCHITECTURE.md` | Standard architecture summary |
| `**/CONTEXT_INDEX.md` | Pre-existing context index (e.g. tria-style) |
| `architecture/**/*.md` | Dedicated architecture folder |
| `docs/architecture/**/*.md` | Architecture under docs |
| `docs/system/**/*.md` | System-design docs |
| `docs/design/**/*.md` | Design folder |
| `**/SYSTEM.md`, `**/HLD.md` | High-level design docs |

### Purpose 2 — Architecture Decision Records (ADRs)

Decisions made and why. Often the most load-bearing context.

| Glob pattern | Why it matches |
|---|---|
| `**/adrs/**/*.md` | ADR directory |
| `**/decisions/**/*.md` | Decisions directory |
| `architecture/decisions/**/*.md` | Architecture/decisions |
| `docs/adr/**/*.md` | Docs/adr (Nat Pryce convention) |
| `docs/decisions/**/*.md` | Docs/decisions |
| `**/ADR-*.md` | Direct ADR file naming |

When an ADR directory is found, count entries and record the highest ADR
number — this is what SEA needs to avoid collision when generating new ADRs.

### Purpose 3 — Engineering Conventions

How the team writes, names, structures, and reviews code.

| Glob pattern | Why it matches |
|---|---|
| `CONTRIBUTING.md` (any depth) | Conventions for contributors |
| `CONVENTIONS.md`, `STANDARDS.md` | Explicit standards doc |
| `STYLE_GUIDE.md`, `CODE_STYLE.md` | Code style |
| `architecture/standards/**/*.md` | Standards under architecture |
| `docs/standards/**/*.md` | Standards under docs |
| `docs/conventions/**/*.md` | Conventions folder |
| `.cursorrules`, `CLAUDE.md`, `AGENTS.md` | AI-collaboration conventions (also load-bearing) |

### Purpose 4 — Patterns Library

Reusable patterns the project has named and documented.

| Glob pattern | Why it matches |
|---|---|
| `architecture/patterns/**/*.md` | Patterns under architecture |
| `docs/patterns/**/*.md` | Patterns under docs |
| `**/PATTERN_*.md`, `**/*_PATTERN.md` | Direct pattern file naming |

### Purpose 5 — Tech & Debt Inventory

What's in the stack, what's deprecated, what's deferred.

| Glob pattern | Why it matches |
|---|---|
| `**/TECH_RADAR.md`, `**/TECHNOLOGY_RADAR.md` | Thoughtworks-style radar |
| `**/TECHNICAL_DEBT.md`, `**/TECH_DEBT.md` | Debt inventory |
| `**/DEPENDENCIES.md` | Dependency catalogue |
| `**/STACK.md` | Stack reference |

### Purpose 6 — Domain Models & Glossary

What the system *is about* — entities, relationships, vocabulary.

| Glob pattern | Why it matches |
|---|---|
| `**/DOMAIN_MODEL.md`, `**/DOMAIN.md` | Domain model |
| `**/ONTOLOGY*.md` | Ontology spec |
| `**/GLOSSARY.md` | Glossary |
| `**/ENTITY_MODEL.md`, `**/PLATFORM_ENTITY*.md` | Entity models |
| `**/SUBDOMAIN*.md` | Subdomain models |

### Purpose 7 — Existing Specs

Requirements material that already exists.

| Glob pattern | Why it matches |
|---|---|
| `.specifications/**/*.md`, `.specifications/**/*.yaml` | Prior SRD output |
| `specs/**/*.md` | Generic specs folder |
| `requirements/**/*.md` | Requirements folder |
| `docs/specs/**/*.md`, `docs/requirements/**/*.md` | Docs subfolder |
| `**/SRD*.md`, `**/REQUIREMENTS.md` | Direct spec files |

### Purpose 8 — Prior SEA / sulis-security Output

What other plugins have already produced.

| Glob pattern | Why it matches |
|---|---|
| `.architecture/**/*` | Prior SEA output |
| `.security/**/*` | Prior sulis-security output |
| `.context/**/*` | This plugin's own prior output (for `refresh`) |

### Purpose 9 — Build & Stack Indicators

Not indexed as authoritative sources, but used to *infer* language/stack so
SRD/SEA can be context-aware about typical conventions.

| Glob pattern | Why it matches |
|---|---|
| `Makefile`, `justfile`, `Taskfile.yml` | Build entry point |
| `package.json`, `pnpm-workspace.yaml` | Node ecosystem |
| `Cargo.toml`, `go.mod`, `pyproject.toml`, `pom.xml`, `*.csproj`, `Gemfile`, `composer.json` | Language manifests |
| `Dockerfile`, `docker-compose.yml` | Container/deploy |
| `.github/workflows/*.yml`, `.gitlab-ci.yml` | CI |

These contribute to an inferred `stack` field in the index but are not asked
about individually.

### Purpose 10 — Open-Ended Probe

After all the above, ask the user: *"Are there other documents I should know
about? Anything in `README.md`, internal wikis, or elsewhere in the repo I
haven't surfaced?"*

This catches the genuinely project-specific documents that pattern matching
will always miss.

---

## Scan Limits

To keep discovery fast and avoid pathological repos:

- **Max files scanned:** 5000. Above this, the scan reports "very large
  repo — recommend narrowing scope" and asks the user for a subdirectory.
- **Max single-file size for content preview:** 100 KB. Larger files get a
  path-only listing.
- **Excluded by default:** `node_modules/`, `vendor/`, `.git/`,
  `target/`, `dist/`, `build/`, `.next/`, `.venv/`, `__pycache__/`,
  `*.lock`, lockfiles, binaries.
- **Symlinks:** followed only within the repo root.

---

## Presentation Rules

When surfacing candidates to the user for classification:

1. **Group by purpose**, not by directory. The user is classifying
   "architecture docs," "ADRs," "conventions" — not folders.
2. **Show file path + first 10 lines (or first 500 chars)** as preview.
3. **Batch within purpose, one question per purpose.** Don't ask 22 separate
   questions about 22 ADRs — surface the ADR registry as a single entry
   ("22 ADRs in `architecture/decisions/`. Classify the registry: ...").
4. **Ask whether the registry is current.** If the directory exists but the
   most recent ADR is from 2024, the user may classify it as
   `superseded`.
5. **End with the open-ended probe** (Purpose 10).

---

## Classification Inputs

After scanning, each candidate is presented to the user with one of these
classifications (see `classification-taxonomy.md` for full definitions):

- `authoritative` — load-bearing; downstream plugins MUST respect
- `informational` — useful context, not binding
- `superseded` — older version; ignore for new work
- `out-of-scope` — exclude entirely from downstream consumption

A candidate with no classification is treated as `informational` by default.

---

## Refresh Logic

`/sulis:refresh-context` re-runs the scan and:

1. Re-validates that each previously-indexed file still exists. Missing files
   become `superseded` with a note.
2. Compares mtimes against the index's `Last validated` date. Files modified
   since the last validation are flagged for re-review.
3. Surfaces newly-matched files that didn't exist at the last scan.
4. Asks the user only about the *deltas* — not the full catalogue. If
   nothing has changed, the refresh is a no-op with a timestamp update.

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| 0.1.0 | 2026-05-14 | Initial protocol. Ten scan purposes, ten file-pattern catalogues. |
