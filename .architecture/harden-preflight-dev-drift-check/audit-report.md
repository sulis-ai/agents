# harden-preflight-dev-drift-check — Codebase Audit

> **Date:** 2026-05-28
> **Scope:** `plugins/sulis/scripts/_wpxlib.py`, `plugins/sulis/scripts/wpx-arrival-check`,
> `plugins/sulis/scripts/wpx-train` (read-only reference), `plugins/sulis/skills/run-all/SKILL.md`,
> `plugins/sulis/skills/change/SKILL.md`. Driven by the change spec
> (`.changes/harden-preflight-dev-drift-check.SPEC.md`) and lesson #52.
> **Tooling:** Python 3 CLI scripts (`gh` shell-outs behind a `GHClient` Protocol), pytest unit/integration suite.
> **Change identity:** CH-01KSQB · harden · `change/harden-preflight-dev-drift-check` · base `dev`.
> **founder_facing:** false (internal orchestration/CLI tooling).

## Summary

This is a **targeted, gap-driven hardening change**, not a broad MECE-3 sweep. The
spec names two surfaces and forbids three classes of work (no train guard, no
product-repo workflow change, no scope-lint). The audit is scoped to the two
gaps the spec asks for plus their orchestration wiring. Both gaps are real and
both are provable with failing characterisation tests against the existing
`GHClient`/`mock_gh` test seams.

- **Critical findings:** 0
- **High findings:** 0
- **Medium findings:** 3 (operational gaps — pre-existing drift rediscovered per-WP; silent unprotected-repo blind spot)
- **Low findings:** 1 (the failed-check set already computed by `_poll_ci` but discarded — a reuse opportunity, not a defect)

| Pillar | Findings | Top concern |
|---|---|---|
| Form | 0 | The `GHClient` Protocol seam (HD-005) is already a clean port; new helpers extend it, no new structural debt |
| Armor | 3 | No pre-flight read of `dev` HEAD's recorded CI conclusion before a wave dispatches; no detection of the private-free-plan unprotected-repo case (silent gating gap) |
| Proof | 1 | No test asserts a pre-flight blocker on red dev; no test asserts the 403→warning path (both are net-new behaviour, test-first per CLAUDE.md #1) |

This change is **operational hardening (Armor)** with its **verification (Proof)**
written test-first. There is **no Form gap** — the `GHClient` Protocol introduced
in HD-005 is exactly the port a new pre-flight helper plugs into, and the
arrival-check probe is the right home for the protection distinction. We extend;
we do not restructure.

## Findings by Pillar

### Form

No findings. The relevant seams are already well-factored:

- `GHClient` Protocol + `RealGHClient` + `_resolve_gh()` (`_wpxlib.py:924–1110`) is a
  domain-owned port over the `gh` CLI. A new pre-flight helper that calls
  `_gh_check_runs(repo, branch, *, gh=...)` is **EXPAND-Create against an existing
  port** — not a Wrap. (Confirmed: the module's own comment at `_wpxlib.py:917`
  states this explicitly.)
- `wpx-arrival-check` already isolates the protection probe in
  `_check_rc02_protections` (`wpx-arrival-check:128`). The unprotected-repo
  distinction is a refinement of that one function.

### Armor (Operational)

| ID | File | Line | Gap | Severity | Delta |
|---|---|---|---|---|---|
| A-01 | `plugins/sulis/scripts/_wpxlib.py` | 1196 | No non-polling read of `dev` HEAD's **current recorded** CI conclusion. `_poll_ci` waits for in-flight runs (`time.sleep` loop, cap up to `CI_DEFAULT_CAP`); a pre-flight wants the latest *completed* conclusion, cheaply, with no wait. | medium | HD-001 |
| A-02 | `plugins/sulis/scripts/_wpxlib.py` | 1212 | The failed-check set is computed (`failed = [...]`) then **discarded** — `_poll_ci` returns only the verdict string `'green'\|'failed'\|'timeout'`, not the count/names needed to say "dev has N pre-existing CI failures". | low | HD-001 |
| A-03 | `plugins/sulis/skills/run-all/SKILL.md` | 124 (loop entry) | The parallel loop dispatches a wave (Steps 1-8) **before** any check that `dev` HEAD is CI-green. Pre-existing red on `dev` (landed via a manual/non-train merge on an unprotected repo) is inherited by every branch off `dev`, so every WP rediscovers the same red per-branch instead of one up-front blocker. | medium | HD-002 |
| A-04 | `plugins/sulis/scripts/wpx-arrival-check` | 132 | `_check_rc02_protections` does `rc, out, _ = _gh(...)` — **stderr is discarded** (`_`). On a private free-plan repo the protection API returns 403 with body "Upgrade to GitHub Pro…" on stderr. Today that 403 is flagged as a hard RC-02 *error* indistinguishable from a genuine "protection not configured on a plan that supports it". The free-plan case can't be distinguished, so the unprotected-repo warning can't be raised. | medium | HD-003 |
| A-05 | `plugins/sulis/skills/run-all/SKILL.md` + `plugins/sulis/skills/change/SKILL.md` | run-all loop entry; change `ship` step ~321 | Neither surface emits a one-time, plain-English warning when the repo can't enforce merge-gating (private + free plan). Founders on the common case (private product, free plan) silently assume branch-ci gates merges when it only gates Sulis-routed (train) merges. | medium | HD-004 |

### Proof (Verification)

| ID | File | Gap | Severity | Delta |
|---|---|---|---|---|
| P-01 | `plugins/sulis/scripts/tests/unit/` (no test exists) | No characterisation test asserts a non-polling pre-flight helper reports `(verdict, failed_check_names)` faithfully from recorded check-runs (red → failed + names; green → green + empty). | medium | HD-001 (Red) |
| P-02 | `plugins/sulis/scripts/tests/unit/test_wpx_arrival_check.py` | No test asserts that a 403 "Upgrade to GitHub Pro…" on `branches/dev/protection` is classified as *unprotected-free-plan* (warning-eligible) and NOT as a hard RC-02 error, while a genuine missing-protection on a protection-capable repo still errors. | medium | HD-003 (Red) |

## Spec Drift

The spec is the contract for this change; there is no prior SRD for this repo
(it is the Sulis codebase itself). Recon confirmed no `.context/` index. No
code-vs-spec drift to reconcile beyond the gaps above — the gaps *are* the spec.

One **observation** worth surfacing (not a drift, an alignment check): the spec's
non-goal "no train-refuses-on-red guard" is correct and verified in code —
`wpx-train` already polls `_poll_ci` and routes to `_pause_train_state` before
the merge loop (`wpx-train:1377–1400`). None of the deltas touch the train's
merge gate.

## What Was Not Audited

- **`wpx-train`'s merge gate** — read-only reference only. The spec's first
  non-goal forbids adding a guard there; recon confirmed it already pauses on
  red. Deltas reuse `_gh_check_runs`/`GHClient` but do not modify the train.
- **The consuming product repo's `branch-ci` workflow** — lives in the product
  repo's own `.github/workflows`, out of scope per spec non-goal #2. This change
  is orchestration-side only.
- **Scope-lint to changed paths** — explicitly deferred (spec non-goal #3 /
  lesson #52 "optional, consider not required").
- **Live exercise of the 403 path** — `sulis-ai/agents` is itself *public*
  (`private: false`, confirmed via `gh api`), so the free-plan 403 cannot be
  reproduced against this repo live. The 403 path is exercised via `mock_gh`
  (`exit_code: 1` + stderr body), which is the existing test convention.

## Suggested Acceptance Order

The deltas form two near-independent tracks (pre-flight; protection/warning) that
share only the orchestration skills. Helper-level work precedes wiring per the
change brief.

1. **HD-001** (medium) — pre-flight CI-conclusion helper in `_wpxlib.py`
   (`(verdict, failed_check_names)`, non-polling). Foundation for HD-002.
2. **HD-003** (medium) — refine `_check_rc02_protections` to distinguish the
   private-free-plan 403 from genuine misconfiguration. Foundation for HD-004.
3. **HD-002** (medium) — wire the pre-flight blocker into `/sulis:run-all`
   before wave dispatch. Depends on HD-001.
4. **HD-004** (medium) — wire the one-time unprotected-repo warning into both
   `/sulis:run-all` and `/sulis:change ship`. Depends on HD-003.

HD-001 and HD-003 can be accepted/implemented in parallel; HD-002 and HD-004 are
their respective orchestration follow-ons.
