# Code Review: batch train-2026-05-28T140133Z — WP-001 + WP-002

> **Timestamp:** 2026-05-28T140609Z (ISO 8601 UTC)
> **Scope:** bundled-tip review (Step 10.5) of the change CH-01KSQB batch
> **Range:** de2ba4b..1624e0f on `change/harden-preflight-dev-drift-check`
> **WPs:** WP-001 (preflight CI-conclusion helper), WP-002 (free-plan 403 distinction)
>
> **Outcome:** Ready to merge

---

## At a glance

This batch adds two independent pieces — a read-only helper that checks
`dev`'s recorded CI result, and a refinement to the repo arrival-check that
recognises when a repo's plan can't enforce branch protection. They touch
different files with no shared code, so there's nothing that only breaks when
they sit together. Both were written tests-first, both passed CI on the
combined tip, and both passed individual review before merge. Nothing needs
attention.

## What to fix

No issues that need attention.

## How this pull request is shaped

- **Size — clean.** ~150 lines of source across two files, plus their tests.
- **Scope — clean.** Two cohesive, independent additions; one harden change.
- **Safety — clean.** No migrations, no schema/IDL, no infra, no secrets. Both
  changes are read-only probes (read GitHub check-runs / read the protection
  API); no input handling, auth, data mutation, or new dependencies.
- **Completeness — clean.** Both pieces ship tests; WP-002 carries a
  characterisation test pinning the preserved public-repo behaviour.

---

## Technical detail

### Verdict

`PASS` per CR-06. No critical/high/medium/low in the diff. Build Verification
empty (combined tip passed branch-ci: manifest validity + `compileall` +
`pytest plugins/sulis/scripts/tests/unit/` + routing-coverage gate). Both
changed source files read end-to-end.

### Summary

- **Build Verification:** 0 PR-introduced errors (combined-tip branch-ci green).
- **PR Hygiene:** 0 high / 0 medium. Scope clean (single harden change), Size
  small (~150 source lines), Safety clean (read-only probes), Completeness
  clean (tests present).
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — `_preflight_ci_conclusion` reuses the `GHClient`/`_gh_check_runs` port; `_poll_ci` untouched |
| Security | 0 | 0 | none — both are read-only probes; no input/auth/mutation/secrets/new-deps |
| Quality | 0 | 0 | none — both tests-first; WP-002 characterisation-pinned |

### Findings in the Changes

None. Detail of the end-to-end read:

- `_wpxlib.py` `_preflight_ci_conclusion` — correct closed-set verdict
  (green/failed/pending/unknown); reads `conclusion` explicitly (lesson #59);
  non-polling (returns `pending` immediately on incomplete runs); reuses
  `_gh_check_runs`; `_poll_ci` left byte-for-byte intact (confirmed in diff);
  deliberate non-extraction of the pass-set predicate documented (two callers,
  independent calibration).
- `wpx-arrival-check` `_check_rc02_protections` — captures the previously
  discarded stderr; `_is_freeplan_protection_403` gates on `rc != 0` + marker
  substring; free-plan 403 → `rep.warn` (gating-gap message), genuine non-zero
  rc → original `rep.error` preserved (the `elif rc != 0` branch is intact);
  the required-status-checks parsing on the success path is unchanged; the
  `main` probe suppresses a duplicate free-plan warning.

### Cross-WP composition (Step 10.5 focus)

WP-001 adds a module-level function to `_wpxlib.py`; WP-002 modifies a function
and adds two helpers to `wpx-arrival-check`. Disjoint files, no shared symbols,
no import coupling. The downstream consumers of `_preflight_ci_conclusion`
(WP-003/WP-004) are NOT in this batch, so there is no producer/consumer seam to
verify here. The combination is sound.

### Watch List

- `_FREEPLAN_403_MARKER` matches GitHub's 403 body substring ("upgrade to
  github pro"). Brittle to GitHub wording changes — but documented as such in
  WP-002 and pinned by its test (drift fails loudly), so this is an accepted,
  test-guarded design, not a finding.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** The combined tip passed branch-ci
  (manifest JSON validity, `python3 -m compileall plugins/sulis/scripts`,
  `pytest plugins/sulis/scripts/tests/unit/`, routing-coverage gate) green
  during the train's Step-8 bundled-tip CI — this is the mechanical floor for
  this published-artifact repo (no separate typechecker; stdlib-only tooling).
- [✓] **CR-02 Dispatch shape.** Single-reader review. Genuine code surface is 2
  source files (`_wpxlib.py` +51, `wpx-arrival-check` +44) + 2 test files,
  ~150 source lines. Justified by: small disjoint surface, already per-WP
  reviewed clean (Step 6.5, 0 findings each), combined-tip CI green, internal
  CLI tooling with no attack surface. Parallel three-lens dispatch would be
  disproportionate for this surface.
- [✓] **CR-03 Full-file reads.** Both changed source files read end-to-end via
  the combined diff (de2ba4b..1624e0f).
- [✓] **CR-04 Evidence discipline.** Findings (none) — observations cite
  file/symbol + the diff hunks.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical / 0 high / 0 medium / 0 low.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build
  Verification empty; both files read end-to-end; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (port reuse,
  `_poll_ci` untouched). Security: nothing surfaced — no SEC/SC/INF primitives
  apply (read-only probes; no input, auth, mutation, secrets, or new
  dependencies). Quality: nothing surfaced — both tests-first; WP-002
  characterisation-pinned; no dead surface / contract drift / perf
  anti-patterns in the diff.
- [✓] **CR-09 PR Hygiene applied.** Scope: clean. Size: clean (~150 source
  lines). Safety: clean (0 migrations / 0 schema / 0 infra / 0 secrets).
  Completeness: clean (tests present). No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** git range de2ba4b..1624e0f (change branch full delta;
  the train's gate_handoff range 57142ab..1624e0f excluded WP-001 — its branch
  tip was the range start — so the full change-branch delta was used instead).
- **Neighbour expansion:** not required — disjoint additive changes; consumers
  (WP-003/004) not yet in tree.
- **Note:** the per-WP code-review bundles the executors produced (Step 6.5)
  are committed into the change branch under `.architecture/.../code-reviews/`
  — ephemeral review artifacts that ideally would not live in the repo. Logged
  as an observation, not a finding.
