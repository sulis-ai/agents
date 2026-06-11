# TDD — identify a change by its unique id, never the non-unique handle

> **Change:** CH-8BP0XN · change_id `01KTV4SS9N8BP0XN8GCQAXT6PC` · `fix` · kind: backend
> **Tier:** S (see SIZING.md) · **Mode:** brownfield delta-driven
> **Sources:** `.changes/fix-use-change-id-not-handle.SPEC.md`; audit-report.md;
> hardening-deltas/HD-001..005.

## 1. Problem (one paragraph)

A change's identity is its 26-char ULID `change_id`; the 6-char `CH-XXXXXX`
handle is a **display label** derived from it. The live store has 26 handles each
shared by 2–4 changes. Two act-on-a-change paths still treat the handle as
identity: the cockpit recreate-on-demand path (passes `record.handle` to the CLI
though it holds `record.changeId`), and the CLI `recreate` verb (no
`--change-id` entry point). A third path (`nuke`) routes through a legacy
resolver whose handle rung is dead post-#101 (tail-mint vs head-lookup). This TDD
makes every act-on path resolve by the full id, retires the dead rung, and pins
the behaviour with a regression fixture reproducing the live collision state.

## 2. Form — Structural integrity

The hexagonal seams already exist; this is a **signature correction**, not new
structure. (Respect-don't-restate: the cockpit's ports/adapters layout and the
CLI's resolver layer are documented in-code and unchanged in shape.)

- **`RecreateRunner` port** (`apps/cockpit/server/ports/RecreateRunner.ts`): the
  cockpit owns this port; its identity key MUST be the unique `change_id`, not
  the handle. Method becomes `recreate(changeId: string)`. The two adapters
  (`SulisChangeRecreator` production, `FakeRecreateRunner` in-memory) follow.
  Whose-interface test (Ports&Adapters vs Wrappers): this is the cockpit's own
  port → the change is EXPAND/REORGANISE of an owned contract, not a wrapper.
- **CLI resolver layer**: one safe matcher family (`_changes_matching_handle`,
  `_emit_ambiguous_match`, `_select_change_id_refusing_conflict`) becomes the
  single resolution authority for all four verbs; the legacy
  `_scan_state_dir_by_prefix` head-prefix rung is removed (dead code).
- **Worktree keying** (defence-in-depth, HD-005): prefer the id-keyed co-located
  worktree dir over the slug-keyed legacy sibling path in the recreate fallback.

## 3. Armor — Operational hardening

- **Identity by unique key** (the change itself): every act-on path resolves to
  exactly one change by `change_id`; an ambiguous founder-typed handle **refuses
  and disambiguates** (lists handle + readable name + branch), never silently
  picks. Destructive verbs (`ship`/`nuke`) inherit the same refusal.
- **Existing Armor preserved**: spawn-not-exec + `shell: false` argv array;
  bounded recreate timeout (30s, SIGKILL); the `changeHandleGuard` shape-guard
  (alphanumerics, no leading hyphen — the argparse flag-confusion vector). The
  guard's character class already matches the ULID charset, so it guards a
  `--change-id` argument unchanged. Typed `RecreateOutcome` across the seam (no
  raw throw).
- **Backward-compat**: an unambiguous `--handle`/`--slug` still resolves; only
  the ambiguous case changes behaviour (refuse, not guess). Display read paths
  (dashboard, changeset/PR correlation, `SulisChangeStoreReader`) keep reading
  the handle for display — untouched.

## 4. Proof — Verification protocol

- Every act-on path gets a behavioural test resolving an exact id against a
  colliding-handle fixture (not a mock — a real in-memory adapter / temp store,
  MEA-09).
- One regression fixture reproduces the live state (26 colliding handles, one
  shared by 4) and proves self-resolution across all four verbs (HD-003).
- The cockpit seam gets a behavioural test asserting the recreate call carries
  `record.changeId`, not `record.handle` (HD-004).

## 5. Components touched

| Component | File | Change |
|---|---|---|
| CLI recreate | `plugins/sulis/scripts/sulis-change` `cmd_recreate` | add `--change-id`; resolve by id first |
| CLI nuke | `plugins/sulis/scripts/sulis-change` `_resolve_nuke_target` | route through safe matcher; add `--change-id`; remove dead rung |
| CLI resolver | `plugins/sulis/scripts/sulis-change` `_resolve_change_id` / `_scan_state_dir_by_prefix` | remove dead head-prefix rung |
| CLI candidate list | `_emit_ambiguous_match` | add readable name |
| Worktree path (DiD) | `plugins/sulis/scripts/_wpxlib.py` recreate fallback | prefer id-keyed dir |
| Cockpit port | `apps/cockpit/server/ports/RecreateRunner.ts` | `recreate(changeId)` |
| Cockpit adapters | `SulisChangeRecreator.ts`, `FakeRecreateRunner.ts` | spawn `--change-id`; record `lastArg` |
| Cockpit serving path | `routes/_recreate-on-demand.ts` | pass `record.changeId` |

<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->

## Verification Plan

### 1. User-observable behaviour (Q1)

Opening, recreating, shipping, or nuking a change by its handle acts on the
**right** change every time, even when that handle is shared. Observable: the
correct branch + workspace materialise; two colliding-handle changes stay in two
conversations; a destructive verb never touches a sibling; an ambiguous
founder-typed handle yields a candidate list + a question. Restates SPEC
Verification Plan §1 in test-artifact terms below.

### 2. Verification environment(s) (Q2)

Local + CI. Python paths run under pytest against a temp `SULIS_STATE_DIR`
fixture with synthesised colliding handles + temp git worktrees. Cockpit paths
run under vitest against the in-memory `FakeRecreateRunner` and constructed
records. No deployed environment; resolution is pure local git + state-store +
subprocess logic.

### 3. Fresh-clone reproducibility (Q3)

Yes. Fixtures build their own temp store + worktrees (no dependence on the
developer's `~/.sulis`); the 26-collision condition is synthesised, not borrowed
from live data. Passes from a fresh clone at the merge SHA.

### 4. Per-integration verification strategy (Q5–Q13)

Two internal integrations, both `existing`:

- **CLI resolution path** — `existing` at `plugins/sulis/scripts/sulis-change`
  (`cmd_recreate`, `_resolve_nuke_target`, `_select_change_id_refusing_conflict`)
  + `plugins/sulis/scripts/_wpxlib.py` (`ulid_handle`, `_changes_matching_handle`).
  Strategy: in-memory temp-store fixture; drive each verb against a
  colliding-handle fixture; assert exact-id resolution or a disambiguation
  refusal. Resilience primitive: the CLI is invoked by the cockpit under a
  bounded spawn timeout (30s) with SIGKILL + typed `RecreateOutcome` failure —
  the existing recreate-bounding pattern (no new primitive needed; cite
  `references/architecture-patterns.md` bounded-subprocess / timeout). Test seam:
  the `RecreateRunner` port. **Concrete (Shape 1)** — `recreate --change-id`
  resolution test ships with HD-001.
- **Cockpit recreate-on-demand path** — `existing` at
  `apps/cockpit/server/routes/_recreate-on-demand.ts`,
  `adapters/SulisChangeRecreator.ts`, `ports/RecreateRunner.ts`. Strategy:
  behavioural test through the `FakeRecreateRunner` in-memory adapter asserting
  the recreate call carries `record.changeId`. Mock contract: the fake records
  `lastArg` and returns a typed `RecreateOutcome`; it never spawns. **Concrete
  (Shape 1)** — ships with HD-004.

Idempotency/replay (Q10): recreate stays idempotent — re-resolving the same id
returns the same change; an already-present worktree is `{ok:true,
alreadyPresent:true}`. Asserted. Auth boundary (Q11): `n/a` — local resolution,
no auth crossed. Failure mode (Q12): an id matching no change returns a clean
"not found" (CLI `emit_error`; cockpit degrades to the typed `UNAVAILABLE_NOTE`).
Asserted.

### 5. Per-kind verification adapter (Q4, Q14–Q20)

`kind: backend`. Adapter per the canonical kind→adapter table: behavioural test
against the resolution logic + a state/persistence assertion (correct branch +
worktree materialised) + an idempotency check on recreate. Concrete artifacts
(Shape 1):

- Python: `plugins/sulis/scripts/tests/unit/test_sulis_change_safe_resolution.py`
  (extend) + a new `test_change_identity_resolution.py` / `collision_fixture`
  suite under `plugins/sulis/scripts/tests/` — pytest nodeids land in the WP
  `verification:` frontmatter.
- TypeScript: `apps/cockpit/server/tests/recreate-on-demand.test.ts` (extend) —
  vitest spec.

Multi-adapter (Q18): spans the Python CLI and the Node cockpit; each verified by
its own behavioural suite. No `frontend` adapter (no new visual surface). Infra
(Q19): existing pytest + vitest harnesses; nothing new.

### 6. Infrastructure needs surfaced (deferred)

None. No vendor mocks, no test OAuth accounts, no new seed-data infra. The
`collision_fixture` is built in-repo by HD-003 (not a deferred external need).
All integration rows are **concrete (Shape 1)** — no Shape 2 deferrals, no
Shape 3 trivial carveouts.

## Sizing Report

- **Tier:** S (computed) / S (confirmed silently — focused fix, reuses existing
  safe-matcher substrate; no founder-facing tier consequence).
- **TDD length:** ~135 lines — within tier-S band given a brownfield change
  touching two languages; no restating of covered architecture (ports/adapters
  layout referenced, not re-derived).
- **ADRs produced:** 2 (expected 1–2). ADR-001 the `recreate(changeId)` port
  signature change (affects CLI + cockpit); ADR-002 no new CF contract artifact
  for the CLI↔cockpit subprocess seam.
- **Authoritative sources referenced:** in-code #101/#274 safe-resolution work;
  no `.context/` index exists to reference.
- **Circuit breakers:** none triggered.
