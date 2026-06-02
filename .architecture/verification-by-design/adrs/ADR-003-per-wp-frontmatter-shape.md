---
id: ADR-003
title: Per-WP `verification:` field is a structured YAML map (three shapes)
status: accepted
change_id: 01KT2BPBFESCCDY8F7Y5M8RN4R
date: 2026-06-01
resolves: SRD Open Question 3
---

# ADR-003 — Per-WP `verification:` field is a structured YAML map (three shapes)

## Decision

Every Work Package frontmatter emitted by `/sulis:plan-work` after this
refinement carries a `verification:` field. The field's value is a
**structured YAML map** in exactly one of three canonical shapes:

### Shape 1 — Concrete (the common case)

```yaml
verification:
  adapter: backend
  artifact: tests/api/test_orders.py::test_post_creates_order
```

- `adapter`: one of the seven canonical kinds (see ADR-007 and
  `VERIFICATION_QUESTIONS.md`).
- `artifact`: a stable test-artifact reference. Format depends on the
  adapter — for backend, a pytest nodeid path; for frontend, a Vitest
  / Playwright spec ref; for methodology, a fixture path under
  `tests/methodology/`. The schema is per-adapter and documented in
  `VERIFICATION_QUESTIONS.md`'s adapter table.

Optional `additional-adapters:` array for WPs spanning multiple
adapters:

```yaml
verification:
  adapter: backend
  additional-adapters: [contract]
  artifact: tests/api/test_orders.py::test_post_creates_order_with_idempotency_header
```

### Shape 2 — Deferred

```yaml
verification:
  adapter: backend
  deferred-to-follow-on: recording-mock-sendgrid
```

- `adapter` still names the adapter (so the slice-end scan knows which
  taxonomy it is) — but the artifact does not yet exist, and the WP
  ships pre-infrastructure.
- `deferred-to-follow-on` carries the canonical need identifier per
  FR-011. The slice-end review reads this field to aggregate.

### Shape 3 — Trivial carveout

```yaml
verification:
  na: true
  justification: "trivial-change carveout (CW-05): comment-only edit in changeset.py docstring; no behaviour change"
```

- `na: true` is the explicit positive opt-out signal.
- `justification` is required; the rubric fails if it is missing,
  empty, or shorter than 30 substantive characters (mirrors the
  Verification Plan section's placeholder rejection).

## Context

SRD Open Question 3 surfaced three sub-shapes (single string, single
map, structured map with alternatives). The structured-map shape is the
one FR-005 already specifies, but the open question was *should it be
locked as the schema*. Two design constraints make this answer obvious:

1. **Three distinct meanings need three distinct shapes.** Shape 1
   is "we have a test"; Shape 2 is "we know what's needed but it's
   deferred"; Shape 3 is "this WP is a carveout". A single-string
   field can't express all three without ambiguity ("n/a" could mean
   either deferred or carveout).
2. **Machine-readable for the slice-end scan.** FR-012's auto-draft
   trigger requires the slice-end scan to programmatically distinguish
   deferred entries from concrete ones. YAML map with a stable key
   (`deferred-to-follow-on:`) is the cleanest contract.

## Alternatives considered

1. **Single string field, e.g. `verification: backend/tests/api/test_orders.py::test_post`
   (rejected).** Cannot express the deferred case (a slug like
   `deferred:recording-mock-sendgrid` is ad-hoc and not machine-stable
   against future format changes). Cannot express trivial carveout
   without overloading the string.

2. **Two separate fields — `verification-adapter:` + `verification-artifact:`
   (rejected).** Increases the surface (two fields to validate), and
   forces every WP to set both even when one is irrelevant (trivial
   carveout). Decisions like "WP touches both backend AND contract"
   can't be expressed without a third field.

3. **JSON inline string, e.g. `verification: '{"adapter":"backend",…}'`
   (rejected).** YAML is the WP's frontmatter format; introducing
   embedded JSON would force every consumer to parse twice. Readability
   collapses for the founder.

## Consequences

**Positive.**
- One field, three shapes — explicit and discriminable. The rubric's
  validation logic is a small finite state machine (look for `na:` →
  trivial; look for `deferred-to-follow-on:` → deferred; otherwise
  concrete).
- Slice-end scan is a simple YAML parse + dict lookup, no string
  munging.
- All three shapes are founder-readable (`na: true` reads as plain
  English; `adapter: backend` is the adapter name; `artifact:
  <path>` is a test path).

**Negative.**
- Three shapes means three code paths in the validator. Mitigated by
  exhaustively-typed fixtures (one per shape, asserted in WP-007).
- Discriminating keys (`na:`, `deferred-to-follow-on:`) are
  load-bearing — if the validator misses one, a wrong shape passes.
  Mitigated by P-VER's failure-mode test fixtures (FR-009 acceptance
  criterion 3).

**Neutral.**
- Schema can extend later (e.g., `verification-evidence:` for citing
  the test's actual passing-output) without breaking existing shapes.
