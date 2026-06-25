# Decompose Validation — portable-agent-context (CH-GJ9KQR), remediation wave

> Rubric: `plugins/sulis/references/decompose-validation-rubric.md` v0.5.0
> Scope: the **remediation wave** WPs (WP-009, WP-010) and the **remediation
> follow-up** WP (WP-011), all added after consumer-level reality checks found
> the headline capability built but not fully live. The done set (WP-001..008)
> was validated at the original decompose; this run re-validates the full set
> with the three remediation WPs in place.

## At a glance

**Verdict: PASS-WITH-RATIONALE.**

Three remediation work packages close the verified live-path gaps. WP-009 wires
the live assemble→inject resume path (with real Working Set + brain readers) so
the "resume recovers rich context from our store" capability runs in the live
`SessionManager`. WP-010 closes the OpenAI-key redaction blind spot on the
store-write surface. **WP-011** closes the FINAL live-path gap: driving the real
`SessionManager` resume as a consumer found WP-009's rich path only fires *given
a saved memory*, but the live flow never establishes one (the assembler
hard-requires `get_memory`; the only thing that writes a memory —
`SessionManager.checkpoint` — is a dead hook with zero live callers), so every
first resume still degrades to the plain brief. WP-011 regenerates the
structured summary on demand from durable messages (reusing the WP-003
`summarise_memory` seam) so the FIRST resume works before any checkpoint, and
wires `checkpoint` into the live lifecycle to keep the memory fresh — WP-004's
degrade-to-plain-brief isolation preserved throughout. Its acceptance is a
**cold-memory live-path observation** (no pre-created memory, no checkpoint
called), not a component call.

The single SHOULD finding (two cross-kind dependency edges) is **pre-existing on
the already-shipped WP-006** (the optional cockpit frontend WP) and is not
introduced by any remediation WP; rationale recorded below.

---

## Summary

| Metric | Count |
|---|---|
| WPs validated | 11 (WP-001..011; this run added WP-011) |
| Total checks | 10 phases |
| PASS | 9 phases |
| FAIL (MUST) | 0 |
| FAIL-WITH-RATIONALE (SHOULD) | 1 (P4.09 — pre-existing on WP-006) |

---

## Phase-by-phase results

| Phase | PASS | FAIL | Notes |
|---|---|---|---|
| 1 Inventory completeness | ✓ | — | WP-009/010/011 carry Context, Contract, DoD (Red/Green/Blue), `id:` (sequence), `estimatedTokenCost:`, `dependsOn:` — same frontmatter-driven shape as the shipped WP-001..008. |
| 2 Atomicity | ✓ | — | Each WP is one coherent move; ≤15 files; titles carry no " and ". WP-011 folds the on-demand-build (correctness floor) + the lifecycle checkpoint (freshness) over the SAME live resume path / SAME files (`context_payload.py` / `durable_sink.py` / `manager.py`) — one coherent move, not a bundle (the on-demand build alone leaves a non-shippable intermediate where the first resume after a fresh checkpoint goes stale; the checkpoint alone leaves the first-ever resume cold). |
| 3 Module naming + clean code | ✓ | — | Descriptive kebab slugs; no jargon abbreviations; module names (`manager.py`, `durable_sink.py`, `context_payload.py`, `_secret_patterns.py`) are the existing discoverable names. |
| 4 Dependency graph correctness | ✓ (4.01–4.08) / ⚠ (4.09) | — | DAG acyclic; all deps resolve; topo order valid. WP-011 `dependsOn` WP-002/003/004/009 (all backend; WP-009 is the live wiring WP-011 makes cold-memory-robust) — adds zero cross-kind edges. 4.09: one SHOULD finding — pre-existing on WP-006, NOT any remediation WP (see Recommended improvements). |
| 5 Performance + non-functional | ✓ | — | No request-handler primitives in this run; WP-011 records the off-hot-path constraint (the lifecycle checkpoint runs at close/respawn/maintenance, never inside `on_event`) + the standard-tier budget on the regenerated summary; no external-API WP. N/A by primitive. |
| 6 Peer-collision risk | ✓ | — | `wpx-index audit-contracts` → `fixture_violations: []`. WP-011 shares the `manager.py` / `durable_sink.py` / `context_payload.py` region with the now-`step-7-complete` WP-009, but WP-009 lands FIRST (WP-011 `dependsOn` it) — sequential, not concurrent, so no shared-`Create` collision. WP-010's scope (`_secret_patterns.py`) is disjoint. |
| 7 ServiceSpec compliance | — | — | N/A — no services introduced (no `service-specs/` for this change; local binding, ADR-002). |
| 8 Cross-WP identifier canonicalisation | ✓ | — | No invented ULID/`dna:`/`urn:` literals; identifiers (`CH-GJ9KQR`, thread id, change slug) sourced from the change record + TDD. |
| 9 P-VER (Verification Plan) | ✓ | — | TDD `## Verification Plan` present + canonical citation annotation present; WP-009/010/011 each carry `verification: adapter: backend` matching `kind: backend` (9.08). WP-011: Shape 1 concrete (`artifact: tests/integration/test_cold_memory_live_resume.py`). |
| 10 P-PLAT (Platform Contract) | ✓ | — | No `touch-class: write\|deploy` platform touch in this run (the deferred hosted-service adapter is out of scope, ADR-002). N/A. |

---

## Blocking gaps (MUST failures)

None. Every MUST passes. `wpx-index lint` → `header: canonical, round_trip: ok`,
`pending: 1`, exit 0. `wpx-index list-ready` → 1 pending (WP-011, gated behind
WP-009 — becomes ready when WP-009 flips `step-7-complete` → `done` on its
merge, exactly as WP-009 was gated behind WP-007); 8 done; 0 blocked.

---

## Recommended improvements (SHOULD failures)

**P4.09 — cross-kind dependency edge (pre-existing, WP-006).**
`wpx-index audit-contracts` reports WP-006 (frontend cockpit raw-view re-point)
`dependsOn` WP-002 / WP-004 (backend) directly. **This is pre-existing on the
already-shipped, done WP-006 — not introduced by the remediation wave.** Both
new WPs (WP-009, WP-010) are `kind: backend` and depend only on backend /
composite WPs, so they add zero cross-kind edges.

*Rationale (carried from the original decompose):* WP-006 is the optional /
deferrable cockpit strangle WP that reads the same store ops; the change has no
separate data-contract WP for the cockpit↔store read seam because the read
surface is the `ThreadStore` port itself (defined in the WP-001 contract WP).
The edge is acceptable-with-rationale and unchanged by this wave; remediating it
would be a separate cosmetic re-wire of a done WP, out of scope for closing the
verified live-path gaps.

---

## Detailed findings per check

### WP-009 — live assemble→inject resume wiring (GAP 1 + GAP 2)

- **Atomicity (P2):** one move — instrument the live spawn/resume seam to use the
  existing assembler + readers + brief seam. GAP1 (assemble+inject) and GAP2
  (real readers) are the SAME wiring over the SAME files (`manager.py` composition
  root + the two readers); separating them would create a non-shippable
  intermediate (an injected payload with empty readers is the exact stub the
  prove-run flagged). Correctly folded, not bundled.
- **Acceptance shape (the load-bearing requirement):** Red drives the **live
  `SessionManager`** spawn/resume path and observes the rich payload reaching the
  brief with REAL Working Set + brain content — explicitly NOT a direct
  `ContextPayloadAssembler` / `seed_payload_for_resume` call. This is the
  correction to WP-007, whose drive proved the component only.
- **Primitive (P3/P1.09):** `reinforce-instrument` — wiring existing components
  into the live path (the §3.2 brief-injection arrow was designed, never wired).
  No new port → not EXPAND-Create. Characterisation test recorded
  (`characterisation_test:` frontmatter) per the REINFORCE discipline.
- **Dependency (P4):** depends on WP-002/003/004/005 (the built components) +
  WP-007 (supersedes its component-level acceptance for the headline). All done;
  acyclic; ready.
- **P-VER (P9.08):** `verification: adapter: backend, artifact:
  tests/integration/test_live_resume_injection.py` — Shape 1 concrete; adapter
  matches `kind: backend`.

### WP-010 — scrub modern OpenAI keys on write (GAP 3)

- **Atomicity (P2):** one move — widen the shared secret catalogue with the
  OpenAI key pattern(s) + tests. Single control point (`_secret_patterns.py`);
  the redact + outbound-scrub + store-write consumers all inherit it (Non-Neg #2).
- **Verified blind spot grounding:** the prove-run drove the real detector — a
  realistic `sk-proj-…` and legacy `sk-…` key produced ZERO hits from both
  detect-secrets and the in-house catalogue, while Stripe/AWS/GitHub keys were
  correctly caught. The Red cases pin this (fail-before, pass-after) plus
  false-positive negatives (`ask-me`, short `sk-`, git SHA, ULID).
- **Primitive (P3):** `reinforce-harden` — a security primitive widened to cover
  a verified blind spot on a new persistence surface. Orthogonal REINFORCE move.
- **Peer-collision (P6):** disjoint scope from WP-009 — `_secret_patterns.py` +
  its tests only. Parallelisable.
- **P-VER (P9.08):** `verification: adapter: backend, artifact:
  tests/unit/test_secret_patterns.py` (+ outbound + store-write redaction) —
  Shape 1 concrete; adapter matches `kind: backend`.

### WP-011 — cold-memory resume (on-demand summary + fresh memory)

- **Verified gap grounding:** driving the REAL `SessionManager` resume as a
  consumer with NO prior checkpoint reproduced the failure: `_compose_resume_brief`
  catches `MEMORY_NOT_FOUND` (the assembler's `get_memory` at
  `context_payload.py:249`) and degrades to the plain brief, because the only
  thing that writes a memory — `SessionManager.checkpoint` (`manager.py:720`) —
  has zero live callers (grep-verified dead hook; referenced only in tests).
  WP-009's own `test_live_spawn_degrades_to_default_when_assembly_fails` encodes
  this current behaviour. So the headline ("resume recovers rich context")
  still does NOT fire on the common first-resume case.
- **Atomicity (P2):** one move — make the live rich-resume path robust to a cold
  memory. The on-demand build (regenerate the summary from `get_messages` +
  `summarise_memory` on `MEMORY_NOT_FOUND`) is the correctness floor; wiring
  `checkpoint` into the lifecycle is the freshness optimisation. Same live path,
  same files (`context_payload.py` / `durable_sink.py` / `manager.py`);
  separating them leaves a non-shippable intermediate. Correctly folded.
- **Acceptance shape (the load-bearing requirement):** Red drives the **live
  `SessionManager`** resume on a thread with durable **messages but NO
  pre-existing `ThreadMemory`** (no `put_memory`, no `checkpoint`), provider
  transcript unavailable, and OBSERVES the rich fragment (conversation summary
  at minimum; Working Set + brain when present) reaching `pre_prompt.txt`. A
  test that pre-creates the memory or calls `checkpoint` itself does NOT satisfy
  the WP — this is the cold-memory live path.
- **Reuse (Blue / Non-Neg #2):** the on-demand build and
  `DurableAppendSink.checkpoint` share the single `summarise_memory`-under-
  standard-budget definition (EP-03); no second summary builder.
- **Isolation (P5 / WP-004 ADV-1):** a memory build / checkpoint failure
  degrades to the plain brief, isolated and logged; the genuinely-unrecoverable
  case (no messages AND no memory) still degrades — pinned by a negative case.
  The lifecycle checkpoint runs OFF the `on_event` hot path.
- **Primitive (P3):** `reinforce-instrument` — instruments the existing live
  resume path to be cold-memory-robust and wires the existing dead `checkpoint`
  hook into the lifecycle. No new port → not EXPAND-Create. `characterisation_test:`
  recorded per the REINFORCE discipline.
- **Dependency (P4):** `dependsOn` WP-002/003/004/009 — all backend; WP-009 is
  the live wiring this WP makes cold-memory-robust. Acyclic; adds zero cross-kind
  edges.
- **P-VER (P9.08):** `verification: adapter: backend, artifact:
  tests/integration/test_cold_memory_live_resume.py` — Shape 1 concrete; adapter
  matches `kind: backend`.

---

## Methodology

- [✓] **P1 Inventory completeness.** 11 WPs read end-to-end. WP-009/010/011 carry
  Context, Contract, DoD (Red/Green/Blue), `id:` (sequence id, prefixed
  `CH-GJ9KQR-WP-NNN`), `estimatedTokenCost:`, `dependsOn:` — frontmatter-driven
  shape matching the shipped set. INDEX lists all 11. Dependency shape section
  present. Gaps: none.
- [✓] **P2 Atomicity.** Purpose statements single-move; touch surfaces ≤15
  files; no " and " in titles; one primitive each. WP-009 GAP1+2 fold justified
  (same files, one live path). WP-011 on-demand-build + lifecycle-checkpoint fold
  justified (same live path / same files; either alone is non-shippable).
- [✓] **P3 Module naming.** Descriptive slugs; existing discoverable module
  names; no jargon abbreviations.
- [✓] **P4 Dependency graph.** DAG built from `dependsOn:`. Cycles: 0. Orphans:
  0. All targets resolve. Topo order valid. WP-011 → WP-002/003/004/009 (all
  backend; zero new cross-kind edges). 4.09: 1 SHOULD finding — pre-existing
  WP-006 cross-kind edge, NOT any remediation WP; rationale recorded.
  `wpx-index lint` exit 0 (`header: canonical, round_trip: ok, pending: 1`).
- [✓] **P5 Performance + non-functional.** No request-handler/external-API
  primitives in this run. WP-009/011 record off-hot-path + standard-tier budget
  constraints (WP-011's lifecycle checkpoint runs at close/respawn/maintenance,
  never inside `on_event`). N/A by primitive.
- [✓] **P6 Peer-collision risk.** `wpx-index audit-contracts` →
  `fixture_violations: []`, `wp_count: 11`. WP-011 shares the manager/durable_sink/
  context_payload region with WP-009 but lands AFTER it (`dependsOn` WP-009) —
  sequential, no shared-`Create` collision; WP-010 disjoint. The two reported
  `violations` are pre-existing WP-006 cross-kind deps (P4.09), not collisions
  and not introduced by any remediation WP.
- [—] **P7 ServiceSpec compliance.** N/A — no services introduced (local
  binding, ADR-002; no `service-specs/`).
- [✓] **P8 Cross-WP identifier canonicalisation.** No invented ULID/`dna:`/`urn:`
  literals. Shared identifiers (`CH-GJ9KQR`, thread id, change slug) sourced from
  the change record + TDD.
- [✓] **P9 P-VER.** TDD `## Verification Plan` present + canonical
  `VERIFICATION_QUESTIONS.md` citation annotation present (9.01/9.06).
  WP-009/010/011 each carry a `verification:` field whose `adapter: backend`
  matches `kind: backend` (9.08). Shape 1 (concrete) for all three. Grandfather:
  not applicable (dogfood window).
- [—] **P10 P-PLAT.** N/A — no `touch-class: write|deploy` platform touch in this
  run (hosted-service adapter deferred, ADR-002).
