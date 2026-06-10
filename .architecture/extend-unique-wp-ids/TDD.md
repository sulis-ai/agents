# Technical Design — globally-unique Work Package ids via change-handle prefix

> **Change:** CH-5DMB1N · extend · `unique-wp-ids`
> **Spec:** [../../.changes/extend-unique-wp-ids.SPEC.md](../../.changes/extend-unique-wp-ids.SPEC.md)
> **Recon:** [../../.changes/extend-unique-wp-ids.RECON.md](../../.changes/extend-unique-wp-ids.RECON.md)
> **Status:** designed
> **Tier:** S (contained internal-tooling extend — see Sizing Report)

---

## 1. What this change does

Today two different changes can each mint a Work Package called `WP-001`, and
those bare ids collide — the same root cause that drove the cross-change train
mis-routing fixed for *branches* in PR #283. PR #283 namespaced WP **branches**
per change (`wp/{primitive}-{slug}/wp-NNN`). This change does the same for the
**id label**: mint ids as `{CH-HANDLE}-WP-NNN` (e.g. `CH-5DMB1N-WP-001`),
keeping the human-friendly 1/2/3 sequence within a change but making every id
globally unique across changes.

The per-change `NNN` sequencing logic is **byte-for-byte unchanged** — only the
rendered label gains a prefix. This is the id-label twin of #283's branch-label
namespacing; the two together close the collision class for good.

---

## 2. The two load-bearing decisions

### D1 — One id-matcher, defined once, reused by every caller (Form)

The WP-id recognition that today reads `wp_id.startswith("WP-")` is scattered
across five call sites. Widening each independently is exactly how the matcher
and its validators drift (the failure the existing `validate_wp_index_header` ↔
`parse_index_md` shared-regex discipline was built to prevent — #60, EP-03).

**Decision:** define the widened id recognition **once** — a single module-level
regex plus a small predicate/extractor surface in `_wpxlib.py` — and have every
caller reuse it. The matcher recognises **both** shapes for one release:

- prefixed: `CH-<HANDLE>-WP-<NNN>` (e.g. `CH-5DMB1N-WP-001`)
- legacy bare: `WP-<NNN>` (e.g. `WP-001`)
- existing source-tagged: `WP-<SOURCE>-<NNN>` (e.g. `WP-HD-AA-001`) — still valid

It exposes two operations the callers need:

1. **`is_wp_id(s)`** — does this string name a Work Package? (used by the
   `parse_index_md` row-filter, the `_normalise_wp_reference` full-id detection,
   and the P-VER rubric filename filter).
2. **`wp_nnn_suffix(s)`** — return the `wp-NNN` tail, lowercased, for branch +
   slug composition (used by `_branch_name` and `resolve_wp_branch`).

This is **EXPAND-Create at the abstraction level** — one new shared predicate
that the existing call sites consume. It is *not* a Wrap: we are not layering
over internal code, we are extracting the shared primitive the EP-03 rule
requires (and that the codebase already practises for the table-header regex).

See **ADR-001**.

### D2 — Strictly additive, one-release back-compat (Armor / safety)

Changes already in flight carry bare `WP-NNN` ids in their committed INDEX
files. If the parser stops understanding them, those changes break mid-run.

**Decision:** new ids are prefixed; existing bare ids stay bare and remain
parseable. **No migration pass** over in-flight INDEX files. Both shapes are
understood for exactly one release. Dropping bare-id support is a separate,
future change — recorded as a tracked follow-up (already on the task list) so
the deprecation is actioned, not forgotten. See **ADR-002**.

### The chicken-and-egg constraint (why THIS change's WPs are bare)

This change's own Work Package ids **must use the current bare `WP-NNN`
scheme**, not the new prefixed scheme — because the parser and the `run-all`
loop won't understand prefixed ids until this very change ships. Minting this
change's WPs as `CH-5DMB1N-WP-001` would make them invisible to the very tooling
that has to execute them. They are therefore `WP-001`, `WP-002`, `WP-003`. This
is the one place the new convention is deliberately *not* applied; it switches
on for the *next* change minted after this one merges.

---

## 3. The seam (located by recon — design, not re-search)

All id-shape recognition lives in `plugins/sulis/scripts/`. Five call sites, all
inheriting the D1 shared matcher:

| # | Site | Today | After |
|---|---|---|---|
| 1 | `_wpxlib.py:parse_index_md` (~L1801) | `if not wp_id.startswith("WP-"): continue` — **silently drops** a prefixed row | `if not is_wp_id(wp_id): continue` |
| 2 | `_wpxlib.py:_normalise_wp_reference` (~L1730) | `if ref.startswith("WP-")` full-id detection | `if is_wp_id(ref)` |
| 3 | `_wpxlib.py:_branch_name` (~L1990) | `nnn = wp_id.lower().removeprefix("wp-")` | `nnn = wp_nnn_suffix(wp_id)` |
| 4 | `_wpxlib.py:resolve_wp_branch` (~L2218) | same `removeprefix("wp-")` | `nnn = wp_nnn_suffix(wp_id)` |
| 5 | `_p_ver_rubric.py` (~L111) | `if name.startswith("WP-"): continue` — skips WP files in a fixture dir | `if is_wp_id_filename(name): continue` |

**Site 1 is the load-bearing back-compat point** — the silent-drop. **Sites 3/4
are the branch-cleanliness point**: `removeprefix("wp-")` is a no-op on a
prefixed id (`ch-5dmb1n-wp-001` doesn't start with `wp-`), so without
`wp_nnn_suffix` the branch would become `wp/{scope}/wp-ch-5dmb1n-wp-001-{slug}`
— a leaked, doubled id. The shared suffix extractor keeps branches clean and the
per-change namespacing from #283 intact. **Site 5** is a *filename* filter that
was not in the original recon seam list but inherits the same rule — prefixed WP
files start with `CH-`, so the bare `startswith("WP-")` would mis-classify them
as SRD/TDD artifacts.

The suffix-match logic in `_normalise_wp_reference` for *short* Depends-On /
Blocks refs (`PERMS` → `WP-S2-PERMS`) is already tolerant of any prefix
(`endswith`) and stays untouched.

The filename glob `{wp_id}-*.md` (`_wp_slug_from_file`) follows the id
automatically — no change needed once the minted id changes.

---

## 4. Mint path (the authored canonical id rows)

The example/canonical id rows that teach the prefixed shape live in five
markdown surfaces. These are **docs/standards edits**, separable from the code:

- `skills/plan-work/references/work-package-template.md` (the `id:` /
  `sequence_id:` template rows)
- `skills/design/SKILL.md`
- `agents/engineering-architect.md`
- `agents/orchestrator.md`
- `agents/executor.md`

Plus the two standards that describe the id shape and the back-compat window:

- `references/standards/WORK_PACKAGE_STANDARD.md` — the WP-01 `id` row (L47)
- `references/change-work-standard.md` — CW-04 (the id-label twin of the WP
  branch-ref subsection #283 already added)

---

## 5. Pillars (MECE-3)

**Form** — D1: one matcher, defined once, consumed by five callers. No new
component beyond the shared predicate; the predicate is the EP-03-mandated
shared primitive. No dependency-direction change.

**Armor** — D2: strictly additive, one-release back-compat; no migration; no
behaviour change to NNN sequencing or to #283 branch namespacing. The risk is a
silent regression in either back-compat (a dropped legacy row) or branch
cleanliness (a leaked prefix in a branch name) — both are pinned by tests.

**Proof** — the load-bearing regression guard is a **parametrised test** proving
`parse_index_md` returns a prefixed `CH-…-WP-NNN` row *paired with* a legacy
bare `WP-NNN` row from the **same parse** (both shapes survive one release).
Status, eligibility, and branch resolution each gain a prefixed-id fixture
alongside the retained legacy bare-id fixture. Branch resolution additionally
asserts the resolved branch carries the clean `wp-NNN` tail, not the doubled
prefix.

---

## 6. Reconciling the parked `canonicalise-cross-wp-ids` effort

The parked effort under `.architecture/canonicalise-cross-wp-ids/` was never
substantively designed — it contains only a stray executor journal
(`work-packages/.executor-WP-001.md`), no spec, no TDD, no real WP. Its intent —
"make WP ids unique across changes" — is **exactly** what this change realises,
the canonical way (handle-prefix, mirroring #283's branch scheme). There is no
salvageable design to fold in. It is **superseded** by this change: the intent
lives here; the parked stub is retired. See **ADR-002**.

---

## 7. Verification Plan

<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->

This change is internal tooling with **no user-visible surface**; there is no
user-journey scenario to author (`n/a — non-founder-facing`). Verification is
the wpx pytest suite, extended with prefixed-id fixtures.

1. **User-observable behaviour verified** — a WP minted under a change renders
   `{CH-HANDLE}-WP-NNN`; the parser returns prefixed rows (not dropped) *and*
   legacy bare rows; status / eligibility / branch resolution operate correctly
   on both shapes within one release. (No founder-facing surface; the "user"
   here is the change/run-all machinery.)

2. **Verification environment(s)** — local + CI. The wpx unit suite under
   `plugins/sulis/scripts/tests/unit/` (real fixtures, no network), run as the
   blocking gate before merge.

3. **Bootstrap-from-zero** — a fresh clone at the merge SHA runs
   `pytest plugins/sulis/scripts/tests/unit/ -k "wpx or compute_wp_status or
   train_branch"` and every case — new prefixed-id and retained legacy bare-id —
   passes with no extra setup. The matcher is pure-Python; no external dependency.

4. **Per-integration verification strategy** — there is no external integration.
   The only "integration" is internal: the shared matcher ↔ its five callers.
   Strategy: **real, in-process** (no mock) — the unit suite exercises
   `parse_index_md`, `_normalise_wp_reference`, status/eligibility computation,
   and branch resolution against real INDEX/WP fixtures carrying both id shapes.
   Classification: `existing` (the test files already exist; this change adds
   prefixed-id cases and retains the legacy bare-id cases).

5. **Per-kind verification adapter (`backend`)** — pytest nodeids. The
   load-bearing artifact:
   - `plugins/sulis/scripts/tests/unit/test_wpx_index_multitable.py` (or
     `test_wpx_index_roundtrip.py`) ::`test_parse_index_keeps_prefixed_and_bare_ids`
     — the parametrised both-shapes regression guard (executor picks the
     existing file whose fixtures it extends; the contract is one parse, both
     shapes returned).
   - `test_wpx_train_branch_resolution.py` — a prefixed-id branch-resolution
     case asserting the clean `wp-NNN` tail.
   - `test_compute_wp_status.py` / `test_compute_wp_status_callers.py` — a
     prefixed-id status/eligibility case.
   - `test_wpx_wp.py` — prefixed-id WP-file handling.
   Verification shape: **concrete** — every code WP ships its own RED→GREEN
   tests the moment it lands.

6. **Infrastructure needs surfaced (deferred)** — none. Fully hermetic; the
   existing fixtures cover it. The only follow-on is the legacy-removal change
   (tracked task, **not** test infrastructure).

---

## 8. Sizing Report

- **Tier (computed + confirmed):** S. sFPC ≈ 4 (one new shared predicate
  abstraction + edits to 5 mint surfaces + 2 standards + test fixtures; no new
  entities, no integrations). ASR ≈ 3 (one-release back-compat invariant;
  single-source-of-truth matcher constraint; #283 branch-namespacing
  preservation). Higher of the two → S.
- **Coverage:** no `.context/` index for this repo; no prior TDD for this seam.
  Form/Armor/Proof all authored fresh but kept short — the change is contained.
- **TDD length vs target:** within the S target; no "why is this big" paragraph
  needed.
- **ADRs produced vs expected:** 2 (matcher single-source-of-truth; additive
  back-compat + supersession). Both lock a real decision affecting >1 call site;
  neither restates an existing ADR. Within the S maximum.
- **Sections that referenced rather than restated:** the seam table points at
  `_wpxlib.py` line ranges rather than reproducing code; the standards-reconcile
  WPs cite the exact lines (WORK_PACKAGE_STANDARD L47, CW-04) rather than
  quoting them.
- **Circuit breakers triggered:** none.
