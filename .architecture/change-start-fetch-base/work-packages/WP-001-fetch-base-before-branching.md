---
id: WP-001
title: "sulis-change start fetches origin/{base_ref} before cutting the change branch"
status: pending
change_id: 01KTP2EA90VM797BXBWTYMCEB4
kind: backend
primitive: fix
group: REINFORCE
sequence_id: WP-001
dependsOn: []
blocks: []
estimated_token_cost:
  input: 6k
  output: 5k
tdd_section: "n/a — contained fix; no TDD (see Notes)"
adrs: []
verification:
  adapter: backend
  artifact: "plugins/sulis/scripts/tests/integration/test_sulis_change_lifecycle.py::test_start_branches_off_fetched_origin_when_local_main_stale"
---

## Context

`cmd_start` in `plugins/sulis/scripts/sulis-change` (lines ~469–506)
cuts the change branch off the **local** `base_ref` (`main` by default).
It sets `base_ref = args.base or "main"`, then calls
`git_worktree_add(repo_root, branch, worktree_dest, base_ref)` (which runs
`git worktree add -b {branch} {dest} {base_ref}`) and `git rev-parse base_ref`
— all against whatever local `main` happens to be.

There is **no `git fetch origin {base_ref}` first**. When the developer's
local `main` is behind `origin/main`, the new change starts from a stale
base. Sibling subcommands in the same file already fetch before they act —
see `finish` at line ~818:

```python
rc, _, err = _run(["git", "fetch", "origin", base_ref], cwd=repo_root, timeout=60)
if rc != 0:
    emit_error(f"git fetch origin {base_ref} failed: {err}")
```

This WP brings `start` up to that convention — but with one deliberate
difference: `start` must **degrade gracefully** on fetch failure rather than
`emit_error`-ing the founder out of starting a change offline (spec
guardrail, mirrored from `test_start_degrades_gracefully_with_no_remote`).

**Primitive = fix; group = REINFORCE.** The shape is a one-call hardening of
an existing code path (add the missing fetch + redirect the branch base to
the fetched tip), proven by a new characterisation test. It is not a new
component (not EXPAND-Create) and not a structural move (not REORGANISE) —
it reinforces the existing `start` path against a stale-base failure mode.
A characterisation test pins the corrected behaviour; the local-fallback
path is preserved verbatim.

## Contract

### Files modified

```
plugins/sulis/scripts/sulis-change                                   (cmd_start: + ~12 LOC)
plugins/sulis/scripts/tests/integration/test_sulis_change_lifecycle.py  (+ 3 RED/coverage tests)
plugins/sulis/skills/change/SKILL.md                                 (docs-truth correction, line ~131)
```

> **Why `change/SKILL.md` is in scope.** Line ~131 currently *claims*
> `sulis-change start` "fetches `origin/main` before branching, so there is
> nothing to gate here". That claim is **false against current code** — and it
> is precisely the false-confidence that masked this bug. After the Green step
> the claim becomes true. This is a docs-truth correction (the doc must match
> the shipped behaviour), **not** new prose. Do not ship the corrected wording
> ahead of the code — the SKILL.md edit lands in the same change, gated on the
> code fix passing.

### Behavioural contract

`cmd_start`, **before** creating the worktree/branch, attempts to fetch the
latest base ref from origin and branches off the fetched tip when the fetch
succeeds:

1. After `base_ref = args.base or "main"` and the
   already-exists guard, attempt `git fetch origin {base_ref}` via `_run(...)`.
2. **On fetch success** (`rc == 0`): branch off the fetched tip. The cleanest
   seam is to pass `f"origin/{base_ref}"` (or the resolved `FETCH_HEAD` SHA)
   as the base into `git_worktree_add`, and to `git rev-parse` that same ref
   for `base_sha`. The executor picks whichever of `origin/{base_ref}` /
   `FETCH_HEAD` resolves cleanly in the existing fixture; the contract is only
   that the branch base SHA equals `origin/{base_ref}`'s tip when a fetch
   succeeded.
3. **On fetch failure** (`rc != 0`, e.g. no remote / no network): `_log(...)`
   a one-line note that the fetch could not happen and `start` is falling back
   to the local `{base_ref}`, then proceed exactly as today — branch off the
   local `base_ref`. **No `emit_error`.** No crash. Exit 0.
4. **`--base <branch>` honoured identically.** `base_ref` is already
   `args.base or "main"`, so the same fetch-then-remote-preferred resolution
   applies whatever the base ref is: fetch `origin/{base_ref}`, branch off the
   remote-resolved tip on success, fall back to the local `{base_ref}` on fetch
   failure. There is **no special-casing of `main`** — a custom `--base` must
   get the same staleness protection and the same offline fallback.

#### Implementation guidance (from the originating handoff)

Mirror the **robust base-resolution already proven in-repo** — do not invent a
new pattern. Two established conventions cover this (CP-01 — internal prior art):

- The **`finish` fetch** at line ~818 (`_run(["git", "fetch", "origin",
  base_ref], cwd=repo_root, timeout=60)`) — the in-file fetch convention to
  copy verbatim in tone/structure (diverging only in failure handling).
- The **local-vs-remote resolve** used by `wpx-worktree create`'s
  `--base-branch` handling — the precedent for "prefer the remote-resolved ref,
  fall back to the local ref" when the remote is unavailable.

Concretely: prefer `origin/{base_ref}` when the remote ref resolves cleanly
after the fetch; fall back to the local `{base_ref}` only on fetch failure /
no remote (fresh-clone-friendly). **Pin `base_sha` to the resolved
(remote-preferred) ref** — i.e. `git rev-parse` the same ref the branch was
cut from, so the recorded `base_sha` is the remote tip on the happy path and
the local tip on the fallback path.

### Public-surface invariants (must NOT change)

- The `start` JSON result shape is unchanged — same keys
  (`branch`, `primitive`, `slug`, `change_id`, `handle`, `worktree_path`,
  `pushed_to_origin`, …). No new required field. (A purely additive,
  optional field such as `base_fetched: bool` is permitted but not required;
  if added, it must default sensibly and not break existing assertions.)
- The existing `metadata["base_sha"]` continues to be the SHA the branch was
  actually cut from (now the fetched tip on the happy path; the local tip on
  the fallback path).
- No behaviour change to any other subcommand (`finish`, `adopt`, `list`,
  `status`, `mark-shipped`, `nuke`). The edit is confined to `cmd_start`.

### What this WP is NOT

- It does **not** change `git_worktree_add`'s signature or its other callers
  (`adopt`, the issue-#53 regression test monkeypatch). If passing
  `origin/{base_ref}` as the existing `base_ref` parameter is sufficient
  (it is — that parameter already feeds `git worktree add -b … {base_ref}`),
  no signature change is needed.
- It does **not** add a `--no-fetch` flag. Graceful degradation on fetch
  failure already covers the offline case; a bypass flag is unnecessary.
- It does **not** fetch any ref other than `base_ref`. No `--all`, no pruning.

## Definition of Done

### Red — Failing test written first (Non-Negotiable #1)

Three test cases, per the originating handoff. All added under the
`# ─── start ───` section of
`plugins/sulis/scripts/tests/integration/test_sulis_change_lifecycle.py`,
using the existing `local_git_repo` + `run_tool` fixtures and the module's
`_git` / `_run` helpers. Mirror the `_force_conflicting_local_commit` /
`_origin_advancer` sibling-clone pattern already in this file for advancing
`origin`.

- [ ] **(1) Local `main` behind `origin/main` → branch off the fetched tip
      (RED today).**
      `test_start_branches_off_fetched_origin_when_local_main_stale`:
      1. Clone the fixture's bare `origin` into a sibling dir.
      2. In that sibling clone, commit a new file on `main` and
         `git push origin main` — advancing `origin/main` one commit ahead of
         the fixture repo's local `main`.
      3. Capture `origin/main`'s new tip SHA (e.g. `git ls-remote origin
         refs/heads/main`, or rev-parse in the sibling clone).
      4. Run `sulis-change start --repo-root {local_git_repo} --slug
         fetch-base-test --primitive fix`.
      5. Assert `result.ok`.
      6. Resolve the change branch's base commit — the SHA the worktree was
         cut from. Assert it **equals the advanced `origin/main` tip**, NOT
         the fixture's stale local `main` tip. (Read `base_sha` from the
         written metadata via `read_change_metadata`, or rev-parse the
         worktree's `HEAD`/merge-base against the two candidate SHAs.)

      FAILS against current code (branch is cut off stale local `main`, so the
      base SHA equals the local tip, not the advanced `origin/main` tip) — RED
      for the right reason.

- [ ] **(2) Offline / no remote → graceful fallback to the local ref, no
      crash.** `test_start_degrades_gracefully_with_no_remote` (this case may
      already exist in the file — if so, confirm it still asserts the right
      thing; if not, add it). With no reachable `origin`, `start` must exit 0,
      create the local branch + worktree, base off the local `{base_ref}`, log
      the fetch-failure note (never `emit_error`), and report
      `pushed_to_origin: false`.

- [ ] **(3) `--base <branch>` honoured with the SAME resolution.**
      `test_start_with_explicit_base_branches_off_fetched_origin`:
      1. In the fixture repo, create a second branch (e.g. `release`) and push
         it to `origin`.
      2. Via a sibling clone, advance `origin/release` one commit ahead of the
         fixture's local `release` and push.
      3. Capture `origin/release`'s advanced tip SHA.
      4. Run `sulis-change start --repo-root {local_git_repo} --slug
         base-flag-test --primitive fix --base release`.
      5. Assert `result.ok`.
      6. Assert the change branch's base SHA **equals the advanced
         `origin/release` tip** — proving the fetch-then-remote-preferred
         resolution applies to a custom `--base`, not just `main`. (Same
         `base_sha` / merge-base assertion technique as case 1.)

      FAILS against current code (custom `--base` is also cut off the stale
      local ref) — RED for the right reason.

### Green — Implementation makes the test pass

- [ ] `cmd_start` in `plugins/sulis/scripts/sulis-change` fetches
      `origin/{base_ref}` before worktree creation and branches off the
      fetched tip on success (per the Behavioural contract above), for both the
      default `main` and an explicit `--base`.
- [ ] Case (1) test passes — branch based on the advanced `origin/main` tip.
- [ ] Case (3) test passes — explicit `--base release` based on the advanced
      `origin/release` tip (same resolution as `main`).
- [ ] Case (2) `test_start_degrades_gracefully_with_no_remote` still passes —
      the no-remote path must still exit 0, create the local branch + worktree,
      and report `pushed_to_origin: false` (the fetch failure is logged via
      `_log`, never `emit_error`'d).
- [ ] **Docs-truth: `plugins/sulis/skills/change/SKILL.md` (line ~131) now
      matches the shipped behaviour.** The claim that `start` "fetches
      `origin/main` before branching, so there is nothing to gate here" is true
      only after the code fix lands. Verify the wording describes what the code
      actually does — fetch-then-branch-off-the-remote-tip, degrade to local
      offline — and that it does not over-claim (it must not imply a hard gate;
      `start` degrades gracefully). The corrected wording must not ship ahead
      of the passing code tests.
- [ ] All existing `start` integration tests stay green
      (`test_start_creates_branch_and_worktree`,
      `test_start_pushes_change_branch_to_origin`,
      `test_start_writes_change_record`, etc.).

### Blue — Refactor / hygiene complete

- [ ] The fetch call mirrors the sibling pattern at line ~818 in tone and
      structure (`_run(["git", "fetch", "origin", base_ref], cwd=repo_root,
      timeout=60)`) — same convention, divergent only in the failure handling
      (`_log` + fall through, not `emit_error`). No new helper invented for a
      single call site (CP/EP: convention over novelty; the one-call inline
      fetch matches the existing in-file style).
- [ ] The fallback `_log` message is plain-English and names what happened and
      what `start` did instead (e.g. "Could not fetch origin/{base_ref}
      (no remote/offline?); starting from the local {base_ref}.") — consistent
      with the existing degrade-gracefully `_log` lines in this file
      (the push-failure `_log` at line ~457).
- [ ] `ruff check` + `ruff format --check` clean on the two Python files
      (`sulis-change` + the integration test). The `change/SKILL.md` edit is
      Markdown prose — no linter beyond the repo's normal docs checks.
- [ ] Full `sulis-change` test suite green
      (`pytest plugins/sulis/scripts/tests -k "change or start"` and the wider
      suite the change runs in CI).

## Sequence

- **dependsOn:** none — single contained fix, no prior WP required.
- **blocks:** none.
- **Parallelisable with:** n/a (sole WP in this change).

## Estimated Token Cost

- **Input:** ~6k (the `cmd_start` body + `git_worktree_add` helper + the
  sibling fetch pattern + the existing `start` integration tests + the
  `_origin_advancer` fixture pattern for test parity).
- **Output:** ~7k (~12 LOC in `cmd_start` + two new ~35-LOC integration tests
  with sibling-clone setup + the one-paragraph docs-truth correction in
  `change/SKILL.md`).
- **Total:** ~13k.

## Notes

- **Touch surface:** 1 script + 1 test file + 1 skill doc = 3 path entries.
  Well under the MUST ≤ 15. The doc is in scope because it currently asserts a
  behaviour the code does not yet exhibit (docs-truth), not because the fix is
  large.
- **Why REINFORCE/fix and not EXPAND:** the change adds a missing
  resilience step (fetch-then-branch-off-fresh) to an existing code path and
  pins it with a characterisation test. No new public surface, no new
  component, no structural move.
- **Why graceful degrade and not a hard gate:** unlike `finish` (which is a
  ship-time operation where a stale base is a real hazard worth blocking on),
  `start` must work offline — a founder cutting a new change on a plane has no
  remote to fetch. The spec is explicit: degrade to the local ref with a
  logged note, never `emit_error`. This also keeps
  `test_start_degrades_gracefully_with_no_remote` green.
- **Seam choice (executor's call):** passing `origin/{base_ref}` straight
  through the existing `base_ref` parameter of `git_worktree_add` is the
  lowest-blast-radius option (the parameter already lands in `git worktree
  add -b … {base_ref}`). `FETCH_HEAD` is an equivalent alternative. Either
  satisfies the contract; do NOT widen `git_worktree_add`'s signature for
  this.
- **No TDD / journey-walk:** this is a contained, non-user-facing tooling fix
  (the surface is the `sulis-change` CLI used by the change machinery, not a
  founder-facing product surface). Per the change brief, journey-walk is
  exempt; no TDD or ADR is warranted for a single-call hardening with an
  established in-file convention to follow.

## Verification Plan

- **What user-observable behaviour is verified:** starting a new change when
  local `main` is behind `origin/main` produces a change branch based on the
  up-to-date `origin/main` tip — not the stale local copy. The same holds for
  an explicit `--base <branch>` (branches off the fetched `origin/{base}` tip).
  Offline start still works (degrades to local base, exit 0). The
  `change/SKILL.md` description of `start`'s base-resolution matches the
  shipped behaviour (docs-truth).
- **Verification environment:** local + CI, via the `local_git_repo` fixture
  (real git, bare `origin` remote) driven by the `run_tool` subprocess
  harness — the established pattern for `sulis-change` integration tests.
- **Bootstrap-from-zero:** a fresh clone at the merge SHA runs
  `pytest plugins/sulis/scripts/tests/integration/test_sulis_change_lifecycle.py`
  and the new test plus all existing `start` tests pass with no extra setup
  (git is the only dependency; the fixture wires its own remote).
- **Per-integration strategy:** the integration here is git-over-a-local-bare-
  remote. Strategy: **real** (no mock) — the fixture's bare `origin` and a
  sibling clone advance `origin/main` for real, mirroring the existing
  `_force_conflicting_local_commit` pattern. Classification: `existing`
  (the fixture and helpers already exist; this WP adds one test that uses
  them). No vendor mock, no network — fully hermetic.
- **Per-kind adapter (`backend`):** the verification artifacts are pytest
  nodeids in
  `plugins/sulis/scripts/tests/integration/test_sulis_change_lifecycle.py`:
  - `::test_start_branches_off_fetched_origin_when_local_main_stale` (case 1 —
    primary)
  - `::test_start_degrades_gracefully_with_no_remote` (case 2 — offline
    fallback)
  - `::test_start_with_explicit_base_branches_off_fetched_origin` (case 3 —
    `--base` honoured)
  The docs-truth check on `change/SKILL.md` is verified by reading the
  corrected line against the shipped `cmd_start` behaviour (no separate test
  artifact — Markdown prose).
- **Verification shape:** **concrete** — the WP ships its own RED→GREEN tests
  the moment it lands. No deferred infrastructure.
- **Acceptance criteria:** cases 1 and 3 fail against current code (prove the
  gap), pass after the fix; case 2
  (`test_start_degrades_gracefully_with_no_remote`) and all existing `start`
  tests stay green; `change/SKILL.md` line ~131 describes the now-shipped
  fetch-then-branch-off-remote (degrade-to-local-offline) behaviour and does
  not over-claim a hard gate.
