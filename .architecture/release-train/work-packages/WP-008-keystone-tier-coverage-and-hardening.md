---
# Identity (WP-01)
id: WP-008
title: "Keystone remediation — full 22-primitive tier coverage + writer hardening + cross-language contract rules"
kind: backend
source: code-review
parent_phase: release-train
change_id: 01KSQNPBPN7W74QVAZ25F79RNH

# Scope (WP-02..04)
atomic_branch: yes
estimate: small
blast_radius: medium                    # changes the contract the whole train reads (tier map + format rules)

# Change primitive
primitive: extend
group: expand

acceptance_criteria:
  - "_PRIMITIVE_TIER in plugins/sulis/scripts/_changeset.py maps ALL 22 change primitives from references/change-primitives.md to a non-None tier (founder decision: cover all 22 so every code-altering change gets versioned)"
  - "the 13 previously-unmapped primitives resolve to their founder-approved tier: move/inline/merge/decompose/abstract/deprecate/test/document → patch; generate/replace/delete/secure/gate → minor"
  - "the existing 9 change-primitive mappings + 4 Conventional-Commits mappings are unchanged (create/extend/compose/reuse/strangle/wrap/harden/instrument/feat → minor; fix/chore/refactor/docs → patch)"
  - "no primitive in the 22-primitive vocabulary returns None from tier_for_primitive; None remains ONLY for genuinely-unmapped/admin tokens (admin, docs-only, unknown strings)"
  - "the breaking=True → major override path is unchanged (per-changeset tier override remains the escape hatch)"
  - "_dump_changeset raises ValueError if change_id, primitive, or tier contains a newline; change_id and primitive also reject ':' (the summary | block scalar is unchanged and stays safe)"
  - ".changesets/README.md gains a 'Rules for re-implementers' section documenting the exact parser grammar the WP-003 bash reader must match"
  - ".changesets/README.md tier table lists all 22 primitives and matches _PRIMITIVE_TIER exactly (verified by a conformance test)"
  - "the _changeset.py module docstring + the _PRIMITIVE_TIER code comment are TRUE: the 'audited against the 22-primitive vocabulary' claim holds and the group-coverage comment is accurate"
  - "next_version's strict-dotted-triple requirement (raises on malformed input) is documented in its docstring"
  - "the misnamed test_tier_for_primitive_full_mapping either genuinely covers the full 22-primitive mapping or is renamed to match what it asserts"
  - "the existing 19 tests stay green; full suite green (existing + new)"

test_plan:
  unit:
    - "plugins/sulis/scripts/tests/unit/test_changeset.py::test_tier_for_primitive_all_22_primitives_mapped"
    - "plugins/sulis/scripts/tests/unit/test_changeset.py::test_tier_for_primitive_newly_mapped_patch_primitives"
    - "plugins/sulis/scripts/tests/unit/test_changeset.py::test_tier_for_primitive_newly_mapped_minor_primitives"
    - "plugins/sulis/scripts/tests/unit/test_changeset.py::test_tier_for_primitive_admin_docs_only_is_none"
    - "plugins/sulis/scripts/tests/unit/test_changeset.py::test_dump_changeset_rejects_newline_in_change_id"
    - "plugins/sulis/scripts/tests/unit/test_changeset.py::test_dump_changeset_rejects_newline_in_primitive"
    - "plugins/sulis/scripts/tests/unit/test_changeset.py::test_dump_changeset_rejects_newline_in_tier"
    - "plugins/sulis/scripts/tests/unit/test_changeset.py::test_dump_changeset_rejects_colon_in_change_id_and_primitive"
    - "plugins/sulis/scripts/tests/unit/test_changeset.py::test_write_changeset_rejects_injected_newline"
    - "plugins/sulis/scripts/tests/unit/test_changeset.py::test_readme_tier_table_matches_primitive_tier_map"
  integration: []
  verification:
    - "branch-ci green on the WP branch (pytest + ruff + mypy on _changeset.py)"
verification_gates: [unit]              # pure module — no API boundary, no integration

# Lineage (WP-06)
derived_from:
  - finding: code-review::PR-1fd6d60::CR-WP001-01 (tier map omits 13 of 22 primitives; docstring overclaims a full audit)
    found_in: .architecture/release-train/code-reviews/PR-1fd6d60-2026-05-28T171158Z/REVIEW.md
    severity_at_discovery: high
  - finding: code-review::PR-1fd6d60::CR-WP001-02 (raw scalar fields permit newline injection → forged tier)
    found_in: .architecture/release-train/code-reviews/PR-1fd6d60-2026-05-28T171158Z/REVIEW.md
    severity_at_discovery: medium
  - finding: code-review::PR-1fd6d60::CR-WP001-03 (block-scalar/quote/comment grammar undocumented for the bash re-implementer)
    found_in: .architecture/release-train/code-reviews/PR-1fd6d60-2026-05-28T171158Z/REVIEW.md
    severity_at_discovery: medium
  - finding: code-review::PR-1fd6d60::CR-WP001-04 (README tier-table not conformance-tested; next_version undocumented ValueError; misnamed test; over-claiming comment)
    found_in: .architecture/release-train/code-reviews/PR-1fd6d60-2026-05-28T171158Z/REVIEW.md
    severity_at_discovery: low
generated_by:
  activity: code-review/release-train/PR-1fd6d60
  agent: sulis-engineering-architect
addresses_findings:
  - "issue-66::changeset-with-no-tier-ships-no-release (a code-altering primitive resolving to None reproduces the #66 invisibility for a different primitive set)"
invalidated_by:
  activity: null
  result: null

# Lifecycle (WP-07)
status: pending
depends_on: [WP-001]                     # remediates the merged WP-001 keystone; nothing else precedes it
blocks: [WP-002, WP-003, WP-004]         # the writer + GHA + skill must read the FINALISED contract (tier map + format rules), not the pre-remediation keystone

# Composite (WP-08)
child_wps: []
kinds: null

rollback: |
  Revert the edits to plugins/sulis/scripts/_changeset.py (restore the 9+4 tier
  map, drop the newline/colon guard), plugins/sulis/scripts/tests/unit/test_changeset.py
  (drop the new tests, restore the old test name), and .changesets/README.md
  (drop the 'Rules for re-implementers' section, restore the 4-row tier table).
  Pure in-place revert — no new files, no data migration. The keystone returns
  to its merged-but-incomplete state (13 primitives back to None).
---

# WP-008 — Keystone remediation: full 22-primitive tier coverage + writer hardening + contract rules

## Context

TDD §Form (the changeset YAML seam) + §Proof (the deterministic core) +
§Armor (the writer's injection-safety). ADR-002 (tier from primitive),
ADR-004 (the bash GHA re-reads the same format), ADR-005 (the contract doc and
the code cannot drift).

This WP is a **bounded remediation of the merged WP-001 keystone**, driven by
the batch code-review at
`.architecture/release-train/code-reviews/PR-1fd6d60-2026-05-28T171158Z/` and one
founder decision. It is **not a redesign**: the module shape, the public surface,
the no-pyyaml round-trip, and the 19 existing tests all stay. WP-008 closes four
specific gaps the review surfaced and the founder's decision settled.

`_changeset.py` is the keystone every other train WP reads or writes:
WP-002 (the ship writer), WP-003 (the bash GHA bump authority), and WP-004 (the
release-train skill) all conform to the tier map and the YAML format finalised
here. Because they consume the **finalised** contract — not the
pre-remediation one — this WP `blocks` all three. It lands as Round 1.5: after
the keystone is merged, before the writer/authority/skill round.

### The founder decision (drives FIX 1)

The review surfaced that the tier map covered only the 9 change primitives +
4 Conventional-Commits types named in the spec, leaving 13 of the 22 primitives
resolving to `None` → no changeset → no release. For a release train whose whole
job is "every change is labelled," a code-altering change type that ships with no
release record reproduces the exact #66 invisibility for a different primitive
set.

**The founder chose:** *cover all 22 types so every code-altering change gets
versioned.* The per-changeset `tier:` override (edit on `dev` before release)
remains the escape hatch for the rare case the default is wrong — that path is
unchanged.

## Contract — the four fixes (all test-first, Red → Green → Blue)

### FIX 1 — complete `_PRIMITIVE_TIER` for all 22 change primitives (the founder decision)

The map must cover every primitive in `references/change-primitives.md`. The
founder-approved default tiers:

**patch** (behaviour-preserving / not a new shipping surface):

| Primitive | Group | Why patch |
|---|---|---|
| `move` | REORGANISE | behaviour-preserving relocation |
| `inline` | REORGANISE | folds an abstraction back; behaviour-preserving |
| `merge` | REORGANISE | combines over-fragmented modules; behaviour-preserving |
| `decompose` | REORGANISE | splits a unit; behaviour-preserving |
| `abstract` | REORGANISE | extracts a shared primitive; behaviour-preserving |
| `deprecate` | CONTRACT | marks for removal; behaviour preserved |
| `test` | REINFORCE | adds tests; no shipping-surface change |
| `document` | REINFORCE | docs only; no runtime change |
| `fix` (CC) | — | bug fix *(existing — unchanged)* |
| `chore` (CC) | — | housekeeping *(existing — unchanged)* |
| `refactor` (CC) | — | restructure *(existing — unchanged)* |
| `docs` (CC) | — | docs *(existing — unchanged)* |

**minor** (new or changed surface / behaviour):

| Primitive | Group | Why minor |
|---|---|---|
| `generate` | EXPAND | emits new code from a schema; adds surface |
| `replace` | SUBSTITUTE | swaps implementation; observable behaviour may change |
| `delete` | CONTRACT | removes behaviour consumers may depend on |
| `secure` | REINFORCE | adds a security control; changes observable access behaviour |
| `gate` | REINFORCE | adds a feature flag / new path |
| `create` | EXPAND | net-new surface *(existing — unchanged)* |
| `extend` | EXPAND | adds behaviour via an extension point *(existing — unchanged)* |
| `compose` | EXPAND | new orchestrated behaviour *(existing — unchanged)* |
| `reuse` | EXPAND | new call site / behaviour *(existing — unchanged)* |
| `strangle` | SUBSTITUTE | gradual replacement *(existing — unchanged)* |
| `wrap` | SUBSTITUTE | new translation surface *(existing — unchanged)* |
| `harden` | REINFORCE | adds resilience behaviour *(existing — unchanged)* |
| `instrument` | REINFORCE | adds observability surface *(existing — unchanged)* |
| `feat` (CC) | — | new feature *(existing — unchanged)* |

**major:** only via the existing `breaking=True` override — **unchanged.**

**Result:** no primitive in the 22-vocabulary resolves to `None`. `None` remains
the meaningful answer only for genuinely-unmapped/admin tokens (`admin`,
`docs-only`, any unrecognised string) — those don't touch `plugins/sulis/**` and
write no changeset.

**Doc + comment truth.** The module docstring's claim that the mapping is
*"audited against the 22-primitive vocabulary"* becomes TRUE (all 22 now mapped),
and the `_PRIMITIVE_TIER` comment listing the five groups becomes accurate. The
`.changesets/README.md` tier table is extended to list all 22 primitives so it
matches `_PRIMITIVE_TIER`. Cite `references/change-primitives.md` in the comment
(reference the canonical list; don't duplicate it).

### FIX 2 — reject newlines (and `:`) in the raw scalar fields at `_dump_changeset` (security hardening)

`change_id`, `primitive`, and `tier` are interpolated raw into the YAML
(`f"change_id: {change_id}"` etc.). A newline embedded in any of them injects a
forged extra YAML line — e.g. a fake `tier: major` ahead of the real one. The
Python reader is immune (last-value-wins), but the WP-003 bash GHA re-reads this
format and a naive first-match reader (`grep -m1 '^tier:'`) would trust the
forged value and bump the wrong version.

**Guard at `_dump_changeset`:**

- Raise `ValueError` if `change_id`, `primitive`, or `tier` contains a newline
  (`\n` or `\r`).
- Additionally reject `:` in `change_id` and `primitive` (neither legitimately
  contains a colon — a ULID is `[0-9A-Z]`, a primitive is a single lowercase
  token — and a `:` could split a line into a forged key/value).
- `summary` stays a `|` literal block scalar (already injection-safe — every
  line is 2-space-indented under the block header, so it cannot escape to a
  top-level key) — **unchanged.**

The guard message names the offending field so a caller sees which value failed.

### FIX 3 — add a "Rules for re-implementers" section to `.changesets/README.md` (cross-language contract)

The WP-003 bash GHA must parse this format identically to the Python reader.
Today the parser rules live only in `_parse_changeset` / `_strip_inline_comment`
/ `_coerce_scalar` — the bash reader would have to reverse-engineer them. Document
the actual rules the Python parser implements, so the format is a written spec:

- **Block scalars (`summary: |`):** 2-space indent is the block-scalar unit;
  each block line is the source line with its leading 2 spaces stripped.
- **Block end:** the block ends at the first line that is not 2-space-indented
  (the next top-level `key:`).
- **Internal blank lines** inside the block are preserved (rendered as empty
  lines).
- **Trailing blank lines** at the end of the block are stripped.
- **Quoting:** a scalar value may be single- or double-quoted; the matching outer
  quotes are stripped.
- **Inline comments:** a `#` that is preceded by whitespace (or at column 0) and
  is outside quotes starts a comment and is stripped; a `#` inside quotes is
  preserved.
- **Booleans:** the bare values `true` / `false` coerce to boolean; everything
  else is a string.
- **Injection rule (from FIX 2):** `change_id`, `primitive`, `tier` never
  contain a newline; `change_id` / `primitive` never contain `:` — the writer
  guarantees this, so a re-implementer may treat each as a single safe line.

### FIX 4 — the low-hanging correctness/doc items (from CR-WP001-04)

- **`next_version` docstring:** document that it requires a strict dotted triple
  (`x.y.z`) and raises `ValueError` on malformed input (the `int(part)` /
  three-way unpack will raise — make the contract explicit in the docstring).
- **Misnamed test:** `test_tier_for_primitive_full_mapping` currently asserts a
  *partial* mapping. Under this WP the mapping is genuinely full, so the
  full-coverage assertion is satisfied by the new
  `test_tier_for_primitive_all_22_primitives_mapped`; rename the old test to what
  it actually checks (e.g. `test_tier_for_primitive_named_subset`) OR fold its
  assertions into the new full-coverage test. Either way no test claims "full"
  while checking "partial."
- **Over-claiming comment:** the code comment that lists all five primitive groups
  as if covered is now accurate (all groups ARE covered) — verify the wording
  matches reality after FIX 1.
- **Doc-drift loop:** add a test that the `.changesets/README.md` tier table
  matches `_PRIMITIVE_TIER` (the existing `test_readme_examples_parse` only checks
  the worked *example*, leaving the *table* unchecked — this closes that loop).

## Definition of Done — Red / Green / Blue

### Red (write the failing tests first — MUST)

Add these tests to `plugins/sulis/scripts/tests/unit/test_changeset.py` **before**
any implementation; run them and confirm they fail (assertion / `ValueError`
not raised / `KeyError`).

- `test_tier_for_primitive_all_22_primitives_mapped` — **the keystone assertion.**
  Parametrised over **every** primitive in the 22-vocabulary
  (`reuse, compose, extend, generate, create, move, refactor, inline, merge,
  decompose, abstract, replace, strangle, wrap, deprecate, delete, test,
  instrument, secure, harden, gate, document`): assert
  `tier_for_primitive(p) is not None` for each. Best sourced as a module-level
  constant list of the 22 so the test fails loudly if a primitive is missed.
- `test_tier_for_primitive_newly_mapped_patch_primitives` — assert
  `move, inline, merge, decompose, abstract, deprecate, test, document` each → `patch`.
- `test_tier_for_primitive_newly_mapped_minor_primitives` — assert
  `generate, replace, delete, secure, gate` each → `minor`.
- `test_tier_for_primitive_admin_docs_only_is_none` — **kept** (existing): assert
  `admin`, `docs-only`, and an unknown string still → `None` (the None path is
  narrowed to admin/unknown, not removed).
- `test_dump_changeset_rejects_newline_in_change_id` — a `change_id` containing
  `\n` raises `ValueError`.
- `test_dump_changeset_rejects_newline_in_primitive` — a `primitive` containing
  `\n` raises `ValueError`.
- `test_dump_changeset_rejects_newline_in_tier` — a `tier` containing `\n` raises
  `ValueError`.
- `test_dump_changeset_rejects_colon_in_change_id_and_primitive` — a `:` in
  `change_id` or `primitive` raises `ValueError`.
- `test_write_changeset_rejects_injected_newline` — the guard fires through the
  public `write_changeset` entry point (the realistic injection vector), and the
  concrete forged-`tier: major` payload from the review is rejected (no file
  written).
- `test_readme_tier_table_matches_primitive_tier_map` — parse the tier table out
  of `.changesets/README.md` and assert every `(primitive → tier)` row matches
  `_PRIMITIVE_TIER`, and that the table covers all 22 primitives (the doc-drift
  loop closer).

Also confirm the existing 19 tests still run (they go green again in Green; some
e.g. the renamed full-mapping test change name only).

### Green (minimum boring code to pass)

- Extend `_PRIMITIVE_TIER` with the 13 founder-approved entries (8 patch +
  5 minor) per FIX 1. Keep it a literal dict — no reflection, no dynamic
  dispatch; the 13 new keys sit alongside the existing 13 entries.
- Add the newline/`:` guard to `_dump_changeset` per FIX 2: a small private
  helper (e.g. `_reject_unsafe_scalar(field_name, value, *, forbid_colon)`)
  raising `ValueError` with the offending field named. Call it for `change_id`,
  `primitive`, `tier` before building `lines`. `summary` is not passed through it.
- Author the "Rules for re-implementers" section in `.changesets/README.md` per
  FIX 3; extend the tier table to all 22 primitives so it matches the map.
- Apply the FIX 4 doc/comment/rename items.
- All tests green (the new ~10 + the existing 19, with the one rename).

### Blue (refactor — MUST, not optional)

- **Single source of truth for the 22-vocabulary.** The
  `test_tier_for_primitive_all_22_primitives_mapped` test and any README-table
  conformance test should derive the canonical 22 from one place (a module-level
  list, or parsed from `references/change-primitives.md`) rather than two
  hand-copied lists that can drift. Prefer one list referenced by both the test
  and the comment.
- **Confirm the docstring + comment are now true** — re-read the module docstring
  ("audited against the 22-primitive vocabulary") and the `_PRIMITIVE_TIER`
  comment (the five groups) against the finalised map; they must be accurate, not
  aspirational.
- **Keep the bash mirror in lockstep.** Leave (or update) the note that WP-003's
  bash GHA mirrors both the tier map and the format rules; FIX 3's "Rules for
  re-implementers" is now the authority the bash reader conforms to. No second
  copy of the tier map should live anywhere yet (it lands in WP-003's bash).
- Re-run the full suite (ruff + mypy + pytest); confirm green.

## Estimated token cost

input: ~9k / output: ~6k

## Notes

- **Not a redesign.** The public surface, the no-pyyaml round-trip, and the 19
  existing tests are unchanged in shape. WP-008 only (a) widens the tier map,
  (b) adds a writer guard, (c) writes down the format rules, and (d) fixes the
  doc/test correctness items the review listed.
- **Pure module — no mocks.** Tests use `tmp_path` for file I/O, exactly like
  WP-001 and `test_change_store.py`. No network, no `gh`, no subprocess.
- **The `tier:` override is preserved.** Covering all 22 with defaults does NOT
  remove the per-changeset override — the written `tier:` field stays
  authoritative and editable on `dev` before the release PR (ADR-002).
- **Why this blocks WP-002/003/004.** Those three conform to the contract this
  WP finalises — the tier map (so the writer computes the right tier for any of
  the 22 primitives) and the format rules (so the bash GHA parses identically).
  Building them on the pre-remediation keystone would bake in the 13-primitive
  gap and the undocumented format. WP-008 is Round 1.5 for exactly this reason.
