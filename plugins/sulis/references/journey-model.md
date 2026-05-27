# Journey Model

<!-- summary -->
The Concierge owns a 7-phase journey from "I have an idea" to "my product
is built, tested, and security-reviewed." Each phase has explicit entry
criteria, exit criteria, the specialist invoked, and the artifacts
produced. Phase Auto-Progression (per AAF-08 / v1.11.2) advances
automatically on clean verdicts — never asking *"want me to move to the
next phase?"*.
<!-- /summary -->

> **Version:** 0.1.0
> **Status:** Active — Calibration period 90 days from 2026-05-16.

---

## The 7 Phases

| # | Phase | Founder time | Specialist invoked |
|---|---|---|---|
| 1 | Greet | 2-3 minutes | (concierge alone) |
| 2 | Discover | 1-2 minutes (mostly wait) | sulis-context |
| 3 | Specify | 30-60 minutes (long conversation) | srd:requirements-analyst |
| 4 | Design | 20-40 minutes (long conversation) | sea:engineering-architect |
| 5 | Implement | hours to days (mostly autonomous) | sulis-execution:executor |
| 6 | Verify | 5-15 minutes (mostly wait) | sea:engineering-architect (verify) |
| 7 | Secure | 10-20 minutes (mostly wait) | sulis-security:security-reviewer |

---

## Phase 1 — Greet

**Purpose:** capture the founder's goal in plain English; route to the
right path.

**Entry criteria:** founder runs `claude --agent sulis` in an
empty session OR no `.sulis/{project}/JOURNEY.md` exists.

**Activities:**
- Open with the canonical greeting.
- Reflect understanding in 1-2 sentences.
- Ask at most one plain-English clarifying question.
- Capture goal in JOURNEY.md `## Goal`.
- Apply branch decision (build / fix / pitch / design / strategise).

**Exit criteria:** JOURNEY.md exists with `## Goal` populated; current
phase set to 2 (or to non-build branch).

**Produces:** `.sulis/{project}/JOURNEY.md`.

**Auto-progress to:** Phase 2 (Discover) if the goal is "build a
product"; otherwise hand off to the correct specialist plugin and end
the concierge session.

---

## Phase 2 — Discover

**Purpose:** establish whether the project is greenfield (empty repo) or
brownfield (existing codebase with prior work).

**Entry criteria:** Phase 1 complete; founder's goal is "build a
product".

**Activities (v0.1.0):**
- Recommend `/sulis:discover-context` to the founder.
- When founder returns, read `.context/{project}/INDEX.md`.
- Translate findings in plain English (no jargon — say "files" not
  "modules"; "documentation" not "ADRs").
- Identify path: greenfield vs brownfield vs hybrid.

**Exit criteria:** `.context/{project}/INDEX.md` exists.

**Produces:** `.context/{project}/INDEX.md` (sulis-context's output).

**Auto-progress to:** Phase 3.

---

## Phase 3 — Specify

**Purpose:** capture detailed functional and non-functional requirements
through guided facilitation.

**Entry criteria:** Phase 2 complete; INDEX.md exists.

**Activities (v0.1.0):**
- Recommend `claude --agent requirements-analyst` to the founder.
- Founder spends 30-60 minutes in SRD facilitation (long conversation
  with the requirements analyst).
- When founder returns, read the produced spec artifacts.
- Verify Phase 5 of SRD validation returned PASS — if GAPS_FOUND, route
  back to the SRD analyst to resolve.
- Translate the spec into a plain-English summary for the founder.

**Exit criteria:**
- `.specifications/{project}/SRD.md` exists.
- `.specifications/{project}/NFR.md` exists.
- `.specifications/{project}/PRIMITIVE_TREE.jsonld` exists.
- `.specifications/{project}/GLOSSARY.md` exists.
- `.specifications/{project}/COMPLETENESS_REPORT.md` shows PASS verdict.

**Produces:** all of the above plus possibly `MISUSE_CASES.md`,
`RECONCILIATION_MAP.md`, `EXPLORATION_JOURNAL.md`.

**Auto-progress to:** Phase 4.

---

## Phase 4 — Design

**Purpose:** translate requirements into a Technical Design Document plus
an ordered Work Package backlog ready for implementation.

**Entry criteria:** Phase 3 complete; SRD PASS.

**Activities (v0.1.0):**
- Recommend `/sulis:draft-architecture` (produces TDD + ADRs).
- When founder returns, read TDD + ADRs.
- Recommend `/sulis:plan-work` (produces Work Packages with INDEX).
- When founder returns, read Work Package INDEX.
- Translate: "[N] components, [M] technical decisions recorded, [K]
  tasks to build (organised so [a, b] can happen in parallel)."

**Exit criteria:**
- `.architecture/{project}/TDD.md` exists.
- `.architecture/{project}/adrs/ADR-*.md` exist (at least one).
- `.architecture/{project}/work-packages/INDEX.md` exists.
- `.architecture/{project}/work-packages/WP-*.md` exist (at least one,
  status `pending`).

**Produces:** TDD, ADRs, Work Packages, INDEX, SIZING.md.

**Auto-progress to:** Phase 5.

---

## Phase 5 — Implement

**Purpose:** actually build the code that implements each Work Package,
running the Red-Green-Blue cycle per WP.

**Entry criteria:** Phase 4 complete; WP INDEX exists.

**Activities (v0.1.0):**
- Recommend `/sulis:run-all` to the founder.
- Executor processes WPs in topological order.
- When founder returns (or when executor surfaces a blocker), read WP
  status in INDEX.md.
- For each blocker, translate to plain English and either resolve
  silently (AAF-01 step-1-silent) or ask the founder a plain-English
  question.

**Exit criteria:**
- All WPs in INDEX have `status: done` with acceptance evidence (commit
  SHAs, dates).
- No `blocked` WPs remain.

**Produces:** code, tests, commit history. WP frontmatter updates.

**Auto-progress to:** Phase 6.

---

## Phase 6 — Verify

**Purpose:** confirm the built code meets the design — pillar coverage,
contract tests, chaos tests, referential integrity.

**Entry criteria:** Phase 5 complete; all WPs `done`.

**Activities:**
- Recommend `/sulis:verify-architecture` to the founder.
- When founder returns, read `.architecture/{project}/COMPLETENESS_REPORT.md`.
- If PASS: auto-progress to Phase 7.
- If GAPS_FOUND: translate gaps; apply AAF triage. Step-1/2-silent
  gaps trigger re-invocation of executor; step-3 survivors get asked of
  founder in plain English.

**Exit criteria:** Verify report shows PASS.

**Produces:** `.architecture/{project}/COMPLETENESS_REPORT.md`.

**Auto-progress to:** Phase 7.

---

## Phase 7 — Secure

**Purpose:** business-risk assessment over the built product.

**Entry criteria:** Phase 6 complete; Verify PASS.

**Activities:**
- Recommend `/sulis:codebase-assess` to the founder.
- When founder returns, read `.security/{project}/viability-report-*.md`.
- Translate findings by severity:
  - **CRITICAL** → must-fix-before-ship items (1 sentence each in
    business-risk terms).
  - **CONCERN** → medium-priority items (1 sentence each).
  - **ADVISORY** → minor notes (grouped).
  - **PASS** → not surfaced (clean primitive).

**Exit criteria:** Viability report produced; concierge has presented
the final journey summary to the founder.

**Produces:** `.security/{project}/viability-report-{YYYY-MM-DDTHHMMSSZ}.md` (ISO 8601 UTC timestamp, prevents same-day rerun collisions).

**Final summary** (action-then-report shape, never permission-theater):

> *"Done. Your [thing] is built, tested, verified, and security-
> reviewed.*
>
> *Three things worth knowing:*
> *1. [translated security finding 1, or 'no critical issues found']*
> *2. [translated verify warning, or 'all checks passed']*
> *3. [WP completion stats]*
>
> *What would you like to do next?"*

---

## Branch decisions in Phase 1

Not every founder is building a product. The Phase 1 branch decision
routes correctly:

| Founder said | Path |
|---|---|
| build / make / ship / create a product / app / SaaS | Phases 2-7 (concierge primary path) |
| fix bugs / harden / audit my code | Phases 2, 6, 7 (skip Specify + Design + Implement; route to harden-style workflow if relevant) |
| pitch / fundraise / make a deck | Recommend `/investor-coach:start`; end concierge session |
| design / branding / visual identity | Recommend `/sulis-design:start`; end concierge session |
| business strategy / GTM / pricing | Recommend `/sulis-strategy:start`; end concierge session |
| explore an existing codebase | Recommend `/sulis:discover-context`; offer to continue with SEA codebase-audit afterwards |

---

## Transition criteria — when to advance

Each phase advances **automatically** when its exit criteria are met
(Phase Auto-Progression per AAF-08 / v1.11.2). The concierge does not
ask the founder *"want me to move to the next phase?"*. Instead:

> *"Requirements done. Starting design — recommending you run
> `/sulis:draft-architecture` next."*

The single exception is the AAF-05 revoke signal — a founder who has
said *"slow down"* or *"check with me on each phase"* opts into per-
phase confirmation. The concierge honors the revoke until reversed.

---

## Version History

| Version | Date | Change | Author |
|---|---|---|---|
| 0.1.0 | 2026-05-16 | Initial 7-phase model. Calibration period 90 days. Promotion to MUST repo-wide requires evidence from three end-to-end sessions where the journey ran cleanly. | Standards team |
