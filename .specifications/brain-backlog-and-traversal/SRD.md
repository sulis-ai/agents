# SRD — Brain as a living backlog + traversable memory

> Change: CH-01KT60 · `create` · `brain-backlog-and-traversal`
> Authored by Sulis this session (drafting ownership transferred by the
> founder; normally the requirements-analyst owns this artifact).
> Audience note: non-technical-founder default.

## Summary

Make the brain a **living backlog and memory** the founder can deposit
ideas into and interrogate. Two paired pieces sit on one principle.

**Guiding principle (the spine this change embodies):** *no orphan
requirements.* Every idea is rooted in an **opportunity** — the why, the
problem, who has it — before it becomes a **requirement** — the what. The
capture path enforces that discipline at the door. The longer arc (rooting
*every* session in an opportunity, a dedicated opportunity-analyst agent) is
deliberately out of this slice and captured as roadmap items so it is not
lost.

- **Capture path.** A lightweight way to project a scoped-out idea into the
  brain: root it in an opportunity, optionally attach the concrete
  requirement, land it durable (`state: draft`), optionally flag it
  **Roadmap**. Generalises emit-wiring beyond full-SRD; wires the currently
  orphaned `sulis-emit-opportunity` + `sulis-emit-product`.
- **Traverse path.** Wire the existing brain query seam
  (`_brain_query.py` / `sulis-brain-query`) into a skill *and* the Sulis
  agent so it answers "what's open / deferred / on the roadmap / the state
  of the work" **off the brain graph** — distinct from `/sulis:dashboard`
  and `/sulis:inbox`, which read the change-store.

## Grounding findings (from recon + schema inspection)

These shape the requirements and are recorded so design inherits them:

- **The ref chain is deep and mandatory.** `Requirement.source` is
  required and must point to an `Opportunity` (or Actor); `Opportunity.for_product`
  is required and must point to a `Product`; `Product.belongs_to_tenant` is
  required and must point to a `Tenant`. So a durable captured idea bottoms
  out at: Requirement → Opportunity → Product → Tenant. The capture path
  must lay down (or reuse) this backing chain — this is the dangling-refs
  gap the brief named, made concrete.
- **No "proposed"/"deferred" state exists.** `Requirement.state` =
  {draft, approved, implemented, verified}; `Opportunity.state` =
  {hypothesis, validated, defined, dropped}. Captured-and-set-aside ideas
  live as **draft** (requirement) / **hypothesis** (opportunity). "Roadmap"
  is therefore a *label we attach*, not a built-in state — its storage
  mechanism is a design-stage call.
- **The query seam is orphaned.** `_brain_query.py` already has
  `find_requirements`, `find_entities`, `where_field_equals`, ref-traversal
  (`find_testresults_verifying`); `sulis-brain-query` exposes `--list`,
  `--by-id`, `--verifying`, `--passing-verifying`. Nothing in any skill or
  the agent calls it. No `--state` / `--type` / opportunity filter yet.
- **Store is single-repo.** `.brain/instances/product-development` exists
  (decision / design / lifecyclerun present; no requirement / opportunity /
  product yet). Per-repo store is the correct home for this slice.

## Functional Requirements

**FR-01: Lightweight capture command.** The founder can deposit a
scoped-out idea into the brain through a single command
(`/sulis:capture`) without running a full spec session. The command speaks
in plain English (an idea, a why, a what) and never exposes entity / IDEF0
/ ref vocabulary.

**FR-02: Opportunity-first rooting (the principle, enforced).** Capture
walks the *why* and the *what* **together in one sitting**: it roots the
idea in an Opportunity first (the why is mandatory — `source` must
reference a real Opportunity, by schema), then captures the concrete
requirement (the what) in the same pass. An idea cannot be captured as a
bare requirement with no why. The why-rooting has two intensities:
*quick* (a one-line why for an idea dropped mid-conversation) and *full*
via the opportunity-analyst agent (FR-11), which pressure-tests and matures
the why; either way the what is captured in the same sitting.

**FR-03: Requirement capture sourced from the opportunity.** In the same
sitting as FR-02, capture emits a draft Requirement whose `source` is the
rooting Opportunity — the why and the what land together. (If the idea is
genuinely only a why with no statable what yet, the Opportunity may stand
alone as a `hypothesis`, but the default flow captures both.)

**FR-04: Backing-chain bootstrap (wires the orphaned emitters).** The
first capture in a repo lays down the backing chain the schema requires —
a Tenant, a Product, and reuses them on subsequent captures so the
why → product → tenant refs are whole and non-dangling. This wires the
currently-orphaned `sulis-emit-product` and `sulis-emit-opportunity` into a
live caller.

**FR-05: Roadmap labelling.** A captured idea can be marked **Roadmap**
(deliberately set aside / planned-for-later) at capture time, distinct from
a freshly-captured untriaged idea. The traverse path can list the Roadmap
separately from "just captured."

**FR-06: Durable + recoverable.** Captured entities persist in the
per-repo `.brain/instances` store, travel with the repo, and survive
scope-narrowing — an idea rightly scoped out of the current work is
recoverable later by name or by traversal, never lost.

**FR-07: Backlog traverse command.** A `/sulis:backlog` skill answers, off
the brain graph: what opportunities and requirements exist, what is **open**
(draft / hypothesis), what is on the **Roadmap**, and what is **done/built**
(implemented / verified) — the state of the work. It reads brain entities —
explicitly *not* the change-store that `/sulis:dashboard` and `/sulis:inbox`
read.

**FR-08: Conversational traverse from the agent.** The Sulis agent can
answer "what's open / deferred / on the roadmap / the state of the
requirements" inline in normal conversation by calling the brain query
seam — the founder need not remember the command.

**FR-09: Query-seam extension + wiring.** `sulis-brain-query` /
`_brain_query.py` gain the filters the traverse path needs — by entity type
(opportunity, requirement), by state, and a Roadmap view — surfaced via the
CLI and consumed by FR-07 and FR-08. This wires the orphaned read seam into
real callers.

**FR-11: Opportunity-analyst agent.** A full facilitation agent that
pressure-tests and validates the *why* — mirroring the requirements-analyst,
framed around the brain's job-to-be-done shape (*"when… I want… so I can…"*).
It takes a raw or quick-captured opportunity and matures it through the
brain's opportunity states (hypothesis → validated → defined): clarifies the
problem, who has it, the job, the evidence, and the boundary against
adjacent whys. It emits / updates the Opportunity entity and is the
quality bar that makes the opportunity-first principle real, rather than a
prompt that accepts any answer. It composes with capture (FR-02 full
rooting) and stands alone (mature an existing opportunity later).

**FR-10: Dogfood — first deposits are these ideas.** The first ideas
captured through the new path are this change's own pieces — the capture
path and the brain-traversal command — landed rooted in an opportunity,
proving the path end-to-end so these ideas are not lost. The
opportunity-analyst is delivered in this change rather than deferred, so it
is exercised (not merely recorded) by running it against the capture
path's own opportunity.

## Non-Functional Requirements

**NFR-01: Best-effort, never blocking.** If the brain machinery is
unavailable (schemas not vendored, downstream consumer), capture and
traverse degrade gracefully — the emitter / query returns
`{"ok": false, "error": ...}` and the command reports the situation in
plain English. A brain failure never crashes a session.

**NFR-02: Founder-mode throughout.** The founder never sees entity types,
ref ids, IDEF0, `tool_ref`, or schema vocabulary. Capture and traverse
speak only in why / what / open / roadmap / done.

**NFR-03: Single-repo scope.** Per-repo `.brain/instances` only. No
cross-repo or central-store assumptions; the cross-repo home for
Product / Opportunity (Platform tier) is out of scope and unaffected.

**NFR-04: Idempotent capture.** Re-capturing the same idea (stable seed)
does not create a duplicate; opportunity and requirement emission is
deterministic on a stable seed, matching the existing emit convention.

## Scope decision (recorded)

The brief mandated a *thin* first slice. The founder consciously expanded
scope to include the **full opportunity-analyst agent (FR-11)** in this
change, overriding the thin-slice mandate. Rationale: a lightweight
why-prompt would capture shallow opportunities and hollow out the
opportunity-first principle; the agent is what gives the principle teeth,
and building capture's why-rooting twice (shallow now, agent-backed later)
is the rework this methodology exists to avoid. Scope is founder-owned; this
is the founder's call, recorded here.

## Non-goals (captured as Roadmap, not lost)

- Rewiring **all** sessions (specify / requirements) to be opportunity-rooted.
  The principle is embodied in the capture path here; enforcing it everywhere
  is a follow-on.
- Cross-repo / Platform-tier central store for Product + Opportunity.
- Idea **history / time-travel** (bitemporal evolution, #67) — stays off.

## Constraints

- Build on the existing emit + query seams; do not re-implement them.
- Reuse the existing testable-state scenario loop (specify authors journeys
  → emit → design resolves the Design placeholder → `verify-acceptance
  --scenario` runs from-graph; shipped v0.90.0 / PR #154).
- Roadmap-label storage mechanism is a design-stage decision (label field
  vs priority vs convention) — schema permits extra fields
  (`additionalProperties` not forbidden), but the validator's tolerance is
  to be confirmed at design.
- No third-party platform write/deploy touch → no Platform Contract gate.

## Verification Plan

> Section heading fixed per ADR-001 (`## Verification Plan`).

### Foundational (Q1–Q4)

- **Q1 — What proves this works, end to end?** Two run-from-graph
  scenarios (below): one capture journey, one traverse journey, each
  authored in plain English, emitted, and runnable via
  `sulis-verify-acceptance --scenario`.
- **Q2 — What is the unit-level safety net?** pytest coverage for: the
  capture orchestration (rooting → bootstrap → emit), the backing-chain
  bootstrap + reuse (idempotence), and the new query-seam filters
  (by-type, by-state, roadmap view). Red-Green-Blue per Work Package.
- **Q3 — What are the failure modes to assert?** brain-unavailable
  (emit/query returns `ok:false`, command degrades, NFR-01); duplicate
  capture (idempotent, NFR-04); capture attempted without a why (rejected,
  FR-02); query against an empty store (returns empty, not error).
- **Q4 — What is explicitly NOT verified here?** the cross-repo store, the
  opportunity-analyst agent, idea history — all out of scope.

### Per-kind (CLI / Python scripts + skill + agent body)

- **Scripts (capture orchestrator, emitter wiring, query filters):** pytest
  against a temp `.brain/instances`; assert emitted JSON-LD validates
  against the vendored schemas; assert ref chain is whole (no dangling
  source / for_product / belongs_to_tenant).
- **Skills (`/sulis:capture`, `/sulis:backlog`):** scenario-run journeys
  exercise the founder-facing path; manual smoke against this repo's store.
- **Agent (conversational traverse, FR-08):** journey asserts the agent
  answers "what's open" by querying the brain seam, not the change-store.
- **Opportunity-analyst agent (FR-11):** a journey takes a raw why,
  matures it through the agent, and asserts the emitted Opportunity moves
  hypothesis → validated/defined with a populated job-statement; assert it
  composes with capture (full-rooting path) and stands alone.

### Acceptance scenarios (authored with the founder)

1. **Capture an idea (why + what together)** — the founder deposits an
   idea, is walked through the why (rejected if absent) and then the what in
   the same sitting, and it lands recoverable: an Opportunity + a draft
   Requirement sourced from it.
2. **Pressure-test a why** — the founder brings a raw why to the
   opportunity-analyst; it matures hypothesis → validated/defined with a
   populated job-statement.
3. **Ask what's open** — the founder asks the backlog (command or
   conversation) and sees open ideas, the Roadmap, and what's done/built —
   read off the brain graph, not the change-store.

## Acceptance (observable)

- Running the capture command on a fresh idea produces, in the per-repo
  store: a Tenant + Product (bootstrapped once), an Opportunity (the why),
  and — if a what was given — a draft Requirement whose `source` resolves to
  that Opportunity. No dangling refs.
- The two ideas of this change + the opportunity-analyst idea are present in
  the store as Roadmap items after the dogfood.
- Running the backlog command lists open opportunities + requirements and
  the Roadmap, sourced from brain entities (not the change-store).
- Asking the Sulis agent "what's open?" in conversation returns the same,
  off the brain graph.
- Both verification scenarios run green from-graph.
- Full test suite green; new pytest coverage for capture + query filters.
