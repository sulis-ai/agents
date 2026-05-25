# Red-Green-Blue Cycle Standard

<!-- summary -->
Red-Green-Blue is SEA's variant of the classical TDD cycle, adapted for
production-grade work packages. **Red** writes failing tests including
hardening/chaos assertions. **Green** makes them pass with "boring code" —
explicit, type-safe, and free of hidden state. **Blue** refactors with all
tests still green, extracting shared primitives. Every Work Package's Definition
of Done references this cycle. The cycle is mandatory; the REFACTOR (Blue) step
is not optional — it is where shared primitives are identified and extracted.
<!-- /summary -->

> **Version:** 0.1.0
> **Status:** Active — Calibration Period

---

## Provenance

Red-Green-Blue extends the classical TDD cycle (Beck, 2002) and the
Red-Green-Refactor discipline (Fowler). The addition is the inclusion of
**hardening assertions in Red** — fault-injection and chaos tests are written
as failing tests up front, alongside functional ones. This pulls the operational
hardening pillar of [[mece-3-architecture]] forward into the test-first loop
rather than treating it as a post-implementation concern.

This is practitioner knowledge, not peer-reviewed research.

---

## Severity Convention

| Severity | Meaning |
|----------|---------|
| **MUST** | Non-negotiable. Violations block delivery. |
| **SHOULD** | Default. Deviation requires explicit justification in the Work Package. |

---

## The Cycle

### RGB-01: Red — Define failure, including hardening

**Severity:** MUST

Before writing any implementation code, write the failing tests. Tests are
written at three levels, all in Red:

1. **Functional failing tests** — assert the happy-path behaviour the Contract
   promises. These fail because the implementation does not yet exist.
2. **Edge-case failing tests** — assert behaviour at boundaries (empty input,
   maximum size, null fields, concurrent access).
3. **Hardening failing tests** — assert resiliency, security, and observability
   behaviour. Examples:
   - "Given downstream returns 5s latency, request times out at 2s"
   - "Given downstream returns 500 N times, circuit opens after N+1th call"
   - "Given a request, a trace span is emitted with `operation.name` attribute"
   - "Given an unauthenticated caller, the endpoint returns 401, not 200"

All three layers exist before any production code is written. The implementation
target is *all* failing tests, not just the functional ones.

| Attribute | Detail |
|-----------|--------|
| **In Practice** | Each Work Package's Red section lists every failing test by name. Hardening tests use fault injection (testcontainers with toxiproxy, mocked clock for retries) rather than relying on production observation. |
| **Anti-Pattern** | Writing only the functional failing test in Red and "adding chaos tests later". Tests passing on first run (means they weren't actually written first). |
| **How to verify** | Git history shows test commits preceding implementation commits. Each Work Package's Red checklist enumerates failing tests by file:test_name. |

### RGB-02: Green — Boring code makes the tests pass

**Severity:** MUST

Write the simplest implementation that makes the failing tests pass. The
"simplest" implementation in SEA's frame is **boring code** — see
[[boring-code]]. Boring beats clever. Explicit beats implicit. Type-safe
beats dynamic.

| Attribute | Detail |
|-----------|--------|
| **In Practice** | Implementation is the most direct path from input to assertion. No premature abstraction. No "framework" written before there are three concrete cases. Types are declared explicitly at every public surface; inference is allowed only for local variables. |
| **Anti-Pattern** | Writing a generic factory in Green because "we might need it for the next WP". Using reflection or metaprogramming because it shortens the implementation. Implementing more than the failing tests require. |
| **How to verify** | Every failing test in Red is now passing. Coverage on the new code is ≥90% (because tests were written first). The implementation contains no code that is not exercised by a Red test. |

### RGB-03: Blue — Refactor with all tests green

**Severity:** MUST

Once Green is achieved, refactor. This step is **not optional**. Blue is where
shared primitives are extracted, duplication is removed, names are improved,
and the design is paid down.

Blue is bounded: refactoring stays within the file(s) touched by this Work
Package. Cross-file refactors that emerge during Blue are captured as separate
Work Packages, not pursued mid-stream (per EP-07 boy-scout scope rule in
CLAUDE.md).

| Attribute | Detail |
|-----------|--------|
| **In Practice** | Look for duplication between this WP's code and existing code (per EP-03). If two or more components implement the same pattern, extract the shared primitive — within the file scope. Improve names. Remove dead code introduced during Green. |
| **Anti-Pattern** | Skipping Blue because "it works". Refactoring across many files in a single WP (creates merge conflicts; violates Sequence ID discipline). Adding new behaviour during Blue (Blue is structural; behavioural change requires a new Red). |
| **How to verify** | The Blue checklist in the Work Package is ticked. All tests still pass after Blue. The diff for Blue contains no test changes (only structural code changes). |

---

## How Red-Green-Blue Integrates with MECE-3

The three pillars of [[mece-3-architecture]] each map to a stage of the cycle:

| Pillar | Where it lives in RGB |
|---|---|
| **Form** (Structural Integrity) | Designed up front in the TDD; refined in **Blue** through primitive extraction. |
| **Armor** (Operational Hardening) | Asserted as failing tests in **Red**; implemented in **Green**. |
| **Proof** (Verification Protocol) | Every failing test in **Red** is the Proof. Contract tests, integration tests, and chaos tests are all "Red tests" that turn Green. |

Hardening is not a phase that comes after building. It is encoded as Red tests
that drive Green implementation.

---

## Work Package DoD Template

Every Work Package's Definition of Done has three sub-sections that mirror the cycle:

```markdown
## Definition of Done

### Red — Failing tests written
- [ ] `tests/order.test.ts::creates_order_with_valid_input` — functional happy path
- [ ] `tests/order.test.ts::rejects_negative_quantity` — edge case
- [ ] `tests/order.test.ts::times_out_after_2s_on_slow_payments` — hardening (timeout)
- [ ] `tests/order.test.ts::opens_circuit_after_5_payment_failures` — hardening (CB)
- [ ] `tests/order.test.ts::emits_otel_span_with_order_id` — hardening (observability)

### Green — Implementation makes tests pass
- [ ] All Red tests pass
- [ ] Implementation is "boring" per [[boring-code]] — explicit types, no hidden state
- [ ] Code coverage on new files ≥ 90%

### Blue — Refactor complete
- [ ] Duplication removed within the WP's file scope (EP-03)
- [ ] Shared primitives extracted where ≥2 instances exist
- [ ] All tests still pass after refactor
- [ ] No new behaviour introduced in Blue
```

---

## Gotchas

- **Skipping Blue compounds.** A WP that skips Blue leaves duplication that
  the next WP either inherits (cementing it) or has to extract retroactively
  (paying interest). Blue is mandatory.
- **Hardening tests are not optional in Red.** A WP that only asserts functional
  behaviour in Red is not done — it is missing the entire Armor pillar's tests.
- **Don't write hardening tests against production observation.** Use fault
  injection (toxiproxy, mock clock, chaos primitives) so the test is
  deterministic and runs in CI, not "we observed it fail in staging once".
- **Blue stays in scope.** Cross-file refactors discovered during Blue become
  new WPs in the queue. Following the rabbit hole breaks the Sequence ID
  contract and creates merge conflicts with other in-flight WPs.

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| 0.1.0 | 2026-05-12 | Initial standard. Codifies the three-stage cycle with hardening in Red and boring code in Green. |
