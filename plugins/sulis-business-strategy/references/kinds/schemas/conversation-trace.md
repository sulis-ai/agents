# Conversation Trace Schema (v1alpha1)

> **Used by:** any Kind in this plugin whose generate stage is conversational.
> **Output target:** `find-output/CONVERSATION_TRACE.md`.
> **Purpose:** an audit artifact that records the rhythm of the generate-stage conversation — what phase, what turn, what was asked, what was captured. Read post-hoc to verify the agent followed the diverge-then-converge discipline rather than form-walking.

The trace is the agent's self-reported record of how it drove the conversation. It is **not** a substitute for the BRIEF_PACK (which records what was captured) or the Verdict (which records evaluation against the rubric) — it records how the conversation got there.

The trace also enables a **Phase B self-check**: at the Phase A → B transition, the agent reads the most recent Claude Code session log and verifies its trace claims against actual conversational turns. Mismatch routes to flagged-and-retry rather than silent acceptance.

---

## Frontmatter (REQUIRED)

```yaml
---
trace_schema_version: v1alpha1
kind: <apiVersion>/<kind>        # e.g. business-strategy/v1alpha1/BusinessContext
kind_invocation_started: <ISO-8601 datetime>
session_log_path: <best-effort discovered path, or "not-found">
self_check_at_phase_b: passed | failed | skipped
---
```

---

## Section order (REQUIRED)

1. **Phase A — Divergent**
2. **Phase B — Saturation / Convergence Pivot**
3. **Phase C — Convergent**
4. **Phase D — Consolidation**
5. **Self-check log** (the Phase B session-log verification result)

Phases the agent never reached are written as `## Phase X — Not Reached` with a one-line reason ("stopped at Phase A: blocking criterion fired").

---

## Phase A — Divergent

The agent writes this section incrementally as Phase A unfolds, NOT at the end:

```markdown
## Phase A — Divergent

**Started:** turn 1 (relative to Kind invocation)
**Opening question:** "{the actual question asked verbatim}"
**Opening style:** hypothesis-first | open-broad

### Turn log

- **Turn 1:** {one-line summary of agent's question}. Founder response touched: [Q1, Q2, Q5]. Multi-domain capture: yes.
- **Turn 2:** Followed thread on {topic}. Founder response touched: [Q2, Q6]. Multi-domain capture: yes.
- **Turn 3:** Followed thread on {topic}. Founder response touched: [Q3]. Multi-domain capture: no.
- **Turn 4:** **Reflection checkpoint #1.** Coverage map: 8/34 questions touched. Mirrored back: "{summary}". Founder: confirmed / extended / corrected.
- **Turn 5:** {next question}...
- **Turn 8:** **Reality probe fired:** competitor invisibility. Founder named 2 competitors.
- **Turn 12:** **Reflection checkpoint #2.** Coverage map: 18/34.
- **Turn 14:** Saturation signal — last 3 turns introduced no new concepts.

### Phase A stats

- **Duration:** 14 turns
- **Multi-domain captures:** 6 / 14 turns (43%)
- **Reflections:** 2
- **Reality probes fired:** 1 (competitor invisibility)
- **Hypothesis-first questions:** 9 / 14 (64%)
- **Exit reason:** saturation_signal
```

**Recording rules:**

- **Turn = a single agent-question + founder-response pair.** Count from the start of the Kind invocation (turn 1 = first question the agent asks in this Kind run, not the start of the Claude Code session).
- **Multi-domain capture:** the founder's single response touched ≥ 2 of the 9 / 34 coverage targets. This is the divergent signal.
- **Hypothesis-first:** the question was framed as "I'm hearing X — is that right?" or similar, not as an open prompt. This is the inference-over-interrogation signal.
- **Reflection checkpoint:** every 3-4 turns, the agent mirrors back and waits for confirmation.
- **Reality probe:** one of the named patterns (scope creep, assumption stacking, competitor invisibility, NFR neglect, anti-goal contradiction, generic-language drift). Max one per reflection.

---

## Phase B — Saturation / Convergence Pivot

```markdown
## Phase B — Saturation / Convergence Pivot

**Entered:** turn 15 (after Phase A exit at turn 14)
**Coverage map surfaced to founder:** yes
**Founder choice:** pin-gaps | keep-wide | stop

### Self-check (against session log)
- Trace claims: Phase A ran 14 turns.
- Session log evidence: {actual count of agent-question events since Kind invocation, OR "session log not discovered"}.
- Mismatch: yes / no
- Action: none | flagged in trace | retried Phase A

### Decision
- Routing: enter Phase C (pin gaps) | re-enter Phase A (founder wants more exploration) | stop (founder done)
```

The Phase B self-check is the load-bearing enforcement: the agent must verify its own narrative against an external source (the session log). If the agent claimed "14 turns of divergent exploration" but only 3 conversational turns have happened since the Kind started, that's a mismatch — Phase A was skipped, not completed.

---

## Phase C — Convergent

```markdown
## Phase C — Convergent

**Entered:** turn 16
**Approach:** targeted gap questions, hypothesis-first

### Gap log

- **Turn 16:** Q19 (tier structure). Skipped — explicit rationale: "pre-commercial, no pricing yet".
- **Turn 17:** Q22 (defensible advantage). Captured as Assumed; validation path noted.
- **Turn 18:** Q33 (pivot triggers). Captured as Assumed; validation path noted.
- **Turn 20:** Q28 (technology stack). Captured as Validated; cited architecture/ARCHITECTURE.md.

### Phase C stats
- **Duration:** 5 turns
- **Gaps addressed:** 4
- **Skipped with rationale:** 1
- **Validated:** 1, **Assumed:** 2, **Unknown:** 0
```

---

## Phase D — Consolidation

```markdown
## Phase D — Consolidation

**Entered:** turn 21
**V/A/U scoring applied:** yes
**Provenance frontmatter generated:** yes (5 input artifacts hashed)
**Draft surfaced to founder:** yes — completeness dashboard shown
**Founder confirmation:** at iteration 1
**Final artifact written:** product/context/BUSINESS_CONTEXT.md
**Total iterations through find→generate→evaluate→decide loop:** 1
```

---

## Self-check log (Phase B verification detail)

```markdown
## Self-check log

**Discovery attempt:** `ls -t .sulis/threads/sessions/*.jsonl 2>/dev/null | head -1`
**Resolved path:** `.sulis/threads/sessions/{session-id}.jsonl` (or "not-found")

**Method (when log is discoverable):**
1. Count user-message events in the log since the Kind invocation timestamp.
2. Compare to trace's Phase A turn count.
3. Verify reflections actually happened (look for agent messages containing "let me mirror back" or equivalent reflection-phrase signals).
4. Verify multi-domain captures (founder messages of substantive length — > 50 words — are stronger candidates for multi-domain content; one-liners are weaker).

**Result format:**
- `passed` — trace claims align with session log evidence within ±20% tolerance.
- `failed` — mismatch ≥ 20%. Agent should flag in trace and re-enter Phase A (one re-entry max per Kind run).
- `skipped` — session log not discoverable. Trace claims accepted on self-report; flag in frontmatter so reviewers know.

**Failure action:**
On `failed`, the agent appends a `### Self-check failure` block under Phase B and re-enters Phase A with the rhythm constraints surfaced more strongly to itself. One re-entry max per Kind run — second failure routes to the decide stage with `reason_class: content_deficient` and the rubric's R-T criteria firing.
```

---

## Rules and constraints

### Recording discipline (MANDATORY)

- **Write incrementally, not at the end.** The trace exists at all times during the conversation. Each turn appends a new line. Each phase transition writes the stats block. Do NOT batch-write the whole trace at the end — that's reconstruction, not observation.
- **Be honest.** A trace that claims 14 turns of divergent exploration when only 3 happened is worse than no trace at all. Honest "Phase A — 2 turns, founder went straight to convergence with terse answers" is more useful than fabricated rhythm theatre.
- **Reflect the founder's actual answers, not their idealised counterparts.** If the founder gave one-liners, record one-liners. The trace's job is observation, not aspiration.

### Cross-Kind reuse

Any Kind whose generate stage is conversational uses this same schema. As of v0.1.0 that's BusinessContext and Identity. Future conversational Kinds (Brand, ToneOfVoice, Principles, Vision) inherit the same trace structure.

Non-conversational Kinds (purely deterministic transformations) do not produce a trace.

### What this schema does NOT cover

- **Full session transcripts.** Those are Claude Code's responsibility (`.sulis/threads/sessions/*.jsonl`).
- **Rubric verdicts on the trace itself.** A future v2 rubric extension may add R-T criteria (Phase A ≥ 5 turns, multi-domain ratio ≥ 30%, etc.). For v0.1 the trace is review-only — read it post-hoc to verify rhythm.
- **Cross-run comparisons.** Comparing trace from run N against run N+1 to detect drift is a post-run tool, not embedded here.

### Promotion path

Once 3-5 real conversation traces exist:

1. Review them. Identify what form-walking actually looks like in trace data.
2. Pick threshold values for the rubric criteria (R-T1 turn count, R-T2 multi-domain ratio, etc.) informed by what real traces show.
3. Promote the trace from review-only to rubric-checked: extend `business-context-rubric.md` and `identity-rubric.md` with R-T criteria, and extend Verdict structure with `phase_log`.
4. The agent's manual self-discipline can then be supplemented by rubric-enforced phase requirements.

Until then, the trace is the audit trail. The rubric trusts the trace's existence but does not check its contents.
