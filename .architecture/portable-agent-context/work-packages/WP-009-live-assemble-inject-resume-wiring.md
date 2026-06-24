---
id: CH-GJ9KQR-WP-009
change_id: "01KVX26BDXGJ9KQRJ11HACHMZV"
kind: backend
primitive: reinforce-instrument
group: reinforce
title: Wire the live assemble→inject resume path with real Working Set + brain readers
status: pending
dependsOn: [CH-GJ9KQR-WP-002, CH-GJ9KQR-WP-003, CH-GJ9KQR-WP-004, CH-GJ9KQR-WP-005, CH-GJ9KQR-WP-007]
characterisation_test: plugins/sulis/scripts/tests/integration/test_live_resume_injection.py
implements:
  - "spec:create-portable-agent-context#resume-from-our-context"
  - "spec:create-portable-agent-context#provider-agnostic-injection"
  - "TDD.md§3.2 (the `◀── assembled payload ──` brief-injection arrow)"
verification:
  adapter: backend
  artifact: plugins/sulis/scripts/tests/integration/test_live_resume_injection.py
prov:
  wasGeneratedBy: "engineering-architect:codebase-audit"
  source: "prove-run gap GAP-1 + GAP-2 (consumer reality check); TDD.md§3.2/§5"
estimatedTokenCost:
  input: ~16k
  output: ~10k
---

## Context

TDD §3.2 (the brief-injection arrow `brief argv (ADR-004/005) ◀── assembled
payload ──`) and §5 (the load-bearing **provider-independent resume** journey).

**This WP closes the gap a `/sulis:prove` consumer-level reality check found:
the headline capability is built as components but NOT connected into the live
system.** WP-003 built `ContextPayloadAssembler`, WP-004 built
`seed_payload_for_resume` + `DurableAppendSink`, WP-007 *claimed* the seam-close
— but its verification artifact (`test_provider_independent_resume.py`) drives
the assembler **directly**: it constructs `DurableAppendSink` /
`ContextPayloadAssembler` and calls `seed_payload_for_resume` itself. It proved
the COMPONENT, not the live path.

Two verified gaps fold into this one WP (same files, one coherent wiring):

- **GAP 1 (the headline — BLOCKED).** `seed_payload_for_resume`
  (`durable_sink.py`) and `ContextPayloadAssembler` are referenced ONLY in
  tests — never in production code. The live resume path
  (`manager.py::_respawn`, `manager.py::_attach_durable_sink`) calls only
  `sink.seed_next_order_from_store()` (the order counter). It does **not**
  assemble the payload and does **not** inject it into the (re)spawned agent.
  The brief seam already exists and is the intended target: the brief is
  delivered as `~/.sulis/changes/{change_id}/pre_prompt.txt` and resolved into
  an argv element by `claude_pty._read_pre_prompt` → `spawn_argv`
  (`SessionSpec.brief_change_id`). The missing work: **at the manager spawn /
  resume seam (the composition root that owns `_durable_store_for(key)`),
  ASSEMBLE the `ContextPayload`, RENDER it, and COMPOSE it into the brief
  sidecar** so the (re)spawned agent receives the rich Sulis-owned context
  through the existing brief seam. This is spec Scope 4 — specified, never built.

- **GAP 2 (partial stub — folds in here).** The assembler's
  `working_set_reader` and `brain_reader` (`context_payload.py:212–222`)
  default to empty lambdas (`lambda: ""` / `lambda: []`) and are never wired to
  real sources. Without real readers, even a wired assembler yields an empty
  Working Set + empty brain — only the message summary is real. The live wiring
  MUST inject REAL readers at the composition root (WPB-07):
  - `working_set_reader` → read the change's
    `.changes/{primitive}-{slug}.WORKING-SET.md` (the live reasoning state —
    problem / current best solution / decisions-in-flight / the *why* /
    rejected-with-rationale). For this change that is
    `.changes/create-portable-agent-context.WORKING-SET.md`.
  - `brain_reader` → select the bound change's relevant brain entities (start
    simple, per spec: the change's Opportunity / Requirements / Decisions /
    Design / Scenarios + recency — via the existing `_brain_query` read seam,
    NOT a new traversal). Reuse, don't rebuild.

## Contract

No new public port. This is REINFORCE-Instrument wiring of existing components
into the live spawn/resume path (TDD §3.2 — the arrow is already designed; this
WP makes it real). The shape:

- The manager's composition root constructs a `ContextPayloadAssembler` bound to
  the change's `ThreadStore` (via the existing `_durable_store_for(key)` /
  `_thread_store_factory`), with **real** `working_set_reader` + `brain_reader`
  injected (the injection points already exist on the assembler ctor — WP-003).
- The readers are pure, side-effect-free functions of the change/thread id
  (WPB-01 dependency direction preserved — no provider, no subprocess; the
  store adapter and these two readers own all IO, kept out of the assembler).
- At the spawn / resume seam (before `_spawn_process` resolves the brief via
  `claude_pty._read_pre_prompt`), the manager assembles the payload, renders it
  to a vendor-neutral brief fragment, and composes it into the change's
  `pre_prompt.txt` sidecar — so the existing brief argv seam delivers it
  unchanged (no new injection mechanism, ADR-004/005).
- A thread with no checkpoint yet (`MEMORY_NOT_FOUND`) degrades to the existing
  default brief (the resume must never crash the spawn — mirror
  `_read_pre_prompt`'s ignore-on-bad-id posture and `append_event`'s isolation).
- Rendering is **additive over** the existing `_default_change_pre_prompt`: the
  rich payload augments the default brief; it does not replace the change
  binding / recon pointer the default already carries.

## Definition of Done

**Red** — `test_live_resume_injection.py` failing FIRST, driving the **LIVE**
`SessionManager` spawn/resume path (NOT the assembler directly):

- Stand up a real `LocalThreadStore` under an explicit tmp root (never
  `~/.claude/projects`), seed a non-empty thread + a checkpoint, AND write a
  real `.changes/{primitive}-{slug}.WORKING-SET.md` + at least one real brain
  entity for the bound change.
- Drive `manager.open(key, spec)` (or `_respawn`) with `spec.brief_change_id`
  set to the bound change, the durable store factory pointed at the tmp store.
- **Make the provider transcript unavailable** (point `HOME` at an empty dir so
  `~/.claude/projects` carries nothing).
- **Observe the rich payload reaching the brief**: assert the spawned agent's
  resolved brief (the `pre_prompt.txt` the adapter's `_read_pre_prompt` returns,
  or the argv element `spawn_argv` produces) contains the assembled
  Sulis-owned context — and crucially that it carries **REAL Working Set
  content** (a string from the WORKING-SET.md) AND **REAL brain content** (an
  entity from `_brain_query`), not empty-lambda output. Assert it stays within
  the standard-tier budget and is vendor-neutral (no Claude-JSONL structure).
- This is the acceptance: **a live-path observation, not a component call.** A
  test that constructs `ContextPayloadAssembler` / `seed_payload_for_resume`
  itself does NOT satisfy Red — it must go through `SessionManager`.

> Provider transcript unavailable / no real second provider in scope: drive the
> manager's spawn path with a test/stub adapter that records the resolved brief
> argv (the same shape `claude_pty.spawn_argv` produces) — the assertion is on
> what the manager composed into the brief seam, observed at the spawn boundary.

**Green** — the manager constructs the assembler with real readers at the
composition root and composes the assembled+rendered payload into the brief
sidecar at the spawn/resume seam; the live drive passes; Working Set + brain
content are present and real; budget + vendor-neutral assertions hold
end-to-end through the manager.

**Blue** —
- No mock on the integration path (MEA-09): real store, real readers, real
  assembler reached through the real manager; a stub adapter is permitted only
  to capture the resolved brief at the spawn boundary (it is the observation
  surface, not a mocked-out collaborator on the assemble path).
- Dependency direction preserved (MEA-01 / WPB-01): the readers stay pure; the
  assembler still touches no filesystem/provider — IO lives in the store
  adapter and the two injected readers, wired only at the composition root.
- The assemble/inject runs OFF the live event hot path (at the spawn/resume
  seam), never inside the `on_event` observer fan-out (WP-004 ADV-1 — a
  payload-assembly error must not stall the live pump). An assembly failure
  degrades to the default brief, isolated and logged, never raised into the
  spawn.
- Extract the brief-render fragment as one named function (one definition of
  "render the payload into the brief") if a second call site appears (EP-03).

## Verification

Shape 1 (concrete): `adapter: backend`,
`artifact: tests/integration/test_live_resume_injection.py`. The covering
journey is the spec's **provider-independent resume** — re-driven over the
**live manager path** (this WP supersedes WP-007's component-level drive as the
acceptance for the headline capability; WP-007's test stays as the
component-level contract test).

## Notes

- **Why REINFORCE-Instrument, not EXPAND-Create.** The components exist
  (WP-003/004); the brief seam exists (ADR-004/005, `claude_pty`). This WP
  *instruments the live spawn/resume path* to use them — no new port, no new
  architecture. (Catalogue cross-group walk: REUSE the assembler + readers +
  brief seam; the move is REINFORCE-Instrument over the existing pump/spawn.)
- **File scope (no overlap with WP-010):** `manager.py` (the spawn/resume
  wiring + composition root), `durable_sink.py` (if the resume-seed helper needs
  a thin live entry point), `context_payload.py` (only if the reader injection
  needs a documented composition-root constructor — the ctor params already
  exist), the two real readers (new small modules or functions, e.g. a
  `working_set_reader` over `.changes/*.WORKING-SET.md` and a `brain_reader`
  over `_brain_query`), and the new wiring test. Parallelisable with WP-010.
