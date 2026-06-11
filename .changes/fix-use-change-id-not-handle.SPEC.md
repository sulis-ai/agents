---
founder_facing: false
kind: backend
---

# Spec — identify a change by its unique id, never the non-unique handle

**Change:** CH-8BP0XN · fix

## Intent

A change is identified internally by a long unique id, but shown to the founder
as a short 6-character handle (`CH-XXXXXX`). Those short handles are **not
unique** — in the live store today, 26 handles are each shared by 2–4 different
changes (e.g. `CH-01KSNX` maps to four unrelated changes). Several code paths —
in the cockpit server and the `sulis-change` CLI — resolve a change *by that
handle*, so they can land on the **wrong** change. The observed symptoms:

- A session starts working on the **wrong change** (the cockpit rebuilds a
  tidied change's workspace by handle and materialises a *sibling's* worktree).
- **Two sessions braid into one conversation** (two colliding-handle changes
  resolve to one workspace, so two `claude` processes run in one directory and
  append to one transcript).

Root cause: the short handle is used as an **identity key** when it is only safe
as a **display label**. This change makes every place that *acts on* a change
resolve by the full unique id, and makes founder-typed handles disambiguate
safely instead of silently picking one.

## Scope

- **Resolve by unique id everywhere a change is acted on.** Every change-by-handle
  resolution path in the cockpit server and the `sulis-change` CLI resolves to a
  single change by its full unique id, not the 6-character handle. The handle
  becomes a display label only.
- **Cover all four CLI verbs, including the destructive ones.** `recreate`,
  `focus`, `ship`, and `nuke` all resolve unambiguously. `ship` and `nuke` are
  destructive (a wrong-change merge or an irreversible delete), so they are
  in-scope precisely because a colliding handle there is the worst case.
- **Reconcile the mint/lookup mismatch.** Handles are now minted from the random
  *tail* of the id (collision-resistant, per #101), but the resolver still matches
  the timestamp *head* — so newer changes can fail to resolve or mis-resolve by
  handle. Resolution must match how handles are actually minted (resolve against
  the stored handle / full id, not a head-prefix heuristic).
- **Add a disambiguation prompt.** When a founder types a handle that genuinely
  matches more than one change, the tool lists the candidates (handle + readable
  name + branch) and asks which — it never silently picks one.
- **Regression coverage.** Automated tests prove that with today's colliding
  handles present, each change resolves to *itself* across all four verbs.

## Non-goals

- **Relabelling the 26 existing colliding handles** — deferred as cosmetic. Once
  identity runs on the unique id, the old handles are display text only; rewriting
  them would orphan external references (PR bodies, dashboard, changeset notes)
  for no correctness gain. Captured as a follow-up.
- **Detecting / repairing already-corrupted workspaces** from past collisions (a
  workspace with mixed history, or a transcript with two changes braided). This
  fix prevents *new* occurrences; unpicking existing damage is a separate
  follow-up (a detection scenario may be added there).
- **The terminal-WS `?changeId` defence-in-depth** — already captured separately;
  not part of this change.
- **Changing the founder-facing handle format** — the handle stays `CH-XXXXXX`;
  only its *role* (display, not identity) changes.

## Acceptance

- Given two changes that share a handle, recreating/opening one materialises
  **its own** branch and workspace — never a sibling's. (Scenario 1, 2)
- Opening two colliding-handle changes yields **two separate** workspaces and
  **two separate** conversations — never one shared. (Scenario 3)
- `nuke` and `ship` driven against a colliding handle never act on the wrong
  change: they either resolve to the exact id or stop and disambiguate — they
  never delete or merge a sibling. (Scenario 4)
- A founder-typed handle that matches multiple changes produces a candidate list
  + a question, not a silent pick. (Scenario 5)
- A newer change (handle minted from the id's tail) resolves correctly by its
  displayed handle — the mint/lookup mismatch is gone. (Scenario 6)
- With the current store (26 colliding handles, 79 tidied changes) present, the
  full regression suite proves every change resolves to itself. (Scenario 7)

## Constraints

- **No third-party platform touch.** This is internal git + local state + cockpit
  server + CLI only — no GitHub/Stripe/cloud write, so no Platform Contract is
  required. `n/a` for the platform-contract gate, justified: the change never
  calls an external platform.
- **Preserve the founder-facing handle.** `CH-XXXXXX` stays the thing the founder
  reads and types; the change must not force the founder to type long ids.
- **Backward-compatible resolution.** Existing callers that pass a handle keep
  working — an unambiguous handle resolves as before; only the *ambiguous* case
  changes behaviour (disambiguate instead of guess).
- **Must not break** the existing change-store read path (`SulisChangeStoreReader`),
  the dashboard, or changeset/PR correlation, all of which read the handle for
  display.

<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->

## Verification Plan

### 1. User-observable behaviour (Q1)

The founder opens, recreates, ships, or nukes a change by its handle and the
**right** change is acted on every time — even when that handle is shared by
several changes. Concretely observable: the correct branch + workspace appear;
two colliding-handle changes stay in two separate conversations; a destructive
verb never touches a sibling; an ambiguous handle yields a candidate list and a
question rather than a silent pick.

### 2. Verification environment(s) (Q2)

Local, against a constructed fixture store containing deliberately
colliding-handle changes (mirroring the live `CH-01KSNX`-maps-to-four case). The
behavioural resolution tests run in CI as standard unit/integration tests. No
deployed environment is required — resolution is pure local git + state-store
logic.

### 3. Fresh-clone reproducibility (Q3)

Yes. The tests build their own temporary change store + git worktrees from a
fixture (no dependence on the developer's `~/.sulis`), so they pass from a fresh
clone with zero prior state. The colliding-handle condition is synthesised in the
fixture, not borrowed from live data.

### 4. Per-integration verification strategy (Q5–Q13)

Two internal integrations, both classified `existing`:

- **The `sulis-change` CLI resolution path** — `existing`, at
  `plugins/sulis/scripts/sulis-change` and `plugins/sulis/scripts/_wpxlib.py`
  (handle mint `ulid_handle`) and the prefix resolver in `plugins/sulis/scripts/sulis-change`.
  Verified by driving each verb (`recreate`/`focus`/`ship`/`nuke`) against a
  colliding-handle fixture and asserting exact-change resolution or a
  disambiguation prompt.
- **The cockpit recreation path** — `existing`, at
  `apps/cockpit/server/adapters/SulisChangeRecreator.ts` (and any cockpit handle→record
  lookup). Verified by a server-side behavioural test that the recreate request
  carries the unique id and materialises the correct worktree.

No external integrations. Idempotency/replay (Q10): recreate stays idempotent —
re-resolving the same id returns the same change; this is asserted. Auth boundary
(Q11): `n/a` — no auth boundary is crossed; resolution is local. Failure mode
(Q12): an id that matches no change returns a clean "not found", asserted.

### 5. Per-kind verification adapter (Q4, Q14–Q20)

`kind: backend`. Adapter: behavioural test against the resolution logic + a
persistence/state assertion (the correct branch + worktree materialised), plus an
idempotency check on recreate. Concrete test artifact (Shape 1): a
`test_change_identity_resolution` suite under `plugins/sulis/scripts/tests/` for the
CLI paths, and a `SulisChangeRecreator` / resolution test under
`apps/cockpit/server/tests/` for the cockpit path. Multi-adapter (Q18): the change
spans the Python CLI and the Node cockpit server — both verified by their own
behavioural suites; no `frontend` adapter (no new visual surface). Infrastructure
(Q19): existing test harnesses (pytest, vitest) — nothing new.

### 6. Dogfood / acceptance criterion (Q20)

Satisfied when the regression suite, run against a fixture reproducing the live
collision state (26 colliding handles, including a handle shared by four changes),
proves every change resolves to itself across all four verbs, and the
disambiguation prompt fires on a genuinely ambiguous founder-typed handle. The
seven scenarios below are the acceptance journeys.

## Scenarios

Plain-English verifiable journeys (each drives an action and observes the
outcome):

1. **Colliding-handle recreate resolves to self.** Two changes share a handle.
   Recreate one → its own branch + workspace appear, never the sibling's.
2. **Tidied colliding change rebuilds for itself.** Open a shipped/tidied change
   whose handle collides → its workspace is rebuilt for itself and the session is
   briefed for itself.
3. **Two colliding changes stay separate.** Open both colliding-handle changes →
   two separate workspaces, two separate conversations — never one shared.
4. **Destructive verbs never hit the wrong change.** Drive `nuke` (and `ship`)
   against a colliding handle → the tool resolves the exact id or stops to
   disambiguate; it never deletes or merges a sibling.
5. **Ambiguous handle disambiguates.** Type a handle matching several changes →
   a candidate list (handle + name + branch) + a question appears; nothing is
   silently picked.
6. **New-style handle resolves.** A change whose handle was minted from the id's
   tail resolves correctly by its displayed handle (mint/lookup mismatch gone).
7. **Regression against the live collision state.** With a fixture reproducing
   today's 26 colliding handles, every change resolves to itself across all four
   verbs.
