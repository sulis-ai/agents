# use-change-id-not-handle — Codebase Audit

> **Date:** 2026-06-11
> **Change:** CH-8BP0XN · change_id `01KTV4SS9N8BP0XN8GCQAXT6PC` · primitive `fix`
> **Scope:** change-identity resolution surface —
> `plugins/sulis/scripts/sulis-change`, `plugins/sulis/scripts/_wpxlib.py`,
> `apps/cockpit/server/` recreate-on-demand path, and every grepped call site
> that resolves a change by handle.
> **Tooling:** Python (argparse CLI + `_wpxlib` library), TypeScript (cockpit
> Fastify server, hexagonal ports/adapters), pytest + vitest.

## What I read

I scoped to the resolution surface (not a full-repo analyse-codebase, per the
focused-baseline instruction). I read both resolver families in the CLI, the
handle-mint function, every cockpit non-test source file that references
`handle` / `changeId` / a `.recreate(` call, the `RecreateRunner` port and its
production adapter, the change-store reader, the handle shape-guard, and the
existing safe-resolution test suite. I grepped the whole repo for
`--handle`, `ulid_handle`, `_resolve_by_prefix` / `_scan_state_dir_by_prefix`,
`by_handle`, and `record.handle` to find ALL act-on-a-change call sites.

## Ground-truth verification (the diagnosed problem)

Confirmed, with one important refinement. The diagnosis is correct that **the
daemon/read side is already keyed by `change_id`** and **the defect is on the
act-on-a-change paths**. But the codebase is further along than "several paths
resolve by handle" implies: the #101/#274 work already built a *safe* matcher
family and wired it into `recreate` and `mark-shipped`. The residual defect is
narrower and sharper than a blanket "resolve by handle everywhere":

1. The **cockpit throws away an id it already holds.** It reads the full record
   by `change_id`, then re-resolves by the non-unique `handle` through a CLI
   subprocess. (Primary leak.)
2. The CLI `recreate` verb **has no `--change-id` entry point at all**, so the
   cockpit physically *cannot* pass the id it holds.
3. `nuke` still routes through the **legacy** `_resolve_change_id` chain whose
   handle rung is dead (mint/lookup mismatch), inconsistent with the safe
   matcher the other verbs use.

## Summary

- **Critical findings:** 0
- **High findings:** 2
- **Medium findings:** 2
- **Low findings:** 1

| Pillar | Findings | Top concern |
|---|---|---|
| Form | 2 | `RecreateRunner.recreate(handle)` makes the non-unique handle the seam's identity key; legacy worktree path keyed by `{primitive}-{slug}`, not id |
| Armor | 2 | Cockpit re-resolves a held `change_id` by the non-unique handle (A-01); `nuke` uses the dead-rung legacy resolver (A-02) |
| Proof | 1 | No end-to-end colliding-handle regression across all four verbs; no fixture for the live 26-collision state |

## Findings by Pillar

### Form

| ID | File | Line | Gap | Severity | Delta |
|---|---|---|---|---|---|
| F-01 | `apps/cockpit/server/ports/RecreateRunner.ts` | 44-51 | The port method is `recreate(handle: string)`. The hexagonal seam between cockpit and CLI takes the **non-unique handle** as its identity key. Whose-interface test: this port is the cockpit's own → the contract should carry the unique id. | high | HD-001 |
| F-02 | `plugins/sulis/scripts/_wpxlib.py` | 4373 | `change_worktree_path(repo_root, primitive, slug)` composes the **legacy** sibling worktree path from `{primitive}-{slug}`, not `change_id`. Co-located worktrees are now id-keyed (`~/.sulis/changes/{change_id}/worktree`), but `cmd_recreate` falls back to this slug-keyed path when git reports the branch checked out nowhere. Two changes sharing primitive+slug would collide here. (0 such collisions in live data → low realised risk, but it is the structural reason recreate must key by id end-to-end.) | low | HD-005 |

### Armor

| ID | File | Line | Gap | Severity | Delta |
|---|---|---|---|---|---|
| A-01 | `apps/cockpit/server/routes/_recreate-on-demand.ts` | 126 | `runner.recreate(record.handle)` — the resolver holds `record.changeId` (the record was read by id at `requireChange`) but passes `record.handle`, the **non-unique** key, across the spawn seam. A colliding handle here makes the CLI either refuse (degrade to "couldn't reach this shipped change's contracts") or, pre-#101, materialise a sibling's worktree. This is the cockpit half of the "session works on the wrong change" symptom. | high | HD-001 |
| A-02 | `plugins/sulis/scripts/sulis-change` | 1532 (via 1366-1380, 1309) | `_resolve_nuke_target` resolves each candidate's `change_id` through the **legacy** `_resolve_change_id`, whose handle rung calls `_scan_state_dir_by_prefix(prefix=handle_tail)` against full-ULID **dir names that start with the timestamp head** — so a tail-minted handle never matches (dead rung; the mint/lookup mismatch). It is masked by rung 0 (first-slug-match) and the final >1-match refusal, so `nuke` is not *currently* unsafe — but it is inconsistent with the safe `_changes_matching_handle` matcher that `recreate`/`mark-shipped` use, and the dead rung is a latent foot-gun. | medium | HD-002 |

### Proof

| ID | File | Gap | Severity | Delta |
|---|---|---|---|---|
| P-01 | `plugins/sulis/scripts/tests/unit/test_sulis_change_safe_resolution.py` | The existing suite unit-tests the matcher (`_changes_matching_handle`, `_select_change_id_refusing_conflict`) but there is **no end-to-end regression** that builds a fixture store reproducing the live collision state (26 colliding handles, one shared by 4 changes) and proves every change resolves to itself across all four verbs. No cockpit test asserts the recreate spawn carries the change_id. No test exercises a `recreate --change-id`. | medium | HD-003, HD-004 |

## Adversarial / spec drift

No `SRD.md`, `MISUSE_CASES.md`, or `.context/` index exists for this change — the
authoritative input is the SPEC. Code-vs-spec drift is captured per scenario in
the journey walk below; every gap maps to a Hardening Delta.

## Journey Walk — the seven SPEC scenarios, hop-by-hop, outside-in

Each scenario is walked from the founder action inward. For each hop I cite the
handling component and verdict.

### Scenario 1 — Colliding-handle recreate resolves to self → **GAP → fix**

Founder recreates one of two colliding-handle changes.
- Hop 1 — cockpit reads the record by `changeId`: `requireChange` →
  `SulisChangeStoreReader.readChangeRecord(changeId)` ✅ unique.
- Hop 2 — serving path resolves the worktree: `resolveForServing` →
  `resolveContractWorktree` (`routes/contract.ts:97`) ✅ holds `record.changeId`.
- Hop 3 — recreate spawn: `runner.recreate(record.handle)`
  (`_recreate-on-demand.ts:126`) ❌ **passes the non-unique handle**, discarding
  the held id. → GAP (A-01 / F-01) → HD-001.
- Hop 4 — CLI resolves: `cmd_recreate --handle` → `_changes_matching_handle`
  refuses on >1 ✅ safe, but on a real collision it **refuses instead of
  resolving the change the cockpit already identified** → the founder sees a
  degrade, not their change. Closed by HD-001 (`recreate --change-id`).

### Scenario 2 — Tidied colliding change rebuilds for itself → **GAP → fix**

Same path as Scenario 1 (tidied = worktree absent-but-recreatable). The
absent-but-recreatable branch (`_recreate-on-demand.ts:125-141`) is exactly
where `runner.recreate(record.handle)` fires. → GAP (A-01) → HD-001.

### Scenario 3 — Two colliding changes stay separate → **already-green (once HD-001 lands)**

Two separate workspaces / two separate conversations.
- Worktree separation: co-located worktrees are keyed by `change_id`
  (`~/.sulis/changes/{change_id}/worktree`, `_wpxlib.py:5108`) ✅; the only
  shared-path risk is the legacy slug-keyed fallback (F-02 / HD-005, low).
- Conversation/session separation: bound by `SULIS_CHANGE_ID` (the full id);
  `resolve_current_change` (`_wpxlib.py:5022`) prefers the worktree's committed
  manifest and warns loudly on env-var disagreement (#244) ✅. No handle is used
  to bind a session. → already-green; HD-001 removes the last way two changes
  could resolve to one worktree via recreate.

### Scenario 4 — Destructive verbs never hit the wrong change → **partially-green → fix (consistency)**

- `mark-shipped` (ship): `_select_change_id_refusing_conflict` — safe matcher,
  refuses on ambiguity AND on explicit-vs-session conflict (#274) ✅.
- `nuke`: `_resolve_nuke_target` refuses on >1 final match ✅, but resolves each
  candidate id via the **dead-rung legacy** `_resolve_change_id` (A-02). Not
  currently unsafe, but inconsistent and latent. → GAP → HD-002 (route `nuke`
  through the same `_changes_matching_handle` matcher; retire the dead rung).

### Scenario 5 — Ambiguous handle disambiguates → **already-green (CLI) / GAP (cockpit surfacing)**

- CLI: `_emit_ambiguous_match` (`sulis-change:1424`) already lists candidates
  (change_id + branch + slug + stage) and refuses ✅. SPEC asks for handle +
  readable name + branch — the candidate payload carries slug + branch; add the
  readable `intent`/name field for parity. → minor fill inside HD-002.
- Cockpit: when recreate-by-id is requested with an id that maps cleanly, no
  prompt is needed (the id is unambiguous by construction). The disambiguation
  prompt is a **founder-typed-handle** affordance, which lives at the CLI / skill
  surface, not the cockpit recreate path. → already-green at the CLI; covered by
  HD-002's candidate-list parity.

### Scenario 6 — New-style handle resolves → **already-green at matcher / GAP at legacy rung**

A change whose handle was minted from the id's tail (#101).
- Safe matcher path: `_changes_matching_handle` matches on stored handle OR
  recomputed `ulid_handle(cid)` ✅ migration-robust — `recreate`/`mark-shipped`
  resolve a tail-minted handle correctly today.
- Legacy path: `_scan_state_dir_by_prefix` matches the tail against full-ULID
  dir names (head) → never matches (A-02). Dead, but masked. → fixed by HD-002
  retiring the rung.

### Scenario 7 — Regression against the live collision state → **GAP → fix**

No fixture reproduces the 26-collision store (one handle shared by 4 changes)
and proves self-resolution across all four verbs. → GAP (P-01) → HD-003 (Python
CLI fixture + cross-verb regression) and HD-004 (cockpit recreate-carries-id
test).

### Out-of-scope (recorded, not planned as WPs)

| Item | SPEC Non-goal | Why out |
|---|---|---|
| Relabel the 26 existing colliding handles | yes | cosmetic; would orphan PR/dashboard refs once identity runs on the id |
| Detect/repair already-corrupted workspaces | yes | this fix prevents new occurrences; unpicking past damage is a separate follow-up |
| Terminal-WS `?changeId` hardening | yes | captured separately |
| Change the `CH-XXXXXX` handle format | yes | handle stays; only its role changes |

## Suggested acceptance order

1. **HD-001** (high, Form+Armor) — add `recreate --change-id` to the CLI and
   make the cockpit pass `record.changeId`. Closes Scenarios 1, 2, 3.
2. **HD-002** (medium, Armor) — route `nuke` through the safe matcher; retire
   the dead `_scan_state_dir_by_prefix` rung; add the readable name to the
   candidate list. Closes Scenarios 4, 5, 6.
3. **HD-003 + HD-004** (medium, Proof) — the 26-collision regression fixture
   across all four verbs (Python) and the cockpit-carries-id test (TS). Closes
   Scenario 7; proves 1–6 stay closed.
4. **HD-005** (low, Form) — opportunistic: key the recreate fallback worktree by
   change_id so a shared primitive+slug can never collide. Defence-in-depth for
   F-02; bundle only if cheap, else defer.

## What was not audited

- The whole-repo structural baseline (intentionally — focused on the resolution
  surface per the change brief).
- The daemon side (already correct per the diagnosis; spot-confirmed that
  session binding uses `SULIS_CHANGE_ID`, the full id, not the handle).
- Dashboard / changeset / PR correlation read paths (SPEC Constraint: must not
  break; they read the handle for **display only**, which this change preserves).
