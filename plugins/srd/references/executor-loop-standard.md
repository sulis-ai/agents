# Executor Loop Standard

<!-- summary -->
A marketplace-wide encoding of the control loop autonomous-execution
agents run when a step fails. Every fallible step gets a local **OODA
loop** — Observe the failure output **verbatim**, Orient by running
**Five Whys** to a single root cause, Decide the **minimum change**
that addresses it, Act by re-running the failed step. A bounded
**self-heal budget** per failure type prevents infinite retry
pathologies. A **scope guard** halts when the root cause is outside the
agent's scope — agents fix what's inside their contract, escalate
everything else via a structured `BLOCKER-NNN.md` record. The spiral
metaphor is load-bearing: each iteration narrows in (Five Whys
converges; retry budget approaches exhaustion); the agent does not
loop indefinitely.
<!-- /summary -->

> **Version:** 0.1.0
> **Status:** Active — Calibration Period (90 days from 2026-05-17)
> **Applies to:** All autonomous-execution agents in the Sulis AI
> marketplace — including the WP executor, the orchestrator, and any
> future agent that takes actions whose outcomes it observes and
> reacts to. Does NOT apply to facilitation agents (SRD, IDC,
> concierge) — their OODA flavours (Two-Model Reconciliation for SRD;
> drill-in policy for concierge) operate on different inputs.

---

## Provenance

This standard codifies a discipline observed across the marketplace
but never formally encoded. SRD's Two-Model OODA Reconciliation
handles requirements analysis; sulis-security's OODA spiral handles
security assessment; SEA's verify is a one-shot check. None of them
covered the case of an **execution** agent taking an action, observing
a failure, and deciding what to do next without halting or asking for
help on every failure.

The failure mode this standard exists to prevent is **naive retry** —
the agent observes a failure (test fails, CI fails, deploy fails),
retries the same action with no diagnosis, and either succeeds by
luck or fails the same way. Naive retry burns iterations, masks root
causes, and produces no audit trail. The alternative naive failure
mode is **immediate escalation** — the agent halts on first failure
and waits for human help, defeating the autonomy the marketplace is
designed to enable.

The middle path is **bounded self-healing**: diagnose the root cause,
attempt a minimum fix inside the agent's scope, re-run, spiral until
success or exhaustion, escalate cleanly when the agent cannot
proceed. OODA + Five Whys + scope guard + budget = the operational
shape of bounded self-healing.

Provenance: the founder, designing the WP executor, articulated the
shape as *"OODA spiral with Five Whys for self-healing and
propelling."* This standard names the discipline and the bounded
mechanism.

---

## Boundary Definition

This standard governs **the control loop an autonomous execution
agent runs when a step fails**. It does NOT govern:

- **Which steps an agent runs** — that is the agent's lifecycle, defined
  by its own contract (e.g. the WP executor's 10-step lifecycle from
  `git-workflow-standard.md` and `sulis-execution/references/lifecycle.md`).
- **The success path** — when steps succeed, the agent simply advances
  to the next step. The loop fires only on failure.
- **Diagnosis of root causes outside the agent's contract** — those
  surface via the escalation contract; resolving them is human work.
- **Long-running optimisation** — the loop is bounded; it is not a
  search algorithm.
- **OODA in facilitation agents** — SRD's Two-Model Reconciliation is a
  different shape (continuous decomposition during requirements
  analysis); the concierge's drill-in policy is a third (inspection
  vs decision routing). Each has its own standard or section.

The intersection with other standards is named explicitly in the
Composition section.

---

## Severity Convention

| Severity | Meaning |
|----------|---------|
| **MUST** | Non-negotiable. Violations block delivery. |
| **SHOULD** | Default. Deviation requires explicit justification (an ADR or equivalent decision record). |

---

## EL-01: OODA loop on every fallible step (MUST)

Every step in an autonomous-execution agent's lifecycle that can fail
runs a local **OODA loop** on failure:

- **Observe** the failure output.
- **Orient** by diagnosing the root cause (see EL-03).
- **Decide** the minimum change that addresses the root cause.
- **Act** by applying the change and re-running the failed step.

**Naive retry is forbidden.** An agent that retries a failed step
*without* running Observe and Orient first is in violation. The retry
is the Act step of OODA; running it without the preceding three steps
strips the loop of its diagnostic value and leads to the failure mode
this standard is written to prevent.

If a step succeeds on the first attempt, no OODA loop fires. If it
fails, OODA fires per below.

### Scope of "fallible step"

A step is fallible if any of these could produce a failure outcome:

- It runs external code (tests, lint, build, CI).
- It hits an external system (push, deploy, health-check, smoke-test).
- It modifies shared state (merge, deploy, INDEX update).
- It depends on the output of another step (refactor depends on
  green tests; smoke-test depends on healthy deploy).

A step is **not fallible** if it is purely deterministic and
side-effect-free (reading a file the agent just wrote, computing a
hash, formatting a string). Those steps do not require OODA loops on
failure — failure means a bug in the agent and should be a hard halt.

---

## EL-02: Observe captures the failure output verbatim (MUST)

The Observe step captures the failure output **verbatim** — the
original error message, log, stack trace, exit code, HTTP response
body, deploy log, health-check JSON, smoke-test stderr. Do not
summarise. Do not paraphrase. Do not pre-classify ("looks like a
timeout") at this step.

The original output is the **evidence**. Summary belongs in the
Orient step's output (the Five Whys trace and root cause statement),
where it is correctly identified as an interpretation, not a fact.

### Why verbatim matters

Agents that summarise too early lose the signal in the noise. A
*"tests failed"* summary discards the specific test name, the
assertion that broke, the stack trace pointing at the line in the
code, the line of input that triggered the bug. The Orient step needs
all of that to diagnose; if Observe threw it away, Orient is
guessing.

The verbatim output also forms the first section of the BLOCKER
record (EL-07) if escalation fires — a human investigator needs the
original output, not the agent's interpretation of it.

### Volume

If the output is genuinely massive (a 50 MB log file), the agent may
extract the relevant slice — but the extraction must be conservative
(retain context lines before/after the failure marker) and journal
the original output's location for retrieval.

---

## EL-03: Orient runs Five Whys, bounded at 5 (MUST)

The Orient step diagnoses the root cause by running **Five Whys**
(https://en.wikipedia.org/wiki/Five_whys — the Toyota Production
System discipline). The agent asks "why" at each level, drilling from
the symptom toward the underlying cause:

```
Symptom: Test test_cancel_subscription failed with TimeoutError.
1. Why? → The HTTP call to /v1/subscriptions/cancel timed out.
2. Why? → The endpoint returned a 503 after 30 seconds.
3. Why? → The downstream billing service is slow.
4. Why? → The test was hitting a real billing service, not a mock.
5. Why? → The test fixture didn't apply the mock for this endpoint.

Root cause: Missing mock for /v1/subscriptions/cancel in the test fixture.
```

### Bounded at 5

The drill is **bounded at 5 iterations**. If no root cause emerges at
depth 5, the agent escalates (per EL-06) with the partial Five Whys
trace recorded. The bound is the discipline: agents are not allowed
to drill indefinitely, and they are not allowed to stop at the first
plausible-looking cause.

### One-cause discipline

Each Why drills toward **one** more specific cause. Agents do not
fork the drill ("there are three possible causes"). If the cause is
genuinely ambiguous at some level, the agent picks the most likely
branch, drills it, and records the alternative branches in the
escalation record if the chosen branch dead-ends.

This is the convergence property of the spiral: each Why narrows
the cause; branching defeats convergence.

### Output: one root-cause statement

Orient's output is **one** single root-cause statement, typically one
sentence, sometimes two. It is the **hypothesis** the Decide step
acts on. If Orient produces a list of possible causes, the agent has
not finished the work — pick one (the most likely) and drill further.

---

## EL-04: Decide names the minimum change inside the agent's scope (MUST)

The Decide step produces **the smallest change that, if applied,
would address the root cause hypothesis**.

- Smallest in **footprint** — fewest files, fewest lines, fewest
  primitives touched.
- Smallest in **risk** — least likely to introduce unrelated
  regressions.
- Inside the **agent's scope** — within the contract the agent is
  executing (e.g. for the WP executor, inside the WP's Contract
  section).

If the minimum change is outside the agent's scope, EL-05 (scope
guard) fires.

### Composes with EP-07 Boy-Scout Scoping

Decide step output is exactly one fix for one root cause. The agent
does not pile on unrelated cleanups or "while we're here"
improvements during a diagnosis cycle. The Boy Scout rule applies to
the agent's *normal* work (in the Act step of EL-05 Acting on a
green path), not to a diagnosis cycle. Diagnosis cycles are tight
and targeted; cleanup belongs to the next normal cycle.

### Composes with CP-01..CP-05 (Convention Preference)

When the minimum change involves a technical choice (which library,
which retry pattern, which timeout value), Decide defaults to the
established convention per CP-01..CP-05. Bespoke choices during
diagnosis are doubly suspect — both the original failure AND the
diagnosis introduce novelty.

---

## EL-05: Act re-runs the failed step (MUST)

The Act step applies the Decide step's change and **re-runs the
specific step that failed**, not the whole lifecycle.

- If the step now succeeds → exit the OODA loop; the agent advances
  to the next step in its lifecycle.
- If the step still fails → log the attempt under
  `## Self-heal attempts` in the agent's working journal, increment
  the budget counter, spiral back to Observe with the new failure
  output.

### Why re-run the same step

Re-running the whole lifecycle from the start would be wasteful
(redundant work on the already-green steps) and risky (the
already-green steps could now fail because of the change, masking
the diagnostic signal). The discipline is: fix what broke, re-test
what broke, advance.

### Idempotency of the failed step

The standard assumes each fallible step is **idempotent on re-run**
or has a well-defined re-run procedure. If a step is not idempotent
(e.g. a deploy that creates a non-rollback-safe resource), the
agent's lifecycle is wrong — that step should be split into a
preparation phase (idempotent) and a commit phase (single-shot, with
explicit rollback).

For the WP executor: tests are idempotent; lint is idempotent;
commit is idempotent (re-creates an equivalent commit); push is
idempotent; merge is single-shot but rollback-safe via revert
(GIT-10); deploy is idempotent in the Sulis SDK contract; health-
check is idempotent; smoke-test is idempotent.

---

## EL-06: Scope guard halts and escalates out-of-scope failures (MUST)

If Orient's Five Whys identifies a root cause that is **outside the
agent's scope**, the agent **halts immediately** and escalates per
EL-07. It does not attempt a fix.

### What "outside scope" means

A root cause is out of scope when fixing it would require the agent
to:

- Modify code, configuration, or infrastructure outside the
  contract it is executing (e.g. the WP executor cannot modify CI
  configuration; that is its operating environment, not its work).
- Fix a bug in another agent's output (e.g. a TDD section the
  executor depends on is internally contradictory; the executor's
  fix is to escalate, not to rewrite the TDD).
- Resolve a platform issue (e.g. staging cluster down, dependency
  registry unreachable, secrets backend timing out).
- Acquire authorisation it does not have (e.g. for the WP executor:
  modifying `main` requires founder authorisation per GIT-06; the
  executor cannot self-authorise).

### What "in scope" means

A root cause is in scope when fixing it requires changes only inside
the contract the agent is executing — for the WP executor, that is
the files and configs the WP names in its Contract section, plus
any test/lint/format/type-check rules that apply to those files.

### The check happens at Orient, not at Act

The scope check fires at the end of Orient — when the root cause is
known but before any fix is attempted. This prevents the agent from
acting on out-of-scope diagnoses and discovering the scope problem
mid-fix (which leaves partial state).

---

## EL-07: Self-heal budget per failure type (MUST)

Every failure type has a **bounded self-heal budget** — a maximum
number of OODA cycles the agent runs before halting and escalating.
The budget exists to prevent infinite-loop pathologies (an agent
that converges asymptotically on a fix but never quite gets there).

### Default budgets

The marketplace defines default budgets per common failure type. The
WP executor's budgets are in `sulis-execution/references/self-heal-
budget.md`. The pattern is:

| Failure type | Default budget |
|---|---|
| Test failure during GREEN | 3 attempts |
| Refactor regression during BLUE | 2 attempts (then revert + narrower scope) |
| Lint / type / format | 5 attempts (most are auto-fixable) |
| Push rejection | 2 attempts |
| CI failure on branch | 3 attempts |
| Merge-to-target conflict | 2 attempts (rebase only) |
| Deploy failure | 3 attempts |
| Health-check timeout | 5 attempts (with exponential backoff) |
| Smoke-test failure | 2 attempts |
| Five Whys non-convergence | 1 attempt to find root cause; if not found, escalate |

### Budget exhaustion → escalate

When a failure type's budget is exhausted, the agent halts and
escalates per EL-08. It does not silently give up; it does not retry
beyond budget; it does not increase the budget mid-flight.

### Per-WP scope

The budget is **per-scope** (per-WP for the executor). Each new WP
gets fresh budgets. Within a WP, attempts accumulate across the
lifecycle — three CI-failure attempts at step 7 exhausts the CI
budget for that WP regardless of which step a future CI failure
might occur in.

### Why bounded

Unbounded retry is the classic distributed-systems failure mode.
Three attempts is the convention from the SRE book and the dominant
retry-budget pattern (Google SRE, AWS SDK defaults, gRPC retry
policy). The specific numbers are calibrated per failure type — lint
failures auto-fix and warrant more attempts; merge conflicts are
likely structural and warrant fewer.

---

## EL-08: Escalation contract — the BLOCKER record (MUST)

When the agent halts and escalates (scope guard fires per EL-06, or
budget exhausts per EL-07), it writes a structured escalation
record. The format is fixed so that downstream agents (the
orchestrator, the concierge, a human investigator) can read it
consistently.

### File location

`<scope>/BLOCKER-<scope-id>.md` — for the WP executor:
`<repo>/BLOCKER-WP-NNN.md` co-located with the WP file at
`.architecture/{project}/work-packages/BLOCKER-WP-NNN.md`.

### Required sections

```markdown
# BLOCKER-WP-NNN: <one-line plain-English summary>

> Created: <ISO-8601> by <agent name>
> Scope: <WP ID or equivalent>
> Step: <lifecycle step number + name>
> Trigger: scope-guard | budget-exhausted | five-whys-non-convergence

## Failure observation (verbatim)

<verbatim output from the failed step — error message, log, stack
trace, response body, etc. NOT summarised.>

## Five Whys trace

1. **Why did <symptom>?** → <answer>
2. **Why did <that>?** → <answer>
3. **Why did <that>?** → <answer>
4. **Why did <that>?** → <answer>
5. **Why did <that>?** → <answer or "non-convergence">

## Root cause

<one-line root cause statement>

## Scope verdict

- [ ] in-scope (executor could fix; budget exhausted)
- [ ] out-of-scope (scope guard fired)
- [ ] indeterminate (Five Whys non-convergence)

Reason: <why this verdict>

## Attempted fixes (if any)

| Attempt | Change applied | Outcome |
|---:|---|---|
| 1 | <one-line change> | <one-line outcome> |
| 2 | <one-line change> | <one-line outcome> |

## Plain-English summary (for the concierge / founder)

<one or two sentences, AAF-compliant — no internal IDs, no
methodology jargon. This is what the concierge translates into the
founder-facing status update.>

## Suggested next step

<concrete next action — human investigation? infra fix? retry after
external blocker resolved? abandon and re-decompose?>
```

### Why structured

The orchestrator reads BLOCKER files to know which WPs are blocked
and why; it can attempt to dispatch other ready WPs in parallel if
the blocked WP doesn't block them transitively. The concierge reads
the **Plain-English summary** section to surface the blocker to the
founder. A human investigator reads the **Failure observation** and
**Five Whys trace** to root-cause. Each consumer needs a different
slice; the structure makes the slices discoverable.

---

## Worked Examples

### Example 1 — in-scope, fixed within budget

WP-007 (cancel-subscription flow). Step 3 (GREEN): tests fail.

**OODA cycle 1:**

- **Observe.** Verbatim output: `FAILED test_cancel_returns_204
  - assert response.status_code == 204 - assert 500 == 204`.
- **Orient (Five Whys):**
  1. Why did the test fail? → Endpoint returned 500.
  2. Why 500? → The cancel handler raised `KeyError: 'subscription_id'`.
  3. Why? → The handler reads `request.body['subscription_id']`
     but the test sends `subscriptionId` (camelCase).
  4. Why does the test send camelCase? → The TDD spec says the API
     uses camelCase per the existing API convention.
  5. Why does the handler expect snake_case? → The handler was
     hand-coded without referencing the API conventions config.

  **Root cause:** Handler reads the wrong field name. Fix: change
  handler to read `request.body['subscriptionId']` per the API
  convention.

- **Scope check:** In scope (handler is inside WP-007's Contract).
- **Decide.** Minimum change: rename the field access in the
  handler from `subscription_id` to `subscriptionId`.
- **Act.** Apply the change. Re-run test. Test passes.

Outcome: WP advances. Budget consumed: 1 of 3 GREEN attempts.

### Example 2 — out-of-scope, scope guard fires

WP-009 (rate-limit billing webhook). Step 9 (health-check): fails
with 503.

**OODA cycle 1:**

- **Observe.** Verbatim: `Health check returned 503 — service
  unavailable. Sulis SDK error: staging cluster reports 'no healthy
  upstream'.`
- **Orient (Five Whys):**
  1. Why 503? → No healthy upstream pods.
  2. Why? → Deployment didn't roll out to staging.
  3. Why? → Staging cluster's autoscaler reports
     `InsufficientCapacity`.
  4. Why? → Staging cluster is at quota.
  5. Why? → Platform team hasn't increased the quota since the
     billing-service rollout.

  **Root cause:** Staging cluster quota exhaustion.

- **Scope check:** **Out of scope.** The WP executor cannot
  increase staging quota — that requires platform-team access
  the executor does not have, and is an infrastructure concern
  outside the WP's Contract.
- **Action:** Halt. Write `BLOCKER-WP-009.md`. Plain-English
  summary: *"WP-9 is blocked — staging cluster is at its capacity
  limit and a new deployment can't fit. This isn't a code issue.
  The platform team needs to increase the staging quota. Once
  done, I can retry the deploy."*
- **Concierge** surfaces this to the founder: *"WP-9 is blocked
  on staging infrastructure — the cluster is full and the new
  deploy can't fit. The platform team needs to free up capacity;
  not something the code can fix. When they're done, I'll retry."*

Outcome: BLOCKER-WP-009.md created; orchestrator dispatches another
ready WP (if any); founder informed.

### Example 3 — budget exhausted, escalation

WP-014 (new password-reset email). Step 5 (lint): fails repeatedly.

**OODA cycles 1-5:**

- Cycle 1: Lint reports `import order` violation. Fix: run
  formatter. Re-lint: still fails (different file).
- Cycle 2: Lint reports same `import order` on a different file.
  Fix: run formatter. Re-lint: still fails.
- ... (continues through cycle 5) ...
- Cycle 5: Same pattern. Budget for `Lint / type / format` is 5.
  Exhausted.

**Halt.** BLOCKER-WP-014.md:
- **Root cause:** Formatter is re-introducing the same import-order
  violation it claims to fix (formatter / linter rule conflict).
- **Scope verdict:** In-scope but budget-exhausted. Likely indicates
  a config-level conflict between the project's formatter and
  linter that the WP executor can't resolve in isolation.
- **Suggested next step:** Manual investigation of the formatter ↔
  linter rule conflict. The fix likely lives in
  `pyproject.toml` / `eslint.config.js` — outside this WP's
  Contract — and should land as its own small WP first.

Outcome: WP-014 blocked; founder informed in plain English. The
underlying config conflict gets its own ticket.

---

## Anti-Patterns

### "Just retry, it might work this time"

Naive retry without OODA is forbidden (EL-01). Retrying a failed
step without diagnosis is exactly the failure mode this standard
prevents. If the agent finds itself wanting to retry without
observing and orienting first, the right move is: stop, observe the
failure verbatim, run Five Whys, decide a minimum change, *then*
retry.

### "I'll stop at the first plausible cause"

Five Whys is a discipline. Stopping at the first plausible cause
(usually a level-1 or level-2 symptom dressed up as a cause) is the
discipline's classic failure mode. Drill all five levels. If the
true cause emerges at level 3, the remaining whys can be brief —
but the agent at least confirms there is no deeper cause.

### "Three causes are all worth fixing"

Five Whys produces **one** root cause. Three causes is a branching
drill, which defeats convergence (EL-03). If the cause is genuinely
multi-factorial, pick the most likely branch and drill it; record
the alternatives in the BLOCKER record for the dead-end case.

### "While we're here, let me also clean up..."

Decide produces the **minimum change** (EL-04). Diagnosis cycles are
tight and targeted. Boy Scout improvements belong to normal cycles,
not diagnosis cycles. If the agent finds itself bundling unrelated
fixes during a self-heal, the diagnosis loses signal and the change
loses targeting.

### "Out-of-scope but I can fix it anyway"

Scope guard (EL-06) is non-negotiable. An agent that "helpfully"
fixes things outside its contract is exceeding its authority and
introducing changes the contract didn't sanction. The right move is
to halt and escalate; the human (or another agent) decides whether
the out-of-scope fix is wanted.

### "Increase the budget — it's *almost* working"

Budget exhaustion (EL-07) is a signal that the agent isn't
converging. Increasing the budget mid-flight masks the signal and
allows pathological loops to persist. If the budget is
systematically wrong (a failure type warrants more attempts than
the default), update the budget standard between sessions — not
mid-WP.

### "The error message is too long; I'll summarise it"

Observe captures verbatim (EL-02). Summarising too early loses the
signal in the noise — the specific test name, the line, the input
value, the stack trace — all of which Orient needs. If the output
is genuinely massive (50 MB), the agent extracts the slice around
the failure marker but journals the original output's location for
retrieval.

### "Escalate without the trace"

The BLOCKER record format (EL-08) is fixed. Skipping the Five Whys
trace or the verbatim observation leaves downstream consumers
(orchestrator, concierge, human investigator) without the evidence
they need. The discipline is to escalate **with** the work product
of the loop, not in spite of it.

---

## Composition with Other Standards

- **Convention Preference (CP-01..CP-05)** — Decide step defaults to
  the established convention when the minimum change involves a
  technical choice. Bespoke choices during diagnosis are doubly
  suspect.
- **Audience-Adapted Framing (AAF-01..AAF-09)** — the BLOCKER
  record's **Plain-English summary** section is AAF-compliant: no
  internal IDs, no methodology jargon, written for the concierge to
  surface to the founder directly.
- **Engineering Principles (EP-02 / EP-03 / EP-07)** — Quality
  Paramount (the loop refuses to silently give up); Reuse First
  (Decide checks for existing primitives before introducing new
  code in a fix); Boy-Scout-Scoped (Decide produces minimum change
  only).
- **Git Workflow Standard (GIT-01..GIT-10)** — every fix attempted
  by an autonomous executor follows the encoded workflow (commit
  messages cite the BLOCKER record when relevant; reverts use the
  GIT-10 procedure; no `--no-verify`).
- **SRD Two-Model OODA Reconciliation** — different OODA flavour,
  different scope. The SRD analyst's OODA reconciles a Domain Model
  against a Code Model during requirements analysis; recursive
  decomposition. This standard's OODA is the execution-time control
  loop on failure; flat, bounded, terminating. Both inherit from
  John Boyd's original Observe-Orient-Decide-Act shape but operate
  on different inputs and produce different outputs.
- **Decision Discipline (sulis concierge)** — the concierge owns
  the decision of *when to surface a BLOCKER to the founder* (it
  always does — blockers are founder-facing by definition) and
  *how to phrase it* (per AAF). The agent owns the decision of
  *whether to escalate* (per EL-06 / EL-07).

---

## Version History

| Version | Date | Change | Author |
|---|---|---|---|
| 0.1.0 | 2026-05-17 | Initial draft. Calibration period: 90 days. Promotion to MUST repo-wide requires evidence from three executor sessions in which the loop fired and produced (a) correct self-healing for in-scope failures, (b) correct escalation for out-of-scope failures, (c) correct BLOCKER records that downstream agents and humans could act on without re-asking the executor for context. Encodes EL-01..EL-08. Provenance: founder articulated the shape as "OODA spiral with Five Whys for self-healing and propelling"; this standard names the discipline, the bounded mechanism, and the escalation contract. | Standards team |
