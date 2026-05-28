---
# Identity (WP-01)
id: WP-009
title: "Batch-gate remediation — keystone accepts str|Path + the Action loop-guard expression loads"
kind: backend
source: code-review
parent_phase: release-train
change_id: 01KSQNPBPN7W74QVAZ25F79RNH

# Scope (WP-02..04)
atomic_branch: yes
estimate: small
blast_radius: high                      # FIX 1 unblocks the producer (every non-admin ship); FIX 2 guards the one workflow that pushes to main

# Change primitive
primitive: fix
group: reinforce

acceptance_criteria:
  - "write_changeset and read_changesets in plugins/sulis/scripts/_changeset.py accept a str OR a pathlib.Path for changesets_dir, coercing Path(changesets_dir) at entry of BOTH functions, so a plain-str dir argument no longer raises AttributeError: 'str' object has no attribute 'mkdir' / 'is_dir'"
  - "a new unit test proves a plain-str dir argument round-trips: write a changeset to a str dir, then read it back from the same str dir, with the written fields intact"
  - "the existing 50 changeset tests stay green (the Path callers are unaffected — Path(p) on a Path is a no-op)"
  - "the producer end-to-end is proven: executing the corrected /sulis:change ship step-4.7 snippet writes a changeset file under .changesets/ without an AttributeError"
  - ".github/workflows/release-on-merge.yml line 36 single-quotes the string literal inside the ${{ }} loop-guard expression: ${{ !startsWith(github.event.head_commit.message, 'release: sulis') }} (GitHub Actions expressions accept single-quoted literals only; the double-quoted form fails at expression evaluation while passing YAML lint)"
  - "the loop-guard prefix 'release: sulis' remains an EXACT prefix of the step-9 'Commit, tag, push' commit message ('release: sulis v${NEW_PLUGIN} (v${NEW_META})') — the two stay in lockstep"
  - "the WP-002 spec example (work-packages/WP-002-ship-writes-changeset.md ~line 94) is corrected so it no longer passes the str literal as the origin of the bug — it passes Path('.changesets') with the import, OR is annotated that the keystone now coerces str (matching the SKILL.md snippet)"

test_plan:
  unit:
    - "plugins/sulis/scripts/tests/unit/test_changeset.py::test_write_read_changeset_round_trip_accepts_str_dir"
  integration: []
  verification:
    - "branch-ci green on the WP branch (pytest + ruff + mypy on _changeset.py); the full changeset suite stays at 50 green + 1 new = 51"
    - "producer end-to-end: run the corrected step-4.7 snippet against a scratch dir and assert a *.yaml changeset is written (no AttributeError)"
    - "GHA expression: actionlint clean if available, ELSE a documented manual check that the expression parses (single-quoted literal) and that startsWith's prefix is an exact prefix of the step-9 commit message"
verification_gates: [unit]              # pure module + one workflow-file literal; no API boundary, no integration seam

# Lineage (WP-06)
derived_from:
  - finding: code-review::PR-e858389::CR-BATCH-01 (ship step 4.7 calls write_changeset('.changesets', ...) with a str; _changeset.py calls changesets_dir.mkdir() -> AttributeError; producer never writes a changeset; dev accumulates none)
    found_in: .architecture/release-train/code-reviews/PR-e858389-2026-05-28T191515Z/REVIEW.md
    severity_at_discovery: critical
  - finding: code-review::PR-e858389::CR-BATCH-02 (release-on-merge.yml:36 loop-guard uses a double-quoted literal inside ${{ }}; GitHub Actions rejects at expression evaluation while YAML lint passes; the bot's own release commit could re-trigger the workflow)
    found_in: .architecture/release-train/code-reviews/PR-e858389-2026-05-28T191515Z/REVIEW.md
    severity_at_discovery: high
generated_by:
  activity: code-review/release-train/PR-e858389
  agent: sulis-engineering-architect
addresses_findings:
  - "issue-66::ship-flow-writes-no-changeset (the producer crashing on every non-admin ship leaves dev empty — the #66 invisibility surviving silently behind a runtime crash)"
invalidated_by:
  activity: null
  result: null

# Lifecycle (WP-07)
status: pending
depends_on: [WP-002, WP-003]            # forward-fixes two defects in the MERGED WP-002 (the str call-site + spec example) and WP-003 (the GHA loop-guard literal); both are merged on change/create-release-train, gate-blocked, nothing shipped to main
blocks: []                              # blocks nothing new — WP-005/006/007 do not depend on these fixes; but MUST be DONE before the change ships

# Composite (WP-08)
child_wps: []
kinds: null

rollback: |
  Revert the three edits: (1) the Path(changesets_dir) coercion at the entry of
  write_changeset + read_changesets in plugins/sulis/scripts/_changeset.py, plus
  the new str-dir round-trip test in tests/unit/test_changeset.py; (2) the
  single-quote of the loop-guard literal in .github/workflows/release-on-merge.yml
  line 36 (back to double quotes); (3) the WP-002 spec-example correction.
  Pure in-place revert — no new files, no data migration. Reverting restores the
  producer crash (FIX 1) and the non-loading guard (FIX 2), so it is only ever a
  last resort.
---

# WP-009 — Batch-gate remediation: keystone accepts `str | Path` + the Action loop-guard expression loads

## Context

TDD §Form (the changeset YAML seam — the keystone's public surface is the
producer/consumer contract) + §Armor (the writer's robustness and the Action's
loop-guard, which protects the one workflow that pushes to `main`). ADR-002 (tier
from primitive), ADR-004 (the bash GHA re-reads the format).

This WP is a **forward remediation of two defects the batch-composition code-review
found in the just-merged WP-002 + WP-003**
(`.architecture/release-train/code-reviews/PR-e858389-2026-05-28T191515Z/`). Both
WPs are merged on `change/create-release-train`; the batch gate returned `Block`
(one CRITICAL), so **nothing shipped to `main`** — the WPs stay on the isolated
change branch and are fixed here before the change ships. It is **not a redesign**:
each fix is unambiguous and one line of behaviour, backed by a test.

The two defects are exactly the class the batch-composition gate exists to catch —
each per-WP review (PASS for WP-002, approve-with-fixes for WP-003) covered its WP
in isolation and could not see them. The seam test passed only because it called
the keystone with a real `Path`; the ship snippet itself was never executed.

### Why FIX 1 is CRITICAL

The producer never writes a changeset. WP-002's ship step 4.7 calls
`_changeset.write_changeset('.changesets', …)` passing a `str`; `write_changeset`
immediately calls `changesets_dir.mkdir(parents=True, exist_ok=True)`, which raises
`AttributeError: 'str' object has no attribute 'mkdir'` (reproduced: `python3 -c
"…write_changeset('.changesets', …)"` → `AttributeError`). So **every non-admin
ship crashes the step**, and `dev` accumulates no changesets — the release train
has nothing to release. This is the #66 invisibility surviving silently behind a
runtime crash: the train mechanism is built, but the producer feeding it is broken.
`read_changesets` has the symmetric latent bug (`changesets_dir.is_dir()` on a
`str` raises) — a `str` caller would fail there too.

### Why FIX 2 is HIGH

The Action's loop-guard won't load. `.github/workflows/release-on-merge.yml:36`
writes the guard with a **double-quoted** string literal inside `${{ }}`:

```yaml
if: '${{ !startsWith(github.event.head_commit.message, "release: sulis") }}'
```

GitHub Actions expressions accept **single-quoted** string literals only. The
double-quoted form is rejected at expression evaluation — YAML lint passes (the
outer single quotes make it valid YAML), so it slips through static checks. If the
guard fails to evaluate, the bot's own `release: sulis …` commit (pushed by the
final step) could re-trigger the one workflow that pushes to `main` and tags — a
release loop on the highest-blast-radius workflow.

## Contract — the two fixes (both test-first / verified)

### FIX 1 — harden the keystone to accept `str | Path` (CRITICAL; the ROOT fix)

**Chosen shape: keystone coercion (the most robust), with a call-site clarity
correction.** Coercing at the keystone (not only at the one call site) immunises
**every** caller — present and future — against the same class, and makes the
SKILL.md snippet correct as-written (it passes `'.changesets'`). A pure call-site
fix would leave the keystone fragile and the next caller free to pass a `str`
again.

Coerce `changesets_dir = Path(changesets_dir)` at the **entry of BOTH**
`write_changeset` and `read_changesets`, before any `.mkdir()` / `.is_dir()` /
`.glob()` call:

- `write_changeset`: insert `changesets_dir = Path(changesets_dir)` as the first
  line of the body (before the `when = …` line and well before
  `changesets_dir.mkdir(...)`).
- `read_changesets`: insert `changesets_dir = Path(changesets_dir)` as the first
  line of the body (before `if not changesets_dir.is_dir(): return []`).
- Widen the type hints to `changesets_dir: str | Path` on both functions
  (the module already does `from __future__ import annotations`, so the union
  syntax is safe on the supported runtimes), and note in the docstrings that a
  `str` is accepted and coerced.
- `Path(p)` where `p` is already a `Path` is a no-op, so the existing 50 tests
  (which all pass a `Path`) stay green.

**ALSO (call-site clarity):** the SKILL.md step-4.7 snippet is now correct
as-written (it passes `'.changesets'`, which the keystone coerces). Optionally
keep it as a plain `str` for founder-readability (no `from pathlib import Path`
needed in the snippet) — that is the recommended shape now that the keystone is
robust. Do not require the snippet to import `Path` unless you prefer the explicit
form; the keystone coercion is what makes either correct.

**ALSO (correct the origin spec):** the WP-002 spec at
`work-packages/WP-002-ship-writes-changeset.md` (~line 94) passes the `str` literal
`'.changesets'` in its example — the origin of the bug. Correct it so the spec no
longer reads as prescribing a broken call. Two acceptable forms: (a) annotate that
the keystone now coerces `str` (so the `str` literal is fine), or (b) pass
`Path('.changesets')` with the import. Match whichever shape the live SKILL.md
snippet uses, so the spec and the implementation agree.

### FIX 2 — single-quote the loop-guard literal (HIGH)

In `.github/workflows/release-on-merge.yml`, change line 36 from the double-quoted
literal to a single-quoted one:

```yaml
# before (rejected at expression evaluation):
if: '${{ !startsWith(github.event.head_commit.message, "release: sulis") }}'
# after (loads):
if: '${{ !startsWith(github.event.head_commit.message, ''release: sulis'') }}'
```

> **Note on YAML quoting.** The whole `if:` value is a single-quoted YAML scalar
> (the leading `'`), because the `: ` inside the literal would otherwise be read by
> YAML as a nested mapping. To put a single-quoted GHA-expression literal *inside*
> that single-quoted YAML scalar, each inner `'` is doubled (`''`) per YAML's
> single-quote escaping — that is how `''release: sulis''` renders as the
> expression literal `'release: sulis'`. (An alternative that avoids the doubling
> is a YAML block/double-quoted scalar for the `if:` value, but the doubled-inner-
> single-quote form is the minimal change and keeps the existing scalar style.)
> The accompanying comment block (lines 32-35) that explains the quoting MUST be
> updated to describe the single-quoted-literal reality, not the old double-quoted
> one.

The prefix `release: sulis` MUST remain an **exact prefix** of the step-9 commit
message `git commit -m "release: sulis v${NEW_PLUGIN} (v${NEW_META})"` — do not
change the prefix text, only the quote style around it.

## Definition of Done — Red / Green / Blue

### Red (write the failing test first — MUST)

Add **one** new unit test to `plugins/sulis/scripts/tests/unit/test_changeset.py`
**before** the implementation; run it and confirm it fails with
`AttributeError: 'str' object has no attribute 'mkdir'` (and, for the read leg,
`'str' object has no attribute 'is_dir'`):

- `test_write_read_changeset_round_trip_accepts_str_dir` — pass a **plain `str`**
  directory (e.g. `str(tmp_path / ".changesets")`) to `write_changeset`, then read
  it back by passing the **same `str`** to `read_changesets`; assert the file was
  written and the round-tripped record carries the written fields. Pre-fix this
  raises `AttributeError`; post-fix it passes. (Mirror the existing
  `test_write_read_changeset_round_trip` shape; the only difference is the dir
  argument is a `str`, not a `Path`.)

Also confirm — by reading or running — that the **existing 50 tests** are green
before the change (the baseline) and stay green after (the `Path` callers are
unaffected by `Path(Path(...))`).

> **Producer end-to-end (the live CRITICAL proof, not a unit test).** Before the
> fix, executing the SKILL.md step-4.7 snippet (or the equivalent
> `write_changeset('.changesets', …)` with a `str`) crashes with the
> `AttributeError`. After the fix, the same snippet writes a `*.yaml` changeset
> under `.changesets/` and prints `{'wrote': True, …}`. Capture this run as the
> verification evidence for CR-BATCH-01 — it is what the per-WP review never
> executed.

### Green (minimum boring code to pass)

1. **FIX 1 (keystone coercion).** In `plugins/sulis/scripts/_changeset.py`:
   - Add `changesets_dir = Path(changesets_dir)` as the first body line of
     `write_changeset` and of `read_changesets`.
   - Widen both signatures to `changesets_dir: str | Path`.
   - Update both docstrings to note a `str` is accepted (coerced to `Path`).
   - No reflection, no dynamic dispatch — a single explicit `Path(...)` call. Boring.
2. **FIX 1 (call-site + spec).** Confirm the SKILL.md step-4.7 snippet
   (`plugins/sulis/skills/change/SKILL.md`, ~line 488) is correct under the
   coercion (it already passes `'.changesets'`); leave it as a plain `str`, or make
   it explicit `Path('.changesets')` — pick one and make the WP-002 spec example
   (`work-packages/WP-002-ship-writes-changeset.md` ~line 94) match it (this WP
   owns the spec correction).
3. **FIX 2 (GHA literal).** Single-quote the literal at line 36 of
   `.github/workflows/release-on-merge.yml` (doubling the inner single quotes per
   the YAML-quoting note), and update the lines 32-35 comment to describe the
   single-quoted reality.
4. New test green; existing 50 green (51 total).

### Blue (refactor — MUST, not optional)

- **One coercion idiom, both functions.** Use the identical
  `changesets_dir = Path(changesets_dir)` first line in both `write_changeset` and
  `read_changesets` — same idiom, read once, no helper needed for a one-liner
  (extracting a `_coerce_dir` helper for a single `Path()` call would be
  over-abstraction; keep it boring and inline). If a third dir-taking function ever
  appears, THEN extract.
- **Confirm the docstrings are true.** The `write_changeset` docstring says
  "Creates `changesets_dir` if absent" — after the coercion that is still true for
  a `str` argument too; reflect the `str | Path` acceptance accurately.
- **Confirm the WP-002 spec and the live SKILL.md snippet agree** — read both back;
  the spec example and the implementation must use the same dir-argument shape so a
  future reader of the spec cannot reintroduce the bug.
- **Confirm the bash mirror is unaffected.** FIX 1 is Python-side only (the GHA
  reads `.changesets` as a literal bash path, never via `write_changeset`); FIX 2
  is the GHA-side literal. No second copy of the coercion is needed anywhere.
- Re-run the full suite (ruff + mypy + pytest); confirm green.

## Estimated token cost

input: ~7k / output: ~3k

## Notes

- **Not a redesign.** FIX 1 adds one `Path(...)` coercion per function + one
  test; FIX 2 changes one character class (the quote style) on one workflow line
  plus its explanatory comment. The public surface, the no-pyyaml round-trip, and
  the 50 existing tests are unchanged in shape.
- **Why keystone coercion over a call-site-only fix.** The review offered both
  ("ROOT FIX, preferred, most robust" vs "correct the call-site for clarity"). The
  keystone coercion immunises every present and future caller and makes the
  founder-readable SKILL.md snippet correct as-written (it can keep passing the
  plain `str` `'.changesets'`); the call-site-only fix would leave the next caller
  free to pass a `str` and crash again. We do BOTH — coerce at the keystone (the
  robustness) and reconcile the call-site + spec example (the clarity).
- **Forward remediation, not revert.** Both WPs stay merged on the change branch;
  nothing reached `main`. This WP fixes the defects in place before the change
  ships, per the batch gate's `forward-remediation-WP-009` disposition.
- **Pure module + one workflow line — no mocks.** The unit test uses `tmp_path`
  for file I/O exactly like the other 50. The producer end-to-end runs the real
  snippet against a scratch dir. The GHA check is actionlint (deterministic) or a
  documented manual expression read — no mocked Action runtime.
- **Must be DONE before the change ships; does not gate the remaining WPs.**
  WP-005/006/007 do not depend on these fixes functionally, so WP-009 `blocks: []`.
  But the change cannot ship with a producer that crashes on every ship, so WP-009
  is a release blocker for THIS change (Round 2.5, before the founder-gated
  protection round).
