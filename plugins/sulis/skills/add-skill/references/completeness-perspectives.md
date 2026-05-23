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

1. Construct 3–5 scenarios from the skill's target category. Use the
   fixtures pattern below to make this repeatable.
2. Run the skill against each scenario. Record the output.
3. For each, judge: did the output match the expected shape? Did Claude
   follow the methodology? Were the gotchas applied?
4. Capture failure modes; classify as:
   - **Skill bug** — SKILL.md is wrong; needs revision
   - **Methodology gap** — the five gates didn't catch something; consider
     a methodology update
   - **Scenario mismatch** — the scenario wasn't actually in scope (revise
     either scenario or skill scope)
5. Watch for **emergent misuse cases** during this perspective —
   real-state testing often reveals failure modes the author didn't
   anticipate. Add them to a running misuse-case candidate list to be
   finalised at Gate 5.

### Fixtures pattern

Two complementary fixture types — use both when possible:

**Real-state fixture (preferred):** point the skill at a real, in-use
project directory. Tests against actual data; exposes failure modes that
synthetic fixtures miss (HD-013 was discovered this way). Limitation: you
can only exercise the categories that happen to be populated.

```bash
# Example: aggregator-pattern skill tested against real platform repo
python3 my-skill/scripts/aggregator.py \
  --project some-real-project \
  --repo-root /path/to/real/repo \
  --format markdown
```

**Synthetic populated fixture:** tempdir with hand-crafted state files
that exercise every category — including the ones the real-state fixture
left empty. Verifies filter discipline (do excluded items stay excluded?
do edge cases like malformed YAML get handled?).

```bash
# Example: synthetic fixture pattern
tmpdir=$(mktemp -d)
mkdir -p "$tmpdir/.architecture/test-proj/{train-runs,work-packages}"

# Synthetic positive case
cat > "$tmpdir/.architecture/test-proj/train-runs/abc.state.json" <<'EOF'
{"phase": "paused", "pause_reason": "..."}
EOF

# Synthetic negative case (verify filter excludes this)
cat > "$tmpdir/.architecture/test-proj/train-runs/xyz.state.json" <<'EOF'
{"phase": "success"}
EOF

python3 my-skill/scripts/script.py --project test-proj --repo-root "$tmpdir"
rm -rf "$tmpdir"
```

The synthetic fixture should include at least one positive and one
negative case per category, so the test verifies both the inclusion path
and the filter discipline.

**Document fixture inventories.** When a skill ships, record in its
COMPLETENESS_REPORT.md which scenarios were tested + which fixture type
was used. Future maintainers can re-run them.

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

## Perspective 4 (optional but encouraged) — Self-test via sibling skills

For batches where multiple skills are authored in sequence, run each
newly-authored skill against ITS OWN code via the relevant sibling skill.

### How to evaluate

For each new skill's source files:
1. Run `sulis:check-readability` against the new code (if Python/JS/TS).
2. Run `sulis:check-build` (manifest hygiene on any new plugin.json).
3. Run `sulis:check-security` (credential leaks in test fixtures often
   slip through).
4. Tier-3 (`sulis:check-tests`) doesn't apply if the new skill doesn't
   ship tests (most don't in v1).

### Pass criteria

- **PASS:** 0 findings from each sibling skill against the new code.
- **FAIL:** ≥1 finding from any sibling skill. Either fix the new code
  OR refine the sibling skill's heuristic if the finding is a false
  positive caused by the new code's legitimate pattern. Both are
  legitimate resolutions — document which you chose and why.

### Track record

The cross-skill self-test pattern has 5 data points (check-readability,
check-tests, code-health, check-build, check-security). All 5 self-tests
returned 0 findings. Evidence that the methodology produces
consistent-quality code, not just consistent-quality skill metadata.

### When NOT to run this perspective

- Single-skill authoring with no sibling skills available
- Skill is operator-facing and the only available sibling skills are
  founder-facing (the audience-conditional gotchas don't apply)
- Skill ships before any sibling skill exists (early bootstrapping)

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
