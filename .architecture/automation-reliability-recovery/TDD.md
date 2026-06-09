# Technical Design — provider-neutral reliability layer for unattended automation

**Change:** CH-01KTMK · `automation-reliability-recovery` · `feat`
**Mode:** brownfield-with-spec — **extend** `plugins/sulis/scripts/_session_manager/`
behind its existing `ProviderAdapter` seam (EP-03; change-primitive: EXPAND-Extend
the seam + EXPAND-Create the layer)
**Kind:** `backend` (`founder_facing: false`; no frontend/visual contract)
**Tier:** M (see `SIZING.md`; ASR-driven — the weight is recovery correctness)
**Sources:** `.changes/feat-automation-reliability-recovery.SPEC.md`; existing
`_session_manager/` (events / adapter / manager / lifecycle / state / session /
socket_server); `.architecture/autonomous-delivery-environment/` (ADE TDD +
ADR-002/003/005, **external prior art**).

> **Respect, don't restate.** The session manager's hexagonal core, the
> three-category typed error model (`events.py`), the `ProviderAdapter`
> Protocol seam (`adapter.py`), the enforced state machine (`state.py`), the
> restart-on-death lifecycle (`lifecycle.py`, the recovery-around-the-core
> precedent), the one-in-flight FIFO (`session.py`), and the contract/fake/
> parity test discipline **already exist** and are documented in those
> modules' docstrings + `SESSION_MANAGER_CONTRACT`. This TDD references that
> structure and specifies **only** what this change adds. This change's ADRs
> (ADR-001..004) live in its own namespace and do **not** renumber the ADE
> set (ADE ADR-001..009, referenced as prior art).

---

## 1. The shape of the change

Today an unattended turn that stops on an API failure simply stops — a human
restarts it. This change adds a thin **reliability layer that sits around the
existing session lifecycle** (ADR-001) and turns a stoppage into one of three
outcomes:

| Class | Trigger (provider-neutral) | Action |
|---|---|---|
| **transient-blip** | `protocol` category, or provider hint (Claude: 429 / reset) | retry with exponential backoff + full jitter, ~10–15-min budget, then reclassify dead-end |
| **dead-end** | `internal`/`expected` deterministic decline, or budget exhausted | abandon cleanly with a typed, observable `error` Event |
| **login-expired** | `expected`/`NOT_AUTHORIZED`, or provider hint (Claude: 401/403) | pause, emit a re-login notification on the existing surface, resume from place after re-auth |

The headline and the risk are the same thing: **doing this around a live,
concurrency-sensitive lifecycle without disturbing it.** The whole design is
shaped by "around, not inside" (the spec's hard constraint; ADR-001) — the
existing turn-complete, one-in-flight slot, and state machine are
byte-unchanged.

Three new pieces, dependencies pointing inward, plus one thin additive
extension of the existing seam:

```
events.py  (Form invariant — UNCHANGED: vocabulary + 3-category errors)
   ▲
classifier.py   EXPAND-Create · pure domain · EventError → RecoveryClass
   ▲                                          (provider-neutral; ADR-003)
recovery.py     EXPAND-Create · RecoveryDriver + RetryPolicy value object
   ▲                            (mirrors LifecycleManager's around-the-core
   │                             shape; ADR-001 + ADR-002)
manager.py      EXPAND-Extend · one wiring line + one error-observation hook
                                (the same slot LifecycleManager attaches to)

adapter.py      EXPAND-Extend · two thin additive Protocol methods
adapters/       (classify_failure detection hint + reauth trigger; ADR-003)
  claude.py     EXPAND-Extend · Claude's 401/403→login, 429→blip, 400→dead-end
```

---

## 2. Form — structural integrity

### 2.1 The seam (unchanged principle, thinly extended surface)

`adapter.py`'s `ProviderAdapter` Protocol is "the only agent-specific
surface" (§2.4). We extend it with **two defaulted, additive methods** —
the same additive discipline `SessionSpec.io_mode` / `brief_change_id`
already set as precedent — and nothing more (spec: "do not fork or widen
beyond the thin detection + re-auth additions"):

- `classify_failure(error: EventError) -> RecoveryClass | None` — the
  provider's detection hint (ADR-003). Defaulted to `None` (defer to the
  neutral classifier) so a future adapter that doesn't override it is still
  safe.
- `reauth() -> ReauthTicket` — begin re-auth, return the re-login link the
  notification carries + a completion handle (ADR-004). Only called on
  `LOGIN_EXPIRED`.

> **This is EXPAND, not WRAP.** We extend a Protocol *we* own and create new
> modules behind it — the Stripe-rule discriminator (§2.4): the public face
> is the session-manager's own seam, not a vendor's. The change-primitive
> walk lands on EXPAND-Extend (the seam) + EXPAND-Create (the layer), never
> SUBSTITUTE-Wrap. No Band-Aid wrapper over the manager (ADR-001 rejected
> that alternative explicitly).

### 2.2 Component inventory (new / changed)

| Component | Move | Form note |
|---|---|---|
| `_session_manager/classifier.py` | EXPAND-Create | pure domain: `RecoveryClass` enum + `classify(EventError, hint)`; depends on `events.py` only; **no adapter import** (provider-neutral, ADR-003) |
| `_session_manager/recovery.py` | EXPAND-Create | `RetryPolicy` frozen value object + `DEFAULT_RETRY_POLICY` (ADR-002) + `RecoveryDriver` (ADR-001); consumes manager primitives via injected capabilities, mirrors `LifecycleManager` |
| `_session_manager/adapter.py` | EXPAND-Extend | two defaulted Protocol methods (`classify_failure`, `reauth`) + `ReauthTicket` value object; `@runtime_checkable` conformance extends to assert the shape |
| `_session_manager/adapters/claude.py` | EXPAND-Extend | implement `classify_failure` (401/403→login, 429/reset→blip, 400/other→dead-end) + `reauth` (Claude re-login link) |
| `_session_manager/manager.py` | EXPAND-Extend | construct + wire the `RecoveryDriver` (one line, beside the `LifecycleManager` wiring); expose the error-observation hook (sibling to `_on_process_death`) |

The two `adapter.py` / `claude.py` items touch **existing** files behind the
Protocol; they are additive (new defaulted methods), so per EP-07 they are
**not** structural changes requiring a characterisation test — they add a
method, they do not restructure existing behaviour. The `manager.py` wiring
is additive (a new hook + construction line), same as the `LifecycleManager`
wiring already there. No REORGANISE-Refactor in this change → no
characterisation-test-before-refactor obligation triggered.

### 2.3 Dependency direction

`classifier.py` → `events.py` only (pure; the innermost new layer).
`recovery.py` → `classifier.py` + `events.py` + injected manager
capabilities (never reaches into `session.py`/`state.py` internals — it uses
the public `read`/`send`/`log.append`/resume primitives). `manager.py` is
the composition root that wires the driver (WPB-07). Adapters depend on the
shared `RecoveryClass` vocabulary, never the reverse. No module the
reliability layer adds is imported *by* `events.py` or `state.py` — the Form
invariants stay dependency-free (the existing `__init__.py` re-exports the
new public surface so callers import from the package).

---

## 3. Armor — operational hardening

This layer **is** Armor — it is the turn-level sibling of the process-level
restart-on-death lifecycle. Existing Armor (typed errors, state machine,
restart-on-death, recovery budget, idle eviction, turn guards) is **kept**;
this fills the one gap: a turn that ends in an `error` Event on a *live*
process.

### 3.1 The recovery pipeline (order is load-bearing)

When an `error`-kind Event lands in a session's log (observed via the
manager's error-observation hook, ADR-001), in this order:

1. **Skip process-death errors.** A `STDIN_BROKEN` "died mid-turn" surfaced
   by `LifecycleManager` is already being handled by restart-on-death — the
   recovery driver does **not** double-handle it (the two seams are
   siblings, not stacked). The driver acts only on errors from a *live*
   session's turn.
2. **Classify** (`classifier.classify`, ADR-003): ask the session's adapter
   for a `classify_failure` hint, else apply the neutral category default →
   one `RecoveryClass`.
3. **Branch:**
   - **transient-blip** → compute `next_delay(attempt, elapsed, policy)`
     (ADR-002, full jitter). If it returns a delay, append a "retry
     scheduled" `error` Event (reusing the observed code), wait the
     jittered delay (against the injected clock), then **re-submit the turn
     via the existing `manager.send`** — which the FIFO queue serialises, so
     a retry is just another turn, never a second in-flight turn
     (one-in-flight untouched). If it returns `None` (budget exhausted) →
     fall to dead-end with "retry budget exhausted" (acceptance: abandoned,
     not a silent hang).
   - **dead-end** → append a typed `error` Event ("abandoned: <reason>",
     reusing the observed code) and stop. **No budget burned** (acceptance:
     dead-end abandoned immediately).
   - **login-expired** → the pause→notify→resume flow (§3.3, ADR-004).
4. **Observe.** Every branch appends an Event to the **existing** log
   (no new stream) so a later reviewer sees, in `read(follow=True)`, exactly
   why a run was retried / abandoned / paused (acceptance).

### 3.2 The retry policy (ADR-002)

Exponential backoff + **full jitter** (AWS convention, CP-01), bounded by a
**wall-clock** total budget (~10–15 min; default 720 s) — the agreed
"persistent" default. On exhaustion, a transient-blip is **reclassified
dead-end** and abandoned with a typed Event. The policy is a frozen
`RetryPolicy` value object with `DEFAULT_RETRY_POLICY`, **injected** into the
driver (the same convention `manager.py` already uses for `recovery_budget`/
`turn_timeout`), so it becomes per-run/per-provider later by a
composition-root selection — **no redesign** (the founder's standing
requirement; ADR-002). The budget is measured against an **injectable clock**
so the test is deterministic and sleep-free (the maintenance-test precedent;
MEA-09).

### 3.3 The pause→notify→resume flow for login-expired (ADR-004)

1. Classifier → `LOGIN_EXPIRED`.
2. Driver calls `adapter.reauth()` → a `ReauthTicket` carrying the re-login
   link + a completion handle.
3. Driver appends an `error` Event with the existing `NOT_AUTHORIZED` code
   and the re-login link in its message — **this Event is the
   notification**, riding the platform's existing message/event surface
   (ADE ADR-005/003); no new screen (spec non-goal honoured).
4. Driver **pauses** the run at the driver level (holds it out of the retry
   loop; does **not** burn the retry budget — login-expiry is not a blip)
   pending the ticket's completion. The state machine and one-in-flight slot
   are untouched (the pause is in the Armor layer, ADR-004 — *not* a new
   `SessionState`).
5. On re-auth confirmation, the driver **resumes via the existing path** —
   `capabilities.supports_resume` + `resume_ref` + the same-key/same-log
   restart `LifecycleManager`/`_respawn` already implement (the
   session-manager half of ADE ADR-002). The agent wakes with full memory
   and **re-runs the incomplete step** — never reports it done (no
   fabricated completion; ADE ADR-002 / NFR-REL-04 discipline inherited).

### 3.4 Bounds & isolation

- The retry wait is bounded by `total_budget_seconds` (no unbounded retry).
- Backoff per-step is capped at `max_delay_seconds` (no runaway delay).
- Recovery is **per-session** (keyed); one session's pause/retry never
  blocks another (the existing per-key parallelism is preserved — the driver
  holds only that session out of *its* loop).
- The driver never touches a session other than the one whose error it
  observed (isolation, parallel to ADE NFR-SEC-06).

### 3.5 Observability

Reuses the existing structured log: every recovery action is an `Event`
(WPB-10 — structured, not string interpolation; the `Event` *is* the
structured record). No bodies/secrets in messages beyond the re-login link
the operator needs. No new logging channel.

### 3.6 Secrets & transport

No new outbound dependency, no new secret handling. `reauth()`'s re-login
link is provider-supplied and operator-facing; the layer carries it, it does
not store credentials (no-new-store non-goal).

---

## 4. Proof — verification protocol

### 4.1 What's reused

The session-manager's `@runtime_checkable` adapter-conformance test,
fake-vs-real adapter parity, deterministic sleep-free tests (synchronous
tick / injected clock), and the in-memory/no-subprocess testability of the
adapter and pure layers all stay and extend.

### 4.2 What's added (provider-neutral first — acceptance)

- **Classifier truth-table test** (`tests/.../test_classifier.py`) — the
  full table in `contracts/reliability-layer.contract.md` against real
  `events.py` value objects (not mocks), **with no adapter dependency**
  (acceptance: classifier + policy are provider-neutral). Includes the
  unknown-code → dead-end fall-through (CF-04 non-happy case).
- **Backoff/budget test** (`test_retry_policy.py`) — `next_delay` jitter
  bounds at attempts 0/3/10, and `None` at budget exhaustion; deterministic
  via a seeded RNG + fake clock (no real sleep; MEA-09).
- **RecoveryDriver per-class tests** (`test_recovery.py`) — built against a
  **fake classifier** returning each `RecoveryClass` and a **fake manager**
  exposing `send`/`log.append`/resume:
  - transient-blip that clears → run survives, re-submitted via `send`, no
    human restart (acceptance #1);
  - transient-blip that never clears → retried until budget exhausted, then
    a typed "abandoned" `error` Event (acceptance #2, not a silent hang);
  - dead-end → abandoned immediately, **budget not consulted** (acceptance
    #3);
  - login-expired → `reauth()` called, `NOT_AUTHORIZED` notification Event
    with link emitted, run paused (not failed), resume after ticket
    completion re-runs the step via the existing resume path, no fabricated
    completion (acceptance #4).
  - process-death `STDIN_BROKEN` error → driver **no-ops** (lifecycle owns
    it; no double-handling).
- **Claude detection test** (`test_claude_classify_failure.py`) — the
  per-provider mapping 401/403→login, 429/reset→blip, 400/other→dead-end;
  the **only** test that exercises a provider (acceptance: detection +
  re-auth exercised per-provider).
- **Adapter conformance extension** — `@runtime_checkable` assertion that
  `ClaudeAdapter` answers `classify_failure` + `reauth` (the
  Codex/Gemini-will-slot-in guarantee, extended).
- **Observability test** — after each action, `read(follow=True)` yields the
  contracted Event shape (the "later reviewer can see why" acceptance).

### 4.3 What is verified manually

The **real** login-expiry → real re-auth → real resume round-trip needs a
live `claude` with a genuinely expired credential; like ADE's real
resume/spawn, it cannot fully bootstrap in CI and is verified manually on
the founder machine. CI covers the logic against the fake clock + fake
re-auth ticket + the recorded-resume discipline the lifecycle already tests.

---

## 5. Decomposition note

`/sulis:plan-work` will produce atomic WPs. Suggested spine (`dependsOn` in
parens): **WP-contract** (the `RecoveryClass` vocabulary + truth table +
`RetryPolicy` shape — the shared constants, CF-05/CF-11) → then in parallel
**classifier** (pure, dependsOn contract) and **RetryPolicy + next_delay**
(pure, dependsOn contract) → **RecoveryDriver** (dependsOn classifier +
policy; built against fakes) → **adapter seam extension** (`classify_failure`
+ `reauth` defaulted on the Protocol; dependsOn contract) → **Claude
detection + reauth** (dependsOn adapter seam) → **manager wiring + hook**
(dependsOn driver + adapter seam) → **observability/integration test**
(dependsOn wiring). No WP is a REORGANISE-Refactor; all are EXPAND-Create or
additive EXPAND-Extend, so none carries a characterisation test in Red.

---

## Verification Plan

<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->

> Concretises the change's verification posture to TDD-level artifacts. The
> SPEC carries no `## Verification Plan` section (it is a lightweight change
> spec, not a full SRD); this section is authored from the SPEC's Acceptance
> list + the canonical 20-question set. Six subsections per ADR-001 of the
> verification standard.

### What user-observable behaviour are we verifying

There is no human user in the loop by design (`founder_facing: false`) — the
"observer" is the **operator reviewing an unattended run** and the **next
turn of the run itself**. Observable: a transient API failure no longer
stops the run (it retries and survives); a never-clearing failure ends as a
typed "abandoned" event within ~12 min instead of hanging forever; a
dead-end ends immediately; an expired login produces a re-login notification
on the existing message surface and, after re-auth, the run continues from
where it paused; and every one of these is legible in the existing
error/event stream.

### Verification environment(s)

- **Local dev + CI** — pytest over the pure classifier, the backoff/budget
  policy (seeded RNG + fake clock, no real sleep), the RecoveryDriver
  (against fake classifier + fake manager), the Claude detection mapping,
  and the adapter conformance extension. Mirrors the existing
  `_session_manager/` test setup (deterministic, sleep-free; MEA-09).
- **Local (founder machine)** — the real login-expiry → real re-auth → real
  resume round-trip against a live `claude` with an expired credential
  (cannot bootstrap in CI; manual, parallel to ADE's real-resume note).

### Bootstrap-from-zero case

The CI suite bootstraps from a fresh clone with **zero new infrastructure**:
the classifier and policy are pure; the driver runs against in-process fakes;
the Claude detection test feeds recorded `EventError` shapes (the existing
`tests/fixtures/session_manager/claude/` error fixtures are the seed —
referenced, not duplicated). No new fixture store is required for the
acceptance-critical (provider-neutral) tests. The one deferred need is the
live re-auth round-trip (manual).

### Per-integration verification strategy

| Integration | Boundary | Strategy | Classification | TDD concretion |
|---|---|---|---|---|
| The existing event stream (`events.py`) | in-process value objects | classify against **real** `EventError` objects (not mocks) | **existing** | `tests/session_manager/test_classifier.py`; imports the real `events.py` types |
| The `ProviderAdapter` seam (`adapter.py`) | in-process Protocol | conformance: assert `ClaudeAdapter` answers `classify_failure` + `reauth`; driver runs against a fake adapter | **existing** | `tests/session_manager/test_adapter_conformance.py` (extended); fake adapter in `test_recovery.py` |
| Claude provider detection (`adapters/claude.py`) | in-process mapping over recorded shapes | feed recorded 401/403/429/400 `EventError`s; assert the hint | **existing** | `tests/session_manager/test_claude_classify_failure.py`; reuses existing claude error fixtures |
| The resume path (ADE ADR-002 / `lifecycle._respawn` + `replace_process`) | in-process, same-key/same-log restart | driver triggers resume via the **existing** path against a fake manager; real round-trip manual | **deferred** | seam: existing `capabilities.supports_resume` + `resume_ref`; concrete WP shape **deferred** — `live-reauth-resume-claude` (manual); resilience: the retry budget cap + the per-session isolation (see `references/architecture-patterns.md` — AP-05/AP-06 turn-level analogue) |
| The clock (backoff/budget timing) | injected callable | inject a fake monotonic clock; assert delays + exhaustion deterministically | **existing** | `tests/session_manager/test_retry_policy.py`; `clock=` injection, seeded RNG |

- *Idempotency/replay (Q10):* a retry is a **new turn** through the existing
  one-in-flight FIFO — never a second concurrent turn; the slot semantics are
  the guard (unchanged). A login-expired pause does not re-fire `reauth()`
  on every observation — the driver holds one pending ticket per session.
- *Auth/authz (Q11):* the only auth here is the provider login the layer
  *detects* expiring (`NOT_AUTHORIZED`) and re-triggers via `reauth()`; the
  layer holds no credentials (no-new-store).
- *Failure if unavailable (Q12):* if `reauth()` itself fails, the driver
  abandons as dead-end with a typed Event (fail-safe, observable) — it does
  not hang.
- *Observability (Q13):* every action is an `Event` on the existing log;
  asserted by reading back the contracted Event shape.

### Per-kind verification adapter

Single adapter — **`backend`** (Q14; the kind→adapter table, canonical
reference cited above): "behavioural API test against a running service +
persistence assertion + (where applicable) idempotency / replay check."
Concretion: pytest behavioural tests over the public package surface
(`_session_manager` re-exports), asserting the recovery behaviour and the
emitted-Event "persistence" into the existing log; the idempotency check is
the retry-is-one-turn / one-pending-reauth assertion above. Artifacts:
`tests/session_manager/{test_classifier,test_retry_policy,test_recovery,test_claude_classify_failure,test_adapter_conformance}.py`.

Verification frontmatter shapes the WPs will use (ADR-003 of the
verification standard): the classifier / policy / driver / Claude-detection
WPs → **concrete** (`adapter: backend` + `artifact:` the named test path);
the **live re-auth resume** path → **deferred** (`adapter: backend` +
`deferred-to-follow-on: live-reauth-resume-claude`) for the manual
round-trip, **concrete** for the trigger-the-existing-resume logic against
the fake manager.

### Infrastructure needs surfaced (deferred)

- `live-reauth-resume-claude` — a manual procedure (live `claude` + a
  genuinely expired credential) to verify the real login-expiry → re-auth →
  resume-from-place round-trip end-to-end. Mirrors ADE's manual
  real-resume/real-spawn need; cannot bootstrap in CI. Follows the canonical
  `{noun}-{noun}-{vendor-or-scope}` identifier recipe.

No new CI fixtures are required for the acceptance-critical provider-neutral
tests — they reuse the existing `events.py` types and the existing Claude
error fixtures.

---

## 6. Sizing Report

- **Tier:** M computed and confirmed (see `SIZING.md`). sFPC ~5 (would read
  tier S alone); ASR ~9 (drives M — the weight is recovery correctness
  around a live lifecycle, not feature count). Higher-of-the-two-axes rule
  applied.
- **TDD length:** ~tier-S target despite tier-M classification, because
  Form and most of Proof are **covered** by the existing platform (the
  hexagonal core, the error model, the recovery-around-the-core precedent,
  the test discipline) — the new sections are the Armor gap (the turn-level
  retry/pause/resume) + the thin seam extension. No circuit breaker tripped
  (length ≤ 1.5× target; restating covered ground was refactored to
  references).
- **ADRs produced:** 4 (ADR-001 placement; ADR-002 retry-budget value
  object; ADR-003 provider-neutral classification / thin detection hint;
  ADR-004 pause/resume reuse of ADE ADR-002 + existing surface). Within
  tier-M max. None duplicate the ADE set (ADR-002/003/005 referenced as
  prior art, not renumbered).
- **Referenced (not restated):** the session-manager hexagonal core, the
  three-category error model (`events.py`), the `ProviderAdapter` seam, the
  enforced state machine, the restart-on-death lifecycle (the around-the-core
  pattern this layer mirrors), the one-in-flight FIFO; and from ADE: ADR-002
  (resume), ADR-003 (single sanctioned write path), ADR-005 (one coherent
  surface). All reused, not rebuilt (EP-03).
- **Sections referencing rather than restating:** §1, §2 (seam), §3.3
  (resume), §4 (test discipline).

## 7. Open architecture questions (founder-owned only)

None requiring a founder decision. The single founder-owned call — the
retry/give-up policy — was **already made** (persistent: exponential backoff
+ jitter, ~10–15-min cap) and is recorded as ADR-002 with the structure that
lets it become a per-run/per-provider setting later without redesign.

One judgement call made silently, surfaced here for the founder's awareness
(not a question): the SPEC says "~10–15-min total budget" — the design picks
**720 s (12 min)**, mid-range, as `DEFAULT_RETRY_POLICY.total_budget_seconds`.
It is a single named constant, trivially tunable, and the founder can move it
within (or beyond) the band at any time without a redesign.
