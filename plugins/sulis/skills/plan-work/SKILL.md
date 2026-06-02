---
name: plan-work
description: "Turns a blueprint into a to-do list of independent, shippable tasks."
---

# Decompose — TDD to Atomic Work Packages

When invoked, read the project's `TDD.md` and `PRIMITIVE_TREE.jsonld` and
produce one Work Package per atomic, parallelisable unit of work.

If arguments are provided, treat them as the project name. If not, infer
from the most recently modified folder in `.architecture/`.

If no TDD exists, stop and tell the user to run `/sulis:draft-architecture` first.

---

## What a Work Package Is

A Work Package (WP) is the **atomic unit of execution**. One execution agent
picks up one WP, implements it end-to-end, and merges. Other agents can be
working on parallel WPs simultaneously.

**Atomicity rules:**

1. A WP can be implemented without reading any other WP's content. The
   Context and Contract sections are sufficient.
2. A WP introduces exactly one logical capability or change. "Add the order
   creation port" is one WP. "Add the order creation port and the payment
   port" is two.
3. A WP's Definition of Done is verifiable in CI. There is a green/red signal.
4. A WP's changes do not collide with other WPs at the merge level — enforced
   by the Sequence ID `dependsOn` graph.

---

## What a Work Package Contains

```markdown
---
id: WP-007
title: Implement Postgres OrderRepository adapter
status: pending                  # MUST be `pending` for a new WP (L-03 canonical "ready to start"); add-wp rejects `todo`/`ready`. Later: in_progress | done | blocked
sequence_id: WP-007
dependsOn: [WP-001, WP-003]      # the domain entity and the port must exist first
blocks: [WP-012]                 # the application service uses this adapter
estimated_token_cost:
  input: 8k                      # rough budget for the executing agent
  output: 3k
tdd_section: 3.4 (Adapters)
adrs: [ADR-001]
verification:
  adapter: backend                              # MUST — one of the seven canonical kinds (see VERIFICATION_QUESTIONS.md)
  artifact: tests/infrastructure/persistence/postgres-order-repository.test.ts::respects_5s_transaction_timeout
---

## Context

What part of the architecture this WP touches. One paragraph. Link to the
TDD section and any relevant ADRs. Name the components from the
PRIMITIVE_TREE this WP advances.

## Contract

The exact interfaces, types, and ports this WP introduces or modifies.
Code-level signatures (not implementation).

```typescript
// domain/order/OrderRepository.ts (already exists — this WP implements it)
export interface OrderRepository {
  save(order: Order, idempotencyKey: IdempotencyKey): Promise<void>;
  findById(id: OrderId): Promise<Order | null>;
}

// infrastructure/persistence/PostgresOrderRepository.ts (this WP creates)
export class PostgresOrderRepository implements OrderRepository { ... }
```

State invariants the contract must preserve:
- `save()` is idempotent on `(order.id, idempotencyKey)`.
- `findById()` never throws on not-found; returns `null`.
- `save()` honours the 5s transaction timeout from TDD section 4.1.

## Definition of Done

### Red — Failing tests written
- [ ] `tests/contracts/OrderRepositoryContract.ts::saves_and_retrieves_order` — applies to this adapter
- [ ] `tests/contracts/OrderRepositoryContract.ts::idempotent_save_returns_existing_on_duplicate_key`
- [ ] `tests/contracts/OrderRepositoryContract.ts::findById_returns_null_for_missing_id`
- [ ] `tests/infrastructure/persistence/postgres-order-repository.test.ts::respects_5s_transaction_timeout` (chaos: toxiproxy 6s latency on postgres)
- [ ] `tests/infrastructure/persistence/postgres-order-repository.test.ts::emits_otel_span_with_table_name_attribute`

### Green — Implementation makes tests pass
- [ ] All Red tests pass against ephemeral Postgres (testcontainers).
- [ ] In-memory adapter still passes the shared contract test (regression safety).
- [ ] Implementation follows `references/boring-code.md` — explicit types, no module-level state, no metaprogramming.
- [ ] Coverage on `PostgresOrderRepository.ts` ≥ 90%.

### Blue — Refactor complete
- [ ] Duplication between save/update paths removed (single internal `upsert`).
- [ ] Shared connection-acquisition logic extracted if a second adapter (in a later WP) will reuse it.
- [ ] No new behaviour introduced in Blue.
- [ ] All tests still green after refactor.

## Sequence

- **dependsOn:** WP-001 (`Order` entity exists), WP-003 (`OrderRepository` port exists)
- **blocks:** WP-012 (`CreateOrder` application service depends on this adapter)
- **Parallelisable with:** WP-008 (Payment adapter — different file scope, different test scope)

## Estimated Token Cost

- **Input:** ~8k (this WP + the two dependency WP outputs + relevant TDD section)
- **Output:** ~3k (implementation file + adapter test file + contract test additions)
- **Total:** ~11k

## Notes

- Use `pg` driver (already in package.json from WP-001 setup).
- The 5s transaction timeout is non-negotiable per NFR-04.
```

### Required frontmatter field — `verification:` (MUST)

Every WP frontmatter MUST carry a `verification:` field. The field is
a structured YAML map in exactly one of three canonical shapes per
`ADR-003` (the per-project ADR for the verification-by-design change;
see e.g. `.architecture/{project}/adrs/ADR-003-per-wp-frontmatter-shape.md`)
(see WP-Standard's `WP-04 Test plan` for the human-readable counterpart;
the `verification:` field is the machine-readable seam between the WP
and the behavioural test ledger per FR-015). The three shapes:

1. **Concrete** — the common case. `adapter:` + `artifact:` (a stable
   test-artifact reference, format per-adapter).

   ```yaml
   verification:
     adapter: backend
     artifact: tests/api/test_orders.py::test_post_creates_order
   ```

2. **Deferred** — `adapter:` + `deferred-to-follow-on:` carries the
   canonical need identifier (FR-011). The slice-end review reads this
   field to aggregate deferred infrastructure needs across the slice.

   ```yaml
   verification:
     adapter: backend
     deferred-to-follow-on: recording-mock-sendgrid
   ```

3. **Trivial carveout** — `na: true` with a `justification:` of at
   least 30 substantive characters. The justification is the explicit
   positive opt-out signal; bare `na: true` fails the rubric.

   ```yaml
   verification:
     na: true
     justification: "trivial-change carveout (CW-05): comment-only edit; no behaviour change"
   ```

The `adapter:` value MUST be one of the seven canonical kinds enumerated
in
[`VERIFICATION_QUESTIONS.md`](../../references/standards/VERIFICATION_QUESTIONS.md)
(the canonical kind → adapter source). For multi-adapter WPs, an
optional `additional-adapters:` array names the secondary adapters.
Empty / missing / malformed `verification:` fields are rejected by
P-VER failure mode 8.

---

## Required Reading (load before decomposing)

These standards shape the WP set's *shape*, not just the content:

- `../../references/standards/WORK_PACKAGE_STANDARD.md` — WP shape; the
  `kind:` enum (step 4a); cross-kind decomposition rules (WP-08.5).
- `../../references/standards/CONTRACT_FIRST_STANDARD.md` — when the WP set
  spans a producer/consumer seam, decompose contract-first (step 4b).
- `../../references/standards/WP_BACKEND_STANDARD.md` — per-kind execution
  doctrine for `kind: backend` WPs (the gates step 11 validates).
- `../../references/standards/WP_FRONTEND_STANDARD.md` — per-kind execution
  doctrine for `kind: frontend` WPs.
- `../../references/standards/UX_VISUAL_DESIGN_STANDARD.md` — UXD-14:
  frontend WPs `dependsOn` the visual contract (a design-time artifact,
  not its own WP).
- `../../references/change-primitives.md` — the change-primitive vocabulary
  step 3 still applies orthogonally to `kind`.

---

## Workflow

1. **Read inputs** — `TDD.md`, `PRIMITIVE_TREE.jsonld`, `SIZING.md`,
   `.context/{project}/INDEX.md`, any existing `HANDOVER.md` from SRD, any
   prior WPs. Plus the contract artifacts the design phase produced (the
   **data contract** for any seam, and the **visual contract** for any
   user-facing surface — see `draft-architecture`'s "Define the contracts"
   step). If a cross-kind TDD has no contract artifacts, **stop and route
   back to `draft-architecture`** to produce them (don't manufacture
   contracts during decomposition).
2. **Inventory** — list every component, port, adapter, and resilience
   primitive mentioned in the TDD. Each becomes a candidate WP.
3. **Assign primitive (MUST).** Per `references/change-primitives.md`,
   walk the cross-group decision priority for each candidate WP:
   ```
   1. Can I Reuse existing code?
   2. Can I Compose existing pieces?
   3. Can I Extend through an extension point?
   4. ✱ Before Wrap over internal: try Refactor/Move/Decompose instead
   5. Should I Replace rather than wrap?
   6. Do I need Strangle (gradual replace)?
   7. Wrap (only if subject is external or transitional in Strangle)
   8. Should I Contract (deprecate, then delete)?
   9. Must I Generate / Create net-new?
   REINFORCE runs orthogonally.
   ```
   
   **Ports & Adapters check (MUST).** Before assigning `wrap`, apply the
   discriminator question from `references/change-primitives.md`: *"Whose
   interface is the public face of this new code?"* If the WP creates a
   new module that implements a port defined inside the domain (e.g.
   `StripePaymentGateway implements PaymentGateway`), the primitive is
   **`create`** — you're writing an adapter, not wrapping. The Stripe SDK
   is called *by* the adapter; the adapter is not a wrapper at the
   architecture level. See "Ports & Adapters vs Wrappers" in the
   catalogue.
   
   Record the chosen primitive in WP frontmatter (`primitive:`, `group:`).
   For composites, record `composite_of:`. Apply mandatory fields per
   primitive:
   - **SUBSTITUTE-Wrap:** `subject_ownership` + `justification` + `removal_plan`
   - **SUBSTITUTE-Strangle:** `removal_plan` with target date
   - **REORGANISE-***: `characterisation_test` path
4. **Atomise** — for each candidate, ask: can this be implemented in one
   commit/PR by one agent? If no, split. Typical sizes:
   - One port definition + its contract test = 1 WP
   - One adapter implementing a port = 1 WP
   - One application service / use case = 1 WP
   - One observability primitive (e.g. "wire up OpenTelemetry") = 1 WP
   - One resilience policy (timeout + retry + CB for one dependency) = 1 WP

4a. **Assign `kind` (MUST).** Per
    `references/standards/WORK_PACKAGE_STANDARD.md` WP-01, every WP carries
    `kind:` ∈ `backend / frontend / async / docs / infra / contract /
    composite`. The kind dispatches the executor + the verification gates
    (WP-05) + the per-kind doctrine (`WP_BACKEND_STANDARD.md` /
    `WP_FRONTEND_STANDARD.md` / …). Decide kind by what the WP *touches*:
    - HTTP handlers, application services, ports, repository adapters,
      domain logic → `backend`
    - React/Vue/Alpine components, pages, layouts, state, frontend tests →
      `frontend`
    - Queue consumers/producers, scheduled jobs, message envelopes →
      `async`
    - Terraform, Dockerfiles, CI workflows, deploy config → `infra`
    - Docs/README/CHANGELOG/spec text only → `docs`
    - API/SDK schema artifacts (operations + types + errors + stubs) →
      `contract` (see step 4b)
    - Spans multiple kinds atomically (rare) → `composite` with child WPs
    Record in WP frontmatter (`kind:`).

4b. **Cross-kind detection + contract-first decomposition (MUST when
    cross-kind).** If the WP set spans a **producer/consumer seam**
    (backend + frontend, or tool + caller — i.e. ≥ 2 of {backend, frontend,
    async} touch the same operation surface), apply
    `references/standards/CONTRACT_FIRST_STANDARD.md` + `WORK_PACKAGE_STANDARD.md`
    WP-08.5:

    - **Emit a `kind: contract` WP first.** Its scope is the schema layer
      for the seam: operations + input/output types + the three error
      categories (Protocol / Expected / Internal per CF-03) + LLM-/dev-
      facing descriptions + **example stubs covering happy AND error AND
      empty cases** (CF-04). Gates per WP-05's contract row.
    - **Producer + consumer WPs `dependsOn` the contract WP — never each
      other.** Frontend `dependsOn: [WP-contract]`; it does **NOT**
      `dependsOn` the backend WP. Both build in parallel (CF-05 parallel-
      not-sequential) — the consumer against a mock generated from the
      contract.
    - **Emit an integration WP last.** `kind: composite` (or `kind: docs`
      with `produces: integration-check`) that `dependsOn` all the per-kind
      siblings and runs the conformance check (CF-07) — swap mock for real
      producer, validate against schema.
    - **User-facing surfaces require the visual-contract WP (MUST, #45).**
      `draft-architecture` emits a visual-contract WP (`kind: contract`,
      `contract_type: visual`, with `mockup:` + empty `signed_off_at`). Every
      `kind: frontend` WP MUST carry `visual_contract: <that WP id>` AND list
      it in `dependsOn` — so list-ready won't dispatch the frontend WP until
      the contract WP is `done`, and the contract WP only reaches `done` once
      the founder signs off the rendered mockup. This is enforced at the
      toolchain (`wpx-index` refuses a frontend WP without it, and refuses to
      flip an unsigned contract WP to `done`) — not just convention.
    - **Exempt:** single-kind non-visual WP sets, `--prototype` changes, and a
      frontend WP with a logged `visual_contract: exempt — <reason>`.

4d. **Set the `verification:` field per WP (MUST).** For every WP
    emitted, set the required `verification:` frontmatter field
    documented in "What a Work Package Contains" above. The setter
    procedure:

    1. **Read the change's `kind:`** from the change record (e.g.
       `.changes/{slug}.yaml`).
    2. **Resolve the adapter** by looking up the kind → adapter row
       in
       [`VERIFICATION_QUESTIONS.md`](../../references/standards/VERIFICATION_QUESTIONS.md)
       (the canonical kind → adapter source — never inline the
       table; cite by path per NFR-004). For multi-adapter WPs,
       set `adapter:` to the primary and list secondaries in an
       optional `additional-adapters:` array.
    3. **Choose the shape** per `ADR-003` (the per-project ADR; see
       e.g. `.architecture/{project}/adrs/ADR-003-per-wp-frontmatter-shape.md`):
       - **Shape 1 (concrete)** — the WP's behaviour has a real
         test artifact that will exist by the WP's Definition of
         Done. Set `adapter:` + `artifact:` (per-adapter format —
         pytest nodeid for backend, spec ref for frontend, fixture
         path for methodology, etc.).
       - **Shape 2 (deferred)** — the WP ships pre-infrastructure;
         the test cannot be written until a follow-on lands. Set
         `adapter:` + `deferred-to-follow-on:` with the canonical
         need identifier (FR-011). The slice-end deferred-needs
         scan in
         [`references/lifecycle.md`](../../references/lifecycle.md)
         reads this field to aggregate needs across the slice and
         auto-draft follow-ons (ADR-005).
       - **Shape 3 (trivial carveout)** — `na: true` with a
         `justification:` of ≥ 30 substantive characters explaining
         why the WP has no behavioural test. Bare `na: true`
         without justification fails P-VER failure mode 3.
    4. **Reject malformed shapes.** The skill MUST NOT emit a WP
       with an empty / missing / malformed `verification:` field —
       P-VER failure mode 8 surfaces the regression at rubric
       time, but the skill catches it at emission time.

    The field is the machine-readable seam between the WP and the
    behavioural test ledger at
    `.specifications/{change}/verification-ledger.md` (FR-015).

4e. **Set the `platform:` / `touch-class:` field when a WP touches a
    third-party platform (MUST when applicable).** For every WP, triage:
    *does this WP's scope touch a third-party platform* — a service outside
    our own code (GitHub Actions, Stripe, an email provider, a cloud API)?

    - **No third-party touch → omit both fields.** Absence is the signal for
      "no gated touch"; P-PLAT reads a WP with neither key as not-applicable.
    - **Touches a third party → set both keys** in the WP frontmatter:

      ```yaml
      platform: "<lowercase-hyphenated slug>"    # the platform the WP touches
      touch-class: "write | deploy | read-only"  # per the ADR-001 gate posture
      ```

      Choose `touch-class:` by what the WP *does to* the platform — the same
      axis [`PLATFORM_CONTRACT_STANDARD.md`](../../references/standards/PLATFORM_CONTRACT_STANDARD.md)
      and ADR-001 gate on: `write` / `deploy` are hard-gated (a Platform
      Contract is required), `read-only` is soft-recommended.

    These two keys are the **detection signal** the decompose-validation
    rubric's **Phase 10 — P-PLAT (Platform Contract)** reads to decide whether
    the WP set requires a Platform Contract. P-PLAT owns the field's full
    meaning and the fail condition (a `write`/`deploy` touch with no referenced
    contract fails the rubric) — this skill only *emits* the field; it does not
    restate P-PLAT's logic (cite, never inline; NFR-004). The founder-facing
    rationale for tagging a WP uses plain language ("this piece talks to
    {platform}"), not internal IDs.

5. **Build the dependency graph** — for each WP, identify what must exist
   first (`dependsOn`) and what it unlocks (`blocks`). Note: REINFORCE-Test
   WPs are dependencies of any REORGANISE WPs that operate on the same
   subject (characterisation tests must exist first). For cross-kind work
   (step 4b), the graph is contract → {parallel per-kind} → integration.
6. **Estimate token cost** — rough. Input ≈ WP itself + dependency WPs +
   relevant TDD section. Output ≈ implementation files + tests. Round to
   nearest 1k. This is for orchestrator routing, not billing.
7. **Wrap audit (MUST).** Scan the proposed WP set for SUBSTITUTE-Wrap
   primitives. For each:
   - Confirm `subject_ownership` is `external` OR `transitional`
   - For `transitional`, confirm there's a paired Strangle in the dep graph
     with a `removal_plan` date
   - For any Wrap on the same subject as an existing wrapper in the
     codebase (detected via `.context/{project}/INDEX.md` or
     `CODE_INTELLIGENCE.md` if present): **escalate to user before
     finalising**:

     > "Proposed WP-NNN would wrap `{subject}`. Existing wrappers detected:
     > `{path1}`, `{path2}`. Adding another defers the real fix.
     > Recommendation: Refactor `{subject}` directly (REORGANISE-Refactor),
     > or Replace with a new implementation and Delete existing wrappers.
     > Proceed with Wrap anyway? (Y/N)"
7a. **Per-kind gate audit (MUST).** For each WP, confirm its `kind:` matches
    its planned DoD/test plan:
    - `kind: backend` → DoD names unit + integration + smoke per WP-05;
      `WP_BACKEND_STANDARD` patterns (ports & adapters / repository / in-
      memory adapter first / handler / Result / auth) appear in the
      Context/Contract sections where they apply.
    - `kind: frontend` → DoD names component + integration + **a11y (axe)**
      + (page-level) E2E per WP-05; `WP_FRONTEND_STANDARD` patterns
      (component tier / typed client / mock-first / loading/error/empty /
      tokens-not-hex / error boundary) appear where they apply; the WP
      declares which design-tokens it consumes.
    - `kind: contract` → DoD names schema lint + happy/error/empty stub
      coverage + ≥1 consumer mock generated from it.
    A WP whose DoD doesn't match its `kind`'s gates is a misclassified WP —
    fix the kind, fix the DoD, or split.
7b. **Cross-kind shape audit (MUST when the WP set spans kinds).** Verify
    step 4b's shape was applied:
    - ≥1 `kind: contract` WP exists (or single-kind / `--prototype` exempt
      noted).
    - The non-contract per-kind WPs `dependsOn` the contract WP, **not each
      other** (no `frontend dependsOn backend`).
    - ≥1 integration WP closes the graph (`dependsOn` all per-kind
      siblings; runs the conformance check per CF-07).
    - For user-facing surfaces (#45): a visual-contract WP (`kind: contract`,
      `contract_type: visual`) exists, and every `kind: frontend` WP carries
      `visual_contract: <its id>` AND lists it in `dependsOn`. (`wpx-index
      add-wp` already refuses a frontend WP that doesn't — this audit is the
      belt to that braces; a failure here means a WP would be rejected at
      INDEX time.)
    A failed cross-kind shape audit is **FAIL** at step 11 — re-decompose,
    don't paper over.
7c. **Audit cross-WP identifiers (MUST).** For each WP in the proposed
    set, scan its Contract section for **cross-WP shared identifiers**:
    ULIDs (`01[A-Z0-9]{24}` Crockford-base32 shapes), identifier-shaped
    strings (e.g. `dna:*:*`, `urn:*:*`), slugs that ≥2 WPs reference,
    version literals, namespace names, or any token a sibling WP
    Contract would also need to name. For each such identifier:

    1. **If the identifier is already minted in an authoritative upstream
       source** — a TDD "Canonical Identifiers" section, an
       `ADR-NN-canonical-identifiers.md`, an existing instance file the
       WP set references, or the SRD glossary — verify the WP cites the
       upstream source by name/path. No action needed.
    2. **If the identifier is invented inline in the WP Contract** —
       that's a methodology defect. Parallel-dispatched executors will
       each mint their own value and the values will diverge. Either:
       - Author an `ADR-NN-canonical-identifiers.md` that mints the
         identifier deterministically (document the recipe — e.g.,
         `SHA256(name) → Crockford base32`) — and update every WP
         Contract that references the identifier to cite the ADR.
       - OR add a "Canonical Identifiers" section to the TDD that does
         the same.

       Halt decomposition; route back to `/sulis:draft-architecture` to
       add the canonical source. Restart decompose-validate after the
       upstream is in place.

    **Why this matters.** Parallel-dispatched WPs that cross-reference a
    shared identifier inherit drift if each WP's executor mints its own
    value. CH-01KSZ4 (release-train-as-entities, wave 1) lived this:
    WP-003 and WP-004 both minted a tenant ULID, but WP-004 used a
    deterministic `SHA256(name) → Crockford-base32` recipe while WP-003
    used a placeholder pattern. The calling session caught the
    divergence at the post-train audit and reconciled WP-003's branch
    by hand before downstream WPs (WP-001, WP-005, WP-006) inherited
    the drift. Pre-canonicalisation in the design phase prevents the
    recurrence. The mechanical analog of this audit lives in the
    Decompose Validation Rubric as **Phase 8 — Cross-WP identifier
    canonicalisation**.

8. **Write WPs** — one file per WP, using the template above.
9. **Write `INDEX.md`** — list all WPs, their statuses, primitive
   distribution, the dependency graph (as a markdown table and a Mermaid
   `graph TD` diagram), the recommended implementation order (topological
   sort of the graph), and the wrap audit summary.
10. **Report** — total WP count, critical path length, parallelisation
    opportunity (how many WPs can be implemented simultaneously at peak),
    primitive distribution, wrap audit result.

11. **Validate** — apply the
    [Decompose Validation Rubric](../../references/decompose-validation-rubric.md)
    (v0.1.0+; SEA v0.19.0+) to the produced WP set. Write the
    validation report to
    `.architecture/{project}/work-packages/DECOMPOSE_VALIDATION.md`.

    The rubric runs eight phases mechanically where possible:
    - **P1 Inventory completeness** — every WP has Context, Contract,
      DoD/RGB, Sequence, Token cost, Dependencies
    - **P2 Atomicity** — single responsibility per WP; touch surface
      ≤ 15 files (MUST), ≤ 8 (SHOULD); no "and" in titles or purpose
    - **P3 Module naming + clean code** — no jargon prefixes, no
      single-letter abbreviations, descriptive kebab-case slugs
    - **P4 Dependency graph correctness** — no cycles, all targets
      exist, transitive depth ≤ 8, valid topological order. **Includes the
      data-contract wiring check (#48): run `wpx-index audit-contracts` —
      a cross-kind seam (≥2 of backend/frontend/async) MUST have a
      `kind: contract` (data) WP, and cross-kind deps MUST route through it,
      not directly between implementations (CF-05). A non-empty violation
      list is a MUST failure.**
    - **P5 Performance + non-functional reqs** — endpoint/handler WPs
      have a `## Performance` section with measurable bounds
    - **P6 Peer-collision risk** — no two WPs `Create` the same file
      (catches the `loader/__init__.py` collision class at breakdown
      time, before any executor dispatches)
    - **P7 ServiceSpec compliance** — every service the design names
      has a paired `service-specs/<name>.servicespec.yaml` manifest
      that passes the Lovable Test (a fresh AI agent can build a
      working integration against it with no human docs)
    - **P8 Cross-WP identifier canonicalisation** — every cross-WP
      shared identifier (ULID, slug, version literal, namespace)
      resolves to an authoritative upstream source (TDD section, ADR,
      or instance file). The mechanical analog of step 7c above;
      anchor case CH-01KSZ4 release-train tenant-ULID divergence.

    Verdict is computed deterministically:
    - **PASS** — every MUST passes; no SHOULD failures
    - **PASS-WITH-RATIONALE** — every MUST passes; SHOULD failures
      with documented rationale
    - **FAIL** — ≥1 MUST failure

    On `FAIL`: do NOT declare the decompose done. Surface the blocking
    gaps in plain English to the founder and return to the appropriate
    step (e.g., a peer-collision failure means re-running step 5
    "Detect overlaps + atomicity violations" with the rubric's
    findings in hand).

    On `PASS` / `PASS-WITH-RATIONALE`: report the validation outcome
    in the chat summary so the founder sees that the breakdown was
    formally validated, not just produced.

---

## INDEX.md Structure

```markdown
# Work Package Index — {Project}

> **TDD:** [TDD.md](../TDD.md)
> **SIZING:** [SIZING.md](../SIZING.md)
> **Total WPs:** N
> **Critical path:** WP-001 → WP-003 → WP-007 → WP-012 → WP-015 (5 packages)
> **Peak parallelism:** 6 (after WP-003 completes, WP-004 through WP-009 are unblocked)

## Status Summary

| Status | Count |
|---|---|
| pending | N |
| in_progress | 0 |
| done | 0 |
| blocked | 0 |

## Primitive Distribution

| Group | Primitive | Count | WPs |
|---|---|---|---|
| EXPAND | Reuse | 2 | WP-005, WP-009 |
| EXPAND | Compose | 1 | WP-012 |
| EXPAND | Extend | 3 | WP-002, WP-006, WP-011 |
| EXPAND | Create (incl. adapters) | 5 | WP-001, WP-003, WP-004, WP-007, WP-008 |
| REORGANISE | Refactor | 2 | WP-013, WP-014 |
| REORGANISE | Decompose | 1 | WP-015 |
| SUBSTITUTE | Wrap | 0 | — |
| REINFORCE | Test | 2 | WP-016, WP-017 |
| REINFORCE | Instrument | 1 | WP-018 |
| REINFORCE | Harden | 1 | WP-019 |

> Adapters for ports are counted as Create. WP-004 (Stripe adapter for the
> `PaymentGateway` port) is Create, not Wrap — see "Ports & Adapters vs
> Wrappers" in `references/change-primitives.md`.

## Adapter Distribution

> Per-adapter count across the WP set — the canonical adapter values
> live in
> [`VERIFICATION_QUESTIONS.md`](../../references/standards/VERIFICATION_QUESTIONS.md)
> (cite, never inline). Counts include `verification:` Shape 1
> (concrete) and Shape 2 (deferred) WPs; Shape 3 (trivial carveout)
> WPs are listed in the carveout-count row.

| Adapter | Count | WPs |
|---|---|---|
| backend | N | WP-001, WP-003, … |
| frontend | N | WP-XXX, … |
| async | N | — |
| contract | N | — |
| infra | N | — |
| docs | N | — |
| methodology | N | — |
| (carveout — `na: true`) | N | — |

## Wrap Audit

> All Wrap WPs reviewed for No-Band-Aid-Wrappers compliance.

| WP | Subject | Ownership | Removal Plan | Status |
|---|---|---|---|---|
| (none) | — | — | — | — |

No Wraps proposed. No wrapper rot detected on existing modules.

(If Wraps appear, they would be listed here with `subject_ownership` and
`removal_plan` validated against the No-Band-Aid-Wrappers rule.)

## Dependency Graph

\`\`\`mermaid
graph TD
  WP001[WP-001 Order entity] --> WP003[WP-003 OrderRepository port]
  WP001 --> WP008[WP-008 PaymentGateway port]
  WP003 --> WP007[WP-007 Postgres adapter]
  WP003 --> WP004[WP-004 InMemory adapter]
  WP007 --> WP012[WP-012 CreateOrder service]
  WP004 --> WP012
  WP008 --> WP012
\`\`\`

## WP Table

| ID | Title | Primitive | Status | Depends On | Blocks | Token (in/out) | TDD § |
|---|---|---|---|---|---|---|---|
| WP-001 | Order entity | create | pending | — | WP-003, WP-008 | 4k / 2k | 3.1 |
| WP-003 | OrderRepository port | create | pending | WP-001 | WP-004, WP-007 | 3k / 1k | 3.3 |
| WP-004 | Stripe adapter for PaymentGateway port | create (adapter) | pending | WP-003 | WP-012 | 2k / 2k | 3.4 |
| WP-013 | Refactor OrderService | refactor | pending | WP-016 | WP-015 | 3k / 2k | 3.6 |
| WP-016 | Characterise OrderService | test | pending | — | WP-013 | 2k / 2k | — |
| ... |

## Recommended Implementation Order

1. WP-001 (no deps)
2. WP-002, WP-003 (parallel, both depend only on WP-001)
3. WP-004, WP-007, WP-008 (parallel, depend on WP-003)
4. ...
```

**The WP Table header is canonical — emit it exactly.** The header MUST
begin `| ID | Title | Primitive | Status | Depends On | Blocks |` (ID
first; no separate `kind` column — `kind` aliases to `primitive` and
silently wins first-match, so a `| WP | Title | kind | Primitive | ... |`
header makes the table invisible to the run-all loop). After writing
`INDEX.md`, run the decompose-time lint to catch a drifted header before
it reaches the loop:

```bash
wpx-index lint --project {project}
```

A non-zero exit means the header drifted — fix it to the canonical form
above and re-run.

---

## Adapting Depth

- **Quick** ("just give me a WP list") — atomise and write WPs with skeletons; full Red-Green-Blue checklists deferred until the WP is picked up. Useful for sprint planning.
- **Full** (default) — fully populated WPs with named Red tests, ready for an execution agent to pick up.
- **Single** (`/sulis:plan-work WP-012`) — decompose only one TDD section into WPs. Useful when a TDD section was added/changed mid-project.

**Tier-aware granularity.** Read tier from `.architecture/{project}/SIZING.md`
if present, falling back to `TDD.md`'s Sizing Report appendix. Per
`references/right-sizing.md`:

- Tier S: 3-8 WPs covering the whole TDD.
- Tier M: 8-20 WPs; one WP per significant component or contract.
- Tier L: 20-60 WPs; one WP per port + per adapter + per resilience primitive.
- Tier XL: 60+ WPs organised by bounded context; per-context INDEX.md.

Resist over-decomposition. If a "WP" would have a single line of work in
its DoD, it should be merged into a sibling WP. The dependsOn graph
captures ordering — multiple WPs for one component should be the
exception, not the rule.

---

## Gotchas

- **Atomicity is not negotiable.** If you find yourself writing "WP-007 also needs to update X in WP-008", you have not atomised. Split.
- **Sequence IDs prevent merge conflicts.** A WP's `dependsOn` predecessors must merge first. The `INDEX.md` order is the merge order.
- **Don't decompose by file.** Decompose by capability. One capability may touch several files; one file may be touched by several WPs (sequenced via `dependsOn`).
- **Token cost is rough.** It's a routing signal, not a contract. Round to 1k; do not optimise.
- **Mermaid renders in GitHub.** Use it for the dependency graph — readers will see the visual.
- **Cross-reference ADRs.** If a WP implements a decision made in an ADR, name the ADR in frontmatter. Drift between WPs and ADRs is a maintenance trap.

---

## See Also

- `references/work-package-template.md` — the full WP template
- `references/red-green-blue.md` — the cycle the DoD enforces (plugin root)
