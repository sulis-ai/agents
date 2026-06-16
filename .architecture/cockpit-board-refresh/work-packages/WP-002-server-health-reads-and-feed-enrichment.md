# WP-002 — Server: derive health + last-activity, enrich the board feed

- **Sequence ID:** WP-002
- **dependsOn:** [WP-001]
- **kind:** backend
- **primitive:** EXPAND-Create (`computeHealth`, `readRigorForStage`, `readTestsState`) + REORGANISE-Refactor (`toWireChange`, `changes.ts`)
- **group:** expand
- **characterisation_test:** `server/tests/_change-lookup.test.ts` (pins current `toWireChange` output before the refactor adds fields)
- **Estimated token cost:** input ~22k / output ~8k
- **visual_contract:** n/a

## Context

TDD §1 (Server) + §2 (Armor A-1/A-2) + ADR-001 + ADR-002. The feed
(`GET /api/changes`) must carry, per change: the existing `needsAttention()`
verdict, the new `health` verdict, and `lastActivityAt`. No new endpoint — the
one feed is widened.

## Contract

New pure / best-effort modules:

- `server/lib/computeHealth.ts`
  ```ts
  export function computeHealth(input: {
    testsState: "green" | "red" | "unknown";
    rigorForStage: { ok: boolean; missing: string | null; determinable: boolean };
  }): ChangeHealth;
  ```
  Rule (ADR-001 + FR-31):
  - `red` tests **OR** `rigorForStage.ok === false` → **`off-track`** (reason
    names which).
  - **No CI/test state recorded (`testsState === "unknown"`) AND rigor cannot be
    determined (`rigorForStage.determinable === false`)** → **`unknown`**
    (reason from the fixed set: "no tests run yet" / "too early to tell"). This
    is the FR-31 honest read — a fresh Recon change with nothing behind it must
    NOT read on-track. (BR-12: Recon has no required artifact, so rigor alone
    never pulls a Recon change off-track; absent tests ⇒ unknown.)
  - Else → **`on-track`**.
  **Never emits `worth-a-look`** (reserved for the deferred OODA-spiral signal).
  Pure, no I/O. Reasons are a fixed enumerable set — never interpolated (FR-32).

- `server/lib/readRigorForStage.ts`
  ```ts
  export async function readRigorForStage(
    worktreePath: string, stage: WorkflowStage,
  ): Promise<{ ok: boolean; missing: string | null }>;
  ```
  Best-effort, **read-only**, **never-throws** (mirror `detectOpenBlocker`).
  Encodes the per-stage rule (BR-12): Specify/Design ⇒ spec exists; Implement ⇒
  a design or plan exists; Review/Ship ⇒ tests exist alongside code; Recon ⇒ no
  required artifact. Returns `{ ok, missing, determinable }`:
  - worktree/artifact dir readable and the rule resolves → `determinable: true`,
    `ok` per the rule.
  - worktree gone / artifact dir unreadable / can't resolve the rule →
    `{ ok: true, missing: null, determinable: false }` (can't prove drift ⇒
    don't flag off-track on absence alone; `determinable:false` feeds the
    `unknown` health read, FR-31 / BR-11).
  - **Path containment (MUC-4):** all reads stay inside the change's own
    worktree via `safeJoin`; a containment violation fails soft to
    `determinable: false`, never reads the escaped path, never throws.

- `server/lib/readTestsState.ts`
  ```ts
  export async function readTestsState(
    worktreePath: string,
  ): Promise<"green" | "red" | "unknown">;
  ```
  Best-effort read of the change's recorded CI/test state. Unknown on absence.

Modified:

- `routes/_change-lookup.ts` (`toWireChange`) — gains the enrichment. Signature
  takes the gathered signals (attention verdict, health, lastActivityAt) so it
  stays a pure shaper:
  ```ts
  toWireChange(record, liveness, enrichment: {
    needsAttention: NeedsAttention; health: ChangeHealth; lastActivityAt: string | null;
  }): Change
  ```
- `routes/changes.ts` — per record (inside the existing `Promise.all`): gather
  the cheap signals (`detectOpenBlocker`, last-turn shape → `needsAttention`;
  `readTestsState` + `readRigorForStage` → `computeHealth`; last-activity
  timestamp), pass into `toWireChange`. The **search shaping path** that reuses
  `toWireChange` is updated in lockstep so the board and search agree.

## Definition of Done

### Red
- [ ] **Characterisation:** `server/tests/_change-lookup.test.ts` pins current
      `toWireChange` output; passes before the change.
- [ ] `server/tests/computeHealth.test.ts` — every `{testsState, rigorForStage}`
      combination → expected state + reason, **including the unknown combination**
      (`testsState:"unknown"` + `determinable:false` → `state:"unknown"`, not a
      default `on-track`), and the assertion it never returns `worth-a-look`
      (**S-19**). **Fails** (module absent).
- [ ] `server/tests/readRigorForStage.test.ts` + `readTestsState.test.ts` —
      temp-dir fixtures incl. the absence/never-throw path and the
      `determinable:false` path. **Fail.**
- [ ] `server/tests/changes.enriched.test.ts` — feed against
      `FakeChangeStoreReader` asserts each row carries `needsAttention`,
      `health`, `lastActivityAt`; idle-but-fine stays `flagged: false`. **Fails.**
- [ ] **Degradation suite (never-throw / never-500 — BR-11 / NFR-DEGRADE-1):**
  - `server/tests/changes.degrade.test.ts`:
    - a **gone-worktree** row → liveness `unknown`, health `unknown`, attention
      not-flagged; feed returns **200**; other rows render normally (**S-23**).
    - a **malformed `session.json` / garbage stage / missing fields** row →
      degrades to unknown reads; feed does not throw / does not 500; siblings
      unaffected (**S-24 / MUC-1**).
    - a **partial-enrichment** seed (some rows full, some with absent fields) →
      each row degrades **independently**; feed 200 (**S-21 / EF-2**).
- [ ] **Reason-containment (MUC-3 / FR-32 / NFR-SEC-2):**
  `server/tests/reason-fixed-set.test.ts` — seed a change whose transcript holds
  markup / secret-looking text; assert no `health.reason` or attention `reason`
  contains it (drawn only from the fixed enumerable set) (**S-26**). **Fails.**
- [ ] **Bounded fan-out (MUC-2 / NFR-PERF-3):**
  `server/tests/changes.scale.test.ts` — seed hundreds of changes; assert the
  enrichment completes inside one bounded `Promise.all` (no per-card request, no
  unbounded loop) and the feed returns (**S-25**). **Fails.**

### Green
- [ ] Modules implemented; feed + search shaping wired; all Red tests pass.
- [ ] `needsAttention()` is **reused**, not re-implemented (grep: one definition).
- [ ] Reads are read-only + never-throw; the degradation suite is green (no
      record can 500 the feed, BR-11).

### Blue
- [ ] `toWireChange` stays a pure shaper (gathering lives in the route).
- [ ] Health/attention `reason` strings are a fixed enumerable set — no
      transcript-body interpolation (NFR-SEC-2 grep check + the S-26 test).
- [ ] Path reads contained via `safeJoin` (MUC-4); no read escapes the worktree.
- [ ] Characterisation test still green after refactor.

## Definition of Done — requirements & scenarios

- **Satisfies:** FR-30, FR-31 (unknown health), FR-32, FR-40, FR-42, BR-10,
  BR-11, BR-12; MUC-1, MUC-2, MUC-3, MUC-4; NFR-PERF-3, NFR-PERF-4,
  NFR-DEGRADE-1, NFR-DEGRADE-2, NFR-SEC-2, NFR-SEC-3, NFR-POLL-1.
- **Makes pass:** **S-16** (health-unknown server read), **S-19** (computeHealth
  unknown combo), **S-21** (partial enrichment, server side), **S-23**
  (worktree gone), **S-24** (malformed row), **S-25** (pathological count),
  **S-26** (reason never echoes content). Contributes the producer half of
  **S-3** (off-track) and **S-17** (liveness-unknown carried on the feed).

## verification

```
adapter: backend
artifact: apps/cockpit/server/tests/changes.enriched.test.ts
```
