---
founder_facing: false
---

# Spec — globally-unique Work Package ids via change-handle prefix

**Change:** CH-5DMB1N · extend

## Intent

Today two different changes can each mint a Work Package called `WP-001`, and
those bare ids can collide — the same root cause that drove the cross-change
train mis-routing fixed for *branches* in PR #283. That fix namespaced WP
**branches** per change (`wp/{primitive}-{slug}/wp-NNN`). This change does the
same for the **id label**: mint ids as `{CH-HANDLE}-WP-NNN` (e.g.
`CH-5DMB1N-WP-001`), keeping the human-friendly 1/2/3 sequence within a change
but making every id globally unique.

The per-change NNN sequencing logic does **not** change — only the rendered id
label gains a prefix.

## Scope

1. **Mint path** — new WP ids carry the `{CH-HANDLE}-` prefix. The authored
   example/canonical id rows live in the design + plan-work surfaces:
   `skills/plan-work/references/work-package-template.md`,
   `skills/design/SKILL.md`, `agents/engineering-architect.md`,
   `agents/orchestrator.md`, `agents/executor.md`.

2. **Parser + tooling reads both shapes** (`_wpxlib.py`):
   - `parse_index_md` row-filter `if not wp_id.startswith("WP-")` — today this
     would silently drop a prefixed `CH-…-WP-NNN` row. Widen it to recognise
     both the prefixed shape and legacy bare `WP-NNN`.
   - `_normalise_wp_reference` full-id detection (`ref.startswith("WP-")`) — a
     prefixed id starts with `CH-`; widen the "already-full" recognition. The
     existing suffix-match logic for short Depends-On / Blocks references is
     already tolerant and stays.
   - Anywhere else the bare `WP-` prefix is special-cased in status /
     eligibility / branch wiring inherits the same both-shapes recognition. The
     per-change branch namespacing from #283 (`resolve_wp_branch`,
     `change_scope` threading) already follows the id and needs no sequencing
     change.

3. **Standards reconciled** — `WORK_PACKAGE_STANDARD` (the id row) and
   `change-work-standard` (CW-04) describe the implemented `{CH-HANDLE}-WP-NNN`
   shape, and record the one-release back-compat window for legacy bare ids.

4. **Test fixtures** — the wpx unit suite (`scripts/tests/unit/test_wpx_index_*`,
   `test_compute_wp_status*`, `test_wpx_train_branch_resolution`, `test_wpx_wp`)
   gains prefixed-id coverage: parse, status, eligibility, and branch wiring all
   exercised against `{CH-HANDLE}-WP-NNN` ids, alongside the retained legacy
   bare-id cases.

5. **Supersede the parked effort** — the parked `canonicalise-cross-wp-ids`
   work is reconciled into this change: this is the canonical realisation of
   per-change-unique ids. Do not duplicate it; fold any still-relevant intent
   from it here and retire it.

## Non-goals

- **No change to NNN sequencing.** The 1/2/3 counting within a change is
  byte-for-byte unchanged; only the rendered label gains a prefix.
- **No rewrite of existing in-flight ids.** This is strictly additive — new
  ids are prefixed; existing bare `WP-NNN` ids stay bare and are simply
  *understood* by the widened parser. No migration pass over in-flight INDEX
  files.
- **No removal of legacy support in this change.** Both shapes are understood
  for one release; dropping bare-id support is a separate, future change
  (captured as a follow-up so the deprecation is actioned, not forgotten).
- **No change to founder-facing output.** WP ids are already stripped from
  founder-facing surfaces (FE-06); this change has zero user-visible effect.

## Acceptance

- A WP minted under a change renders its id as `{CH-HANDLE}-WP-NNN`
  (e.g. `CH-5DMB1N-WP-001`).
- `parse_index_md` returns the prefixed row (it is **not** dropped) AND still
  returns a legacy bare `WP-NNN` row from an unmigrated INDEX.
- Status, eligibility, and branch resolution operate correctly on a prefixed
  id and on a legacy bare id within the same release.
- `WORK_PACKAGE_STANDARD` id row + `change-work-standard` CW-04 read the
  implemented prefixed shape and name the one-release back-compat window.
- Full wpx unit suite green, with new prefixed-id fixtures added and the
  legacy bare-id fixtures retained.

## Constraints

- **One-release back-compat is load-bearing.** Changes already in flight carry
  bare `WP-NNN` ids in their committed INDEX files; the parser MUST keep
  understanding them for this release, or in-flight changes break mid-run.
- **Single source of truth for the id matcher.** Per EP-03 / the existing
  `validate_wp_index_header` ↔ `parse_index_md` shared-matcher discipline, the
  widened id recognition must be defined once and reused by every caller
  (parse, lint, status, eligibility) so the matcher and its validators cannot
  drift.
- Must not break the per-change branch namespacing landed in #283.

## Verification Plan

- **How we'll know it works:** the wpx unit + integration suites, extended with
  prefixed-id fixtures, prove parse / status / eligibility / branch-resolution
  on both id shapes. The whole suite must stay green (the existing
  ~2,500-test baseline + the new cases).
- **The load-bearing check:** a parametrised test asserting `parse_index_md`
  returns a `CH-…-WP-NNN` row (regression guard against the silent-drop seam),
  paired with a legacy bare-`WP-NNN` row from the same parse — proving both
  shapes survive in one release.
- **Verified by:** the wpx pytest suite, run as the blocking gate before merge.
- This change is internal tooling with no user-visible surface, so there is no
  user-journey scenario to author (`n/a — non-founder-facing`).
