# Lessons digest — CH-01KSQB (preflight-dev-drift-check), 2026-05-28

> **Work:** the #52 fix — pre-flight dev-clean check on run-all + one-time
> unprotected-repo warning on run-all & ship.
> **Significance:** the **first real end-to-end run-all → train → gates → ship**
> pass driven through a `change/*` branch. Four robustness gaps in Sulis's own
> machinery surfaced — exactly the class of brownfield CI-infra gap #52 itself
> is about. All four are now tracked issues.

## The story

The change itself went cleanly through recon → specify → audit → design: a
tight 4-WP set (helper → CLI gate; predicate refinement → warning), all
`kind: backend`, no contract seam. The two independent helpers (WP-001
CI-conclusion reader, WP-002 free-plan-403 distinction) built in parallel,
tests-first, both per-WP code-review PASS. The two dependent WPs (WP-003 the
`wpx-preflight` CLI + run-all Step-0 gate; WP-004 the `protection-status`
subcommand + warnings + extract-now refactor) built in sequence. Final state:
780 tests pass, all gates PASS, review verdict **good to ship**.

What was *not* clean was the **integration machinery**. Getting the first
batch onto the change branch took three train attempts, none of them the
fault of the change:

1. **The INDEX the architect produced was unparseable** (issue #60). The WP
   table header was `| WP | Title | ... |`; the tooling detects WP tables by a
   header literally beginning with `| ID | Title |`. The run-all loop couldn't
   flip statuses or compute eligibility. Fixed inline (renamed the column,
   dropped a duplicate `kind`/`Primitive` pair that both aliased to
   `primitive`).
2. **The change branch was never on origin** (issue #61). `sulis-change start`
   makes the branch locally but doesn't push it; the train merges via the
   GitHub API, so its first ref-sha lookup 404'd. Pushed it by hand.
3. **The failed train stranded the WPs** (issue #62). Attempt #2 then reported
   `nothing_to_pack` — the errored attempt #1 had flipped the WPs to
   `step-7-shipping` and never rolled back, and `wpx-train abort` crashes with
   a `NameError` (`TRAIN_HELD_STATUS` undefined), so there was no clean CLI
   recovery. Cleared the stranded pre-merge state file by hand (safe — nothing
   had merged).

With those three cleared, attempt #3 succeeded; the remaining trains
(WP-003, WP-004) ran first-try. During WP-004 the executor also caught and
self-recovered from **journal bookkeeping silently no-oping** in chained Bash
blocks (issue #63) — the code/tests/commit were always correct; only the
audit trail had drifted, reconstructed at Step 7.

## Pattern

All four are **integration-/process-tooling robustness gaps**, not logic bugs:
artifact-format contracts that fail silently instead of loudly (#60), an
unpublished integration target (#61), non-transactional failure handling with
a broken recovery path (#62), and bookkeeping that can no-op without erroring
(#63). The common thread: **fail loud, not silent** — every one of these cost
a recovery cycle because the failure mode was quiet (wrong header silently
unmatched; missing branch a raw 404; stranded state silently mis-computed;
journal writes silently dropped). Hardening these toward loud, early failure
is the through-line for the four issues.

## Actionable lessons → issues

| Lesson | Disposition | Issue |
|---|---|---|
| plan-work emits non-canonical WP INDEX header | SEA | [#60](https://github.com/sulis-ai/agents/issues/60) |
| sulis-change start doesn't push the change branch; first train 404s | TASK | [#61](https://github.com/sulis-ai/agents/issues/61) |
| wpx-train recovery: no rollback on early error + abort crashes | SEA | [#62](https://github.com/sulis-ai/agents/issues/62) |
| executor journal bookkeeping silently no-ops in chained Bash blocks | TASK | [#63](https://github.com/sulis-ai/agents/issues/63) |

All four are good candidates for a future `/sulis:resolve-lessons` drain — the
same path #52 itself travelled.
