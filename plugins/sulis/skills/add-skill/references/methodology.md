# Methodology — Why the five gates exist

This document explains the rationale for each gate in `add-skill`. Read it
once. The SKILL.md tells you *what* to do; this tells you *why*.

The methodology is grounded in patterns the kinds-and-tools spec validated for
getting consistent outcomes from agent-driven authoring. See
`kinds-and-tools-learnings.md` for the raw source patterns.

## Why a methodology instead of a checklist

The existing `docs/skill-authoring-guide.md` (97 lines) is a checklist of
tactics: write a gotchas section, use progressive disclosure, frame the
description as a trigger condition. Each tactic is correct. The checklist still
produced inconsistent skill quality.

The reason: tactics don't compose into quality unless they are applied in the
right order against the right discovery. A skill author who writes the gotchas
section before scanning what other skills already document will produce gotchas
that overlap, conflict, or speculate. A skill author who locks the trigger
condition after drafting the body will draft the body around the wrong scope.

The methodology fixes this by structuring the *conversation*, not the artifacts.
Discovery comes first (Find). Commitment comes second (Scope Lock). Drafting
comes third (Generate). Verification comes fourth (Evaluate). Adversarial review
comes last (Adversarial Review). Each gate has explicit pass criteria; the
output is a skill plus an audit trail.

This is the same pattern the kinds-and-tools spec used to ship across 28 turns
of work without vocabulary drift: ground first, lock second, write third, verify
fourth, sweep fifth. See `kinds-and-tools-learnings.md` Section D.

## Gate 1 — Find

### What failure mode it prevents

Vocabulary collision and unrecognised prior art. Two concrete failures:

1. A new skill introduces "verify" as one of its modes; another skill already
   uses "verify" to mean something different. Claude context-switches between
   them and produces confused outputs because the terms don't compose.
2. A new skill wraps a standard from one of the marketplace's existing
   `references/*.md` files but restates it inline, drifting from the source
   over time as the source is updated.

### Why deterministic-first (the hybrid pattern)

The Find phase is HYBRID per the user's design choice: a Python script gathers
the raw inventory (skills, references, gotchas, vocabulary), and Claude
interprets the results.

The split exists because:

- A script can exhaustively enumerate every skill, every reference file, every
  gotchas section, with zero recall loss. Claude reading the marketplace
  conversationally would miss things.
- Claude's judgement is needed to decide whether a flagged collision is real
  ("verify" in two skills with different semantics) or coincidental (two
  skills both mentioning "user" in their descriptions).

This mirrors the kinds-and-tools spec's pattern: deterministic stage primitives
(`read_file`, `glob`, `ripgrep`) for gathering, LLM for the
synthesis/judgement layer.

### Why this gate cannot be skipped

The vocabulary cascade in kinds-and-tools (turn 24) was only cheap because turn
23 had already grounded the terminology against actual codebase patterns. If
you skip Find, every subsequent gate operates on assumptions instead of
evidence — and the cost of correcting those assumptions compounds as more files
get written.

## Gate 2 — Scope Lock

### What failure mode it prevents

Scope creep during drafting. Without an explicit lock, the author starts
writing SKILL.md, realises they have an opinion on tangential things, adds
them, and ships a skill that's bigger and less focused than they intended.

### Why six specific items

The six items locked at Gate 2 (name, plugin home, category, trigger
condition, top-N gotchas, depth modes) are the load-bearing decisions that
shape every other file in the skill. If any of these changes mid-draft, the
draft is wrong.

The kinds-and-tools spec's analog is the apiVersion+kind decision at turn 27.
Locking that decision early made all subsequent decisions cheaper, because
they could be made against a known surface.

### Why no item can be TBD

If something is TBD at Gate 2, it will become a default during drafting (Claude
will pick something to make progress). Defaults that get committed without
deliberate choice are how skills drift in quality.

## Gate 3 — Generate

### What failure mode it prevents

Writing the wrong skill. The drafting is constrained by the Gate 2 lock, so the
output cannot drift from the agreed scope. Templates (`templates/*.template`)
provide a starting shape so the author isn't writing from a blank slate.

### Why progressive disclosure is mandatory

A SKILL.md that inlines all rationale becomes unreadable past ~300 lines.
Claude stops consulting the bottom half. The pattern is: SKILL.md is the
instruction surface; `references/` is the rationale + long-form knowledge;
`templates/` is the structural starting point; `scripts/` is the deterministic
primitives.

This is the same find/generate/evaluate/decide split applied to the skill's
own internal layout.

## Gate 4 — Evaluate

### What failure mode it prevents

Shipping a skill that looks correct on paper but doesn't actually work. The
three perspectives target three different failure modes:

- **Trigger accuracy:** Claude won't invoke the skill when it should (or will
  invoke it when it shouldn't).
- **Gotchas coverage:** the skill's gotchas are speculative rather than
  grounded in actual failures.
- **Functional completeness:** the skill produces the wrong output, or no
  output, in real scenarios.

### Why three perspectives, not one

Each perspective targets a different failure axis. A skill can pass trigger
accuracy and still fail functional completeness (Claude invokes it correctly,
but the body doesn't produce useful output). A skill can pass functional
completeness and fail gotchas coverage (the skill works, but the gotchas
section is fluff). All three are needed.

The kinds-and-tools spec's completeness report uses five perspectives; this
skill uses three because the simpler shape (skill, not full spec) needs less
coverage. If the skill grows in complexity, add perspectives.

### Why DEFERRED is valid but FAIL is not

DEFERRED means the perspective could not be evaluated (e.g., not enough real
scenarios available to test functional completeness on day one). DEFERRED must
be paired with a documented reason and an explicit acknowledged risk.

FAIL means the perspective was evaluated and the skill did not meet the bar.
Publishing a skill with a FAIL verdict is shipping a known-broken skill.

## Gate 5 — Adversarial Review

### What failure mode it prevents

Shipping a skill without having considered how it might be misused or
misinterpret a request. Most skills fail not because they are wrong but
because they are right under the author's mental model and wrong under
another reader's.

### Why borrowed from kinds-and-tools turn 28

The kinds-and-tools spec achieved its "specified" status only after turn 28's
adversarial sweep produced MISUSE_CASES.md. Before that, the spec passed
completeness checks but had not been stressed against hostile or naive use.
The sweep flipped one perspective from PASS to FAIL and triggered negative-
requirement subsections across nine FRs/NFRs.

For skills, the same pattern applies in miniature: name three ways the skill
could mislead Claude; for each, either prevent it or document the open risk.

### Why open risks must be documented, not silent

Every skill ships with some open risks; pretending otherwise is dishonest.
Documenting them (with name, impact, and rationale for acceptance) means
future authors can find them and decide whether the trade-off still holds.
Silent open risks accumulate into the kind of cumulative drift the quality
coverage matrix is meant to surface.

## On the COMPLETENESS_REPORT.md

The report is committed alongside SKILL.md. It is not metadata; it is part of
the skill's identity. Three reasons:

1. **Audit trail.** When the skill is later rewritten or deprecated, the
   report tells the next author which decisions were deliberate and which
   were deferred.
2. **Trust calibration.** A skill with PASS verdicts across all five gates is
   different from a skill with three PASSes and two DEFERREDs. Users and
   future authors should be able to see this at a glance.
3. **Process learning.** Patterns across many COMPLETENESS_REPORT.md files
   reveal where the methodology itself has gaps (e.g., if every skill defers
   the same perspective for the same reason, the methodology needs adjustment).
