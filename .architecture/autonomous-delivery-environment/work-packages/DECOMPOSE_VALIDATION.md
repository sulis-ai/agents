# Decompose Validation — autonomous-delivery-environment (CH-01KT50)

> **Date:** 2026-06-04 (VERTICAL re-slice) · **Decomposer:** sulis:engineering-architect
> **Inputs:** TDD.md (incl. §2.4/§3.6/§4.3/§5.1) + ADR-001..009 + contracts/{openapi.yaml (10 paths), DATA-CONTRACT-GUIDE.md (signed), visual/sulis-app.contract.md (SIGNED)} + SRD.md (FR-01..38, FR-N1..N11, NFR-DISC-01..06, UC-01..11) + the 11 stored verification scenarios A–K + an outside-in walk of apps/cockpit.
> **Standards:** WORK_PACKAGE_STANDARD (WP-01..11), CONTRACT_FIRST_STANDARD (CF-01..09), the vertical-slice + observed-acceptance re-slice mandate.
> **Verdict: PASS** over the whole 11-WP set.

## Why this re-slice exists (the root-cause it closes)

Across prior attempts, work was called "done" on green pipelines / passing
per-piece reviews / deferred verification while the **actual user round-trip was
never observed** — and the **consumption half** of a flow was repeatedly left
unbuilt until the end. The prior 27-WP plan sliced **horizontally** (separate
route WPs, separate UI WPs, ONE integration+acceptance WP at the end). An
outside-in walk of `apps/cockpit` confirmed the consumption half of every NEW
capability was entirely unbuilt: no chat send/stream/bridge route, no
concierge/onboarding/search/products/brain routes; `Chat.tsx` was read-only.

This re-slice makes that failure structurally impossible: each WP is a **complete
observable round-trip** (data + route + bridge + UI), and each carries an
**observed-acceptance gate** (drive the app and SEE the result; green-not-enough).

## Summary

**11 atomic WPs · 2 foundation (1 data contract, 1 signed visual contract) + 9
vertical journey round-trips.** The 9 round-trips map to the 11 stored scenarios
A–K (two slices each cover a journey pair: WP-006 = F+E, WP-011 = H+J).

```
WP count: 11 · foundation 2, vertical round-trips 9
missing dep refs: none · cycles: none · self-deps: none
ready (pending + all deps done): [WP-001] · done: [WP-002]
topo waves: [WP-001] → [WP-003] → [WP-004] → [WP-005, WP-006, WP-007] → [WP-008, WP-009, WP-010] → [WP-011]
```

The prior 27 horizontal WPs are archived verbatim under
`_archive-horizontal-2026-06-04/`; each vertical slice's `derived_from` records
which horizontal WPs it folds, so no contract is lost.

---

## RESLICE-01 Each WP is a complete observable round-trip — PASS

Every journey WP (003–011) spans **data + server route + (bridge where needed) +
the consuming UI** in one branch. No WP ships a route without its consuming UI,
or a UI without its backing route/bridge. Concretely:

- **WP-003** board: read-scope + GET /api/changes + the stage-column Board UI.
- **WP-004** status: status route + computeStatus/needsAttention libs + the thread shell (StageTrack + StatusHeader).
- **WP-005** chat: SessionBridge port+contract+recorded fixture + binding/lock libs + relay route + prod adapter + gate extension + the Composer/SSE UI.
- **WP-006** brain+previews: brain route + readBrain + BrainView + the rendered-preview wiring.
- **WP-007** search: search route + searchChanges + the SearchBar/filter UI.
- **WP-008** product switch: products route + full server-side scope + the ProductSwitcher UI.
- **WP-009** concierge: concierge route + conciergeRead + the ConciergeChat front-door UI.
- **WP-010** onboarding: confirmGate + repoFindOrCreate + onboarding orchestrator route + the OnboardingChat UI.
- **WP-011** start-from-intent: start route + classify/clone/start + the intent/route-offer UI.

The two foundations (WP-001 data contract, WP-002 signed visual contract) are the
only non-round-trip WPs — and they are the shared seam every slice builds on, by
design.

## RESLICE-02 Observed-acceptance gate on every slice — PASS

Each journey WP carries an `observed_acceptance` block with: the scenario id, the
`observable_result` (plain English), `how_observed` (drive the real app, perform
the action, see the result), `not_sufficient` (green CI / deploy / from-graph run
explicitly NOT enough), and `human_hops`. Each WP's last acceptance criterion and
its `verification_gates` include `observed_roundtrip` — the DoD is the observed
round-trip, with the from-graph `sulis-verify-acceptance --scenario` run sitting
on top of the human observation, never instead of it.

The three slices with an irreducibly-human hop name a **BLOCK-and-hand-to-founder**
step explicitly and add the `live_founder_machine` gate:
- **WP-005** chat — driving a real `claude` session (live/resume/spawn/mid-step).
- **WP-009** concierge — a live read-only answer (real `claude -p`).
- **WP-010** onboarding & **WP-011** start — real mint / real `git` / real `sulis-change start`.

All other slices (003, 004, 006, 007, 008) are fully observable by running the
local app, and say so (`human_hops: none`).

## RESLICE-03 Ordering: thinnest-fully-observable first, then dep + risk — PASS

- **FIRST = WP-003 (board READ)** — the thinnest fully-observable round-trip:
  open the app, see real changes; no live agent, no fixture for the human, no
  third-party hop. It proves the vertical pattern (data→route→UI in one branch,
  observed by driving) at lowest risk (a refactor of an existing read surface).
- **Two-way chat (WP-005) sequenced early** — the highest-risk consumption half,
  right after the thread shell it docks into (WP-004), before the lower-risk read
  slices (brain/search). The riskiest round-trip is proven early, not discovered
  broken at the end.
- The remainder follow dependency + risk: reads (006/007) parallel after the
  shell; product switch (008) promotes the trivial scope to the full roll-up;
  discovery (009/010/011) last as they reuse the chat composer + confirm gate.
- **Each slice is independently observable before the next starts.**

## WP-01 Identity — PASS

Every WP carries `id` (WP-001..011, unique), founder-readable `title` framed as
the journey round-trip, `kind` (contract×2 / full-round-trip×9), `source:
feature`, `change_id: 01KT500K2JTE2EGW6TPPQ4D4VN`, `slice_kind`
(foundation / round-trip), and `journey`.

## WP-02 Atomic scope — PASS

Each WP is one branch / one engineer delivering one round-trip. The slices are
larger than the old horizontal WPs because a round-trip is the irreducible unit —
a composer with no relay, or a relay with no composer, is exactly the half-built
failure this re-slice exists to prevent. **WP-005 (chat) is the largest** and its
body explicitly states it must NOT be split (consumption half ≠ production half),
with an internal Red-Green-Blue build order. This is deliberate: atomicity here is
"one observable round-trip", not "one file".

## WP-03 Acceptance criteria — PASS

Each round-trip WP lists falsifiable criteria covering the DATA/ROUTE half, the UI
half, and the OBSERVED round-trip, each tied to specific FR/NFR/ADR clauses
(verbatim acceptance preserved: FR-10 conversation-only search match, FR-N7
bounded search, FR-N10/N11 no-dangling-config, FR-31 idempotency, FR-37
server-side roll-up, FR-N8/N9 concierge containment, FR-N5 no-fabricated-completion).
The three founder-locked decisions are encoded as acceptance in WP-010
(local-only repo pre-selected; one Product per conversation; neutral two-letter
tile).

## WP-04 Test plan + WP-05 per-kind gates — PASS

Each round-trip WP names exact unit + integration + **observed** test artifacts
(supertest route tests, pure-lib unit tests, fixture-bound orchestrator tests,
`.test.tsx` component tests, the driven-app observation, and where applicable the
live founder-machine observation). Per-kind gates: contract (WP-001), and the
union of backend + frontend gates plus `observed_roundtrip` (and
`live_founder_machine` on 005/009/010/011) on every journey slice.

## WP-06 Lineage — PASS

Each WP has `derived_from` (recording the ADR/TDD/SRD clause AND which horizontal
WPs it folds), `generated_by` (re-slice-vertical/2026-06-04 + sulis:engineering-architect),
`addresses_findings` (empty — feature work), `invalidated_by` (null), `depends_on`.

## WP-07 Status — PASS

10 `pending`, 1 `done` (WP-002 — the SIGNED visual contract; `done` keeps the #45
gate open for all UI halves). Machine check: `ready = [WP-001]`.

## WP-08.5 / CF-05 Contract-first cross-kind — PASS (adapted to vertical slices)

- **The contract is the one foundation both halves of every slice build on.**
  WP-001 mirrors the full OpenAPI seam (reads + chat + products + discovery) into
  shared TS types — the single source of truth (CF-02). Within each vertical
  slice, the backend half and the UI half build against that fixed contract; they
  do not build against each other (CF-05), and they land together so the
  round-trip is observable.
- **CF-03 three-category errors** and **CF-09 streaming contract** are satisfied
  in WP-001 (the Error.code union carries chat + discovery + start codes;
  Onboarding/StartFromIntent/Concierge stream events are discriminated unions on
  the literal `type` field, mirroring ChatStreamEvent).
- **CF-07 conformance (recorded→real bridge parity)** is no longer a separate
  end-of-plan WP — it is folded into each bridge-touching slice (WP-005, 009,
  010, 011) as the BLOCK-and-hand-to-founder live observation on top of the
  recorded-fixture CI run. This is the central point of the re-slice: conformance
  is observed per round-trip, not deferred to one final integration WP.

## #45 Visual-contract gate — PASS (carried verbatim)

WP-002 carries `signed_off_at: 2026-06-03T08:31:03Z` + `provenance:
production-approved`, `status: done`. Every UI half (WP-003..011) depends on it
and the gate is satisfied at write-time and at each slice's done-transition. The
signed contract covers every surface incl. concierge, onboarding, product
switcher, per-product board.

## Sensitive act/front-door path constraints (FR-N / NFR-DISC) — PASS

The constraints travel WITH the round-trip that exercises them (not in a separate
late WP):
- **WP-005** chat: binding before any process start (NFR-SEC-02/06); one-in-flight
  lock (FR-20); read-only gate extension (the one sanctioned write path, ADR-003);
  no-fabricated-completion (FR-26/N5); no bodies in logs (NFR-SEC-03).
- **WP-009** concierge: read-only containment (zero writes/mints/starts/signals,
  FR-N8/NFR-DISC-05); consequential intent routed not acted (FR-N9); no new gate
  write-exception (ADR-006).
- **WP-010** onboarding: bounded search (FR-N7); emitter-only mint (FR-32);
  idempotent (FR-31); confirm-gated + all-or-nothing + no-dangling-config
  (FR-N6/N10/N11); no new config store (FR-36/NFR-DATA-01); the three
  founder-locked decisions.
- **WP-011** start: confirm-gated (FR-N6); local-first clone, clone-failure ⇒ no
  change (FR-30); investigation contained in a change (FR-34/N9).
- **WP-008** products: scope-selection verb, no data write/mint/start (FR-38);
  server-side roll-up keeps the seam the scope source of truth (FR-37, ADR-009).

## Change primitives — PASS

- **EXPAND-Extend** for WP-001 (extends shared/api-types.ts).
- **EXPAND-Create** for the new libs/routes/components across the journey slices.
- **REORGANISE-Refactor** for WP-003 (Dashboard → Board) and WP-004 (ThreadView →
  coherent shell) — each carries a `characterisation_test` in Red (EP-07,
  catalogue MUST).
- **EXPAND-Create, NOT SUBSTITUTE-Wrap, for SessionBridge (WP-005)** — an adapter
  for a port WE own; the `claude` CLI is *called by* the adapter (ADR-002). The
  WP carries `subject_ownership: domain-owned-port`. No Band-Aid wrapper, no
  internal-code wrap.
- **EXPAND-Reuse (not Wrap)** for the concierge/discovery transport — they ride
  the EXISTING SessionBridge (ADR-006); the discovery skills + spine emitters +
  classifier + `sulis-change start` are REUSED (ADR-007), not reimplemented.
- **No Wrap-over-internal, no wrapper rot.**

## EP-03 extend-don't-rebuild — PASS

REUSE-dominant: the SessionBridge (reused by concierge/discovery), the chat
composer + SSE client (WP-005, reused by WP-009/010/011), the
discover-project/-context/codebase-mapping skills, the Tenant/Product/Project
spine emitters, the `_specify_classifier`, `sulis-change start`, the existing
contract-preview/VIEWER renderer (reused by WP-006), the existing
ChangeCard/StageBadge/LivenessDot, and `tokens.css`. New code is thin
orchestration + scoping + the new UI surfaces. No rebuild; emitter-only entity
writes (FR-32).

## Scenario linkage (from-graph verification ON TOP OF observed) — PASS (with the same noted follow-up)

- A–F minted + linked to their delivering slice (A→003, B→004, C→005, D→007,
  E→006, F→006).
- G–K linked by name (`verifies_scenario: PENDING-MINT:<letter>` +
  `observed_acceptance.scenario`) to their delivering slice (G→010, H→011, I→009,
  J→011, K→008); author them (`sulis-author-scenario`) and backfill the
  `dna:scenario:<ULID>`. This is the correct hand-off shape — plan-work links the
  acceptance intent; the ULID is minted in specify and backfilled. Critically,
  the from-graph run is the LAYER ON TOP of the observed round-trip, never the
  acceptance by itself.

## Deferred infrastructure needs — PASS (each ships WITH its slice)

Unlike the horizontal plan (fixtures pooled toward end-of-plan integration WPs),
each fixture now lands inside the slice that needs it, so the round-trip is
observable when it lands:
- `recording-bridge-claude-session` → WP-005.
- `seed-brain-entities-fixture` → WP-006.
- `recording-bridge-discovery-session` → WP-009, WP-010, WP-011.
- `fixture-project-directory` → WP-010.
- `fixture-repo-create-target` → WP-010.
- `fixture-local-repo-for-clone` → WP-011.
All follow the canonical `{noun}-{noun}-{scope}` recipe.

## Dependency-graph machine check — PASS

```
WP count: 11 · foundation 2, vertical round-trips 9
missing dep refs: none · cycles: none · self-deps: none
done: [WP-002] · ready (pending + all deps done): [WP-001]
topo waves:
  wave 1: [WP-001]
  wave 2: [WP-003]
  wave 3: [WP-004]
  wave 4: [WP-005, WP-006, WP-007]
  wave 5: [WP-008, WP-009, WP-010]
  wave 6: [WP-011]
```

## Genuine founder-owned gaps

**None blocking decomposition.** The one genuinely founder-owned decision —
**where a newly-created repo lives** (local-only vs hosted-remote) — is RESOLVED
for this slice by the founder-locked default (LOCAL-ONLY `git init`,
confirm-gated, no GitHub publish unless separately confirmed) and baked into
WP-010. Hosted-remote remains a clearly-labelled, separately-confirmed opt-in
surfaced in the UI, not taken silently. The other two parked questions are
settled defaults baked into WP-010: **one Product per conversation** and **search
depth = recursive-under-the-chosen-folder-only**. The third founder-locked call —
**Product icon = neutral two-letter tile** — is baked into WP-010. **No new
founder decision is required to start building.**

The only founder-owned ACTION the re-slice surfaces (not a decision) is the
**BLOCK-and-hand-to-founder live observation** on WP-005/009/010/011 — driving a
real `claude` session — which is inherent to verifying a local agent-driven app,
not a gap in the plan.
