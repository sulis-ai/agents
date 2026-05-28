# Code Review: WP-001 keystone — changeset data model + helper

> **Timestamp:** 2026-05-28T171158Z (ISO 8601 UTC)
> **Target:** batch diff `be79e53..1fd6d604` on `change/create-release-train` (train-2026-05-28T170005Z, batch_size=1)
> **Branch:** feat/wp-001-changeset-data-model-helper → change/create-release-train
> **Files changed:** 3 (`_changeset.py` +331, `tests/unit/test_changeset.py` +313, `.changesets/README.md` +103)
>
> **Outcome:** Needs changes before merge — one open question on the keystone contract that the rest of the train will inherit.

---

## At a glance

The keystone module is well-built and genuinely well-tested (19 tests, every function covered, lint/type/test all clean — not hollow). The review surfaced one thing that matters because everything else in this change reads this module: **the version-tier map only covers the change types listed in the spec, and silently produces no version bump for the others** (delete, replace, move, decompose, and 9 more). For a release train whose whole job is "every change is labelled," a change type that ships with no release entry is a real gap worth a decision before building on top.

Two smaller hardening items: a crafted text field could sneak a fake version tier past a naive reader, and the exact file-format rules the future GitHub Action must match aren't written down yet. Both are cheap to close on the keystone now.

## What to fix

### Worth your call — the version-tier map is missing 13 of the 22 change types

The map turns a change's *type* into a version bump (e.g. a bug-fix → patch, a feature → minor). It currently covers the types named in the spec: fix/chore/refactor/docs → patch; feat/create/extend/compose/reuse/strangle/wrap/harden/instrument → minor; anything breaking → major. Every **other** change type — `delete`, `replace`, `move`, `decompose`, `generate`, `deprecate`, `merge`, `inline`, `abstract`, `test`, `secure`, `gate`, `document` — falls through to "no changeset", meaning no version bump and no release entry.

So if someone ships a `replace` or `delete` change, it would land with no release record — the exact invisibility this change exists to fix (#66), just for a different set of change types. The module's own docstring also claims it was "audited against the 22-primitive vocabulary," which isn't yet true.

**What to do:** decide whether those change types should bump (and at what level) or stay silent by design, then make the map and the docstring agree. This is a release-policy decision — surfaced to the founder below.

### Strongly recommend fixing — a crafted text field can forge a version tier

The `summary` field is safely contained, but the `change_id` / `primitive` / `tier` fields are written raw. A newline embedded in one of them injects an extra line into the file — e.g. a forged `tier: major` ahead of the real one. The Python reader is immune (last-value-wins), but the spec says a **bash** GitHub Action will re-read this format, and a naive bash reader using first-match (`grep -m1 '^tier:'`) would pick up the forged value and bump the wrong version. Cheap to close at the writer (reject newlines in those fields).

### Worth fixing — write down the file-format rules for the GitHub Action

The README promises a bash Action will parse this format, but the trickier rules (how multi-line summaries are indented, how quotes and inline comments are handled) live only in the Python code. Without a written spec, the bash reader (next change, WP-003) is liable to diverge. Add a short "rules for re-implementers" section to `.changesets/README.md`.

### Minor — for awareness
- The README tier *table* isn't checked against the code by any test (only the worked example is) — so they can drift.
- `next_version` raises a low-level error on a malformed version string; document that it expects a strict `x.y.z`.
- One test is named `..._full_mapping` but tests a partial mapping; one code comment lists all five change-type groups as if all were covered.

## How this pull request is shaped

Clean and well-scoped — 3 new files, source and tests together, no migrations, no secrets, no infra, no mixed concerns. Single-purpose keystone commit. No split needed.

## Things to take away

The module is a genuinely strong test-first keystone. The one lesson worth keeping: when a module's purpose is to be a *contract two languages read* (here Python now, bash next), the format's edge rules and the type-to-tier policy are the load-bearing parts — worth pinning in the contract doc and in tests, not just in the implementation.

---

## Technical detail

> Internal taxonomy below for engineers + downstream agents (`/sulis:harden-codebase`, future `/code-review`).

### Verdict

`Request changes` per CR-06 — one HIGH finding in the diff (primitive-map coverage / docstring-code disagreement). Build Verification empty; all 3 files read end-to-end; all three lenses produced output. No CRITICAL → not a train BLOCKER; handled as keystone remediation before dependents dispatch (see disposition).

### Summary

- **Build Verification:** 0 PR-introduced errors (pytest 19 passed; ruff clean; mypy clean) — CR-01 satisfied.
- **PR Hygiene:** clean. Scope low (single `feat:`), Size 747 LOC / 3 files (medium band but single-concern), Safety none (0 migrations/secrets/infra/schema), Completeness good (source + tests together).
- **In the changes:** 1 high, 3 medium, 6 low.
- **In the neighbours:** none (leaf module; no intra-repo imports — confirmed stdlib-only).
- **Draft fixes:** folded into keystone remediation (not deferred WP-AUTO) — see disposition.

| Lens | In changes | Top concern |
|---|---|---|
| Architecture | 1 medium + 3 low | block-scalar/quote rules are a cross-language contract documented only in Python |
| Security | 1 medium | newline injection in raw `change_id`/`primitive`/`tier` → cross-reader `tier` forgery |
| Quality | 1 high + 1 medium + low | primitive→tier map omits 13 of 22 primitives; docstring overclaims a full audit |

### Findings in the changes

**HIGH (quality + architecture) — `_changeset.py:45-68` `_PRIMITIVE_TIER` incomplete + docstring overclaim.** Map covers 9 change-primitives + 4 Conventional-Commits types. 13 primitives from `references/change-primitives.md` (generate, move, inline, merge, decompose, abstract, replace, deprecate, delete, test, secure, gate, document) resolve to `None` → no changeset → no release. Docstring (L45-46) claims "audited against the 22-primitive vocabulary" — false. Either complete the map with deliberate tiers or declare None-by-default and fix the docstring + add a pinning test. Code currently matches the SPEC's explicit subset, so this is a spec-completeness/policy question, not a spec violation — escalated to founder.

**MEDIUM (security) — `_changeset.py:248-252` raw scalar fields permit newline injection.** `change_id`/`primitive`/`tier` interpolated without newline rejection; a `\n` injects an extra YAML line (forged `tier: major` confirmed). Python reader is last-wins (safe); bash GHA (WP-003) first-match would forge a bump. Fix: reject `\n` (and ideally `:`) in scalar fields at `_dump_changeset`. `summary` (L253-256, `|` block with forced 2-space indent) is CLEAN. Path traversal via slug/primitive CLEAN (`_sanitise_slug` whitelists `[a-z0-9]`). No eval/subprocess/unsafe-deser.

**MEDIUM (architecture) — `.changesets/README.md` doesn't specify the block-scalar/quote/comment grammar the bash re-implementer must match.** Parser rules (2-space indent unit, blank-line handling, trailing-strip, quote-stripping, quote-aware inline-comment stripping) live only in `_parse_changeset`/`_strip_inline_comment`/`_coerce_scalar`. Add a "rules for re-implementers" section so WP-003's bash reader can't diverge.

**LOW** — README tier-table not conformance-tested (only the worked example is, via `test_readme_examples_parse`); `next_version` raises undocumented `ValueError` on malformed input (L113); `test_tier_for_primitive_full_mapping` misnamed (partial); comment L46 lists all five groups as if covered; empty scalar coerces to `""` not `None`; `read_changeset_examples` multi-block/negative-filter branch untested.

### Methodology — CR-08 self-attestation

- [✓] **CR-01 Mechanical baseline ran.** pytest `tests/unit/test_changeset.py` → 19 passed; `ruff check` → clean; `mypy _changeset.py` → clean. Outputs in `tool-outputs/`. No coverage gap.
- [✓] **CR-02 Parallel dispatch used.** 747 LOC > 200 → three lenses dispatched concurrently as sub-agents. Single-reader not used.
- [✓] **CR-03 Full-file reads.** All 3 files read end-to-end by each lens.
- [✓] **CR-04 Evidence discipline.** Findings cite file:line + quoted text.
- [✓] **CR-05 Severity rubric.** 1 high, 3 medium, 6 low. No critical.
- [✓] **CR-06 Verdict computed.** `Request changes` (≥1 high in diff). No auto-downgrade to Block (Build Verification empty; full reads done).
- [✓] **CR-07 Lens completion.** Architecture, Security, Quality each produced structured output.
- [✓] **CR-09 PR Hygiene applied.** Scope low; Size medium-band single-concern; Safety none; Completeness good. No PH-03 high → no auto-downgrade.

### Run details
- Diff source: `git diff be79e53..1fd6d604` (the train's actual merge onto the change branch; the gate_handoff range `a8e1fc0..1fd6d604` resolves to the same 3-file content + the already-landed spec commit).
- Neighbour expansion: none — leaf module, stdlib-only imports.
- Lenses dispatched in parallel: yes (3 sub-agents).
- Note: WP-001 already ran per-WP `/code-review` (PASS, 0 findings) during executor Steps 1-7; this batch gate reviewed at greater depth (3 dedicated lenses) and surfaced the contract/policy + injection items the per-WP pass did not.
