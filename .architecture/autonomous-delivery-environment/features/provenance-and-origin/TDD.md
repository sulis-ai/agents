# Technical Design — Files diffs-in-tree · Provenance view · Change origin

**Feature set of:** CH-01KT50 · `create-autonomous-delivery-environment`
**Mode:** brownfield extension — **extend** `apps/cockpit/` (EP-03)
**Parent TDD:** `../../TDD.md` (the cockpit seam, ports, read-only gate, hexagon)
**Tier:** L feature within a tier-L change (see `SIZING.md`, this folder)
**Design targets (signed / approved):**
- `contracts/visual/files-redesign/files-B-repo-browser.contract.md` — **SIGNED** (the repo-browser, already largely built; this set extends it with diff counts)
- `contracts/visual/brain-redesign/provenance-prototype.html` — the Provenance view (dashboard + run-log + coverage-map)
- `contracts/visual/brain-redesign/origin-badge-and-lens.html` — change-origin attribution
- `contracts/visual/end-to-end-journey.html` — the integration spec (files → diff + origin → trace → provenance)
- `contracts/visual/brain-redesign/_brain-brainstorm.md` — rationale (ship C front door, B then A as its two doors)
- `references/cognitive-load.md` (`/Users/iain/Documents/repos/platform/methodology/standards/cognitive-load.md`) — governs all surfaces

> **Respect, don't restate.** The cockpit's hexagonal seam, domain-owned
> ports, the **one sanctioned git-spawn site** (`lib/gitShow.ts`), the
> read-only gate (`scripts/check-read-only.sh` + `read-only-inventory.test.ts`),
> `tokens.css`, the contract/adapter/fake test discipline, and the chat Turn
> Card summaries (`lib/turnSummaries.ts`, `shared/groupTurns.ts`) already
> exist. This TDD references them and specifies **only** what this feature
> set adds. ADR numbering continues the change's namespace from **ADR-010**
> (the change's External ADR Registry tops out at ADR-009).

---

## 1. The shape of the feature set

Three capabilities, sequenced into **two slices** with a deferred third:

1. **Files diffs-in-tree** (Slice 1) — every changed-file row gains a `+N −N`
   count; folders roll those counts up. A pure **extension** of the already-
   shipped repo-browser (the SIGNED `files-B` contract), reached through the
   one git boundary.
2. **Provenance view** (Slice 1) — rename Brain → **Provenance**; replace the
   flat group-by-kind view with the founder-approved three-layer design: a
   **digest dashboard** (front door), a **run-log** lens, and a **coverage-map**
   lens. Reads the existing brain data; the dashboard's "flagged" tile and the
   run-log surface **real** `lifecyclerun` fields (`_gaps`, `_self_critique`,
   `confidence`, `outcome`).
3. **Change origin** (Slice 2) — a worded **Autonomous / Assisted·likely /
   Origin-unknown** badge on Files rows and in an open-file "How this file came
   to be" panel, tracing to a run (+confidence) or a conversation Turn Card.
   An **origin-attribution seam** computes inferred origin from commit ↔ run /
   commit ↔ conversation correlation; **origin-stamping** records it exactly at
   write-time going forward, turning inference into fact.

The architectural spine that holds it together: **every new read reaches data
through the existing seam** (the local Express server, NFR-ARCH-01); the **one**
new outbound read (numstat) routes through the **one** sanctioned git site; the
origin seam is a **domain-owned port** with an inferred adapter now and a
recorded adapter once stamping lands.

The load-bearing risk, and the one genuine founder call, is **origin-stamping**:
it writes commit metadata, and the cockpit is provably read-only (ADR-003).
The honest answer (designed below, ADR-013) is that stamping happens in the
**executor and chat-relay write paths — not in the cockpit read surface** — so
the cockpit's read-only guarantee is untouched. But there is a **pre-existing,
currently-RED read-only gate** that this feature set must reconcile to ship
green (see §3.5). That reconciliation is in scope and is the first thing the
slice does.

---

## 2. Form — structural integrity

### 2.1 The seam (unchanged principle, extended surface)

The server stays the seam. This set adds **read projections** behind existing
reads, **one new domain-owned port** (`OriginAttribution`), and **no new
transport**:

```
            apps/cockpit/
client  ──HTTP──▶  server (THE SEAM)
(React)            │
                   ├─ routes/  changed.ts (EXTEND: +numstat counts)
                   │           provenance.ts (NEW: dashboard digest + edges)
                   │           origin.ts (NEW: GET inferred/recorded origin)
                   ├─ lib/     readChangedFiles.ts (EXTEND: counts)
                   │           readProvenance.ts (NEW: digest + run-log + coverage projections over brain)
                   │           originAttribution/ (NEW: infer from commit↔run / commit↔turn)
                   ├─ ports/   OriginAttribution (NEW domain-owned port)
                   │           gitShow.ts (EXTEND: gitDiffNumstat — the ONE git site)
                   └─ adapters/ InferredOriginAttribution (NOW)
                                RecordedOriginAttribution (after stamping)
```

`OriginAttribution` is **EXPAND-Create**, not SUBSTITUTE-Wrap: the public face
is the cockpit's own port; `git log`/commit-trailer reads are *called by* the
adapter. Two adapters satisfy one contract — inferred (correlation) now,
recorded (read the stamped trailer/sidecar) once stamping lands — exactly the
fake-vs-adapter parity the cockpit already uses (ADR-012).

### 2.2 Component inventory (new / changed)

| Component | Move | Form note |
|---|---|---|
| `lib/gitShow.ts` → `gitDiffNumstat()` | EXPAND-Extend | added to the ONE sanctioned git site; `git diff --numstat <base> --`; read-only |
| `lib/readChangedFiles.ts` | EXPAND-Extend | merge per-file `{added, removed}` into each `ChangedFile` |
| `shared/api-types.ts` `ChangedFile` | EXPAND-Extend | `+ added: number \| null; removed: number \| null` (null = binary/unknown) |
| client `ChangedList.tsx` | EXPAND-Extend | render `+N −N` on file rows; fold child counts into folder rollups (reuse `countFiles`) |
| client `FolderOverview.tsx` | EXPAND-Extend | `+N −N` on overview rows |
| `lib/readProvenance.ts` | EXPAND-Create | digest tiles + run-log (runs→steps) + coverage (Why/What/How/Tested + focused trace) projections over the existing brain read |
| `lib/provenanceEdges.ts` | EXPAND-Create | pure edge resolver over `detail` (satisfies/verifies/decisions/of_run) — the coverage focused-trace |
| `routes/provenance.ts` | EXPAND-Create | `GET /api/changes/:id/provenance` (digest + lenses, one shape) |
| `shared/api-types.ts` provenance shapes | EXPAND-Create | `ProvenanceView`, `ProvenanceDigest`, `RunLogEntry`, `RunStep`, `CoverageColumn`, `FocusedTrace` |
| client `ProvenanceView.tsx` | SUBSTITUTE-Replace | replaces `BrainView.tsx`'s flat group-by-kind front door; `BrainView`/`BrainSection` retired (deprecate-then-delete, ADR-014) |
| client `ProvenanceDashboard.tsx` `RunLogLens.tsx` `CoverageMapLens.tsx` | EXPAND-Create | the front door + two doors (C → B → A; brainstorm) |
| `ports/OriginAttribution.ts` | EXPAND-Create | domain-owned; `originFor(change, path?) → Origin` |
| `adapters/InferredOriginAttribution.ts` | EXPAND-Create | correlate last-changing commit ↔ run window / ↔ conversation turn; honest `confidence: "inferred"` |
| `adapters/RecordedOriginAttribution.ts` | EXPAND-Create (Slice 2 tail) | read the stamped trailer/sidecar; `confidence: "recorded"` |
| `lib/originAttribution/correlate.ts` | EXPAND-Create | pure correlation (commit time/author/message ↔ run `at`/`outcome` ↔ turn timestamp) |
| `routes/origin.ts` | EXPAND-Create | `GET /api/changes/:id/origin` (+ optional `?path=`) |
| `shared/api-types.ts` origin shapes | EXPAND-Create | `Origin` discriminated union (autonomous / assisted / unknown) + `confidence: "inferred" \| "recorded"` |
| client `OriginBadge.tsx` | EXPAND-Create | worded Autonomous / Assisted·likely / Origin-unknown; honesty banner for inferred |
| client `HowThisFileCameToBe.tsx` | EXPAND-Create | the open-file origin panel; trace targets = run log / Turn Card + "Open conversation" |
| client `HowItCameToBeLens.tsx` | EXPAND-Create | Provenance lens grouping Autonomous/Assisted with counts |
| **origin-stamping (write side — NOT the cockpit):** | | |
| executor commit trailer/sidecar writer | EXPAND-Create | stamps `Sulis-Origin: autonomous; run=<ulid>; confidence=<n>` at the executor's commit (ADR-013) |
| chat-relay commit trailer/sidecar writer | EXPAND-Create | stamps `Sulis-Origin: assisted; conversation=<id>; turn=<n>` at the relay's commit (ADR-013) |
| reused: `RenderedPreview`, diff renderer, `tokens.css`, `groupTurns`, `turnSummaries`, Turn Card | REUSE | EP-03 — compose, don't rebuild |

The one `SUBSTITUTE-Replace` (ProvenanceView replacing BrainView's front door)
and the deprecate-then-delete of `BrainView`/`BrainSection` are recorded in
ADR-014. No REORGANISE primitive is needed (the brain *read* is reused as-is;
only the client front door is replaced).

### 2.3 Dependency direction

Client → server (HTTP) only. `lib/` + routes depend on the `OriginAttribution`
port, never on its adapters. Adapters depend on the outside world (the git
boundary, the brain tree, the transcript files). No client filesystem access
(NFR-ARCH-01). The numstat read is **only** in `gitShow.ts` — no second
`spawn("git")` site (the gate proves it).

---

## 3. Armor — operational hardening

This set is **read-only on the cockpit side**; the only writes are the
origin-stamps, which happen **outside** the cockpit, in the already-sanctioned
write paths. The hardening is therefore mostly: *keep the read-only guarantee
intact and provable* while the new reads land, and *contain the one git
extension* within the existing timeout/subprocess discipline.

### 3.1 The numstat read (reuse the existing git discipline)

`gitDiffNumstat` reuses `runGit` verbatim: `spawn` (not `exec`), `args:
string[]`, `shell: false`, the 5-second hard timeout with SIGKILL-on-timeout,
`GitError` on non-zero exit. `git diff --numstat` is read-only (no tree/index
mutation). Binary files report `-\t-` in numstat → mapped to `added: null,
removed: null` (the UI shows no count, not `+0 −0`). No new resilience
primitive is needed; the existing timeout is the bound.

### 3.2 The provenance + origin reads (fail-soft, like the brain read)

Both reuse the brain read's **fail-soft** posture: an absent `.brain`, a
malformed `lifecyclerun`, a missing edge target → the projection omits that
item rather than throwing. A change with no runs yields the dashboard's
**empty** ("no provenance yet") state (the design renders it). The origin seam
returns `{ kind: "unknown" }` (never an error) when neither a run window nor a
conversation turn correlates — the honest "Origin-unknown" badge.

### 3.3 Origin inference is honestly flagged (the trust property)

Every inferred origin carries `confidence: "inferred"` and the badge reads
**"Assisted·likely"** / shows the honesty banner ("we worked this out from the
timeline; it isn't a recorded fact"). A recorded origin (post-stamping) carries
`confidence: "recorded"` and drops the hedge. The seam **never** presents an
inference as a fact — this is the same no-fabrication discipline the chat relay
uses for "resumed" (parent TDD §3.1).

### 3.4 Origin-stamping bounds (the write side; ADR-013)

Stamping is **append-only commit metadata** at the moment the executor or the
relay already commits — it adds no new commit, no new process, no network. A
stamp failure is **non-fatal**: the commit still lands; the origin simply stays
inferred (graceful degradation back to Slice-2's inference path). The stamp is
a **commit trailer** (`Sulis-Origin: …`, the established Conventional-Commits
trailer convention — CP-01) with a **sidecar** fallback (`.sulis/origin/<sha>.json`)
only where a trailer can't be written. No secret, no PII in the stamp (a run
ULID, a conversation id, a confidence number — never message text).

### 3.5 The read-only gate — reconcile-to-green (MUST, blocking, in scope)

**The read-only gate is currently RED on this branch** — four violations the
feature set must reconcile before it can ship green (`bash
apps/cockpit/scripts/check-read-only.sh` fails today):

| File | Violation | Disposition (ADR-015) |
|---|---|---|
| `server/routes/advanced.ts` | two `router.post` (`/reveal`, `/processes/:pid/stop`) — gate rule 5 | **allow-list by path** as a *named operator-action seam*, OR refactor `/reveal` to a GET + drop `/stop` from the cockpit. Recommended: allow-list with a new rule class (operator-action), because reveal/stop are deliberate, audited OS-side actions — see ADR-015 |
| `server/lib/changeAdvanced.ts` | `process.kill(pid,"SIGTERM")` + `"SIGKILL")` — gate rule 4 (non-zero signal) | **allow-list by path** under the same operator-action seam; this is the one place a founder-initiated "stop this process" lives. The liveness probe stays signal-0 everywhere else |
| `server/lib/turnSummaries.ts` | `writeFile` (cache) — gate rule 1; `spawn("claude",…)` — gate rule 2b | **allow-list by path**: the summary cache is a derived, throwaway write (not change/worktree data) and the Haiku spawn is a neutral-cwd summariser (no project context, no session). Both pre-date this set; record the exception with rationale |

These are **pre-existing** (tasks #21/#22 + the turnSummaries pair); they are
**not introduced by this feature set**, but the feature set **cannot ship green
on top of a red gate**, so reconciling them is the **first WP** (WP-P00). The
reconciliation is an **ADR + gate allow-list + parallel test assertions** — the
same path-scoped, named-exception discipline ADR-003 already established (the
value is that each exception is *named and audited*, and everything else still
fails the gate). ADR-015 records each exception and its rationale; this is **not**
a blanket waiver and **not** a rewrite.

Origin-stamping needs **no cockpit gate change** (it lives in the executor +
relay, outside `apps/cockpit/`). ADR-013 records why the read-only guarantee
survives.

### 3.6 Observability

The provenance/origin reads log nothing sensitive (no message bodies, no file
contents) — parity with the brain read. The origin-stamp write logs one
structured line per stamp (`{sha, origin: autonomous|assisted, ref, outcome:
stamped|skipped}`) on the write side, never the message text.

---

## 4. Proof — verification protocol

### 4.1 What's reused

The cockpit's supertest route tests, Vitest component tests, axe-core a11y e2e,
the contract/fake-vs-adapter parity, and the read-only gate (script + inventory
test) all stay and extend.

### 4.2 What's added

**Slice 1 — Files diffs:**
- `gitShow.test.ts` (extend) — `gitDiffNumstat` parses `A/M/D + added\tremoved\tpath`; binary `-\t-` → null counts; non-zero exit → `GitError`; timeout → `TimeoutError`.
- `readChangedFiles.test.ts` (extend) — counts merged onto each `ChangedFile`; `baseKnown:false` legacy case unchanged.
- `routes.changed.test.ts` (extend) — 200 with counts; binary file shows null; clean change `[]`.
- `ChangedList.test.tsx` (extend) — `+N −N` on rows; folder rollup = sum of descendants; binary row shows no count.

**Slice 1 — Provenance:**
- `readProvenance.test.ts` (NEW) — digest tile counts (did/covered/decided/flagged) over `seed-brain-entities-fixture`; the **flagged** tile surfaces a real `_gaps`/`_self_critique`; empty-brain → empty dashboard; malformed `lifecyclerun` skipped.
- `provenanceEdges.test.ts` (NEW) — focused trace for one requirement resolves Why (opportunity), How (design+decision), Tested (scenario/testresult) from `detail` edges; a dangling edge omits, never throws.
- `routes.provenance.test.ts` (NEW) — supertest; 200 digest+lenses; 404 unknown; empty case; reading it starts **no** `claude` process (NFR-SEC-05 parity).
- `ProvenanceDashboard.test.tsx` `RunLogLens.test.tsx` `CoverageMapLens.test.tsx` (NEW) — four tiles + two doors; run→steps→detail; Why/What/How/Tested columns + a single focused trace (never an all-edges blob); worded status never colour-alone; axe-core on each.

**Slice 2 — Origin:**
- `correlate.test.ts` (NEW) — commit-in-run-window → autonomous+run+confidence; commit-near-turn → assisted+turn-ref; neither → unknown; **recorded trailer present → recorded (overrides inference)**.
- `OriginAttribution.contract.test.ts` (NEW) — **one suite** the inferred adapter AND the recorded adapter both satisfy (fake-vs-adapter parity; MEA pattern).
- `routes.origin.test.ts` (NEW) — 200 origin for a change; `?path=` for a file; honest `confidence` field present; 404 unknown.
- `OriginBadge.test.tsx` `HowThisFileCameToBe.test.tsx` `HowItCameToBeLens.test.tsx` (NEW) — worded badges (never colour-alone); inferred shows the honesty banner; trace to run log / Turn Card + "Open conversation"; lens groups Autonomous/Assisted with counts; axe-core.
- **Stamping tests (write side):** executor stamp writes a `Sulis-Origin: autonomous` trailer; relay stamp writes `Sulis-Origin: assisted`; a stamp failure leaves the commit intact + origin falls back to inferred (graceful degradation).

**Read-only gate (WP-P00):**
- `read-only-inventory.test.ts` + `check-read-only-script.test.ts` (extend) — exactly the named operator-action + summary-cache files are exception-listed; **any other** write / non-zero signal / process-start / POST still fails; the gate passes green after the allow-list (the literal `check-read-only.sh` returns clean).

### 4.3 Per-integration verification strategy (TDD concretion)

| Integration | Boundary | Strategy | Class | TDD concretion |
|---|---|---|---|---|
| numstat counts | the ONE git site (`gitShow.ts`) | extend the existing git-boundary tests with a real temp-repo fixture (existing pattern) | **existing** | `server/tests/gitShow.test.ts`; resilience: the existing 5s timeout + SIGKILL (no new primitive) |
| Provenance digest + lenses | in-process read over the brain tree | projections over `seed-brain-entities-fixture` (the parent change already defers this fixture) + at least one real `lifecyclerun` | **existing (fixture deferred upstream)** | `server/tests/routes.provenance.test.ts`; reuses the brain read fixtures |
| Coverage focused-trace | in-process edge resolve over `detail` | pure-function test over fixture entities with known edges | **existing** | `server/tests/provenanceEdges.test.ts` |
| Origin inference | in-process correlation over git log + run `at` + turn timestamps | pure correlation tested against a seeded temp-repo + run/turn fixtures | **deferred** | seam: `ports/OriginAttribution.ts`; fixture `recording-origin-correlation-fixture` (commits + runs + turns with known-true origins); resilience: read-only, fail-soft to `unknown` |
| Recorded origin (post-stamp) | read the stamped trailer/sidecar | the **same** `OriginAttribution.contract.test.ts` the inferred adapter passes | **deferred** | `server/tests/RecordedOriginAttribution.test.ts`; needs `fixture-stamped-commits` |
| Origin-stamping (write side) | executor + relay commit paths | unit-test the trailer writer + a stamp-failure-is-non-fatal test | **deferred** | seam: the executor/relay commit step; fixture `fixture-stampable-commit`; verified end-to-end **manually on the founder machine** (needs a real executor run + a real relay commit) |

`recording-origin-correlation-fixture`, `fixture-stamped-commits`, and
`fixture-stampable-commit` follow the canonical `{noun}-{noun}-{scope}`
identifier recipe so the slice-end review aggregates them.

### 4.4 Verification frontmatter shapes the WPs use (ADR-003 of the verification standard)

- Files-diffs, provenance read, coverage-trace WPs → **concrete**
  (`adapter: backend|frontend` + `artifact:` the named test).
- Origin inference + recorded adapter WPs → **deferred**
  (`adapter: backend` + `deferred-to-follow-on: recording-origin-correlation-fixture` /
  `fixture-stamped-commits`) for the live correlation, **concrete** for the
  pure-correlation logic against the fixture.
- Origin-stamping WPs → **deferred**
  (`adapter: backend` + `deferred-to-follow-on: fixture-stampable-commit`); the
  full live path is manual on the founder machine.
- The read-only-gate WP (WP-P00) → **concrete** (`adapter: backend` +
  `artifact: server/tests/read-only-inventory.test.ts`).

---

## 5. The surfaces → endpoints map

| # | Surface | Endpoint(s) | Reads | Slice |
|---|---|---|---|---|
| 1 | Files diffs-in-tree | `GET /api/changes/:id/changed` (EXTEND: `+ added/removed` per file) | git numstat via the ONE git site | 1 |
| 2 | Provenance dashboard + run-log + coverage | `GET /api/changes/:id/provenance` (NEW) | the existing brain tree (`lifecyclerun` + edges) | 1 |
| 3 | Change origin (badge + panel + lens) | `GET /api/changes/:id/origin` (NEW, optional `?path=`) | git log ↔ run ↔ conversation correlation (inferred); stamped trailer (recorded) | 2 |

All three are **GET-only** read projections reached through the seam. The
provenance view **renames** the existing `…/brain` surface in the UI; the
`…/brain` endpoint **stays** (the provenance projection composes it) — the
rename is a client front-door replacement (ADR-014), not an endpoint removal.

Full request/response shapes: extend `contracts/openapi.yaml` + the runtime
mirror in `shared/api-types.ts` (CF-02 — the contract is the single source of
truth). A ServiceSpec manifest is **not** newly required (CF-10): these are
read projections on an existing internal seam, founder-reviewed via the **signed
visual contracts**, not a published product surface.

---

## 6. The coherent surface (parent ADR-005)

These surfaces dock into the existing one-shell, two-level IA (board → thread).
Provenance is one of the thread's context-rail sections (replacing Brain in the
rail and nav). Origin badges live on Files rows and the open-file panel; the
"How it came to be" lens is a Provenance lens. One token system (`tokens.css`,
no raw hex), the stage palette tinting per entity-kind, worded status never
colour-alone (WCAG 1.4.1), ≤5 primary options at any point (CL-04), progressive
disclosure (dashboard → doors → detail; CL-02). The signed `files-B` contract
and the approved provenance/origin prototypes are the build targets; the
post-build visual check is against the **running surface** (L-13), not a token
diff.

---

## 7. Decomposition note

`/sulis:plan-work` produces atomic WPs. The contract-first seams
(numstat extension; origin-attribution endpoint) get a **contract WP first**,
then parallel backend/frontend WPs (CF-05). Suggested spine (dependsOn in
parens):

```
WP-P00 read-only-gate reconcile (none — blocks everything; ships the set green)
 ├─ WP-P01 contract: ChangedFile +counts + ProvenanceView + Origin shapes (P00)
 │   ├─ WP-P02 numstat backend (P01)  ┐ parallel
 │   ├─ WP-P03 files diffs frontend (P01) ┘  → WP-P04 integrate files diffs (P02,P03)
 │   ├─ WP-P05 provenance read backend (P01) ┐ parallel
 │   └─ WP-P06 provenance frontend: dashboard+run-log+coverage (P01) ┘ → WP-P07 integrate provenance (P05,P06)
 │
 └─ (Slice 2, after Slice 1 observed)
     WP-P08 contract: Origin seam + OriginAttribution port (P01)
      ├─ WP-P09 inferred-origin backend + correlation (P08) ┐ parallel
      ├─ WP-P10 origin frontend: badge + panel + lens (P08)  ┘ → WP-P11 integrate origin (P09,P10)
      ├─ WP-P12 origin-stamping write side (executor+relay trailers) (P08) — outside the cockpit
      └─ WP-P13 recorded-origin adapter (P12, same contract test as P09)
```

**Defer:** the origin **mode-timeline** (the "story" view,
`origin-mode-timeline.html`) — Slice 3, post-stamping; not decomposed here.

---

## 8. Verification Plan

<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->

> Concretises the parent change's `## Verification Plan` for this feature set.
> Nothing here contradicts it.

### What user-observable behaviour are we verifying

The founder opens Files and sees, on every changed row and rolled up onto its
folders, **how much changed** (`+N −N`); opens a file and sees its diff **plus**
how that file came to be. They open **Provenance** and get a plain-English
digest in ~10 seconds (what it did / covered / decided / flagged — the flagged
tile showing a real gap + the agent's own self-critique), then go deeper via
the run-log (runs → steps → detail) or the coverage-map (Why → What → How →
Tested + a single focused trace per requirement). On any file they see a worded
**Autonomous / Assisted·likely / Origin-unknown** badge that, when inferred,
honestly says so, and that traces to the run (+confidence) or the conversation
Turn Card with an "Open conversation" jump.

### Verification environment(s)

- **Local dev + CI** — supertest route tests, Vitest component tests, axe-core
  a11y, the read-only gate (`check-read-only.sh` returns clean after WP-P00).
- **Local (founder machine)** — origin-stamping end-to-end (needs a real
  executor run + a real relay commit); the full inferred→recorded transition.
- The change's **own dogfood path** — this set is itself delivered by the
  cockpit, so its provenance/origin surfaces describe its own runs.

### Bootstrap-from-zero case

Files-diffs + provenance read bootstrap from a fresh clone using a temp-repo
fixture + `seed-brain-entities-fixture` (deferred upstream) with at least one
real `lifecyclerun`. Origin **inference** bootstraps from
`recording-origin-correlation-fixture` (commits + runs + turns with known-true
origins). Origin **stamping** + the recorded adapter cannot fully bootstrap in
CI (need a real executor/relay commit) → `fixture-stampable-commit` +
`fixture-stamped-commits` cover the unit paths; the live path is manual.

### Per-integration verification strategy

See §4.3 (the table is the concretion). Idempotency: re-reading origin yields
the same answer (pure correlation); a re-stamp is a no-op (trailer already
present). Auth/authz: localhost-only, single founder (parent ADR). Failure if
unavailable: a missing brain/run/commit degrades to the empty/`unknown` state,
never an error. Observability: §3.6.

### Per-kind verification adapter

Spans **two** adapters:
- **`backend`** — `server/tests/{gitShow,readChangedFiles,readProvenance,provenanceEdges,routes.changed,routes.provenance,routes.origin,correlate,OriginAttribution.contract,read-only-inventory}.test.ts`.
- **`frontend`** — `client/src/tests/{ChangedList,ProvenanceDashboard,RunLogLens,CoverageMapLens,OriginBadge,HowThisFileCameToBe,HowItCameToBeLens}.test.tsx`; axe-core on each new surface; the L-13 running-surface check against the signed/approved contracts.

### Infrastructure needs surfaced (deferred)

- `recording-origin-correlation-fixture` — commits + run entities + conversation
  turns with **known-true** origins, so inference accuracy is testable.
- `fixture-stampable-commit` — a commit point the executor/relay stamp writer
  runs against (unit).
- `fixture-stamped-commits` — commits carrying `Sulis-Origin:` trailers, so the
  recorded adapter verifies from a fresh clone.

All follow the `{noun}-{noun}-{scope}` recipe.

---

## 9. Sizing Report

See `SIZING.md` (this folder). Tier **L feature** within the tier-L change
(sFPC ≈ 9 new surface; ASR ≈ 7, the read-only-gate reconciliation being the
load-bearing one). TDD length is at target because every capability **reuses**
(the git site, the brain read, the Turn Card summaries, the fake-vs-adapter
parity, the gate discipline) — the new work is projections + one port + one
honestly-flagged correlation, not new infrastructure. ADRs produced: **6**
(ADR-010..015), continuing the change's namespace; none duplicate the existing
registry. No circuit breaker tripped.

## 10. Open architecture questions (founder-owned only)

The genuinely founder-owned calls — surfaced, not guessed (§11 of the parent
TDD discipline):

1. **Origin-stamping — confirm the mechanism is acceptable.** Stamping writes a
   commit trailer (`Sulis-Origin: …`) at the executor's and the relay's existing
   commit — **outside** the cockpit read surface, so the cockpit stays provably
   read-only (ADR-013). It adds no new commit, no network, nothing published.
   This is a *behaviour change to how the agent commits* (every future autonomous
   /assisted commit carries an origin trailer). Confirm the trailer approach, or
   ask for the sidecar-only variant (`.sulis/origin/<sha>.json`, no commit-message
   change). Recommended: trailer (the established Conventional-Commits convention,
   CP-01; greppable, travels with the commit).
2. **The currently-RED read-only gate — confirm the reconcile-don't-remove
   stance.** The Advanced view's "reveal folder" and "stop a process you started"
   are real, founder-initiated OS actions that the gate forbids today. Recommended
   (ADR-015): keep the gate, add a **named operator-action exception** for exactly
   those two files (the same audited-exception discipline as the chat relay), so
   the app stays provably read-only everywhere else. Alternative: drop "stop a
   process" from the cockpit entirely (more conservative, removes a feature the
   founder already has). Confirm keep-with-exception or remove-the-feature.

Everything else is convention-default and recorded in the ADRs.
