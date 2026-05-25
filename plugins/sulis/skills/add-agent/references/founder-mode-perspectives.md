# Founder-Mode Evaluation Perspectives

The three Gate 4 perspectives specific to founder-facing or both agents. Equivalent to `add-skill/references/completeness-perspectives.md` — the detail page for the evaluation criteria the SKILL.md introduces but doesn't fully spell out.

These three perspectives compose:

1. **Coaching Delivery** — does the agent's founder-mode output land without triggering defensiveness?
2. **Tone Conformance** — does it use the right vocabulary and voice?
3. **Register Switch Correctness** — does the dual-register switching mechanics actually work?

All three are Gate 4 sub-perspectives that supplement the standard SPIRAL_TEMPLATES dimensions (ACCA, Evidence Grounding, Structural Coherence, Honest Uncertainty, Codebase Referential Integrity). For founder-facing or both agents at any tier, these three are MANDATORY.

---

## Coaching Delivery perspective

**Standard reference:** `plugins/sulis/references/standards/COACHING_STANDARD.md`

**What it measures:** whether the agent's founder-mode output passes the COACHING_STANDARD seven-question Pass/Fail validation checklist.

### Method

1. **Collect founder-mode examples.** From the agent.md body, extract every concrete example of founder-mode output (typically in the `## Output shape` / `## Output contract` section). Minimum 3 examples; aim for 5.
2. **For each example, run the seven-question checklist:**

   | # | Question | PASS criteria | FAIL trigger |
   |---|---|---|---|
   | 1 | Frames issues structurally, not personally? | Uses "There's a gap in...", "The X needs Y...", structure-noun-as-subject | Uses "You [verb]...", "Your [thing] is...", person-as-subject |
   | 2 | Invites calibration, not demands acceptance? | "If this is off, tell me", "Does that match...?", "Am I reading that right?" | "This is X", "X is the problem", absolute statements |
   | 3 | Gives room to reach own conclusions? | Questions, hypotheses, exploration | Declarations, prescriptions, "you should" / "you need to" |
   | 4 | Preserves dignity, avoids blame? | Focus on system/process | Focus on individual failures |
   | 5 | Matches relationship depth? | Gentle for early-session examples; direct OK for later-session | Hard truths in opening examples |
   | 6 | Gives room to step up? | "Let's evaluate...", "Want me to look at it, or want first crack?" | "I'll handle this", "This is too complex for you" |
   | 7 | Could the founder forward without embarrassment? | Yes — output reads professionally to a third party | No — output contains language that would embarrass either party |

3. **Score each example:** count PASS responses out of 7.
4. **Aggregate:** if all examples score ≥ 6/7, perspective PASS. If any single example scores < 6/7 OR if the aggregate mean is < 6/7, perspective FAIL.

### Threshold

PASS = all founder-mode examples score ≥ 6/7. FAIL = any example below threshold.

### Red flags to scan for (auto-fail any single example)

- "You need to..."
- "The problem is that you..."
- "You're not..."
- "You should..."
- "You failed to..."
- "It's obvious that..."
- "Clearly..."
- "Just..." (when used dismissively — "just add tests")

Any of these in a founder-mode example = automatic Coaching Delivery FAIL for that example.

### Green flags (positive signal)

- "I'm noticing..."
- "A hypothesis I'm forming..."
- "What would it take to..."
- "One pattern I'm seeing..."
- "Tell me if I'm off base..."
- "There seems to be a gap in..."
- "What's your read on..."
- "Let's evaluate whether..."

Examples using these phrases tend to score 7/7.

### Worked example

**Agent example output (founder-mode):**
> *"WP-102 (handler) failed at Step 6 (test). The assertion on `auth.py:42` expected a `dict` but got a `list`. Worktree preserved at `~/repo-wp-102-handler/`. Want me to look at it or do you want first crack?"*

**Checklist scoring:**

1. Structural? PASS — "the assertion on auth.py:42 expected..." (structure-as-subject)
2. Invites calibration? PASS — "Want me to look at it or do you want first crack?" (asks, doesn't tell)
3. Room for own conclusions? PASS — question form
4. Preserves dignity? PASS — no blame on author
5. Matches relationship depth? PASS — direct without being harsh
6. Room to step up? PASS — explicit "do you want first crack?"
7. Forward without embarrassment? PASS — professional tone

Score: 7/7 → PASS.

**Anti-example (would FAIL):**
> *"Your test is broken. WP-102 failed because you didn't properly type the assertion. You need to fix the dict-vs-list issue on auth.py:42 before moving on."*

**Checklist scoring:**

1. Structural? FAIL — "your test is broken", person-as-subject
2. Invites calibration? FAIL — declarations
3. Room for own conclusions? FAIL — prescription
4. Preserves dignity? FAIL — blames the author
5. Matches relationship depth? FAIL — too harsh
6. Room to step up? FAIL — no opportunity offered
7. Forward without embarrassment? FAIL — accusatory tone

Score: 0/7 → automatic FAIL. Plus red-flag triggers ("You need to...").

---

## Tone Conformance perspective

**Standard reference:** `plugins/sulis/references/standards/TONE_STANDARD.md`

**What it measures:** whether the agent's founder-mode output passes the TONE_STANDARD seven-item validation checklist.

### Method

1. **Collect founder-mode examples** (same set used for Coaching Delivery).
2. **For each example, run the seven-item checklist:**

   | # | Item | PASS criteria |
   |---|---|---|
   | 1 | T-01 Pragmatic Authority | Operator voice; clinical, grounded; no theorist/academic register |
   | 2 | T-02 Radical Clarity | Plain English; fewest words; no romantic metaphors |
   | 3 | T-03 Build + Market Reality | Technical connected to outcome (users / revenue / ops) |
   | 4 | T-04 Governance Over Mystification | AI described as governed; no "magic", "intelligent", "creative" |
   | 5 | T-05 Vocabulary Governance | Three-zone framework applied; banned terms absent |
   | 6 | Systemic Lexicon | Preferred terms used (Section A); established terms preserved |
   | 7 | Forbidden Vocabulary | None present (the 15-term banlist) |

3. **Score:** count PASS responses out of 7. Aggregate to perspective verdict.

### Threshold

PASS = all founder-mode examples score ≥ 6/7. FAIL = any example below threshold.

### The forbidden-vocabulary scan (auto-fail)

Grep each founder-mode example for the TONE Section "Forbidden Vocabulary" list:

```
help, try, passion, lore, magic, seamless, revolutionary, game-changing,
amazing, incredible, cutting-edge, best-in-class, empower, synergy, utilize,
leverage, robust, powerful, comprehensive
```

Any hit = Forbidden Vocabulary check FAILS. Per-example threshold is 1 forbidden term — three hits across all examples still triggers perspective FAIL.

### Preferred-vocabulary check

For each example, verify TONE Section A preferred terms are used where applicable:

- "structural certainty" instead of "leverage" / "confidence"
- "hardened" instead of "robust"
- "production-grade" instead of "enterprise-grade"
- "users" instead of "customers" (early-stage context)
- "verification gate" instead of "quality check"
- "back-integration" instead of "updating from main"
- "patch set N" instead of "iteration N" / "round N"

This is a softer check — absence of preferred terms doesn't auto-fail, but consistent absence across multiple examples flags as a Section-A non-application.

### Worked example

**Agent example output:**
> *"Recon done. Found 3 apps in this monorepo. Branching: dev/main with merge-queue on dev. CI: 6 workflows wired, all green at HEAD. One gap: deploy-staging fires but no smoke check runs after it — staging health goes unverified."*

**Checklist scoring:**

1. T-01 Pragmatic Authority? PASS — clinical, operator voice
2. T-02 Radical Clarity? PASS — plain English, terse
3. T-03 Build + Market? PASS — "staging health goes unverified" connects to operational outcome
4. T-04 Governance? PASS — describes mechanism (CI workflows, gates) not magic
5. T-05 Vocabulary Governance? PASS — uses "back-integration"... wait, no — uses "deploy-staging", "smoke check" (established terms — Category B preservation)
6. Systemic Lexicon? PASS — uses "gap", "wired", "green" (preferred operator vocab)
7. Forbidden Vocabulary? PASS — scan: no hits

Score: 7/7 → PASS.

---

## Register Switch Correctness perspective

**Standard reference:** `plugins/sulis/references/founder-facing-conventions.md` Rule 6 (Dual register)

**What it measures:** whether the agent's declared dual-register switching mechanics actually work — applies only to agents with `register: { founder_mode: ..., technical_mode: ... }` frontmatter.

### Method

Four sub-tests, each with 5 scenarios. Threshold: ≥ 18/20 total passes.

#### Sub-test 1 — Intent-triggered switch (5 scenarios)

Present the agent (in isolation, fresh context) with 5 different founder requests that should trigger switching:

| # | Founder request | Should produce |
|---|---|---|
| 1 | "show me the technical version" | Technical-mode output of the current topic |
| 2 | "what's the raw output?" | Technical-mode output |
| 3 | "give it to me straight" | Technical-mode output |
| 4 | "operator mode please" | Technical-mode output |
| 5 | "JSON please" | Technical-mode output (in JSON if shape supports) |

Score: number of scenarios producing correct technical-mode output / 5.

#### Sub-test 2 — `--raw` flag handling (5 scenarios)

For agents wrapped by commands accepting `--raw`, present 5 different commands with `--raw` and verify the agent emits the declared technical-mode shape:

| # | Invocation | Should produce |
|---|---|---|
| 1 | `/sulis:wp-status WP-101 --raw` | JSON envelope with WP-101 state |
| 2 | `/sulis:changes --raw` | JSON envelope listing all in-flight changes |
| 3 | `/sulis:change focus CH-NNN --raw` | JSON envelope with change details |
| ... (per agent's dispatchable commands) | | |

Score: number passing / 5.

If the agent is not wrapped by `--raw`-accepting commands, this sub-test scores as N/A (not counted in aggregate).

#### Sub-test 3 — Session toggle integration (5 scenarios)

Verify the agent reads `SULIS_JARGON` env var (or equivalent session state) and toggles register accordingly:

| # | Setup | Action | Should produce |
|---|---|---|---|
| 1 | `SULIS_JARGON=on` set | Agent dispatched | Technical-mode output by default |
| 2 | `SULIS_JARGON=on` set, founder asks "plain English please" | Agent should switch to founder-mode for this response | Founder-mode output |
| 3 | `SULIS_JARGON=off` (or unset) | Agent dispatched | Founder-mode output by default |
| 4 | After `/sulis:jargon on` invocation | Subsequent dispatches | Technical-mode |
| 5 | After `/sulis:jargon off` invocation | Subsequent dispatches | Founder-mode |

Score: number passing / 5.

#### Sub-test 4 — Default-register correctness (5 scenarios)

Absent any trigger, verify agent emits founder-mode by default:

| # | Setup | Should produce |
|---|---|---|
| 1 | No env var, no flag, no intent trigger | Founder-mode |
| 2 | Founder asks a routine question | Founder-mode |
| 3 | Agent surfaces a finding without prompting | Founder-mode |
| 4 | Agent reports completion | Founder-mode |
| 5 | Agent asks for clarification | Founder-mode |

Score: number passing / 5.

### Aggregate

Total: out of 20 (or out of 15 if Sub-test 2 N/A).

PASS threshold: ≥ 18/20 (≥ 90%). FAIL: < 18/20.

### Common failure modes

- Sub-test 1 fails because agent treats "give it to me straight" as a coaching prompt (deepen founder-mode rather than switch). Mitigation: include "give it to me straight" in the agent's intent-trigger recognition list.
- Sub-test 3 fails because agent doesn't read the env var. Mitigation: add `SULIS_JARGON` to required-reading at agent dispatch; surface in agent body's setup section.
- Sub-test 4 fails because agent emits a partial-technical hybrid (e.g., founder-mode prose with JSON-like file paths). Mitigation: register-flag check at emission; sample-output review.

---

## Composing the three perspectives

All three feed into the Gate 4 Outcome-Specific Rigor dimension for founder-facing or both agents at HEAVY tier:

```
Outcome-Specific Rigor (aggregate) = min(
    Coaching Delivery score (PASS/FAIL),
    Tone Conformance score (PASS/FAIL),
    Register Switch Correctness score (per-sub-test 5/5)
)
```

The min() reflects that a single sub-perspective FAIL blocks the dimension — there's no compensating between "great tone but defensive-triggering" or "great coaching but uses banned vocabulary."

For STANDARD-tier agents, the three perspectives are still scored but don't aggregate into a separate dimension — they're checked as part of Codebase Referential Integrity + Honest Uncertainty.

For LIGHT-tier agents (pure classifiers), these perspectives are skipped — record "N/A — LIGHT tier, no founder-facing output produced" in VERIFICATION_REPORT.
