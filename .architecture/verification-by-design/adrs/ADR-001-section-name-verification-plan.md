---
id: ADR-001
title: Section heading is "Verification Plan"
status: accepted
change_id: 01KT2BPBFESCCDY8F7Y5M8RN4R
date: 2026-06-01
resolves: SRD Open Question 1
---

# ADR-001 — Section heading is "Verification Plan"

## Decision

The new design-time section in every SRD, TDD, and Work Package
frontmatter is named **`## Verification Plan`** — exact casing, exact
spacing, no abbreviation. The literal string appears in:

- `plugins/sulis/skills/requirements-templates/SKILL.md` (the SRD
  template block)
- The TDD template produced by `/sulis:draft-architecture`
- Every reference to the section in agent prompts and skill prose
- The P-VER rubric's section-presence check (the regex anchors on this
  literal)

## Context

SRD Open Question 1 surfaced three candidates: *Verification Plan*,
*Acceptance Strategy*, *How We'll Verify*. The founder's verbatim
framing — *"verification can't be bolted on at the end. It has to start
as a design question — 'how would we actually verify this works?'"* —
implies a **plan**, not a strategy or a how-to. The other artifacts in
the marketplace already use "Plan" terminology (Work Package, plan-work
skill, slice plan), so "Verification Plan" reads as a sibling of the
existing lexicon.

A further constraint: founder-readability (NFR-001, FE-01..FE-11). The
name has to be answerable in plain English by a non-technical founder.
*"How We'll Verify"* fails the read-aloud test ("the how-we'll-verify
section" is awkward). *"Acceptance Strategy"* introduces an unfamiliar
noun ("strategy") and pairs with the testing-jargon "acceptance"
(acceptance test, acceptance criteria — engineer vocabulary).

## Alternatives considered

1. **`## Acceptance Strategy` (rejected).** Reasons: (a) "strategy"
   reads as outcome-after-the-fact in marketing-speak, not as a
   design-time commitment; (b) overloads "acceptance" which already
   means something in BDD/Gherkin contexts; (c) less scannable than
   "Plan" — a founder reading the section heading does not immediately
   know what kind of thing to expect.

2. **`## How We'll Verify` (rejected).** Reasons: (a) reads as
   informal narrative section (a paragraph, not a structured plan);
   (b) implementation-style heading (a question) rather than artifact
   heading (a noun) — every other top-level SRD/TDD heading is a noun;
   (c) the question-form invites prose, the noun-form invites
   structure.

3. **`## Verification` (rejected).** Reasons: (a) too short — reads as
   a category, not a contract; (b) collides with existing usage of
   "verification" as a verb in code-review skill prose and the
   `verify` built-in skill; (c) loses the design-time-commitment
   framing that "Plan" carries.

## Consequences

**Positive.**
- The literal `## Verification Plan` appears in 10+ files; one canonical
  string means the regex check in P-VER is trivial and the
  citation-presence check is unambiguous.
- "Plan" pairs with `/sulis:plan-work` semantically — the user already
  expects "plan" in the design phase.
- Founder-readable (FE-01..11, NFR-001 PASS).

**Negative.**
- Slight ambiguity with project-management "plan" (which is a Gantt /
  schedule artifact). Mitigated by the section's structured subsections
  — anyone opening it sees verification questions, not dates.

**Neutral.**
- One word swap downstream if the founder dislikes it post-merge. The
  literal is touched in fewer than 15 files and a single sed-style
  refactor handles a rename.

## Founder confirmation required?

No. SRD Open Question 1 had a clear recommendation ("Verification
Plan"); the only objection in the brief was naming-aesthetic, which is
covered by the rationale above. Per the dispatch brief's instruction to
*resolve the 7 Open Questions with explicit rationale autonomously*,
this ADR is the resolution. Founder may override post-merge via the
methodology-change pathway (which is itself this change's mechanism —
adding a new adapter row in `VERIFICATION_QUESTIONS.md` would carry the
same workflow).
