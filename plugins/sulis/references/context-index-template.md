# CONTEXT_INDEX.md Template

> **Status:** Active — v0.1.0

This is the canonical schema for `.context/{project}/INDEX.md`. SRD, SEA,
sulis-security, and any future downstream plugin parses this file using this
template. Do not deviate from the heading structure — downstream parsers
match on headings.

---

## Template

```markdown
# Project Context Index

> **Project:** {project-slug}
> **Last validated:** {YYYY-MM-DD}
> **Validated by:** /sulis:{discover-context|refresh-context}
> **Discovery completeness:** {HIGH | MEDIUM | LOW}

## Summary

{One-paragraph human-readable summary of what the cartographer found and how
to read this index. Names the major authoritative sources and any known gaps
in 2-3 sentences.}

## Stack (Inferred)

> Inferred from build files and manifests; not authoritative.

- Language(s): {e.g. TypeScript, Python}
- Frameworks: {e.g. NestJS, FastAPI}
- Build: {e.g. pnpm, poetry}
- Container: {e.g. Dockerfile present; docker-compose for local dev}
- CI: {e.g. GitHub Actions in .github/workflows/}

## Authoritative Sources

Sources the user classified as load-bearing. Downstream plugins MUST respect
these — apply Respect-Don't-Restate.

| Purpose | Path | Covers | Last modified |
|---|---|---|---|
| Architecture | architecture/ARCHITECTURE.md | Clean Architecture; ports/adapters; module boundaries | 2026-02-12 |
| Domain Model | architecture/DOMAIN_MODEL.md | Entity definitions; relationships | 2026-02-12 |
| Conventions | CONTRIBUTING.md | PR conventions; commit format; review checklist | 2026-03-10 |
| Standards | architecture/standards/AGENT_IMPLEMENTATION.md | Agent service implementation rules | 2026-04-01 |

## External ADR Registry

If an ADR library exists outside of `.architecture/{project}/adrs/`, it is
recorded here.

> **Location:** architecture/decisions/
> **Count:** 22
> **Highest ADR number:** ADR-022
> **Most recent:** ADR-022 (2026-04-12)
> **SEA new ADRs MUST start from:** ADR-023

| ADR | Title | Status | Path |
|---|---|---|---|
| ADR-001 | Development philosophy | accepted | architecture/decisions/ADR-001-development-philosophy.md |
| ADR-002 | Persistent planning crash recovery | accepted | architecture/decisions/ADR-002-... |
| ... | ... | ... | ... |

## Patterns Library

| Pattern | Path |
|---|---|
| Action Handler Pattern | architecture/ACTION_HANDLER_PATTERN.md |
| Infrastructure Reconciliation | architecture/patterns/INFRASTRUCTURE_RECONCILIATION.md |

## Informational

Sources the user classified as useful background but not binding.

| Purpose | Path | Notes |
|---|---|---|
| Tech Radar | architecture/TECH_RADAR.md | Evaluation states; not adoption commitments |
| Technical Debt | architecture/TECHNICAL_DEBT.md | Known debt inventory |
| Research | docs/research/...md | Exploration notes |

## Superseded

Sources the user classified as no longer current.

| Path | Reason | Superseded by |
|---|---|---|
| ADR-005-unified-secrets-management-OLD.md | Replaced | ADR-005-unified-secrets-management.md |
| docs/architecture-v1.md | Pre-rewrite | architecture/ARCHITECTURE.md |

## Out of Scope

Sources the user classified to exclude entirely from downstream consumption.

| Path | Reason |
|---|---|
| legacy/v0-docs/ | Different bounded context |

## Known Gaps

Topics the user identified as not covered by existing context. These are
SEA's licence to add new ADRs / TDD sections / NFR entries without
contradicting prior decisions.

- Front-end architecture not formalised (front-end/ directory exists but no ADR/HLD)
- No performance SLAs or RED-metric targets documented
- Agent service contracts not specified
- No incident-response runbook

## Related Domains

Cross-references to sibling indexes outside this project's scope.

- ../{sibling-project}/INDEX.md — sibling project's context

---

## How Downstream Plugins Read This

1. Parse the YAML-ish frontmatter (`Project`, `Last validated`, `Discovery completeness`).
2. For each row in **Authoritative Sources**: load the path, apply Respect-Don't-Restate to anything the file covers.
3. Record the External ADR Registry's `Highest ADR number` — new ADRs start at N+1.
4. Treat **Informational** as path-only awareness; load on demand only.
5. Skip **Superseded** and **Out of Scope** entirely.
6. Read **Known Gaps** as the licence to add new specification or design.
```

---

## Required vs Optional Sections

| Section | Required? | When omitted |
|---|---|---|
| Summary | Always | — |
| Stack | Always | Empty bullet list if nothing inferred |
| Authoritative Sources | Always | Single-row note: "No authoritative sources found." |
| External ADR Registry | Conditional | Omit entire section if no ADR library found |
| Patterns Library | Conditional | Omit entire section if no patterns library found |
| Informational | Always | Empty table if none |
| Superseded | Conditional | Omit entire section if none |
| Out of Scope | Conditional | Omit entire section if none |
| Known Gaps | Always | Single-row note: "None identified during discovery." |
| Related Domains | Optional | Omit if none |

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| 0.1.0 | 2026-05-14 | Initial template. Sections inspired by tria/architecture/CONTEXT_INDEX.md. |
