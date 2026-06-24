---
id: CH-GJ9KQR-WP-011
change_id: "01KVX26BDXGJ9KQRJ11HACHMZV"
kind: backend
primitive: reinforce-instrument
group: reinforce
title: Make rich-context resume robust to a cold memory (regenerate summary on demand + keep it fresh)
status: pending
dependsOn: [CH-GJ9KQR-WP-002, CH-GJ9KQR-WP-003, CH-GJ9KQR-WP-004, CH-GJ9KQR-WP-009]
characterisation_test: plugins/sulis/scripts/tests/integration/test_cold_memory_live_resume.py
implements:
  - "spec:create-portable-agent-context#resume-from-our-context"
  - "spec:create-portable-agent-context#structured-summary-regenerated-at-boundaries"
  - "TDD.md§3.2 (the `◀── assembled payload ──` brief-injection arrow), §4 (degrade path), §5 (Proof)"
verification:
  adapter: backend
  artifact: plugins/sulis/scripts/tests/integration/test_cold_memory_live_resume.py
prov:
  wasGeneratedBy: "engineering-architect:codebase-audit"
  source: "consumer reality check (drove the REAL SessionManager resume with no prior checkpoint): the rich path never fires because its precondition — a saved ThreadMemory — is never established in the live flow; TDD.md§3.2/§4/§5"
estimatedTokenCost:
  input: ~16k
  output: ~10k
---

## Context

TDD §3.2 (the brief-injection arrow), §4 (Armor — the degrade path), and §5
(Proof — the live-path provider-independent-resume acceptance).

**This WP closes the final live-path gap a consumer-level reality check found
by driving the REAL `SessionManager` resume as a consumer.** WP-009 wired the
live assemble→inject seam (`manager._compose_resume_brief`, off both `open`
and `_respawn`) — and it works **given a saved `ThreadMemory`**. The gap is
that, in the live flow, **a memory is never established**, so the rich path
never actually fires:

- **The assembler HARD-REQUIRES the memory.** `ContextPayloadAssembler.assemble`
  (`context_payload.py:249`) calls `self._store.get_memory(thread_id)`, which
  raises `ExpectedError(MEMORY_NOT_FOUND)` when no checkpoint exists. It does
  NOT build the summary from messages on demand.

- **Nothing builds the memory in the live flow.** `DurableAppendSink.checkpoint()`
  (`durable_sink.py:239`) is the ONLY thing that writes a `ThreadMemory`, and
  its only caller, `SessionManager.checkpoint(key)` (`manager.py:720`), has
  **zero callers anywhere in the live flow** (verified by grep — referenced
  only in tests; it is a dead hook). The durable sink appends messages live,
  but a memory is never written.

- **Net effect (verified by driving the live compose with no prior checkpoint).**
  `_compose_resume_brief` catches `MEMORY_NOT_FOUND`, logs *"resume payload
  assembly failed (degrading to the default brief)"*, and the agent receives
  the **plain brief**. The graceful degradation (WP-004 isolation) works
  correctly — but the headline capability ("resume recovers rich context from
  OUR store") still does NOT happen in the real flow, because its precondition
  is never met. WP-009's own `test_live_spawn_degrades_to_default_when_assembly_fails`
  encodes this current behaviour: no checkpoint → plain brief.

**The headline capability is the first resume.** The cold-memory case is not an
edge case — it is the COMMON case: the first time a thread is resumed (death,
login-expiry, fresh attach) there has been no checkpoint, so today every first
resume gets the plain brief. The rich path must fire from durable messages
alone.

## Contract

No new public port. REINFORCE-Instrument: make the existing rich-resume path
robust to a cold memory, and keep the memory fresh at live lifecycle
boundaries. Two folded moves over the same live path (one coherent wiring):

**1. Regenerate the structured summary ON DEMAND when no memory exists yet
(the load-bearing move).**

- On `MEMORY_NOT_FOUND`, the resume seed path regenerates the `ThreadMemory`
  from the thread's durable messages — `store.get_messages(thread_id)` +
  the existing `summarise_memory` seam (the SAME WP-003 free function
  `DurableAppendSink.checkpoint` already uses at `durable_sink.py:249-252`) —
  rather than failing. **Reuse, don't reimplement** (EP-03): the on-demand
  build and the checkpoint build MUST share the single definition of "the
  thread's structured summary" (`summarise_memory` under the standard-tier
  budget). If two summary builders would otherwise exist, extract the shared
  step in this WP's Blue.
- The preferred seam is `seed_payload_for_resume` / the assembler: on
  `MEMORY_NOT_FOUND`, build the memory from messages and assemble over it,
  delivering the same `ContextPayload` shape the warm path delivers. The
  three-category error contract is preserved for the genuinely-empty case
  (a thread with NO messages AND no memory still degrades, see Blue).
- This makes resume work on the **FIRST resume, before any checkpoint has
  run** — without ever reading the provider transcript (ADR-004).

**2. Keep the memory fresh at a natural lifecycle boundary (spec: "structured
summary, freshly regenerated at session/checkpoint boundaries").**

- Wire `SessionManager.checkpoint(key)` (the live-dead hook) into the live
  session lifecycle so the memory is kept current. The natural boundary: at
  session close (`manager.close`, `manager.py:488`, before the sink is popped
  at line 510) and/or immediately before `_respawn` (`manager.py:927`, where
  the sink is already in hand at line 948). The maintenance tick
  (`_maintenance_tick`, `manager.py:952`) is an acceptable additional boundary
  if a crystallisation cadence is wanted. Pick the boundary(ies) that make the
  memory present for the NEXT resume; record the choice in an inline note.
- The on-demand build (move 1) is the correctness floor (first resume works
  with zero checkpoints); the boundary checkpoint (move 2) is the freshness
  optimisation (subsequent resumes read a current, pre-built memory).

**Isolation preserved throughout (WP-004 ADV-1 — non-negotiable).** A memory
build or checkpoint failure MUST degrade to the plain brief, isolated and
logged, and MUST NOT crash the spawn or stall the live pump. Move 2 runs OFF
the live event hot path (at close / respawn / maintenance boundaries), never
inside the `on_event` observer fan-out. Move 1 runs at the spawn/resume seam
inside `_compose_resume_brief`, whose existing try/except already isolates the
spawn — the on-demand build sits inside that same isolation envelope.

**Dependency direction preserved (MEA-01 / WPB-01).** The on-demand build reads
through the `ThreadStore` port (`get_messages`) and reuses `summarise_memory`
(a pure function); the assembler still touches no filesystem/provider. No new
IO surface, no provider read.

## Definition of Done

**Red** — `test_cold_memory_live_resume.py` failing FIRST, driving the **LIVE**
`SessionManager` resume on a **cold memory** (NOT the assembler directly, NOT
with a pre-created memory):

- Stand up a real `LocalThreadStore` under an explicit tmp root (never
  `~/.claude/projects`). Seed a non-empty thread with durable **messages**
  via `append_message` — and **do NOT** `put_memory` and **do NOT** call
  `checkpoint` (the whole point is the cold-memory live path). Write a real
  `.changes/{stem}.WORKING-SET.md` with a distinctive sentinel and at least one
  real brain entity for the bound change (so the rich content is observably
  real, mirroring WP-009's harness).
- Drive `manager.open(key, spec)` (or `_respawn`) with `spec.brief_change_id`
  set to the bound change ULID, the durable store factory pointed at the tmp
  store, and the **provider transcript unavailable** (`HOME` pointed at an
  empty dir so `~/.claude/projects` carries nothing).
- **Observe the rich fragment reaching the brief**: assert the resolved brief
  (the `pre_prompt.txt` the adapter's `_read_pre_prompt` returns, or the argv
  element `spawn_argv` produces) contains the assembled Sulis-owned context —
  at minimum the **conversation summary** regenerated from the durable
  messages, AND (when present in the change worktree) the **REAL Working Set**
  sentinel and **REAL brain** entity. Assert it stays within the standard-tier
  budget and is vendor-neutral (no Claude-JSONL structure).
- This is the acceptance: **a cold-memory live-path observation.** A test that
  pre-creates the memory (`put_memory`), or calls `checkpoint` itself, or
  constructs `ContextPayloadAssembler` / `seed_payload_for_resume` directly,
  does **NOT** satisfy Red. The memory must be built on demand, reached through
  the real `SessionManager`.

> The current behaviour this Red inverts: WP-009's
> `test_live_spawn_degrades_to_default_when_assembly_fails` asserts that a cold
> memory yields the DEFAULT brief. After this WP, the cold-memory path yields
> the RICH brief — update/replace that degrade-assertion to cover the
> genuinely-unrecoverable case instead (no messages AND no memory → still
> degrades; see Blue), so the isolation contract stays pinned.

**Green** — the resume seed regenerates the memory from durable messages on
`MEMORY_NOT_FOUND` (reusing `summarise_memory`), the live cold-memory drive
passes, the rich fragment (conversation summary at minimum; Working Set + brain
when present) reaches the brief, budget + vendor-neutral assertions hold
end-to-end through the manager; AND a checkpoint is taken at the chosen live
boundary so the next resume reads a fresh, pre-built memory.

**Blue** —
- **Reuse, one definition of the summary (EP-03 / Non-Neg #2).** The on-demand
  build and `DurableAppendSink.checkpoint` MUST share the single
  `summarise_memory`-under-standard-budget step. If a second summary builder
  would appear, extract the shared step (a small named helper, e.g. a
  "regenerate memory from the store" function) and have BOTH call sites use it.
- **No mock on the integration path (MEA-09):** real store, real readers, real
  assembler reached through the real manager; the brief-recording stub adapter
  is permitted only as the observation surface at the spawn boundary (reuse
  WP-009's recording adapter; it is not a mocked-out collaborator on the
  assemble path).
- **Isolation intact (WP-004 ADV-1):** the genuinely-unrecoverable case — a
  thread with NO messages AND no memory — still degrades to the plain brief,
  isolated and logged, never raised into the spawn. Pin this with a negative
  case in the test. The boundary checkpoint (move 2) is wrapped so its failure
  cannot stall close/respawn/maintenance.
- **Dependency direction preserved (MEA-01 / WPB-01):** the on-demand build
  reads only through the `ThreadStore` port; the assembler still touches no
  filesystem/provider; no provider transcript is read on any path.
- **Off the hot path:** move 2's checkpoint runs at close / respawn /
  maintenance boundaries, never inside `on_event`.

## Verification

Shape 1 (concrete): `adapter: backend`,
`artifact: tests/integration/test_cold_memory_live_resume.py`. The covering
journey is the spec's **provider-independent resume** — driven over the
**live manager path with a cold memory** (no pre-existing `ThreadMemory`, no
checkpoint called). This WP completes the live-path acceptance WP-009 began:
WP-009 proved the warm-memory live path; this proves the cold-memory live path
(the first-resume common case). WP-009's live test stays as the warm-path
contract; this WP adds the cold-path drive and converts WP-009's
degrade-on-cold-memory assertion into the genuinely-unrecoverable case.

## Notes

- **Why REINFORCE-Instrument, not EXPAND-Create.** The components exist
  (WP-003 assembler, WP-004 `summarise_memory` + `DurableAppendSink.checkpoint`
  + `seed_payload_for_resume`, WP-009 live wiring). This WP *instruments the
  live resume path* to be robust to a cold memory (regenerate on demand) and
  wires the existing dead `checkpoint` hook into the lifecycle — no new port,
  no new architecture. Catalogue cross-group walk: REUSE the assembler +
  `summarise_memory` + the live compose seam + the existing `checkpoint`
  hook; the move is REINFORCE-Instrument over the existing spawn/pump/lifecycle.
- **Why the on-demand build is the floor, not the freshness checkpoint alone.**
  Wiring `checkpoint` into the lifecycle (move 2 only) would still leave the
  VERY FIRST resume cold (no checkpoint has run before the first resume after a
  death/login-expiry). The on-demand build (move 1) is what makes the headline
  capability fire on the first resume. Move 2 keeps subsequent resumes cheap
  and fresh. Both are needed; move 1 is load-bearing.
- **File scope (disjoint from any other open WP):**
  `context_payload.py` (the `assemble` on-demand-on-`MEMORY_NOT_FOUND` branch,
  OR the regenerate step it delegates to), `durable_sink.py`
  (`seed_payload_for_resume` / a shared "regenerate memory from store" helper
  so the assembler and checkpoint share one summary definition), `manager.py`
  (wire `checkpoint(key)` into close/respawn/maintenance; the
  `_compose_resume_brief` isolation envelope is unchanged), and the new
  cold-memory live-path test. WP-009 / WP-010 are done — no concurrency
  concern.

> Note from WP-009/010 security review (ADV-1, fold in here since this WP touches
> summarise_memory): the assembler trims messages + journal to the tier budget but
> copies `participant_context` (the Working Set + brain text) through VERBATIM — a
> large WORKING-SET.md ships an over-budget brief mislabelled as standard tier
> (e.g. 100KB WS → ~25k tokens at a 1.5k budget). Trim participant_context into the
> tier cap too (in summarise_memory / _fit_to_budget, or bound the read), so the
> budget guarantee holds for a large Working Set, not just a large thread.
