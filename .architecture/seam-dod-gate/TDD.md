# TDD — Seam-DoD Gate: drive real-data acceptance at seam-close

> **Change:** CH-01KTP7 · `feat` · `seam-dod-gate`
> **ARCH:** [ARCH.yaml](ARCH.yaml) · **Tier S**
> **Sourced from:** `.changes/feat-seam-dod-gate.{SPEC,HANDOFF,WORKING-SET,RECON}.md`
> **Status:** designed (blueprint only — decomposition into WPs is a separate `/sulis:plan-work` pass)

---

## Sizing note

This is **tier S** focused machinery, not a subsystem. Two-axis sizing:

- **sFPC ≈ 4** — no new persistent entities (ILF 0; reads the existing brain
  store + INDEX), no new external clients (EIF 0), one new gate operation that
  derives-and-reads (EO), one CLI-shaped surface that already exists
  (`sulis-verify-acceptance`, reused). Most of the moving parts are *already
  shipped* (#259 substrate) or *already present* (`_acceptance_gate`,
  `_brain_query`, `_wpxlib` INDEX parser, `wpx-step12`).
- **ASR ≈ 4** — one cross-cutting policy (the seam-close DoD timing rule),
  the agent-step-blocked constraint, the no-scenario-blocks constraint, the
  defence-in-depth (keep-ship-gate) constraint.

The work is overwhelmingly **consume + wire**, not build. The design target
is therefore a small new pure-decision module plus a thin hook at one existing
transition, plus two standards amendments. Five ADRs because the choices are
consequential (gate unit, defence-in-depth, hook point, resolution mechanism,
no-scenario semantics) — not because the surface is large.

---

## The problem (one paragraph)

WPs are tested hermetically against builder-authored fixtures — that certifies
the **shape** of each slice, but the **real data crossing the seam between two
slices** is never driven until ship. The observed-or-blocked acceptance drive
(`sulis-verify-acceptance`) fires only at the **ship stage** (gate 4.8 in
`plugins/sulis/skills/change/SKILL.md`). By then slices are merged-adjacent, so
a blocked seam is expensive to unwind, and every ship surfaces the next
un-driven seam — a slow, serial find-one-fix-one tail ("ships green but never
works"). **Re-time the catch to seam-close.**

## The fix (one paragraph)

Add a **seam-close gate** in the build loop that fires the moment a
contract-first seam closes — when an integration / composite WP completes, or
when a contract WP and all the producer + consumer WPs that `dependsOn` it
reach `done`. At that moment the gate resolves the closing seam to the
Scenarios that verify the requirements its two sides implement, drives those
Scenarios via the **already-shipped** `sulis-verify-acceptance` runner, and
reads the equality|property verdict-invariant over the **real saved record** →
`observed` | `blocked`. `blocked` halts seam-close as "not done", surfaced in
founder English. The ship-stage gate (4.8) stays as a backstop.

---

## MECE-3 pillar coverage

### Form — Structural integrity

The codebase is already hexagonal at the relevant seams; this change adds **one
new pure-decision port** and reuses three existing ones. Nothing in the domain
imports infrastructure.

| Component | Role | New / reused |
|---|---|---|
| `_seam_close_gate.py` (NEW) | Pure decision: given a just-`done` WP + the INDEX dependency graph + the brain store, decide whether a seam closed, resolve it to Scenarios, fold the runner verdicts into `observed`/`blocked`. No I/O of its own beyond reading via the query seams. | **NEW** — the one new module |
| `_acceptance_gate.gate_decision` | Folds Scenario results → `pass`/`blocked` with `require_observed`. **Reused verbatim** — same observed-or-blocked semantics the ship gate uses (no second copy of the rule). | reused |
| `_brain_query` (`find_scenarios_verifying`, `find_scenarios_for_journey`, `find_passing_testresults_for_scenario`) | The read seam onto the brain store. The seam→scenario resolution is built **only** from these existing typed queries — no new traversal primitive (matches the `_verify_scenario_coverage` precedent). | reused |
| `_wpxlib` INDEX parser (`WPRow`, `dependsOn`/`kind`/`status`, snake→camel alias #104) | The read seam onto INDEX.md. Seam-membership is derived from `kind: contract` + the `dependsOn` graph + per-WP `status`. | reused |
| `sulis-verify-acceptance` (CLI) | The runner. Invoked exactly as the ship gate invokes it — `--scenario <id> --target local --repo-root . --json` — and the `gate` field of its JSON envelope is read. **Not reimplemented** (SPEC constraint). | reused |

**Dependency direction:** `_seam_close_gate` depends on `_acceptance_gate`,
`_brain_query`, and the `_wpxlib` INDEX reader — all sideways/inward (decision +
read seams). It does **not** depend on `wpx-step12`, `wpx-train`, or the skills;
those depend **on it** (the hook calls into the gate, never the reverse). This
keeps the gate unit-testable as a pure decision over fixture inputs — the
property `test_ship_acceptance_gate_wiring.py` relies on for the ship gate.

### Armor — Operational hardening

This is internal methodology machinery with no network surface, no secrets, no
external calls of its own (the runner it shells out to already owns its own
timeouts/isolation). The relevant hardening is **failure-mode correctness**, not
resilience primitives:

- **Best-effort evidence, never-fatal** — the gate mirrors the existing
  `sulis-verify-acceptance` contract: a brain-store write failure (evidence
  deposit) NEVER changes the verdict. A seam that drove green stays green even
  if the store is unwritable. Inherited free by reusing the runner.
- **Degrade-closed on the gate decision, degrade-open on detection** — if the
  gate cannot *determine* whether a seam closed (malformed INDEX, missing WP
  row), it does **not** silently pass: it surfaces a plain-English "couldn't
  evaluate the seam at <WP>" and treats the seam as **not-closed-this-turn**
  (re-evaluated on the next WP `done`), rather than fabricating a green. If a
  seam *is* closed but a Scenario can't be driven, that is `blocked` (the
  observed-or-blocked rule), not a skip.
- **No new env/secret reads.** `SULIS_CHANGE_ID` isolation already fixed (#98).
- **Plain-English surfacing (SPEC constraint)** — every block names the seam
  (by the contract WP's title, not its id) and what wasn't driven. No operator
  vocabulary leaks (no `dna:scenario:…`, no `WP-NNN` in the founder line).

### Proof — Verification protocol

Test-first (MUST), mirroring `test_ship_acceptance_gate_wiring.py`. Two test
layers:

1. **Decision-unit tests** over `_seam_close_gate` as a pure function — fixture
   INDEX graph + fixture brain store + fixture runner-verdict, assert
   `observed`/`blocked` and the founder-English message. This is where the six
   acceptance criteria live (fast, hermetic, no subprocess).
2. **Wiring tests** — structural assertions over the live skill/tool text
   (`wpx-step12` invokes the gate at the done-transition; `run-wp`/`run-all`
   SKILL.md document the seam-close gate) — the same shape as
   `test_ship_acceptance_gate_wiring.py`'s assertions over `change/SKILL.md`.

See **Test surface** below for the file/case enumeration.

---

## How the gate hooks into the build loop

### The trigger point — `wpx-step12 wrap`, immediately after the `in_progress→done` flip

Recon confirmed **no seam-close gate exists today** and the natural hook is
"run-wp Step 7 completion / run-all integration-WP completion." Examining the
code resolves "Step 7 completion" to its precise mechanical moment: a WP is not
`done` at Step 7 (push) — Steps 8–12 still run (CI, merge, deploy, health,
smoke, security, **then** the INDEX flip to `done`). The atomic moment a WP
becomes `done` is **`wpx-step12 wrap` Step 12.2** (`wpx-index flip-status --to
done --expected in_progress`).

**Both paths converge here.** The single-WP path (`run-wp --force-single`) calls
`wpx-step12 wrap` at its Step 4. The batch path (`run-all` → `wpx-train`) also
finalises each WP through `wpx-step12 wrap`. So a **single hook at the
done-transition** covers both run-wp and run-all without duplicating logic — see
[ADR-003](adrs/ADR-003-seam-close-hook-at-wp-done-transition.md).

```
wpx-step12 wrap
  12.1 append acceptance evidence
  12.2 flip INDEX status in_progress → done   ← a WP just became done
  12.2a  ┌─────────────────────────────────────────────────┐   ← NEW
         │ seam-close check: did a seam just close?          │
         │   _seam_close_gate.evaluate(just_done_wp, index,  │
         │                             brain_base_dir)       │
         │   • not-closed → no-op, continue                  │
         │   • closed + observed → record, continue          │
         │   • closed + blocked  → surface founder-English,  │
         │     do NOT roll back the flip; emit gate-block in  │
         │     the wrap envelope so the calling session halts │
         │     seam-close as "not done"                       │
         └─────────────────────────────────────────────────┘
  12.3 remove worktree
```

**Why after the flip, not before:** the seam-close predicate asks "are *all*
WPs on both sides of this seam now `done`?" — it must observe the current WP as
`done` to answer. Reordering to before the flip would force the gate to special-
case "…and this one, which is about to flip." Running after the flip keeps the
predicate a clean read over INDEX state. The flip is **not rolled back** on a
block: the WP genuinely reached done; it is the *seam* that is not done, and
that is what the gate reports. (Mirrors the ship gate: a blocked acceptance verdict
does not un-merge the change; it refuses to call it done.)

**Why not roll the gate into `wpx-train` Step 10 instead:** the train batches
deploy/health/smoke per-batch, but the *done flip* is still per-WP via
`wpx-step12 wrap`. Hooking at the per-WP transition means one site, one test
surface, and correct firing whether a seam closes inside a batch or across two
batches/trains. The train's existing `--enable-gate-handoff` phase remains for
the deploy-level gates; the seam-close gate is orthogonal and lives at the
finer-grained transition.

### Identifying that a seam closed — from the dependency graph + INDEX

A **seam** is owned by `CONTRACT_FIRST_STANDARD.md`: a `kind: contract` WP first,
producer + consumer WPs that `dependsOn` it (CF-05 parallel-not-sequential), and
an integration child WP last (CF-07: swap mock→real + conformance check). The
gate reads this structure straight out of INDEX.md via the existing `_wpxlib`
parser (which already aliases snake→camel `dependsOn`, #104).

A seam is **closed** when either:

1. **An integration / composite WP completes** — a WP with `kind: composite`
   (the CF-07 integration child) or carrying `produces: integration-check`
   reaches `done`. This is the canonical "integration last" close. The seam is
   the set rooted at the contract WP this integration WP transitively
   `dependsOn`. **(Primary signal — matches the SPEC's "integration / composite
   WP completes".)**
2. **A contract WP's full fan-out is done** — for a `kind: contract` WP, every
   WP that `dependsOn` it (the producer + consumer side) is `done`, even if no
   explicit integration WP was authored. This is the "producer WP and its
   consumer WP both reach done" close from the SPEC, for decompositions that
   didn't emit a separate integration child.

The gate computes, for the just-`done` WP, the set of seams it could have just
closed (the contract WPs it is part of, by walking `dependsOn` to contract
roots), and for each checks whether that seam is now fully `done`. A seam closes
**once** — the gate records which seams it has already driven (via the brain
evidence the runner deposits, see resolution below) so a later WP `done` in an
unrelated part of the graph doesn't re-fire a settled seam.

> **This change has no contract-WP seams of its own** (it is single-kind
> internal machinery; CF exemption applies). That is fine and is itself a test
> case: the gate must no-op cleanly when the just-`done` WP is part of no seam.

### Mapping a closing seam → requirements → covering Scenarios

This is the load-bearing resolution and is recorded in
[ADR-004](adrs/ADR-004-seam-to-scenario-resolution-via-requirement-bridge.md).
The constraint discovered in code: **WP frontmatter does NOT carry the
requirement ids a WP implements** — the only structured WP→requirement signals
are indirect. Scenarios, however, key cleanly to requirements
(`verifies: [dna:requirement:…]`) and to a journey (`journey:
dna:workflow:…`) — confirmed in this repo's `*.scenarios.jsonld`. So the
bridge is **seam → requirements → Scenarios**, resolved through the brain, not
through WP frontmatter:

```
closing seam (contract WP + its fan-out)
   │
   │ (1) requirements the seam implements
   ▼
{dna:requirement:…}                ← see resolution sources below
   │
   │ (2) _brain_query.find_scenarios_verifying(req_id)   [existing query]
   ▼
{dna:scenario:…}  covering Scenarios
   │
   │ (3) sulis-verify-acceptance --scenario <id> --json   [existing runner]
   ▼
gate verdict per Scenario  →  _acceptance_gate.gate_decision(...)  [reused]
```

**Step (1) — requirements the seam implements.** Resolution sources, in priority
order (the gate uses the first that yields a non-empty set):

- **The seam's contract WP `verification` block.** Per
  `WORK_PACKAGE_STANDARD.md`, WPs carry a `verification:` field
  (adapter + artifact). Where a contract WP additionally declares the
  requirement(s) it satisfies (an `implements:` / `verifies:` list), the gate
  reads it directly. **This is the clean path and the one
  `/sulis:plan-work` should populate going forward** — see the standards
  amendment below, which makes the contract WP carry its requirement ids so the
  seam-close gate has a first-class source rather than an inference.
- **The change's Scenario set, filtered by journey.** Where the contract WP
  names a journey (or the change authored Scenarios at `/sulis:specify`), the
  gate enumerates `find_scenarios_for_journey(journey_id)` and treats the
  Scenarios whose `verifies` requirements intersect the seam's requirements as
  covering. (Reuses the `_verify_scenario_coverage` precedent.)

**Step (2) — covering Scenarios.** `find_scenarios_verifying(req_id)` already
exists and returns exactly the Scenarios whose `verifies` array contains the
requirement. Union across the seam's requirements = the covering Scenario set.

**Step (3) — drive + fold.** For each covering Scenario, invoke
`sulis-verify-acceptance --scenario <id> --target local --repo-root . --json`
and read the JSON `gate`/`verdict` field. Fold the per-Scenario verdicts through
the **reused** `_acceptance_gate.gate_decision(results,
require_observed=not allow_deferred)` so the seam-close gate and the ship gate
share one observed-or-blocked decision rule (no drift).

> **Why a requirement bridge, not "the seam's last Scenario":** Scenarios key
> to requirements + a journey, **not** to seams — confirmed at recon and in the
> `.scenarios.jsonld` shape. They do not tile seams 1:1. A Scenario-keyed
> trigger can't reliably fire per-seam. Hence the gate unit is the **seam**
> (ADR-001) and the seam→Scenario hop goes **through requirements**.

---

## Verdict semantics (observed-or-blocked, at the seam)

The gate's verdict per closing seam:

| Situation | Verdict | Behaviour |
|---|---|---|
| A covering Scenario drove green (**equality** verdict over the real record) | `observed` | seam-close proceeds; recorded |
| A covering Scenario drove green (**property** verdict — a record matching shape X appeared) | `observed` | seam-close proceeds; recorded |
| A covering Scenario's step **failed** | `blocked` | halt seam-close; founder-English (which seam, which step) |
| A covering Scenario was **deferred** (real outcome not driven — credential/infra/agent-step hop absent) | `blocked` (default) | halt; founder-English names the need; **escapable** via `--allow-deferred` |
| The seam needs the **agent-step tier** (live subagent / browser-MCP execution, deferred to #92) | `blocked` | correct behaviour, not a bug; the drive can't run for real yet; escapable via `--allow-deferred` |
| The closing seam has **no covering Scenario at all** | `blocked` | its real-data behaviour was never driven — [ADR-005](adrs/ADR-005-no-covering-scenario-is-blocked-distinct-from-deferred.md). **Distinct from deferred**: deferred has a Scenario that couldn't run; no-coverage has no Scenario. Founder-English: "this seam has no end-to-end check — nothing drove the real data across it." |
| The just-`done` WP is part of **no seam** | `not-closed` (no-op) | the common case for single-kind work; gate is silent |

`observed` maps to `pass` and `blocked` to `blocked` in the reused
`gate_decision` vocabulary. The agent-step-blocked and no-coverage cases are
**new contributors** to `blocked` that the seam-close gate adds on top of
`gate_decision`'s existing `fail`/`manual-pending`/`deferred` handling — they
are computed in `_seam_close_gate` before/around the `gate_decision` call (a
no-coverage seam never reaches `gate_decision` because there are no results to
fold; the gate short-circuits to `blocked` with the no-coverage reason).

### The explicit deferred escape hatch

Reuse the existing `--allow-deferred` flag (already on `sulis-verify-acceptance`
and already threaded through the ship gate). A knowingly-deferred seam — e.g. one
whose only honest check needs the #92 agent-step tier — proceeds with the
deferral **recorded** (the runner's evidence deposit + a plain-English note in
the wrap envelope). The hook passes `allow_deferred` through to the gate, which
passes `require_observed=not allow_deferred` to `gate_decision`. Default is OFF
(observed-or-blocked): the escape is a deliberate, logged choice, never the
default — identical discipline to the ship gate.

---

## Where the standards changes land

### `CONTRACT_FIRST_STANDARD.md` — new **CF-12** (seam-close DoD timing)

Analogous to CF-07 (which says *integration = swap mock→real + conformance
check, "done means wired at the seam"*), CF-12 adds the **timing** rule: the
seam's real-data acceptance is driven **at seam-close, not deferred to ship**.
Proposed wording:

> ### CF-12 — Real-data acceptance is driven at seam-close, not at ship · MUST
>
> A contract-first seam's **real-data behaviour** (the producer's actual output
> crossing to the real consumer) MUST be driven the moment the seam closes — when
> the integration WP completes, or when the contract WP and all the producer +
> consumer WPs that `dependsOn` it reach `done` — **not** deferred to the ship
> stage. The drive uses the change's covering Scenarios (the Scenarios that
> verify the requirements the seam's two sides implement) against a standing app,
> reading the observed-or-blocked verdict over the **real saved record**. A seam
> with **no covering Scenario** is **blocked** (its real-data behaviour was never
> driven), not silently passed. A seam needing an execution tier that isn't live
> yet (e.g. agent-step) is **blocked** until it is, escapable only by a conscious,
> recorded deferral.
>
> CF-07 says *what* "done at the seam" means (wired + conformant). CF-12 says
> *when* it is checked (seam-close, the moment it is cheap to fix) — re-timing the
> catch earlier than the ship-stage backstop. This is the contract-first
> application of the **observed-or-blocked** Definition-of-Done discipline.
>
> **Anti-pattern:** letting both sides pass hermetically against fixtures, merging
> them adjacent, and discovering at ship that the real data never crossed the seam
> — the slow find-one-fix-one tail this rule exists to kill.

The seam *definition* stays owned by CF-01..CF-07 (this change does not redefine
the seam — SPEC constraint); CF-12 adds only the timing-and-DoD rule on top.

Note the requirement-bridge dependency: CF-12's resolution needs the contract WP
to expose the requirements it implements. Land that as part of the WP standard
amendment below (the `implements:` field), so CF-12 has a first-class source.

### `WORK_PACKAGE_STANDARD.md` — DoD wording + contract-WP `implements:`

Two small amendments:

1. **WP-05 / WP-08.5 DoD wording.** Add to the contract / integration WP's
   Definition of Done: *"A seam-spanning (`kind: contract` / integration
   `kind: composite`) WP is not `done` until the seam-close gate reports
   `observed` for the seam — its covering Scenarios drove the real data across
   the seam, or a conscious `--allow-deferred` was recorded. A seam with no
   covering Scenario, or one needing an execution tier not yet live, is blocked
   (per CF-12)."*
2. **Contract WP carries `implements:`** (the requirement bridge, ADR-004). Add
   to WP-08.5: *"A `kind: contract` WP SHOULD carry `implements:
   [dna:requirement:…]` — the requirement ids the seam satisfies — so the
   seam-close gate can resolve the seam to its covering Scenarios directly. When
   absent, the gate falls back to the change's Scenario set filtered by journey."*
   SHOULD (not MUST) because the journey-filtered fallback keeps older WPs
   working; the explicit field is the clean path `/sulis:plan-work` populates
   going forward.

---

## Test surface

Mirrors `plugins/sulis/scripts/tests/unit/test_ship_acceptance_gate_wiring.py`:
a thin **wiring** layer (structural assertions over the live skill/tool text)
plus a **decision-unit** layer (the six acceptance criteria as pure-function
tests over fixtures). All stdlib + pytest, Python 3.11-safe.

### File 1 — `tests/unit/test_seam_close_gate.py` (decision-unit; the 6 criteria)

Pure tests over `_seam_close_gate.evaluate(...)` with a fixture INDEX graph, a
fixture brain store (or a monkeypatched `_brain_query`), and a fixture/stubbed
runner verdict. **Authored failing-first.**

| Test | Acceptance criterion | Asserts |
|---|---|---|
| `test_seam_undriven_scenario_blocks` | **AC-1** | Seam closes; a covering Scenario exists but was never driven green → verdict `blocked`. (Today it passes silently until ship — the bug being fixed.) |
| `test_seam_equality_verdict_passes` | **AC-2** | Seam's covering Scenario drove green with an **equality** verdict → `observed` / pass. |
| `test_seam_property_verdict_passes` | **AC-3** | Covering Scenario drove green with a **property** verdict (record matching shape X appeared) → `observed` / pass. |
| `test_seam_deferred_blocks` | **AC-4** | A deferred / blocked Scenario → `blocked`; founder-English message names the seam and what wasn't driven; **no** `dna:`/`WP-` ids leak into the founder line. |
| `test_seam_no_covering_scenario_blocks` | **AC-5** | Closing seam with **no covering Scenario** → `blocked`; message distinguishes "no end-to-end check" from "couldn't run" (ADR-005). |
| `test_seam_allow_deferred_escape_records` | **AC-6** | With `allow_deferred=True`, a knowingly-deferred seam → pass, **and** the deferral is recorded (evidence/note present in the result). |

Supporting unit tests (not numbered ACs, but needed for correctness):

- `test_unrelated_wp_done_is_noop` — a just-`done` WP in no seam → `not-closed`,
  silent (the common single-kind case; this change's own WPs hit this path).
- `test_integration_wp_completion_detects_seam_close` — detection signal (1):
  an integration / `kind: composite` WP reaching `done` closes its rooted seam.
- `test_contract_fanout_all_done_detects_seam_close` — detection signal (2):
  contract WP + all `dependsOn`-children done, no explicit integration WP.
- `test_seam_close_fires_once` — a settled seam is not re-driven by a later
  unrelated WP `done`.
- `test_malformed_index_does_not_fabricate_green` — Armor: undeterminable
  detection surfaces "couldn't evaluate", treats as not-closed-this-turn, never
  fakes pass.
- `test_gate_decision_is_reused_not_reimplemented` — the fold goes through
  `_acceptance_gate.gate_decision` (assert by behaviour parity on a shared
  fixture, so the two gates can't drift on observed-or-blocked).

### File 2 — `tests/unit/test_seam_close_gate_wiring.py` (structural, mirrors the ship-wiring test)

Structural assertions over the live tool/skill text, exactly as
`test_ship_acceptance_gate_wiring.py` asserts over `change/SKILL.md`:

- `test_wpx_step12_invokes_seam_close_gate` — `wpx-step12` (the done-transition)
  references / invokes the seam-close gate after the status flip.
- `test_runwp_documents_seam_close_gate` — `run-wp/SKILL.md` documents the
  seam-close gate at WP-done.
- `test_runall_documents_seam_close_gate` — `run-all/SKILL.md` documents the
  seam-close gate firing when a seam-spanning WP completes.
- `test_seam_gate_blocks_on_blocked_verdict` — the wiring text states a
  `blocked` seam **stops** seam-close (not call-it-done) — mirrors
  `test_ship_blocks_on_blocked_verdict`.
- `test_seam_gate_treats_deferred_as_blocking_by_default` — the text states
  observed-or-blocked + the `--allow-deferred` escape — mirrors
  `test_ship_treats_deferred_as_blocking_by_default`.

### File 3 — standards-presence tests (lightweight, optional but cheap)

- `test_contract_first_standard_has_cf12` — `CONTRACT_FIRST_STANDARD.md`
  contains a CF-12 seam-close-timing rule.
- `test_work_package_standard_seam_close_dod` — `WORK_PACKAGE_STANDARD.md`
  carries the seam-close DoD wording + the `implements:` contract-WP field.

> **Grounding "done" in the blocking gate, not branch-CI:** this repo's `main`
> is unprotected (RC-02), so branch-CI is advisory. The gate's own "done" is the
> six decision-unit tests passing — a blocking gate — not a green CI badge. That
> is precisely the failure class this change addresses; the tests are the teeth.

---

## Verification Plan

<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->

This change's `kind:` is **methodology** — a pure-decision Python module plus
thin hooks at one transition plus two standards amendments. The
kind→adapter row therefore is *"structural assertions + integration test where
a fresh dispatch produces output with the new shape."* The concrete
verification content lives in **Test surface** above; this section records the
design-time posture and the per-integration classification the P-VER rubric
checks.

### Q1. Posture (what we verify, and how)

The verifiable behaviour is the seam-close gate's **decision** — given a
just-`done` WP + the INDEX dependency graph + the brain store + a per-Scenario
runner verdict, it returns `observed` / `blocked` / `not-closed` with the
correct founder-English message. Verification has two layers, both stdlib +
pytest, Python 3.11-safe (per the `methodology` adapter):

- **Decision-unit tests** (`tests/unit/test_seam_close_gate.py`) — the six
  acceptance criteria as pure-function tests over fixture INDEX graphs, a
  fixture/monkeypatched brain store, and stubbed runner verdicts. Authored
  failing-first. This is the blocking gate the change's own "done" is grounded
  in (not branch-CI; `main` is unprotected, RC-02).
- **Structural / wiring tests** (`tests/unit/test_seam_close_gate_wiring.py`
  + the standards-presence tests) — assertions over the live tool/skill/standards
  text that the hook fires at the `wpx-step12` done-transition and the standards
  carry CF-12 + the seam-close DoD wording. Mirrors
  `test_ship_acceptance_gate_wiring.py`.

The "fresh dispatch produces output with the new shape" half of the adapter is
satisfied by the decision-unit layer: a fresh `evaluate(...)` over a closing-seam
fixture must produce the `observed`/`blocked` verdict shape that did not exist
before this change.

### Q2. Integrations (per-integration classification)

The gate consumes two integration seams; neither is built by this change:

- **The acceptance-drive substrate — `sulis-verify-acceptance` runner +
  verdict-invariant — `existing` (shipped, #259).** Strategy: in-memory /
  stubbed-runner adapter at the decision-unit layer (the gate reads the JSON
  `gate`/`verdict` envelope field; tests stub that envelope), and behaviour-parity
  assertion that the verdict fold goes through the **reused**
  `_acceptance_gate.gate_decision` rather than a second copy
  (`test_gate_decision_is_reused_not_reimplemented`). The runner is invoked
  exactly as the ship gate invokes it (`--scenario <id> --target local
  --repo-root . --json`) — not reimplemented (SPEC constraint). Resilience: the
  runner owns its own timeouts/isolation; the gate inherits best-effort,
  never-fatal evidence semantics free by reuse (no new network surface to harden).
- **The agent-step execution tier — live subagent / browser-MCP drive —
  `deferred` (to #92), canonical need identifier `agent-step-execution-tier`.**
  A seam whose only honest check needs this tier reports `blocked` — correct
  behaviour, not a bug — escapable only via a conscious, recorded
  `--allow-deferred`. The decision-unit test `test_seam_deferred_blocks` pins
  this; no live agent-step drive runs in this change's test suite.

The read seams onto the brain store (`_brain_query`) and INDEX.md (`_wpxlib`
parser) are `existing` reused queries, exercised in the decision-unit layer via
fixtures — not external integrations, so no separate classification.

### Q3. Adapter

`methodology` adapter applies; single adapter (no backend/frontend/async/contract
side). No additional adapters needed (Q18: single adapter).

### Q4. Infrastructure

- **Existing (resolves in-repo today):** `plugins/sulis/scripts/_acceptance_gate.py`
  (the reused `gate_decision`), `plugins/sulis/scripts/_brain_query.py` (the
  reused read queries), `plugins/sulis/scripts/sulis-verify-acceptance` (the
  runner), `plugins/sulis/scripts/tests/unit/test_ship_acceptance_gate_wiring.py`
  (the mirrored test pattern).
- **Deferred:** `agent-step-execution-tier` (#92) — the live agent-step drive a
  subset of seams will eventually need. Not required for this change's own tests
  to pass; its absence is exactly the `blocked` path the gate models.
- **Out-of-scope:** the verification substrate build (#259, shipped) — consumed,
  not rebuilt.

### Per-WP verification shape (for `/sulis:plan-work`)

The decision-unit and wiring WPs use **Shape 1 — concrete**
(`adapter: methodology`, `artifact:` the pytest nodeid, e.g.
`tests/unit/test_seam_close_gate.py::test_seam_undriven_scenario_blocks`). Any WP
covering only an agent-step-tier seam would use **Shape 2 — deferred**
(`deferred-to-follow-on: agent-step-execution-tier`). No trivial-carveout
(Shape 3) WPs are expected — every WP here ships a real test.

---

## What this change explicitly does NOT do (non-goals, from SPEC)

- **Does not build the verification substrate** — shipped (#259). Consumed via
  `sulis-verify-acceptance` + the verdict-invariant. The runner is **not**
  reimplemented.
- **Does not build the agent-step execution tier** — deferred to #92. Seams
  needing it report `blocked` (correct, not a bug).
- **Does not remove the ship-stage drive (gate 4.8)** — it stays as a backstop
  on the same runner ([ADR-002](adrs/ADR-002-keep-ship-gate-as-backstop.md)).
  This change moves the *primary* catch earlier. Defence in depth.
- **Does not redefine the seam** — owned by `CONTRACT_FIRST_STANDARD.md`. CF-12
  adds only the seam-close timing/DoD rule.
- **No new user-visible product surface.**

---

## Open architecture questions (could not fully resolve from the brief)

1. **First-class WP→requirement linkage.** WP frontmatter does not today carry
   the requirement ids a WP implements; the requirement bridge (ADR-004) leans on
   adding `implements:` to the contract WP (WP standard amendment) with a
   journey-filtered fallback. **Decision needed at `/sulis:plan-work`:** whether
   to also backfill `implements:` onto existing contract WPs, or rely on the
   fallback for legacy decompositions. The blueprint takes the fallback as
   sufficient for correctness now; the explicit field is the clean forward path.
   *(Recorded, not blocking — the fallback path is designed.)*

2. **Once-only firing persistence.** The gate must not re-drive a settled seam on
   a later unrelated WP `done`. The design proposes reading the runner's deposited
   brain evidence (`find_passing_testresults_for_scenario`) as the "already
   driven" signal — same source `_verify_scenario_coverage` uses. If a project
   runs with `--no-emit-evidence`, that signal is absent and a seam could re-fire.
   **This is acceptable** (re-driving a green seam is wasteful but not wrong) and
   is noted so `/sulis:plan-work` can decide whether a cheap per-seam marker is
   worth a WP. *(Recorded, not blocking.)*

Neither blocks decomposition. Both are flagged for the founder/`plan-work` pass.

---

## See also

- [ADR-001](adrs/ADR-001-gate-unit-is-the-seam-not-the-scenario.md) — gate unit = seam, not Scenario
- [ADR-002](adrs/ADR-002-keep-ship-gate-as-backstop.md) — keep ship gate 4.8 as a backstop
- [ADR-003](adrs/ADR-003-seam-close-hook-at-wp-done-transition.md) — hook at the WP done-transition (`wpx-step12`)
- [ADR-004](adrs/ADR-004-seam-to-scenario-resolution-via-requirement-bridge.md) — seam→Scenario via the requirement bridge
- [ADR-005](adrs/ADR-005-no-covering-scenario-is-blocked-distinct-from-deferred.md) — no-covering-Scenario seam is blocked, distinct from deferred
- `plugins/sulis/references/standards/CONTRACT_FIRST_STANDARD.md` — CF-07 (the anchor), the seam definition
- `plugins/sulis/scripts/_acceptance_gate.py` — `gate_decision`, reused verbatim
- `plugins/sulis/scripts/_brain_query.py` — the read-seam queries reused for resolution
- `plugins/sulis/scripts/sulis-verify-acceptance` — the runner, reused
- `plugins/sulis/scripts/tests/unit/test_ship_acceptance_gate_wiring.py` — the test pattern mirrored
