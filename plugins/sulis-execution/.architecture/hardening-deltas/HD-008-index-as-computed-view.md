---
id: HD-008
title: INDEX.md becomes a computed view (status derives from origin + train records)
status: implemented
severity: HIGH
pillar: form
sources:
  - SEA audit report 2026-05-23 (Pattern C — INDEX.md is a stored source of truth for WP status, which can drift from authoritative git/origin state; the drift class is what motivated `wpx-train doctor`'s status-drift detection at v0.21.2; the right move is to make the cache disappear so the drift class disappears)
  - Operational anchor: 2026-05-22 slice-2 audit surfaced 3 WPs at INDEX status `done` whose work was never on dev; ad-hoc reconciliation followed; HD-007/HD-001 closed the dispatch boundary so this delta can now close the state-of-record boundary
created: 2026-05-23
implemented: 2026-05-23
---

## Context

`INDEX.md` is `.architecture/{project}/work-packages/INDEX.md` — the
Markdown table that lists every WP, its primitive, its dependencies, and
its `Status` cell (`pending` / `in_progress` / `step-7-complete` /
`step-7-blocked` / `step-7-held` / `done` / `dependency_blocked` /
`auto-draft` / `cancelled` / `blocked`).

Today the Status cell is **stored**: it is mutated by `wpx-index
flip-status` (called from the executor's Step 7, from the train's Step 8
on success, from Step 12 wrap, from failure paths in `_handle_*_failure`
in `wpx-train`). Multiple writers, one cache. The cache is consulted by
the eligibility computer (`find_eligible_branches` reads `wp.status`),
the dependency resolver (`_all_deps_merged` reads `wp.status` for each
dep), `wpx-train queue list`, `wpx-train status`, `wpx-train doctor`,
the run-all skill's ready-set computation, every concierge readback,
and `wpx-step12 wrap`.

`wpx-train doctor` (v0.21.2+) exists specifically because this cache
can drift from origin. The drift cases the doctor detects:

1. **`status_drift_done_no_merge_history`** — INDEX says `done`; no
   train-runs record has a `merge_sha_on_dev` for the WP. Means the
   WP was manually flipped, or shipped via legacy `wpx-pipeline`, or
   state was lost.
2. **`status_drift_done_not_on_dev`** — INDEX says `done`; the
   recorded merge SHA exists but is not reachable from
   `origin/<base_branch>`. Means the work landed and was reverted, or
   the SHA was mis-recorded.

The doctor catches the symptom. It does not address the cause. The
cause is **the cache itself** — the moment WP status is stored
separately from the authoritative state (origin git + train records),
two sources of truth exist and they will diverge under failure modes
(reverts, manual flips, partial-merge crashes, mid-pipeline interruptions,
operator error).

### Why the cache exists today

Two reasons, both addressable:

1. **Historical.** v0.1-v0.10 had no concept of train records; the
   only way to know "is this WP done?" was to ask INDEX.md. The cache
   was the storage.
2. **Cost.** Computing status from origin requires a `gh compare` API
   call per WP. For a 100-WP project that's 100 API calls per status
   read. Today's INDEX read is one filesystem stat.

The cost argument no longer dominates: train records (`train-runs/*.yaml`
and `*.state.json`) are already local and already record
`merge_sha_on_dev` per WP. `is_sha_on_branch` is a single `gh compare`
call. Most WPs are not in flight at any given moment, so a session's
total compute cost is bounded by the number of `in-flight` or
recently-shipped WPs, not the total WP count.

### The architectural cost of the cache

- **The drift class exists.** `wpx-train doctor` is a primitive that
  exists *because* the cache can be wrong. With no cache, there is no
  drift class — status is computed from authoritative state on every
  read.
- **Multiple writers race.** Train's Step 8 flips `step-7-complete` →
  `done` via `flip_index_status_via_cli`; Step 12 wrap also flips per-WP.
  Executor Step 7 flips `in_progress` → `step-7-complete`. Failure
  paths flip to `step-7-blocked`. Six distinct callsites, one
  shared mutable cell per WP — every callsite is a fresh opportunity
  for a missed flip or a wrong-state flip.
- **Status semantics are stretched.** The same `Status` cell encodes
  six conceptually-distinct things: (a) "has the executor started?"
  (`pending` vs `in_progress`), (b) "is the work pushed?"
  (`step-7-complete`), (c) "is the work on dev?" (`done`), (d) "is the
  WP held by an override?" (`step-7-held`), (e) "is the WP blocked by a
  BLOCKER?" (`step-7-blocked` / `blocked`), (f) "is the WP awaiting
  founder disposition?" (`auto-draft`). Some of these are
  authoritative-derivable; some are operator-set. They are not the same
  kind of fact and shouldn't live in the same cell.

### The right model

**Status is computed from authoritative sources.** Specifically:

| Computed status | Computed-from |
|---|---|
| `done` | recorded `merge_sha_on_dev` for this WP is reachable from `origin/<base_branch>` (via `is_sha_on_branch`) |
| `step-7-shipping` | in-flight train record (`train-runs/<id>.state.json`) lists this WP in `bundle` and the record's `phase` is not terminal |
| `step-7-complete` | origin branch `feat/wp-<slug>` exists AND no in-flight train with this WP |
| `pending` / `in_progress` / `dependency_blocked` / `auto-draft` / `cancelled` / `blocked` / `step-7-blocked` / `step-7-held` | INDEX.md's stored cell remains the source for these states; the cache stays valid for operator-set / executor-set states that have no authoritative-state correlate |

The split is principled: **states the system can derive from
authoritative artifacts are computed; states that record human or
executor intent (auto-draft, hold, blocked-by-BLOCKER) remain stored.**

The doctor then has a trivial detector: *"the stored cell and the
computed cell disagree on a state that should have been computed"*.

## Decision

### A. Introduce `compute_wp_status` (Commit A — infrastructure only)

A new function in `_wpxlib.py`:

```python
def compute_wp_status(
    wp_id: str,
    paths: WpxPaths,
    repo: str,
    base_branch: str = "dev",
    *,
    gh: GHClient | None = None,
    stored_status: str | None = None,
) -> str:
    """Return the computed status for ``wp_id``.

    Resolution order (the four authoritative-derivable cases first, then
    fall through to the stored cell for operator/executor intent):

    1. `done` — find_wp_merge_sha(paths.train_runs_dir, wp_id) returns
       a SHA AND is_sha_on_branch(repo, sha, base_branch) is True.
    2. `step-7-shipping` — any `*.state.json` in train-runs/ has this
       WP in `bundle` AND `phase` is one of the in-flight phases
       (planning, committing, verifying, verifying_gates).
    3. `step-7-complete` — origin/`<branch>` exists for the WP's
       canonical branch name AND case 1 + case 2 are both False.
    4. `pending` (no origin branch, no in-flight train) — fall back to
       the stored cell if provided; otherwise return `pending`.

    The function never raises on transient network failure: callers pass
    `stored_status` (typically the cell already parsed from INDEX.md) so
    the function falls back to the cache when a computation is
    inconclusive. This is the *conservative* posture — a True return for
    `done` must be trustworthy (covered by `is_sha_on_branch`'s
    fail-False contract); other returns may degrade to the stored value.
    """
```

The function does not write to INDEX.md. It does not call
`flip_index_status_via_cli`. It only reads.

### B. `wpx-index status` subcommand (Commit A)

A new read-only subcommand:

```
wpx-index status --wp WP-NNN [--repo OWNER/REPO] [--base-branch dev]
                            [--stored | --computed | --both]
wpx-index status --all      [--repo OWNER/REPO] [--base-branch dev]
                            [--show-disagreements-only]
```

- `--wp WP-NNN` returns one WP's status; `--all` returns the whole
  table.
- `--stored` returns the INDEX.md cell value only (no network).
- `--computed` returns the `compute_wp_status` result.
- `--both` (default) returns `{stored, computed, drift}` where `drift`
  is `True` iff they disagree on a computed-eligible state.
- `--show-disagreements-only` filters `--all` output to only WPs with
  drift — gives the founder the doctor-style report deterministically.

The subcommand reads. It does not flip. (Reconciliation stays a
separate, founder-confirmed action via existing `flip-status`
subcommand with `--expected`.)

### C. Migrate eligibility check (Commit B)

`find_eligible_branches` today reads `wp.status` from
`parse_index_md`'s parse. The check at line 1444
(`if wp.status != TRAIN_ELIGIBLE_STATUS and not is_forced`) is the
load-bearing decision: only `step-7-complete` WPs enter the train.

Migration: when called with a `repo` parameter, the function asks
`compute_wp_status` for each candidate WP and uses the computed value
for the eligibility-shape check, while continuing to read
`wp.depends_on` and `wp.id` from the INDEX parse (those don't drift —
they're structural, not status). The dependency check
(`_all_deps_merged`) likewise migrates: a dep is "merged" iff its
computed status is `done`, not iff its stored cell says `done`.

This closes the operational anchor: 3 WPs at stored `done` whose work
isn't on dev would not be treated as merged-deps by the eligibility
computer; downstream WPs would not be falsely unblocked.

### D. Migrate doctor (Commit B)

`cmd_doctor` in `wpx-train` today re-implements the drift detection
inline at lines 1004-1036. Migration:

- Drift detection becomes "for each WP, compute its status; if
  computed != stored AND stored ∈ computed-eligible set, that IS
  drift". One loop, two function calls.
- The existing per-case issue kinds (`status_drift_done_no_merge_history`,
  `status_drift_done_not_on_dev`) are preserved by inspecting *why*
  `compute_wp_status` returned non-`done` (no merge SHA known →
  no-history; merge SHA known but not on branch → not-on-dev).
- Output schema unchanged (the doctor's caller — the run-all skill —
  parses `issues`).

### E. Deprecate `flip_index_status_via_cli` (Commit B)

The function does not get removed in this delta. Instead:

1. Emit a `DeprecationWarning` (and a `_log` line) on every call.
2. Keep the body intact (still writes the cache) so callers continue
   to work and the cache stays approximately in-sync for any reader
   that hasn't migrated yet (forward compatibility).
3. Document at the top of the function: *"As of HD-008, status is
   computed from authoritative sources for the computed-eligible set
   ({done, step-7-shipping, step-7-complete}). This function still
   writes the cache for backward compatibility, but new callers should
   compute and rely on `compute_wp_status` instead. Removal target:
   when all callsites have migrated."*

The 8 existing callsites in `wpx-train` and the run-all skill stay
functional. Migration of each callsite to drop the flip call entirely
is follow-on work (one delta per callsite group, post-HD-008).

### F. Documentation (Commit B)

- Update `references/lifecycle.md` to document the computed-status
  model: which states are computed-from-authoritative-sources, which
  are stored, how the doctor's drift detection is now trivial.
- If `skills/run-all/SKILL.md` relies on the *stored* INDEX status
  for any decision (concretely: the ready-set computation at SKILL.md
  step ~125), surface that and document the migration path. (The
  ready-set today reads INDEX cells for `status == "pending"` AND deps
  at `status == "done"` — once HD-008 lands, this would mean stored
  pending + computed-done-deps, which is a coherent rule but needs to
  be written down.)

## Verification

**Characterisation tests** in
`scripts/tests/unit/test_compute_wp_status.py`:

1. **`test_compute_wp_status_returns_done_when_sha_on_branch`** — given a
   train record with `merge_sha_on_dev: abc123` for WP-NNN AND a mock
   `is_sha_on_branch` that returns True → returns `"done"`.
2. **`test_compute_wp_status_returns_step_7_shipping_when_in_flight_train`** —
   given an in-flight `*.state.json` whose `bundle` lists WP-NNN AND
   `phase: verifying` → returns `"step-7-shipping"`.
3. **`test_compute_wp_status_returns_step_7_complete_when_branch_exists_no_train`** —
   given an origin branch exists (mocked `branch_exists` returns True)
   AND no in-flight train AND no merged record → returns
   `"step-7-complete"`.
4. **`test_compute_wp_status_falls_back_to_stored_when_no_origin_signal`** —
   given no origin branch, no in-flight train, no merged record →
   returns the provided `stored_status` (or `"pending"` if not provided).

Each test exists as a deterministic unit test using
`unittest.mock.patch` over the GHClient calls, mirroring the existing
`test_wpx_train_drift_detection.py` pattern.

**Tests for the migrated eligibility check** (Commit B):

5. **`test_find_eligible_branches_uses_computed_status_when_repo_given`** —
   given a WP whose INDEX stored cell says `done` but
   `compute_wp_status` returns `"step-7-complete"` (because the merge
   SHA was reverted), the WP is still considered for eligibility (not
   skipped as already-done).

**Tests for the migrated doctor** (Commit B):

6. **`test_doctor_uses_compute_wp_status_for_drift_detection`** — given
   a WP at stored `done` whose `compute_wp_status` returns
   `"step-7-complete"`, the doctor reports an issue of kind
   `status_drift_done_not_on_dev` (or `_no_merge_history` depending on
   the cause), preserving the existing schema.

All tests must pass without regressing the existing 298 wpx tests + 31
sdk-python tests + 20 sdk-mcp tests.

## Changes

### ADDED — Commit A

- `scripts/_wpxlib.py`: `compute_wp_status` function and a small
  helper `_in_flight_train_has_wp` that walks `*.state.json` looking
  for in-flight records.
- `scripts/wpx-index`: `cmd_status` handler + `--wp` / `--all` parser
  wiring.
- `scripts/tests/unit/test_compute_wp_status.py`: characterisation
  tests 1-4.

### ADDED — Commit B

- `scripts/tests/unit/test_compute_wp_status_callers.py`: tests 5-6
  (and any additional tests covering migrated callsites).

### MODIFIED — Commit B

- `scripts/_wpxlib.py`: `find_eligible_branches` accepts a `repo`
  parameter (already passed by callers) and consults
  `compute_wp_status` for the eligibility status check and for
  dependency-merged checks. Default behaviour preserved when `repo` is
  None (test-only path).
- `scripts/_wpxlib.py`: `flip_index_status_via_cli` emits a
  `DeprecationWarning` + `_log` line and gains a top-of-function
  docstring explaining the deprecation. Body unchanged.
- `scripts/wpx-train` `cmd_doctor`: drift detection rewritten in terms
  of `compute_wp_status`. Output schema unchanged.
- `references/lifecycle.md`: new section *"Computed status (HD-008)"*
  documenting which states are computed vs stored; doctor's trivial
  drift-detection rule; deprecation of `flip_index_status_via_cli`.
- `skills/run-all/SKILL.md`: if and where the ready-set computation
  reads stored INDEX status, add a note pinning the rule (stored
  `pending` + computed-`done` deps) and pointing at HD-008.

### REMOVED — none in HD-008

No removals. `flip_index_status_via_cli` is deprecated, not removed.
Stored INDEX cells remain valid for the operator/executor-intent
states (`pending`, `in_progress`, `auto-draft`, `cancelled`,
`step-7-blocked`, `step-7-held`, `dependency_blocked`, `blocked`).

## Rationale (delta-shape)

This is split into two commits inside a single dispatch because the
two commits have distinct review profiles:

- **Commit A** is additive: a new function, a new subcommand, a new
  test file. Zero migrated callers. The blast radius is small — review
  focuses on the API surface and the test coverage of the four status
  cases.
- **Commit B** migrates two production callers (eligibility +
  doctor), adds the deprecation warning, and updates two docs. The
  blast radius is larger; review focuses on whether the migrated
  callers still behave correctly under every existing test.

Splitting lets `/sea:code-review` run twice with focused diffs each
time, instead of one 800-line diff that's hard to review thoroughly.
This matches the operational pattern PH-02 (PR Hygiene Size) was
calibrated against in batches 4 and 5.

## Implementation notes (post-landing)

**Commit A** added `compute_wp_status`, `_in_flight_train_has_wp`,
`_IN_FLIGHT_TRAIN_PHASES`, the `wpx-index status` subcommand, and 15
characterisation tests. No callers migrated. Tests: 313 wpx pass
(298 + 15); 31 sdk-python; 20 sdk-mcp; 1 pre-existing flaky
`test_train_lock_second_acquisition_raises`.

**Commit B** migrated three call sites of `find_eligible_branches`
(`queue-list`, `status`, `run`) in `wpx-train` to pass `paths` +
`base_branch`, enabling computed-status eligibility. Added 4 caller
tests (3 for `find_eligible_branches` + 1 for the deprecation
warning).

**Deviation from the original plan: `cmd_doctor` was NOT migrated to
`compute_wp_status`.** During implementation we discovered that
`compute_wp_status` is *deliberately conservative*: when
`is_sha_on_branch` returns False (which happens on both "SHA is not
on dev" AND "API call failed"), the function falls through to the
caller-supplied `stored_status` so eligibility decisions don't
oscillate on transient network errors. That's the correct posture
for eligibility, but the WRONG posture for drift detection — the
doctor specifically wants to distinguish the two cases. Pre-HD-008's
doctor already did the right two-step check (`find_wp_merge_sha`,
then `is_sha_on_branch`) so we kept it as-is and documented the
deliberate non-use of `compute_wp_status` in the doctor's docstring.
Net effect: drift-detection behaviour is unchanged from v0.21.2 —
which is what we want.

**Test count adjusted:** existing
`scripts/tests/integration/test_wpx_train_queue_list.py::test_queue_list_emits_eligible_and_ineligible_lists`
was updated to reflect HD-008's new semantics — under the computed
model, a WP with stored `pending` AND an origin branch that exists
is now correctly evaluated as `step-7-complete` (the work IS pushed)
rather than respecting the stale cache. The test was tightened to
assert this by NOT mocking the origin branch for the pending WP.

**Commit shas:**
- Commit A: `abbbaf6`
- Commit B: (this commit; see git log)

## Why HIGH severity

The drift class is operational, not theoretical: the 2026-05-22 audit
surfaced 3 concrete WPs whose stored INDEX cell was wrong, downstream
WPs were potentially unblocked on false `done` signals, and ad-hoc
reconciliation was required. The cache is the root cause; removing
the cache (for the computed-eligible set) removes the drift class.
This is operational pain probable within 90 days that has already
been observed.

Not CRITICAL because the existing `doctor` primitive catches the
drift before downstream WPs ship on it (the workflow surfaces the
problem), but the structural fix is overdue.
