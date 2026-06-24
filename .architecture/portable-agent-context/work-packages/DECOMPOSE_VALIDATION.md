# Decompose Validation — portable-agent-context (CH-GJ9KQR), remediation wave

> Rubric: `plugins/sulis/references/decompose-validation-rubric.md` v0.5.0
> Scope: the **remediation wave** WPs (WP-009, WP-010) added after a
> `/sulis:prove` consumer-level reality check found the headline capability
> built as components but not wired into the live system. The done set
> (WP-001..008) was validated at the original decompose; this run re-validates
> the full set with the two new WPs in place.

## At a glance

**Verdict: PASS-WITH-RATIONALE.**

Two new work packages close the verified gaps. WP-009 wires the live
assemble→inject resume path (with real Working Set + brain readers) so the
"resume recovers rich context from our store" capability actually runs in the
live `SessionManager` — its acceptance is a live-path observation, not a
component call. WP-010 closes the OpenAI-key redaction blind spot on the new
store-write surface. Both are ready now (all dependencies done), have disjoint
file scopes, and run in parallel.

The single SHOULD finding (a cross-kind dependency edge) is **pre-existing on
the already-shipped WP-006** (the optional cockpit frontend WP) and is not
introduced by this wave; rationale recorded below.

---

## Summary

| Metric | Count |
|---|---|
| WPs validated | 10 (WP-001..010; this wave added WP-009, WP-010) |
| Total checks | 10 phases |
| PASS | 9 phases |
| FAIL (MUST) | 0 |
| FAIL-WITH-RATIONALE (SHOULD) | 1 (P4.09 — pre-existing on WP-006) |

---

## Phase-by-phase results

| Phase | PASS | FAIL | Notes |
|---|---|---|---|
| 1 Inventory completeness | ✓ | — | WP-009/010 carry Context, Contract, DoD (Red/Green/Blue), `id:` (sequence), `estimatedTokenCost:`, `dependsOn:` — same frontmatter-driven shape as the shipped WP-001..008. |
| 2 Atomicity | ✓ | — | Each WP is one coherent move; ≤15 files; titles carry no " and ". WP-009 folds GAP1+GAP2 as ONE wiring (same files, one live path) — not a bundle. |
| 3 Module naming + clean code | ✓ | — | Descriptive kebab slugs; no jargon abbreviations; module names (`manager.py`, `durable_sink.py`, `context_payload.py`, `_secret_patterns.py`) are the existing discoverable names. |
| 4 Dependency graph correctness | ✓ (4.01–4.08) / ⚠ (4.09) | — | DAG acyclic; all deps resolve; topo order valid. 4.09: one SHOULD finding — pre-existing on WP-006, NOT this wave (see Recommended improvements). |
| 5 Performance + non-functional | ✓ | — | No request-handler primitives in this wave; WP-009 records the off-hot-path / budget constraints; no external-API WP. N/A by primitive. |
| 6 Peer-collision risk | ✓ | — | `wpx-index audit-contracts` → `fixture_violations: []`. WP-009 and WP-010 have **disjoint** file scopes (manager/durable_sink/readers vs `_secret_patterns.py`); no shared `Create`. |
| 7 ServiceSpec compliance | — | — | N/A — no services introduced (no `service-specs/` for this change; local binding, ADR-002). |
| 8 Cross-WP identifier canonicalisation | ✓ | — | No invented ULID/`dna:`/`urn:` literals; identifiers (`CH-GJ9KQR`, thread id, change slug) sourced from the change record + TDD. |
| 9 P-VER (Verification Plan) | ✓ | — | TDD `## Verification Plan` present + canonical citation annotation present; WP-009/010 each carry `verification: adapter: backend` matching `kind: backend` (9.08). |
| 10 P-PLAT (Platform Contract) | ✓ | — | No `touch-class: write\|deploy` platform touch in this wave (the deferred hosted-service adapter is out of scope, ADR-002). N/A. |

---

## Blocking gaps (MUST failures)

None. Every MUST passes. `wpx-index lint` → `header: canonical, round_trip: ok`,
exit 0. `wpx-index list-ready` → WP-009, WP-010 ready; 8 done; 0 blocked.

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

---

## Methodology

- [✓] **P1 Inventory completeness.** 10 WPs read end-to-end. WP-009/010 carry
  Context, Contract, DoD (Red/Green/Blue), `id:` (sequence id, prefixed
  `CH-GJ9KQR-WP-NNN`), `estimatedTokenCost:`, `dependsOn:` — frontmatter-driven
  shape matching the shipped set. INDEX lists all 10. Dependency shape section
  present. Gaps: none.
- [✓] **P2 Atomicity.** Purpose statements single-move; touch surfaces ≤15
  files; no " and " in titles; one primitive each. WP-009 GAP1+2 fold justified
  (same files, one live path).
- [✓] **P3 Module naming.** Descriptive slugs; existing discoverable module
  names; no jargon abbreviations.
- [✓] **P4 Dependency graph.** DAG built from `dependsOn:`. Cycles: 0. Orphans:
  0. All targets resolve. Topo order valid. 4.09: 1 SHOULD finding — pre-existing
  WP-006 cross-kind edge, NOT this wave; rationale recorded. `wpx-index lint`
  exit 0 (`header: canonical`).
- [✓] **P5 Performance + non-functional.** No request-handler/external-API
  primitives in this wave. WP-009 records off-hot-path + budget constraints. N/A
  by primitive.
- [✓] **P6 Peer-collision risk.** `wpx-index audit-contracts` →
  `fixture_violations: []`. WP-009 / WP-010 disjoint file scopes; no shared
  `Create`. The two reported `violations` are pre-existing WP-006 cross-kind
  deps (P4.09), not collisions and not this wave.
- [—] **P7 ServiceSpec compliance.** N/A — no services introduced (local
  binding, ADR-002; no `service-specs/`).
- [✓] **P8 Cross-WP identifier canonicalisation.** No invented ULID/`dna:`/`urn:`
  literals. Shared identifiers (`CH-GJ9KQR`, thread id, change slug) sourced from
  the change record + TDD.
- [✓] **P9 P-VER.** TDD `## Verification Plan` present + canonical
  `VERIFICATION_QUESTIONS.md` citation annotation present (9.01/9.06). WP-009/010
  each carry a `verification:` field whose `adapter: backend` matches `kind:
  backend` (9.08). Shape 1 (concrete) for both. Grandfather: not applicable
  (dogfood window).
- [—] **P10 P-PLAT.** N/A — no `touch-class: write|deploy` platform touch in this
  wave (hosted-service adapter deferred, ADR-002).
