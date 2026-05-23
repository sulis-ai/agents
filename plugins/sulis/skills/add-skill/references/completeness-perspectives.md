# Completeness Perspectives — Gate 4 Verification

Detailed criteria for evaluating a skill at Gate 4. Each perspective gets an
explicit verdict (PASS / FAIL / DEFERRED) recorded in
`COMPLETENESS_REPORT.md`.

## Perspective 1 — Trigger accuracy

**Question:** does the `description:` field accurately predict the
conversation contexts in which Claude will invoke this skill?

### How to evaluate

1. Take the SKILL.md `description:` field and the skill name. Discard
   everything else (the body, references, scripts, templates).
2. In a fresh session (or simulate one), present Claude with 8–12 short
   conversation snippets that look like user requests. Mix:
   - 4–6 snippets that SHOULD trigger this skill (true positives)
   - 4–6 snippets that should NOT trigger this skill (true negatives,
     including ones that look superficially similar but aren't a match)
3. For each, ask Claude whether it would invoke this skill. Record the
   answer.
4. Compute precision: of the times Claude said "yes", what fraction were
   true positives?

### Pass criteria

- **PASS:** precision ≥ 85% (no more than 15% false-invocations)
- **FAIL:** precision < 85% — the description is too broad or too vague.
  Revise the description; rerun Gate 4.
- **DEFERRED:** unable to construct a representative test set (e.g., the
  skill's domain is too new). Document why; ship with an explicit risk
  flag.

### Common failure modes

- Description uses internal jargon Claude doesn't have context for.
- Description is a summary ("Generates landing pages") rather than a
  trigger ("Use when the user wants to create, optimise, or A/B test a
  landing page").
- Description's trigger overlaps significantly with an existing skill
  (Gate 1 should have caught this; if it didn't, return to Gate 1).

## Perspective 2 — Gotchas coverage

**Question:** are the skill's gotchas grounded in concrete prior failures,
or are they speculation?

### How to evaluate

1. For each gotcha listed in SKILL.md, identify its source:
   - **Prior art** — another skill's gotchas section mentions a related
     failure
   - **BRIEF_PACK** — Gate 1's inventory surfaced a relevant failure pattern
   - **Author experience** — the author has personally hit this in
     practice (document briefly which case)
   - **Speculation** — no concrete source; the gotcha "feels important"
2. Remove all speculation-sourced gotchas.
3. Verify the remaining gotchas are ordered by likelihood × impact
   (high-likelihood-high-impact first).
4. Verify there are ≤15 gotchas in SKILL.md. Overflow goes to
   `references/advanced-gotchas.md`.

### Pass criteria

- **PASS:** every gotcha has a documented source; ≤15 items; ordered by
  likelihood × impact.
- **FAIL:** ≥1 gotcha is speculation, OR >15 gotchas in SKILL.md, OR
  ordering is wrong.
- **DEFERRED:** not applicable; gotchas coverage can always be evaluated.

### Common failure modes

- Author adds gotchas that "look thorough" without prior-failure source
  (the "5 things to watch out for" antipattern).
- Gotchas are alphabetised or grouped by topic instead of ordered by
  impact.
- Gotchas section silently grows past 15 items.

## Perspective 3 — Functional completeness

**Question:** does the skill produce the promised output in real
scenarios?

### How to evaluate

1. Construct 3–5 real scenarios from the skill's target category. Each
   scenario should:
   - Be representative of typical use (not edge cases)
   - Have a clear expected output (what the skill should produce)
   - Be runnable end-to-end against the skill
2. Run the skill against each scenario. Record the output.
3. For each, judge: did the output match the expected shape? Did Claude
   follow the methodology? Were the gotchas applied?
4. Capture failure modes; classify as:
   - **Skill bug** — SKILL.md is wrong; needs revision
   - **Methodology gap** — the five gates didn't catch something; consider
     a methodology update
   - **Scenario mismatch** — the scenario wasn't actually in scope (revise
     either scenario or skill scope)

### Pass criteria

- **PASS:** ≥80% of scenarios produced the expected output without
  intervention.
- **FAIL:** <80% scenario success rate. Capture failure modes; surface as
  "required revisions" before Gate 5.
- **DEFERRED:** unable to construct real scenarios on day one (e.g.,
  scenarios require production data the author doesn't have access to).
  Document why; ship with explicit risk flag; commit to running scenarios
  within N days of publication.

### Common failure modes

- Scenarios are too narrow (skill passes on contrived inputs, fails on
  real ones).
- Scenarios are too synthetic (skill never tested against actual user
  conversation patterns).
- Output is judged on shape but not on whether it actually helps the user
  achieve their goal.

## On the verdicts

The three verdicts (PASS / FAIL / DEFERRED) compose like this:

| Combination | Publish decision |
|---|---|
| All PASS | Approved — proceed to Gate 5 |
| Any FAIL | Blocked — fix and rerun Gate 4 |
| 1+ DEFERRED, no FAIL | Approved with risk — proceed to Gate 5; risks documented in COMPLETENESS_REPORT.md |
| 2+ DEFERRED | Block; the skill needs more grounding before publication |

DEFERRED is for "could not evaluate"; FAIL is for "evaluated and didn't
meet the bar." Conflating them is how skills with known issues ship.

## Why three perspectives, not more

The kinds-and-tools spec uses five completeness perspectives (requirement
traceability, integration completeness, NFR coverage, tree completeness,
acceptance criteria). The skill artifact is simpler than a full
specification, so three perspectives are sufficient.

If a skill grows in complexity (e.g., it has runnable scripts with their
own correctness concerns), add perspectives:

- **Perspective 4 — Script correctness** — the deterministic scripts in
  the skill's `scripts/` directory produce correct outputs on a fixture
  set.
- **Perspective 5 — Reference freshness** — every referenced standard is
  at the version declared in SKILL.md; no upstream changes have
  invalidated the reference.

Add perspectives only when a failure mode is repeatedly missed; don't add
them speculatively.
