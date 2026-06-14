---
id: WP-001
title: "Widened WP-id matcher (prefixed + legacy bare) defined once, consumed by all five callers"
status: pending
change_id: 01KTR381SP5DMB1N8RBKHCVV9Q
kind: backend
primitive: extend
group: REINFORCE
sequence_id: WP-001
dependsOn: []
blocks: []
estimated_token_cost:
  input: 14k
  output: 10k
tdd_section: "§2 D1, §3 Seam, §5 Proof; ADR-001"
adrs: [ADR-001, ADR-002]
verification:
  adapter: backend
  artifact: "plugins/sulis/scripts/tests/unit/test_wpx_index_multitable.py::test_parse_index_keeps_prefixed_and_bare_ids"
---

> **ID-SCHEME NOTE:** this WP's own id is the **bare** `WP-001`, NOT
> `CH-5DMB1N-WP-001`. The chicken-and-egg constraint (TDD §2, ADR-002):
> the parser and `run-all` loop don't understand prefixed ids until *this*
> change ships, so this change's WPs must use the current scheme to be
> executable. Prefixed minting switches on for the next change.

## Context

WP ids are gaining a change-handle prefix (`{CH-HANDLE}-WP-NNN`, e.g.
`CH-5DMB1N-WP-001`) alongside the retained legacy bare `WP-NNN` and the existing
source-tagged `WP-{SOURCE}-{NNN}`. The recognition that a string *is* a WP id is
today open-coded as `startswith("WP-")` (and `removeprefix("wp-")` for the
branch suffix) in **five** call sites. Widening each independently is how the
matcher and its validators drift — the failure `#60`/EP-03 already fixed for the
table-header regex via `_WP_TABLE_HEADER_RE` / `validate_wp_index_header`.

Per ADR-001 this WP defines the widened recognition **once** and rewires all
five sites to consume it. It is atomic: a half-rewired matcher leaves a
silent-drop site (a prefixed row vanishing from the run-all loop), so the
predicate and its consumers must change together.

**Primitive = extend; group = REINFORCE.** We add one new accepted id shape to
an existing recognition surface and reinforce every consumer against the silent
mismatch, pinned by characterisation tests. No new component beyond the
shared predicate the EP-03 rule mandates; no structural move; no wrapper.

## Contract

### New shared surface — `plugins/sulis/scripts/_wpxlib.py`

A single module-level regex plus two thin readers, sited next to
`_WP_TABLE_HEADER_RE` / `CANONICAL_WP_INDEX_HEADER` so the WP-id matcher lives
beside the WP-table matcher:

```python
# Single source of truth for "is this string a WP id?" and "what's its NNN tail?"
# Recognises three shapes for one release (ADR-002 back-compat window):
#   CH-<HANDLE>-WP-<NNN>     prefixed   (the new mint, e.g. CH-5DMB1N-WP-001)
#   WP-<NNN>                 legacy bare (e.g. WP-001)
#   WP-<SOURCE>-<NNN>        source-tagged (e.g. WP-HD-AA-001) — already valid
_WP_ID_RE = re.compile(...)   # the one definition all callers read

def is_wp_id(s: str) -> bool: ...
def wp_nnn_suffix(s: str) -> str: ...   # lowercased "wp-NNN" tail for branch/slug
```

- **`is_wp_id`** — true for all three shapes. Used by the row-filter, the
  full-id detection, and (via a filename-tolerant variant or `is_wp_id(stem)`
  call) the P-VER filename filter.
- **`wp_nnn_suffix`** — returns the lowercased `wp-NNN` tail. For a prefixed id
  it strips the `CH-<HANDLE>-` prefix so the branch stays clean; for a
  bare/source-tagged id it returns the existing tail unchanged (byte-for-byte
  the result `removeprefix("wp-")` produces today for those shapes).

The exact regex/predicate internals are the executor's call; the **contract** is
the accepted-shapes set above and the two function signatures.

### Files modified

```
plugins/sulis/scripts/_wpxlib.py            (+ matcher surface; rewire 4 sites: L1730, L1801, L1990, L2218)
plugins/sulis/scripts/_p_ver_rubric.py      (rewire 1 site: L111 filename filter)
plugins/sulis/scripts/tests/unit/test_wpx_index_multitable.py   (+ both-shapes regression guard + prefixed fixtures)
plugins/sulis/scripts/tests/unit/test_wpx_index_roundtrip.py    (+ prefixed-id roundtrip case, if matcher fixtures live here)
plugins/sulis/scripts/tests/unit/test_compute_wp_status.py      (+ prefixed-id status case)
plugins/sulis/scripts/tests/unit/test_compute_wp_status_callers.py (+ prefixed-id eligibility case)
plugins/sulis/scripts/tests/unit/test_wpx_train_branch_resolution.py (+ prefixed-id branch case asserting clean wp-NNN tail)
plugins/sulis/scripts/tests/unit/test_wpx_wp.py                 (+ prefixed-id WP-file case)
```

> The executor places new fixtures in whichever existing test file already
> exercises that path; the file list above is the expected home for each, not a
> mandate to touch every file if a path's fixtures already live elsewhere.

### Behavioural contract (the five rewired sites)

1. **`parse_index_md` row-filter (~L1801)** — `if not is_wp_id(wp_id):
   continue`. A prefixed `CH-…-WP-NNN` row is **kept**, not dropped. A legacy
   bare `WP-NNN` row is still kept. Non-WP rows (summary rows, blanks) still
   skipped.
2. **`_normalise_wp_reference` (~L1730)** — `if is_wp_id(ref)` for the
   already-full-id branch. A prefixed ref is recognised as full (not mistaken
   for a short suffix). The existing short-suffix `endswith` logic is
   **untouched** — it already tolerates any prefix.
3. **`_branch_name` (~L1990)** — `nnn = wp_nnn_suffix(wp_id)`. A prefixed id
   yields a clean branch `wp/{scope}/wp-NNN-{slug}`, NOT the doubled
   `wp/{scope}/wp-ch-5dmb1n-wp-001-{slug}`. Bare/source-tagged ids produce
   byte-for-byte today's branch.
4. **`resolve_wp_branch` (~L2218)** — same `wp_nnn_suffix(wp_id)` substitution
   for the fuzzy-glob NNN. The #283 per-change `change_scope` threading is
   **unchanged**; only the NNN extraction is routed through the shared
   extractor.
5. **`_p_ver_rubric.py` (~L111)** — the fixture-dir filename filter skips WP
   files of **both** shapes. A prefixed WP file (`CH-…-WP-NNN-{slug}.md`, which
   starts with `CH-`) is correctly skipped, not mis-classified as an SRD/TDD
   artifact.

### Invariants that must NOT change

- **NNN sequencing is byte-for-byte unchanged** — only the rendered label gains
  a prefix; the 1/2/3 counting within a change is identical.
- **#283 branch namespacing intact** — `change_scope` threading,
  `resolve_wp_branch` dual-prefix resolution, the journal-recorded-branch path
  all behave identically; only the NNN tail extraction is shared.
- **Legacy bare ids stay parseable** (ADR-002 one-release back-compat) — no
  migration, no rewrite of any existing id.
- **The short-suffix Depends-On / Blocks resolution stays** — `PERMS` →
  `WP-S2-PERMS` continues to work for both prefixed and bare known-WP sets.

## Definition of Done

### Red — failing tests written first (Non-Negotiable #1)

- [ ] **Load-bearing both-shapes regression guard.**
      `test_parse_index_keeps_prefixed_and_bare_ids` (parametrised or
      two-row single test): build an INDEX fixture containing **one prefixed
      row** (`CH-5DMB1N-WP-001`) and **one legacy bare row** (`WP-002`) in the
      same table; assert `parse_index_md` returns **both** rows with their ids
      intact. FAILS today — the prefixed row is silently dropped by the
      `startswith("WP-")` filter. RED for the right reason.
- [ ] **`_normalise_wp_reference` recognises a prefixed full id.** Assert a
      prefixed ref passed through `_normalise_wp_reference` returns
      `passthrough`/`unknown` as a *full* id (not treated as a short suffix to
      resolve). Add a case proving the short-suffix path still resolves
      `PERMS` → a prefixed known id.
- [ ] **Branch name / resolution carries the clean NNN tail.** In
      `test_wpx_train_branch_resolution.py`, a prefixed id with `change_scope`
      set resolves to `wp/{scope}/wp-001-{slug}` (clean tail), NOT
      `wp/{scope}/wp-ch-5dmb1n-wp-001-{slug}`. FAILS today (`removeprefix("wp-")`
      no-ops on the prefixed id, leaking the doubled prefix).
- [ ] **Status + eligibility on a prefixed id.** In `test_compute_wp_status.py`
      / `test_compute_wp_status_callers.py`, a prefixed-id WP computes status and
      eligibility correctly, with a retained legacy bare-id case alongside.
- [ ] **P-VER filename filter skips prefixed WP files.** A `CH-…-WP-NNN-*.md`
      file in the rubric fixture dir is skipped (not run through the SRD/TDD
      checks), alongside the retained legacy `WP-*.md` skip case.

### Green — implementation makes the tests pass

- [ ] `_WP_ID_RE` + `is_wp_id` + `wp_nnn_suffix` defined once in `_wpxlib.py`,
      sited next to `_WP_TABLE_HEADER_RE`.
- [ ] All five sites rewired to consume the shared surface (per the behavioural
      contract). No residual `startswith("WP-")` / `removeprefix("wp-")` for WP
      ids outside the shared matcher.
- [ ] All new RED tests pass; all retained legacy bare-id tests stay green.
- [ ] Full wpx unit suite green (`pytest plugins/sulis/scripts/tests/unit`),
      and the wider suite the change runs in CI (the ~2,500-test baseline).

### Blue — refactor / hygiene complete

- [ ] The shared matcher mirrors the existing `_WP_TABLE_HEADER_RE` /
      `validate_wp_index_header` shared-source-of-truth pattern in placement and
      comment style (CP-01 — internal prior art; convention over novelty).
- [ ] No new helper invented where the predicate suffices; no `WPId` dataclass
      (YAGNI per ADR-001 — callers only need `is_wp_id` + `wp_nnn_suffix`).
- [ ] `ruff check` + `ruff format --check` clean on every touched `.py` file.
- [ ] Grep confirms zero remaining open-coded WP-id `startswith`/`removeprefix`
      special-cases outside the shared matcher (the five sites are the complete
      set; the short-suffix `endswith` in `_normalise_wp_reference` is
      intentionally retained and is not a WP-id prefix check).

## Sequence

- **dependsOn:** none — the matcher is the foundation; nothing precedes it.
- **blocks:** none — WP-002 and WP-003 (docs/standards) describe the shape this
  WP implements and may be authored in parallel; they SHOULD land in the same
  change but do not block this WP's execution.
- **Parallelisable with:** WP-002, WP-003 (different files — code vs markdown).

## Estimated Token Cost

- **Input:** ~14k (the matcher region of `_wpxlib.py`, the five call sites,
  `_p_ver_rubric.py`, and the six existing unit-test files whose fixtures it
  extends).
- **Output:** ~10k (the ~15-LOC matcher surface + five small rewires + the
  prefixed-id fixtures across six test files).
- **Total:** ~24k.

## Notes

- **Why one atomic WP and not one-per-site:** a half-rewired matcher is a live
  hazard — the moment a prefixed id exists, any un-rewired site either drops a
  row (site 1), mis-classifies a ref (site 2), leaks a prefix into a branch
  (sites 3/4), or mis-runs a rubric (site 5). The five sites share one
  recognition rule and must flip together. The both-shapes regression guard is
  the single load-bearing test that proves they did.
- **Why REINFORCE/extend and not EXPAND-Create at the WP level:** we add one
  accepted id shape to an existing recognition surface and reinforce its
  consumers; the only "new" thing is the EP-03-mandated shared predicate, which
  is an extraction, not a new public component.
- **No TDD-section gap:** see `../TDD.md` §2/§3/§5 and ADR-001/ADR-002.

## Verification Plan

- **What behaviour is verified:** `parse_index_md` returns prefixed AND legacy
  bare rows from one parse (the load-bearing guard); `_normalise_wp_reference`,
  status, eligibility, branch resolution, and the P-VER filename filter all
  operate correctly on both id shapes; branches carry the clean `wp-NNN` tail.
- **Verification environment:** local + CI; `pytest
  plugins/sulis/scripts/tests/unit` (real fixtures, no network), the blocking
  gate before merge.
- **Bootstrap-from-zero:** a fresh clone at the merge SHA runs the unit suite;
  every new prefixed-id case and every retained legacy bare-id case passes with
  no extra setup (pure-Python matcher; the fixtures are self-contained).
- **Per-integration strategy:** the only integration is internal (shared matcher
  ↔ its five callers). Strategy **real, in-process** (no mock). Classification
  `existing` — the six test files already exist; this WP adds prefixed-id cases
  and retains the legacy bare-id cases.
- **Per-kind adapter (`backend`):** pytest nodeids. Primary load-bearing
  artifact:
  `test_wpx_index_multitable.py::test_parse_index_keeps_prefixed_and_bare_ids`.
  Supporting: `test_wpx_train_branch_resolution.py` (clean-tail branch),
  `test_compute_wp_status.py` / `test_compute_wp_status_callers.py`
  (status/eligibility), `test_wpx_wp.py` (WP-file handling), the
  `_p_ver_rubric` filename-filter case.
- **Verification shape:** **concrete** — RED→GREEN tests ship with the WP.
- **Acceptance:** the both-shapes guard and the clean-tail branch case fail
  against current code (prove the gap), pass after the rewire; every retained
  legacy bare-id test and the full wpx suite stay green.

## Acceptance Evidence

- Branch: feat/wp-001-shared-wp-id-matcher (deleted post-merge)
- Health status: `n/a (no-deploy profile)`
- Smoke-test verdict: n/a
- Completed: `2026-06-10T08:31:53Z` (Step 12 by calling session)
