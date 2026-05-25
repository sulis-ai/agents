# Change Primitives — The Vocabulary of Code Change

> **Status:** Active — v0.6.0

Every code change is one of a finite set of architectural moves. This standard
catalogues those moves, organises them into a Minto pyramid of mutually
exclusive groups, and prescribes the design priority for choosing among them.

When SEA decomposes a TDD into Work Packages, each WP carries a `primitive:`
in its frontmatter. The primitive determines the WP's shape, the testing
strategy, the code intelligence the executor needs, and the risk profile of
the change.

---

## Provenance and Industry Context

This catalogue synthesises a vocabulary that is *not* canonical in the
literature — different authors slice the same space differently. The
synthesis draws on:

- **Martin Fowler, *Refactoring* (1999, 2018)** — the ~70-refactoring
  catalogue and the structural moves (Move, Extract, Inline, Rename,
  Decompose Function, Branch by Abstraction)
- **Fowler, *Strangler Fig Application* (2004)** — gradual replacement
  through routed calls
- **Kent Beck — code smells, characterisation tests** — the prerequisite for
  any Refactor
- **Lehman & Belady, *Programs, Lifecycles, and Laws of Software Evolution*
  (1985)** — the categories of system evolution at architectural scale
- **Eric Evans, *Domain-Driven Design* (2003)** — bounded-context boundaries
  and Anti-Corruption Layers (which we treat with caution — see No
  Band-Aid Wrappers)
- **Gang of Four, *Design Patterns* (1994)** — Adapter, Facade, Bridge,
  Proxy, Strategy patterns inform the SUBSTITUTE group
- **Barbara Minto, *The Minto Pyramid Principle* (1973)** — the hierarchical
  MECE structure used to organise the 22 primitives into 5 groups

**Honest about the gap:** there is no single agreed taxonomy of "code change
primitives." The 22 below are our working set — granular enough to drive
different WP shapes, tractable enough to actually use. Edge cases that
don't fit cleanly are usually composites (see "Composite Primitives").

---

## The Minto Pyramid

**Governing question (top):** *What is the relationship of this change to
the existing codebase?*

**Five MECE groups (middle):** Every code change has one dominant
relationship to existing code:

| Group | Relationship | Behaviour change? | Structure change? |
|---|---|---|---|
| **EXPAND** | Introduce new code or new usage of existing code | Yes (adds behaviour) | Adds new structure |
| **REORGANISE** | Change the structure of existing code | **No** (behaviour-preserving) | Yes (rearranges) |
| **SUBSTITUTE** | Change implementation behind a preserved surface | Possibly (often equivalent) | Implementation-only |
| **CONTRACT** | Remove existing code or behaviour | Yes (removes behaviour) | Shrinks structure |
| **REINFORCE** | Add cross-cutting concern over existing behaviour | Yes (adds non-functional) | Adds orthogonal layer |

These five are:

- **Mutually exclusive** — every change has one *primary intent*. Apparent
  overlaps are composites and are explicitly noted as such.
- **Collectively exhaustive** — every code change fits one. See "MECE Check"
  for stress tests.

**22 primitives (bottom):** distributed across the five groups, with
within-group priority encoded.

---

## EXPAND (5 primitives) — introducing new code

Priority order: cheapest to most invasive.

### 1. Reuse

**Definition:** Use an existing component, function, or abstraction as-is to
satisfy a new requirement. The new code is only the call site.

**Priority:** First — always considered before any other primitive.

**Code intelligence needed:** Public surface inventory, consumer count
(high consumer-count modules are battle-tested and safe).

**WP shape:** Call-site additions; no modifications to the reused subject.

**Testing:** Standard unit tests on the new call site. The reused subject's
existing tests carry coverage of its behaviour.

**Risk:** Lowest. The thing already works.

### 2. Compose

**Definition:** Assemble new behaviour by orchestrating existing components.
Pipe outputs to inputs; aggregate; coordinate. No new core capability.

**Priority:** Second — considered after Reuse, before Extend.

**Code intelligence needed:** Surfaces of the components being composed;
their composition contracts (sync/async, error semantics).

**WP shape:** Composition layer (controller, orchestrator, workflow) calling
existing pieces.

**Testing:** Integration tests proving the composition; unit tests on the
composition logic itself.

**Risk:** Low-Medium. Risk lives in the composition contracts, not the
composed pieces.

### 3. Extend

**Definition:** Add behaviour through a *documented extension point* —
factory, registry, plugin system, abstract base class, hook.

**Priority:** Third. Requires an extension point to exist; if none does,
escalate to REORGANISE first (Refactor to create a clean extension point)
or Create.

**Code intelligence needed:** Extension point catalogue; the extension's
contract.

**WP shape:** New module(s) implementing the extension's contract;
registration with the extension point.

**Testing:** Unit tests on the new extension; integration test verifying
the extension is invoked correctly.

**Risk:** Low if the extension point is clean. Higher if the extension
point itself is poorly designed (escalate).

### 4. Generate

**Definition:** Emit code from a schema, template, or specification. The
generated code is a *byproduct*; the source of truth is the schema.

**Priority:** Fourth. When a schema exists or is justified, prefer this over
hand-written Create.

**Code intelligence needed:** Existing generators; the schema language.

**WP shape:** Change is to the schema/template; generated files are not
hand-edited.

**Testing:** Tests run against the generated output; schema-level tests
where applicable.

**Risk:** Medium. Generator bugs propagate to every emission; schema changes
have wide blast radius.

### 5. Create

**Definition:** Net-new module, capability, or surface. Hand-written, not
generated.

**This explicitly includes implementing a new adapter for a domain-owned
port (Cockburn's hexagonal architecture).** Writing `StripePaymentGateway`
to implement the `PaymentGateway` port is Create, not Wrap — the adapter
is fresh code satisfying a contract the domain defined. See "Ports &
Adapters vs Wrappers" under primitive 14 for the load-bearing distinction.

**Priority:** Last resort *for new domain capability*. For adapters of
existing ports, Create is the normal move and runs at the priority of
whatever called for the adapter (typically following Reuse/Compose/Extend
considerations on the *domain* side).

**Code intelligence needed:** Convention map (so the new code matches
codebase idioms); confirmation nothing equivalent exists; for adapters,
the port's interface definition.

**WP shape:** Standard TDD cycle (Red-Green-Blue per RGB standard).
Adapter Creates have an additional sub-checklist: contract test for the
port must pass against the new adapter.

**Testing:** Standard new-code TDD. For adapters, the port's contract test
suite runs against the new adapter (per MECE-3 Proof pillar).

**Risk:** Medium (greenfield within brownfield). Risk of parallel
implementation if Reuse/Compose were inadequately considered. For
adapters, low risk if the port is well-defined.

---

## REORGANISE (6 primitives) — restructuring without behaviour change

Priority order: least disruptive first. **All REORGANISE primitives require
characterisation tests before the change** — the test proves behaviour is
preserved across the move.

### 6. Move

**Definition:** Relocate code from one module/location to another for better
cohesion. No surface change; no caller change beyond import path.

**Priority:** First within REORGANISE.

**Code intelligence needed:** Import graph; cohesion analysis.

**WP shape:** File moves + import-path updates.

**Testing:** Characterisation test for the moved unit, run before and after.

**Risk:** Medium (import churn; merge conflicts).

### 7. Refactor

**Definition:** General restructuring that preserves observable behaviour —
rename, extract function, simplify conditional, restructure data, etc.
Encompasses Fowler's mechanism-level refactorings as a single architectural
primitive.

**Priority:** Second within REORGANISE.

**Code intelligence needed:** Coupling/hotspot map (high-coupling areas need
extra care); test coverage status.

**WP shape:** In-place restructuring under a characterisation test.

**Testing:** **Characterisation test in Red (MUST)** — written before any
restructuring. Green confirms behaviour preserved. Blue is the refactor
itself plus any opportunistic cleanup.

**Risk:** Medium-High. Refactor without characterisation tests is reckless.

### 8. Inline

**Definition:** Fold a premature or no-longer-justified abstraction back into
its caller(s). Opposite of Abstract.

**Priority:** Third within REORGANISE.

**Code intelligence needed:** Consumer count of the abstraction; whether
the abstraction is "earning" its cost.

**WP shape:** Replace the indirection with the inlined content; delete the
abstraction.

**Testing:** Characterisation test on each consumer.

**Risk:** Low if consumer count is 1-2; rises with each consumer.

### 9. Merge

**Definition:** Combine two related modules that have over-fragmented.
Opposite of Decompose.

**Priority:** Fourth within REORGANISE.

**Code intelligence needed:** Cohesion analysis (do these modules share
state, callers, or vocabulary?).

**WP shape:** Combined module replacing the two originals; import-path
updates.

**Testing:** Characterisation tests covering both original modules' surfaces.

**Risk:** Medium.

### 10. Decompose

**Definition:** Split an oversized, mixed-concern, or god-class unit into
smaller cohesive ones.

**Priority:** Fifth within REORGANISE.

**Code intelligence needed:** God-class / feature-envy / shotgun-surgery
detection; method clustering analysis.

**WP shape:** New module(s) carved out of the original; original retained
as a thin facade or deleted.

**Testing:** Characterisation tests on each carved-out concern.

**Risk:** High. Breaks existing imports; risk of accidental behaviour change
during the split.

### 11. Abstract

**Definition:** Extract a pattern appearing N+ times into a shared primitive
(function, class, module). Inverse of Inline.

**Priority:** Last within REORGANISE — premature abstraction is a tax on
every future change.

**Code intelligence needed:** Pattern detection; consumer-count threshold
(typically 3+ near-identical implementations justify extraction).

**WP shape:** New shared primitive; replace each duplicate with a call to it.

**Testing:** Characterisation test on each call site; unit tests on the new
primitive.

**Risk:** Medium. Wrong abstraction is worse than no abstraction.

---

## SUBSTITUTE (3 primitives) — changing implementation behind a preserved surface

**Cardinal rule for this group:** *Before any SUBSTITUTE, check whether
REORGANISE (Refactor / Move / Decompose) achieves the goal instead.* If the
subject is internal code, prefer REORGANISE. SUBSTITUTE is reserved for
genuine implementation swaps and for boundaries with external systems.

### 12. Replace

**Definition:** Swap one implementation for another behind a stable
interface. The old implementation is **deleted**, not preserved behind a
wrapper.

**Priority:** First within SUBSTITUTE when the subject is internal.

**Code intelligence needed:** The existing interface; equivalence-test
feasibility; consumer list (all must be exercised by tests).

**WP shape:** New implementation behind existing interface; old
implementation deleted (or scheduled for delete via Strangle).

**Testing:** **Equivalence tests (MUST)** — same inputs produce same outputs
on old and new before the cutover; standard tests after.

**Risk:** Medium-High. Equivalence is hard to prove for stateful or
side-effecting systems.

### 13. Strangle (Fowler's Strangler Fig)

**Definition:** Gradually replace a legacy implementation through routed
calls — the new implementation handles some traffic, the old handles the
rest, the routing layer shrinks the old over time until it's deleted.

**Priority:** Second within SUBSTITUTE. Use when Replace is too risky to
do in one move (large legacy, multiple consumers, partial migration
needed).

**Code intelligence needed:** The legacy's surface and consumers; the
routing layer.

**WP shape:** Sequence of WPs: introduce routing; build new implementation
alongside; migrate traffic incrementally; **Delete legacy at the end**.

**Testing:** Per-route equivalence tests; integration tests on the routing.

**Risk:** Medium. The risk is in the *completion* — many Strangles get
stuck partway and become permanent wrapper rot. **A Strangle WP without a
recorded `removal_plan` and target date is a bug.**

### 14. Wrap

**Definition:** Interpose a translation layer over an *existing* interface
that survives the operation. The wrap exposes a different shape than the
underlying; it adds no new domain capability — it only translates.

**This is NOT the same as building an adapter for a port.** See "Ports &
Adapters vs Wrappers" immediately below — that distinction is load-bearing
and gets its own subsection.

**Priority:** Last within SUBSTITUTE — and conditional. **Permitted only
when one of two conditions holds:**

- **(a) External subject:** The wrapped component is external (vendor SDK,
  third-party API, kernel call, code you don't own and cannot modify).
- **(b) Transitional within Strangle:** The wrap is an explicit step in a
  Strangle workflow, with a recorded `removal_plan` and target date.

**Never permitted** as a permanent layer over internal code that could
have been Refactored, Replaced, or Decomposed. See "No Band-Aid Wrappers"
below.

**Code intelligence needed:** External-vs-internal classification of the
subject; existing wrapper count (wrapper rot detection).

**WP shape:** Translation module with explicit `subject_ownership` and
`justification` in WP frontmatter.

**Testing:** Contract tests on the wrapper's exposed interface; integration
tests against the wrapped subject.

**Risk:** Low when used correctly; **catastrophic when used as a band-aid**
— each layer adds cognitive cost and defers the real fix.

---

### Ports & Adapters vs Wrappers — the load-bearing distinction

The Cockburn / hexagonal-architecture "Ports and Adapters" pattern is the
**preferred** way to handle boundaries with external systems and to keep
the domain testable. SEA's MECE-3 Form pillar assumes it
(`references/mece-3-architecture.md` MEA-01: *"the domain receives
capabilities through ports (interfaces defined by the domain) and adapters
(implementations defined by infrastructure)."*). Implementing a new adapter
for a domain-owned port is a normal, frequent architectural move.

**That move is `EXPAND-Create`, not `SUBSTITUTE-Wrap`.**

The distinction:

| Aspect | Port + Adapter (EXPAND-Create) | Wrapper (SUBSTITUTE-Wrap) |
|---|---|---|
| **Whose interface is the public one?** | Domain owns the port interface (defined inside the domain) | External system owns the interface (defined outside the codebase or in legacy code) |
| **Direction of dependency** | Adapter depends inward on the port | Wrapper depends on whatever it wraps |
| **Behaviour of the new code** | Implements a contract the domain defined; may internally call an external SDK as one option | Translates between two existing interfaces; adds no new domain logic |
| **What gets created** | A new adapter satisfying a port — code that lives in `infrastructure/` and may call an external service | A translation layer over a survival surface — code that exists *to make calling something easier* |
| **Survival of the underlying** | The external service is still there but the domain only knows the port | The wrapped thing remains in place, unchanged, behind the wrapper |
| **Primary primitive** | `EXPAND-Create` | `SUBSTITUTE-Wrap` |

**Concrete examples:**

| Example | Primitive | Why |
|---|---|---|
| Domain has port `PaymentGateway`. You implement `StripePaymentGateway` that calls Stripe's SDK directly. | EXPAND-Create | You're creating an adapter for a domain-owned port. The Stripe SDK is called *inside* the adapter; it isn't wrapped at the architecture level. |
| Domain has port `Logger`. You implement `PinoLogger` that uses pino. | EXPAND-Create | Same — adapter for a domain-owned port. |
| `OrderService` exists internally with an awkward API. You write `OrderServiceV2` that translates to a friendlier shape. | SUBSTITUTE-Wrap, internal subject → **REJECT.** Refactor `OrderService` directly. |
| Stripe SDK is awkward. You write a `stripe-sdk-friendly.ts` thin layer to make it easier to call from your adapter. | SUBSTITUTE-Wrap, external subject → permitted, but ask: do you actually need this, or can the adapter just call Stripe directly? If the adapter is your boundary, the "friendly layer" is often redundant. |
| Anti-Corruption Layer (DDD) between two internal bounded contexts. | Composite, primary primitive depends on intent: usually `EXPAND-Create` for the ACL's translation logic, NOT `SUBSTITUTE-Wrap`. The ACL is itself an adapter — it implements a port in your bounded context that internally converts to the other context's vocabulary. |

**The discriminator question:**

> *"Whose interface is the public face of this new code — mine or someone
> else's?"*

- **Mine** (the port I just defined, or a port that already exists in my
  domain): `EXPAND-Create` — you're writing an adapter.
- **Someone else's** (the external service's, or the legacy module's that
  I'm not touching): `SUBSTITUTE-Wrap` — and it had better be external or
  transitional.

When in doubt, look at the dependency direction. Adapters depend *inward*
toward the domain — Robert Martin's "Dependency Rule." Wrappers depend
*outward* toward whatever they wrap.

---

## CONTRACT (2 primitives) — removing code

Priority: **always Deprecate before Delete** for production code.

### 15. Deprecate

**Definition:** Mark code or behaviour for future removal. Add deprecation
warning. Document migration path for consumers.

**Priority:** First within CONTRACT. Always precedes Delete unless the
subject has zero consumers and is in non-production paths.

**Code intelligence needed:** Consumer list; deprecation-warning mechanism
used in this codebase.

**WP shape:** Add deprecation annotation; emit warning on use; document
replacement; do **not** remove yet.

**Testing:** Tests asserting the deprecation warning fires.

**Risk:** Low. The behaviour is preserved.

### 16. Delete

**Definition:** Remove dead, obsolete, deprecated, or duplicate code.

**Priority:** Last within CONTRACT. Permitted when:

- Consumer count is zero, OR
- Deprecation period has elapsed and consumers have migrated, OR
- The code is genuinely dead (no path reaches it)

**Code intelligence needed:** Consumer-count verification; dead-code
detection.

**WP shape:** File/function/class deletion; reference cleanup.

**Testing:** Test suite passes after deletion. Coverage drops on deleted
code, which is fine.

**Risk:** Low when truly dead; **high** when removal turns out to break a
non-obvious consumer (production caller, dynamic dispatch, reflection).

---

## REINFORCE (6 primitives) — adding cross-cutting concerns

These run orthogonally — they can combine with any core primitive (a Create
that also Instruments, a Refactor that also Hardens). Priority: foundations
first.

### 17. Test

**Definition:** Add or backfill tests. Characterisation tests (Beck) before
Refactor; contract tests on ports; integration tests against real
adapters; chaos tests for resilience primitives.

**Priority:** First within REINFORCE. **MUST precede any Refactor on
untested code.**

**WP shape:** New test files; existing module unchanged.

**Risk:** Lowest of any primitive.

### 18. Instrument

**Definition:** Add observability — OpenTelemetry spans, structured logs
with `trace_id`, RED metrics on operations, USE metrics on resources.

**Priority:** Second within REINFORCE.

**WP shape:** Instrumentation added in-place; existing behaviour unchanged.

**Risk:** Low. Risk mostly in observability cardinality / cost.

### 19. Secure

**Definition:** Add authentication, authorisation, audit logging, redaction,
or other security controls.

**Priority:** Third within REINFORCE.

**WP shape:** Security middleware / interceptor / decorator added; existing
business logic unchanged.

**Risk:** Medium. Wrong security policy can lock out legitimate consumers.

### 20. Harden

**Definition:** Add resilience — timeouts, retries with backoff/jitter,
circuit breakers, bulkheads, idempotent receivers. SEA's existing
brownfield specialty (see `references/hardening-deltas.md`).

**Priority:** Fourth within REINFORCE.

**WP shape:** Resilience policy wrapped around external dependencies;
existing call sites unchanged.

**Risk:** Medium. Hardening can mask underlying bugs (a retry on an
idempotency violation papers over a bigger problem).

### 21. Gate

**Definition:** Wrap new behaviour behind a feature flag for controlled
rollout — percentage rollout, user-segment targeting, kill-switch on
incident.

**Priority:** Fifth within REINFORCE.

**WP shape:** Feature-flag check around the new path; both old and new
paths coexist until the flag is removed.

**Risk:** Low operationally; **medium cognitively** — flagged code is
harder to reason about; flags must have a removal plan.

### 22. Document

**Definition:** Add or improve in-code or external documentation —
docstrings, READMEs, architecture diagrams, runbooks.

**Priority:** Last within REINFORCE.

**WP shape:** Documentation files added; runtime behaviour unchanged.

**Risk:** Lowest. (Stale documentation is worse than no documentation, but
that's a maintenance concern, not a change-time concern.)

---

## Cross-Group Decision Priority

The design walk for any new component or capability. Walk in this order:

```
1. Can I REUSE existing code?              (EXPAND-Reuse)
2. Can I COMPOSE existing pieces?           (EXPAND-Compose)
3. Can I EXTEND through an extension point? (EXPAND-Extend)
4. ✱ Before any Wrap/Adapt over internal:
   try REORGANISE (Refactor / Move / Decompose) instead
                                            (REORGANISE-any)
5. Should I REPLACE rather than wrap?       (SUBSTITUTE-Replace)
6. Do I need to STRANGLE (gradual replace)? (SUBSTITUTE-Strangle)
7. Wrap (only if subject is external or transitional within Strangle)
                                            (SUBSTITUTE-Wrap)
8. Should I CONTRACT (deprecate, then delete)?
                                            (CONTRACT-any)
9. Must I GENERATE / CREATE net-new?        (EXPAND-Generate / EXPAND-Create)

REINFORCE runs orthogonally on top of any of the above.
```

The asterisk at step 4 is the **load-bearing addition** that enforces "No
Band-Aid Wrappers" (below).

---

## MUST Rules

### No Band-Aid Wrappers (MUST)

When a change would interpose a Wrap, Bridge, Facade, Anti-Corruption Layer,
or Adapter over **internal** code, you MUST first justify why REORGANISE
(Refactor / Move / Decompose) is not the correct primitive.

If the underlying code has structural problems, fix them — do not wrap them.
Wrap is reserved for:

- External subjects you do not own (vendor SDKs, third-party APIs, kernel
  boundaries, OS facilities)
- Explicit transitional steps inside a Strangle, with a recorded
  `removal_plan` and target date

Permanent wrappers around internal code defer the work without paying it
down. They compound — each additional wrapper costs the same as the
original Refactor would have, and the cumulative cognitive cost is the
sum of all of them.

### Characterisation Tests Before Refactor (MUST)

No REORGANISE primitive (Move, Refactor, Inline, Merge, Decompose, Abstract)
runs without a characterisation test in the WP's Red. The test asserts the
current observable behaviour. Green confirms the behaviour survives the
restructuring. This is Kent Beck's discipline applied at the WP level.

If a characterisation test cannot be written for the subject (deeply
intertwined state, no clear input/output surface), the work is not yet
Refactor — it's Test, then Refactor as a separate WP.

### Strangle Has a Recorded Removal Plan (MUST)

Every Strangle workflow records, at the start, the milestone or date by
which the legacy will be deleted. A Strangle that never completes is
permanent wrapper rot dressed up.

### Deprecate Before Delete in Production Paths (MUST)

Code reachable from production cannot be Deleted without first being
Deprecated, unless the change is internal to a single team's codebase
with explicit acknowledgement.

---

## Anti-Patterns

### Wrapper Rot

**Detection:** Multiple successive wrappers on the same internal subject —
two or more "compatibility layers" / "v2 adapters" / "modernised facades"
around the same underlying module.

**SEA behaviour:** When proposing a new Wrap, check the existing code for
prior wrappers on the same subject. If found, escalate to the user:

> "`OrderService` already has 2 wrappers: `OrderServiceV2`,
> `OrderServiceFacade`. Adding a third defers the real fix. Recommendation:
> Refactor `OrderService` directly, or Replace with a new implementation and
> Delete the existing wrappers. Proceed with Wrap anyway? (Y/N)"

Wrapper rot detection is a requirement for `/sulis:analyse-codebase` (v0.7.0).

### Premature Abstraction

**Detection:** Abstract is proposed with consumer-count < 3, or for a
pattern that hasn't appeared often enough to know its real shape.

**SEA behaviour:** Default consumer-count threshold for Abstract is 3
near-identical implementations. Below that, propose Reuse or Move instead.

### Stuck Strangle

**Detection:** A Strangle in flight for longer than its planned
`removal_plan` date, with the legacy still present.

**SEA behaviour:** `verify` flags any Strangle WP whose `removal_plan` date
is past and whose legacy subject still exists.

### Quota-Driven ADRs

**Detection:** ADRs produced because "the template said so" rather than
because the decision was non-trivial.

**SEA behaviour:** ADR count is *emergent* per right-sizing.md, not
prescriptive. The Sizing Report flags ADR count > tier maximum and
requires justification.

### Speculative Chaos Tests

**Detection:** A chaos test in the Proof section without a corresponding
NFR or MUC.

**SEA behaviour:** Each chaos test must reference a specific NFR or MUC
it defends. Unreferenced chaos tests are dropped.

---

## Composite Primitives

Some changes are composites of multiple primitives. They are explicitly
noted with a primary primitive plus a `composite_of` list in WP frontmatter.

| Composite | Recipe | Primary |
|---|---|---|
| **Migrate** (data, framework, language) | Create new + Strangle old + Delete old (over time) | Strangle |
| **Encapsulate** (narrow public surface) | Refactor + Move + Wrap | Refactor |
| **Expose** (widen public surface) | Move + Wrap | Move |
| **Branch by Abstraction** (Fowler) | Abstract → Create → Replace → (optionally Inline) | Replace |
| **Rename** | Refactor (Fowler-style) | Refactor |
| **Configure** (extract to config) | Move + Create (config schema) | Move |
| **Externalise** (in-code to data) | Move + Create | Move |

WP frontmatter for a composite:

```yaml
primitive: replace
composite_of: [abstract, create, replace, inline]
target: lib/payments/PaymentGateway
```

Single source of truth — the primary primitive drives the WP shape — with
the composite recipe recorded for transparency.

---

## WP Frontmatter Encoding

Every Work Package includes:

```yaml
primitive: <one of the 22>             # required
group: <expand|reorganise|substitute|contract|reinforce>  # derived, but recorded for clarity
composite_of: [<primitive>, ...]       # optional — when the WP is composite

# Required for SUBSTITUTE-Wrap:
subject_ownership: <external|transitional>
justification: "<why Wrap is the right primitive — must satisfy condition (a) or (b)>"
removal_plan: <null if external | target milestone/date if transitional>

# Required for SUBSTITUTE-Strangle:
removal_plan: "<milestone/date for legacy deletion>"

# Required for REORGANISE primitives:
characterisation_test: "<path to the test file proving behaviour preserved>"
```

---

## MECE Check

### Mutually exclusive

The primary-intent rule resolves apparent overlaps:

| Apparent overlap | Primary intent | Resolution |
|---|---|---|
| Wrap (changes structure AND interposes new code) | Change implementation behind a preserved surface | SUBSTITUTE |
| Extract config (Move AND Create new config surface) | Relocate; surface is incidental | REORGANISE-Move (or EXPAND-Create if config schema is new) |
| Encapsulate (Refactor + Move + Wrap) | Narrow public surface | Composite, primary REORGANISE-Refactor |
| Add a test before refactoring | Foundation work | REINFORCE-Test |
| Wrap around vendor SDK | Translation over external | SUBSTITUTE-Wrap, `subject_ownership: external` |
| Branch by Abstraction | Composite | primary SUBSTITUTE-Replace, `composite_of: [abstract, create, replace, inline]` |

### Collectively exhaustive

Stress tests against the 22:

| Hypothetical change | Where it lands |
|---|---|
| Rename a class | REORGANISE-Refactor |
| Add a new endpoint | EXPAND-Extend (controller framework) or EXPAND-Create |
| Add OpenTelemetry spans | REINFORCE-Instrument |
| Replace Postgres with MySQL | SUBSTITUTE-Replace |
| Remove deprecated API | CONTRACT-Delete (after CONTRACT-Deprecate) |
| Add a feature flag | REINFORCE-Gate |
| Split a god-class | REORGANISE-Decompose |
| Combine two trivially-different files | REORGANISE-Merge |
| Hide internal helpers | Composite, primary REORGANISE-Refactor |
| Write a build script | EXPAND-Create |
| Generate types from JSON Schema | EXPAND-Generate |
| Add a docstring | REINFORCE-Document |
| Refactor `OrderService` after writing characterisation tests | REINFORCE-Test (one WP), then REORGANISE-Refactor (next WP) |

If a change genuinely doesn't fit, it is a composite. Record the recipe.

---

## How Other Skills Use This Standard

**`/sulis:draft-architecture`** — computes a primitive distribution for the proposed
TDD's components; surfaces wrap audit in the pre-write announcement.

**`/sulis:codebase-audit`** — uses primitive vocabulary in audit findings
("Module X is a candidate for REORGANISE-Decompose; severity high").

**`/sulis:plan-work`** — assigns a primitive to every WP; produces the WP
INDEX with primitive distribution summary; runs the wrap audit.

**`/sulis:harden-codebase`** — implements REINFORCE-Harden primarily; may compose with
other primitives per delta.

**`/sulis:verify-architecture`** — enforces the MUST rules: No Band-Aid Wrappers,
Characterisation Tests Before Refactor, Strangle Removal Plan, Deprecate
Before Delete.

**`/sulis:analyse-codebase`** (v0.7.0) — code intelligence supports primitive selection:
extension points, reusable abstractions, wrapper rot, coupling/hotspot map.

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| 0.6.0 | 2026-05-14 | Initial catalogue. 22 primitives in 5 MECE groups (Expand, Reorganise, Substitute, Contract, Reinforce). Minto-pyramid structured. Cross-group decision walk with wrap-elimination step at position 4. Four MUST rules (No Band-Aid Wrappers, Characterisation Tests Before Refactor, Strangle Removal Plan, Deprecate Before Delete). Four anti-patterns (Wrapper Rot, Premature Abstraction, Stuck Strangle, Quota-Driven ADRs, Speculative Chaos Tests). Composite primitives table. Provenance: Fowler, Beck, Lehman & Belady, Evans, GoF, Minto. |
