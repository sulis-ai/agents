# TDD — Brain as a living backlog + traversable memory

> Change: CH-01KT60 · `create` · `brain-backlog-and-traversal`
> Sourced from `.specifications/brain-backlog-and-traversal/SRD.md`
> Tier: M (lower edge) · `founder_facing: false`
> This is Sulis built with Sulis — treat as a normal marketplace change.

## How to read this

Three pieces sit on one principle (**no orphan requirements** — every idea
roots in a why before it becomes a what):

1. **Capture** — `/sulis:capture` + a `_brain_capture` orchestrator that
   roots an idea in an Opportunity, bootstraps/reuses the backing chain, and
   emits a draft Requirement sourced from it.
2. **Traverse** — `/sulis:backlog` + Sulis-agent wiring that answers
   open / roadmap / done **off the brain graph** via the extended query seam.
3. **Opportunity-analyst agent** — a full facilitation agent that
   pressure-tests the why (hypothesis → validated → defined).

Six decisions are recorded as ADRs (`adrs/`). This TDD references them at the
point each bites; it does not restate them.

The change **builds on existing seams and does not reimplement them.** The
write seam (`_entity_*`, `_*_emission`, `sulis-emit-*`), the read seam
(`_brain_query`, `sulis-brain-query`), and the testable-state scenario loop
(`sulis-author-scenario`, `sulis-verify-acceptance`) are inputs, extended at
their existing extension points.

---

## Form — Structural Integrity

Form rides the **existing hexagonal seams**; this change adds adapters and
compose-functions at established ports, it does not introduce new
architecture. Per Respect-Don't-Restate, the port contracts live in their
modules' docstrings (`_entity_repository.py`, `_brain_query.py`); summarised
here only where this change touches them.

### Component inventory (what this change adds)

| Component | Kind | Home | Primitive |
|---|---|---|---|
| `_brain_capture.py` | new orchestrator module | `plugins/sulis/scripts/` | EXPAND-Create |
| `sulis-capture` | new CLI (JSON-envelope) | `plugins/sulis/scripts/` | EXPAND-Create |
| `compose_opportunity_from_idea` | new compose fn (sibling) | `_opportunity_emission.py` | EXPAND-Extend |
| `compose_requirement_from_idea` | new compose fn (sibling) | `_requirement_emission.py` | EXPAND-Extend |
| `bootstrap_backing_chain` | new helper | `_brain_capture.py` | EXPAND-Create |
| roadmap sidecar reader/writer | new fns | `_brain_capture.py` + `_brain_query.py` | EXPAND-Create |
| `find_opportunities`, `state=` kwargs, roadmap view | query extension | `_brain_query.py` | EXPAND-Extend |
| `--open/--roadmap/--done/--by-type/--by-state` | CLI modes | `sulis-brain-query` | EXPAND-Extend |
| `/sulis:capture` | new skill | `plugins/sulis/skills/capture/` | EXPAND-Create |
| `/sulis:backlog` | new skill | `plugins/sulis/skills/backlog/` | EXPAND-Create |
| `opportunity-analyst` | new agent | `plugins/sulis/agents/opportunity-analyst.md` | EXPAND-Create |
| Sulis-agent traverse routing | agent-body edit | `plugins/sulis/agents/sulis.md` | REORGANISE (characterised) |

**Primitive note (Ports & Adapters ≠ Wrappers).** Every "new module" here
is a *consumer* of ports the domain already owns (`EntityRepository`, the
query functions) — these are EXPAND-Create/Extend, not SUBSTITUTE-Wrap. The
single edit to internal code (`sulis.md`) is a REORGANISE on an internal
subject and therefore carries a characterisation test (see Proof).

### The dependency picture

```
/sulis:capture (skill, founder English)
        │ invokes
        ▼
sulis-capture (CLI, JSON envelope)
        │ imports
        ▼
_brain_capture.capture_idea(why_intensity, why, what, seed, roadmap)
        │
        ├── bootstrap_backing_chain(repo_foundation, repo_pd, repo_root)   [ADR-002]
        │       ├── Sha256CrockfordTenantDeriver (foundation/tenant)  ← reuse-first
        │       └── compose_product_from_yaml-shape, explicit belongs_to_tenant
        │
        ├── (quick)  compose_opportunity_from_idea(...) → repo_pd.save("opportunity")   [ADR-003,005]
        ├── (full)   read analyst-emitted opportunity by id (find_by_id)               [ADR-004]
        │
        ├── compose_requirement_from_idea(source=<opp id>, ...) → repo_pd.save         [ADR-003,005]
        └── (roadmap) roadmap_add(member_ids)  → .brain/labels/roadmap.jsonld          [ADR-001]

/sulis:backlog (skill)  ─┐
Sulis agent (FR-08)      ─┼─ both call ─► sulis-brain-query --open/--roadmap/--done   [ADR-006]
                          │                       │ imports
                          └───────────────────────▼
                                  _brain_query.find_opportunities / find_requirements(state=) / find_roadmap

opportunity-analyst agent ── emits/updates Opportunity via sulis-emit-opportunity (single-idea path)  [ADR-004,005]
```

Dependencies point inward: skills → CLI → orchestrator → emission/query
modules → `EntityRepository` port → `LocalFileEntityAdapter`. No module
reaches around the port into the on-disk JSON-LD layout (the query seam is
the only reader; the adapter is the only writer).

### Ports this change relies on (referenced, not restated)

- **`EntityRepository`** (`_entity_repository.py`) — the write port.
  `bootstrap_backing_chain` and both compose-emit paths persist through it.
  The Track-2 `StorageServiceAdapter` swap is unaffected by this change
  (ADR-004 consequence).
- **`_brain_query` functions** (`_brain_query.py`) — the read port. Extended
  per ADR-006; existing callers unaffected (kwarg-default-preserving).
- **`TenantDeriver` / `Sha256CrockfordTenantDeriver`** (`_discovery/tenant.py`)
  — the canonical consumer-tenant id recipe (external ADR-002). Reused for
  the bootstrapped Tenant identity (this change's ADR-002).

### Two-domain construction (load-bearing detail)

Tenant is a **`foundation`**-domain entity; Product / Opportunity /
Requirement are **`product-development`**. The orchestrator constructs two
`LocalFileEntityAdapter` instances — `LocalFileEntityAdapter(base_dir,
"foundation")` for the Tenant, `LocalFileEntityAdapter(base_dir,
"product-development")` for the rest — mirroring the per-emitter `--domain`
defaults. The backlog query reads `product-development` (where Opportunities
and Requirements live).

---

## Armor — Operational Hardening

This change has **no network, no external service, no secrets, no
inter-service traffic** (`founder_facing:false`, no Platform write per the
SRD constraint). The Armor surface reduces to one concern: **best-effort,
never-blocking degradation (NFR-01).**

| Concern | Treatment |
|---|---|
| Brain unavailable (schemas not vendored, `jsonschema` missing, `.brain/` absent) | Capture + traverse return `{"ok":false,"error":...}`; the skill renders plain English; **no session crash** (NFR-01). Mirrors `_brain_emit_helper`'s `_try_adapter` / `_safely` pattern. |
| Why missing on quick capture | Orchestrator refuses, emits nothing, returns a plain-English error (FR-02 enforcement; ADR-003). |
| Empty store on traverse | All query views return `count:0` empty, never error (NFR-01, ADR-006). |
| Malformed roadmap sidecar | Roadmap view returns empty; capture's roadmap-add tolerates and rewrites (ADR-001). |
| Duplicate capture | Stable-seed ULID derivation ⇒ overwrite-in-place, no duplicate (NFR-04; ADR-005). |
| Partial chain write (process dies mid-bootstrap) | Bottom-up emit order (Tenant→Product→Opp→Req) means a crash leaves a valid prefix; re-run resolves-or-emits the rest idempotently (ADR-002). No orphan Requirement: the Requirement is the **last** write and only fires after its `source` resolves. |

**Degradation contract (the one Armor primitive that matters).**
`_brain_capture` and the query extensions adopt the existing
`_brain_emit_helper` discipline verbatim: a thin `_try_adapter` that returns
`None` when the brain isn't usable, and `_safely` wrapping the emit calls.
The CLI translates `None`/exception into the `{"ok":false,"error":...}`
envelope; it never raises out of `main()`. **No retries, no circuit breaker,
no timeout** — there is no remote call to protect; adding them would be
cargo-culting (boring-code: don't add machinery the problem doesn't have).

Observability is the existing pattern: the emit helpers already log-and-
continue; capture/traverse emit a single structured envelope on stdout that
is itself the trace. No OpenTelemetry span — there is no distributed call.

---

## Proof — Verification Protocol

Proof rides the **testable-state scenario loop** (shipped v0.90.0, PR #154)
plus pytest, exactly as the SRD's Verification Plan mandates. No mocks for
the store — tests use a temp `.brain/instances` directory and the real
`LocalFileEntityAdapter` against the real vendored schemas (MEA-09: real
adapters, not mocks).

### Contract tests (the seams)

| Seam | Contract asserted |
|---|---|
| `compose_opportunity_from_idea` / `compose_requirement_from_idea` | pure; same inputs → identical dict incl. deterministic id; output validates against the vendored schema (no `unevaluatedProperties` violation) |
| `bootstrap_backing_chain` | resolve-or-emit; second call writes nothing new; tenant id == canonical deriver output; chain refs whole (no dangling) |
| `_brain_query` new modes | `find_opportunities` / `state=` / `find_roadmap` return correct sets; empty store → empty, not error |
| `sulis-capture` / `sulis-brain-query` CLI | JSON-envelope shape (`ok`/`data`/`error`), exit 0/1 — these envelopes are the consumer contract (CONTRACT_FIRST) |

### Failure-mode assertions (SRD Q3)

- brain-unavailable → `ok:false`, command degrades (NFR-01)
- duplicate capture → idempotent, no second instance (NFR-04)
- capture with no why → rejected, nothing emitted (FR-02)
- query against empty store → empty, not error

### Scenario coverage (run-from-graph)

Two journeys authored in plain English via `sulis-author-scenario`, emitted,
runnable via `sulis-verify-acceptance --scenario`:

1. **Capture journey** — deposit an idea (why + what), assert an Opportunity
   + a draft Requirement sourced from it land, chain whole.
2. **Traverse journey** — ask "what's open", assert open ideas + roadmap +
   done come back off the brain graph (not the change-store).

**Sequencing note (the bootstrapping circularity):** these scenarios verify
the capture/emit path, which doesn't exist until built. Requirement +
scenario **emission is deferred to a dogfood step at verify/ship time**,
emitted *through the new capture path itself* (FR-10). The WP order
(next pass) builds the machinery first; the dogfood emission is the last WP.
**No requirement is emitted via the old `--from-srd` path** for this change.

---

## Verification Plan

<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->

Concretises the SRD's `## Verification Plan` (ADR-001 section-name lock) into
TDD-level artifacts. `kind: backend` (Python scripts) + skill/agent bodies →
the canonical kind→adapter table's `backend` row applies: pytest nodeids are
the concrete artifact for the script seams.

### 1. What user-observable behaviour are we verifying

A founder deposits an idea and it lands recoverable, rooted in a why; later
they ask "what's open?" and see their open ideas, their roadmap, and what's
done — answered from the brain, not the change-store. Restated as artifacts:
the capture + traverse scenarios run green from-graph, and the pytest suite
proves the chain is whole and the views are correct.

### 2. Verification environment(s)

Local + CI. pytest under `plugins/sulis/scripts/tests/` (unit + integration)
runs everywhere against a temp `.brain/instances`. Scenario runs use the
existing `sulis-verify-acceptance --scenario` harness. No tier beyond CI is
involved (`founder_facing:false`, no deploy).

### 3. Bootstrap-from-zero case

A fresh clone at the merge SHA must: (a) have the vendored schemas under
`plugins/sulis/brain/compiled/{foundation,product-development}/`; (b) run
`sulis-capture` and have it bootstrap Tenant+Product on first call into a
fresh `.brain/instances`. The bootstrap-test (`test_bootstrap_*`) asserts a
fresh temp dir yields a whole chain with the canonical tenant id, and a
second call is a no-op. Dependency chain that must resolve: `_brain_capture`
→ `_discovery.tenant` + `_product_emission` + `_opportunity_emission` +
`_requirement_emission` + `_entity_adapter_local` (+ `jsonschema`).

### 4. Per-integration verification strategy

The only "integration" is the brain store, which is **in-repo and in-process**
— not a third-party service. Strategy: **in-memory/real-adapter** against a
temp dir; classification `existing` (the `LocalFileEntityAdapter` +
`_brain_query` seams already exist). No recording mock, no sandbox — there is
no remote. Resilience primitive: the `_try_adapter`/`_safely` graceful-
degradation pattern (Armor), asserted by the brain-unavailable failure-mode
test. Test seam: the `EntityRepository` port — tests inject a temp-dir
adapter; the brain-unavailable case is exercised by pointing at a dir with
no vendored schemas and asserting `ok:false`.

- concrete — `plugins/sulis/scripts/tests/integration/test_capture_e2e.py::test_capture_lands_whole_chain`
- concrete — `.../tests/unit/test_brain_capture.py::test_quick_capture_rejects_missing_why`
- concrete — `.../tests/unit/test_brain_query_views.py::test_open_roadmap_done_views`

### 5. Per-kind verification adapter

`kind: backend` → pytest nodeids (per the canonical's backend row). The
skill/agent bodies (`/sulis:capture`, `/sulis:backlog`, opportunity-analyst)
are verified by the two scenario journeys (the founder-facing path) + manual
smoke against this repo's store, per the SRD's per-kind block.

### 6. Infrastructure needs surfaced (deferred)

None. No vendor mock, no test OAuth, no seed-data fixture beyond the temp
`.brain/instances` the tests construct themselves. The change ships its own
verification infrastructure (the scenario journeys are authored in this
change and emitted through the dogfood path).

**Per-WP `verification:` shape (for `/sulis:plan-work`):** all WPs are
**Shape 1 — concrete** (`adapter: backend` + `artifact: <pytest nodeid>`),
except the agent-only WP for `opportunity-analyst.md` and the skill-body WPs,
which are **Shape 1 — concrete** against the scenario-run artifacts. The
dogfood WP is concrete against the from-graph scenario run. No deferred,
no trivial-carveout WPs anticipated.

---

## Sizing Report

- **Tier:** computed **M** (lower edge), confirmed. sFPC ≈ 7 (4 reused
  entities + capture op + traverse op + bootstrap op); ASR ≈ 6 (NFR-01..04,
  the brain-store integration, idempotence). File-count sanity: ~10 touched
  source files — consistent with M.
- **Per-pillar coverage:** Form **referenced** (rides existing ports — TDD
  Form section is short by design); Armor **light** (one degradation
  primitive, no network); Proof **covered** (rides the scenario loop +
  existing pytest harness).
- **TDD length vs target:** within M target; Form deliberately short because
  the ports are pre-existing and documented in their modules (Respect-Don't-
  Restate). No circuit breaker triggered.
- **ADRs:** 6 produced. Above a tier-M "expected" count, justified below.

### ADR rationale (6 ADRs)

Each ADR locks a decision that (a) affects more than one component and (b)
has no existing ADR covering it. The Roadmap-storage (001), tenant-identity
(002), and intake-shape (005) decisions were *explicitly parked by the SRD
as design-stage calls* — they are not discretionary. The tenant-identity ADR
(002) **extends** an existing external ADR (`discover-project` ADR-002)
rather than competing with it, and exists because schema inspection
discovered a latent two-derivation fork that would silently fragment the
graph — recording it is the point. Quick-vs-full (003) and analyst-invocation
(004) are the two compositional seams the SRD's FR-02/FR-11 hinge on.
Query-shape (006) records *what was rejected* (a second read module, a query
engine) more than what was chosen. None restate ground already covered by an
existing ADR; the count reflects the SRD's three explicit design-stage
parks + three genuine composition decisions.

---

## Open Architecture Questions

None blocking. The SRD's one parked validator-tolerance question is **resolved
by inspection** (ADR-001: `unevaluatedProperties:false` everywhere — strict).
The tenant-identity fork (ADR-002) is resolved in favour of the canonical
deriver; if the founder later wants the bootstrapped Product's display name
or category changed, that is a one-line orchestrator constant, not an
architecture question.
