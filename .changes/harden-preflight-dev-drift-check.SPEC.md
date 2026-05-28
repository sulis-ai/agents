---
founder_facing: false
---
# Spec — pre-flight dev-clean check + unprotected-repo warning

**Change:** CH-01KSQB · harden · Closes #52

## Intent

Stop pre-existing breakage on the shared `dev` line from being rediscovered
by every task in a build run. When `/sulis:run-all` starts, check whether
`dev` HEAD is already CI-green *before* dispatching a wave; if it isn't,
surface one up-front blocker ("dev has N pre-existing CI failures — fix these
first") instead of letting each work package trip over the same red
per-branch.

Separately, make founders aware when their repo can't enforce merge-gating:
on a private repo on the free GitHub plan, branch protection is unavailable
(the protection API returns 403). Branch CI still runs but can't gate merges,
so red can land on `dev` via a manual merge or direct push. Detect this case
and warn once, in plain English, that only Sulis-routed (train) merges are
CI-gated.

## Scope

- **Pre-flight dev-clean check on run-all.** Before dispatching a wave,
  determine whether `dev` HEAD is CI-green. If not, stop with a single
  up-front blocker that names the count of pre-existing failures and tells
  the founder to fix `dev` first. The check must reproduce CI's verdict
  **faithfully** — the same build/prepare steps CI runs, in the same order
  (e.g. building workspace deps before lint/typecheck/test) — so it doesn't
  diverge from CI's actual conclusion.
- **Unprotected-repo detection + one-time warning.** Probe branch protection
  (building on the existing arrival-check probe). If it's unavailable because
  the repo is private on the free plan (403 "Upgrade to GitHub Pro…"), emit a
  one-time, plain-English warning on both `/sulis:run-all` and
  `/sulis:change ship`: only merges routed through Sulis (the train) are
  CI-gated; manual `gh pr merge` / direct pushes are not.

## Non-goals

- **No "train-refuses-on-red" guard.** `wpx-train` already polls bundled-tip
  CI and pauses before the merge loop if CI isn't green — verified in recon.
  Adding another guard there would be a no-op.
- **No change to the consuming product repo's branch-ci workflow.** The
  whole-tree format/lint checks live in the product repo's own
  `.github/workflows`; this change is orchestration-side only.
- **Scoping branch-ci format/lint to changed paths is out of scope.** The
  lesson flags it as optional ("consider, not required"); deferred to keep
  this change tight.
- **The warning is informational, not a blocker.** It raises awareness; it
  does not stop run-all or ship. (The pre-flight dev-clean check is the
  blocker; the unprotected-repo notice is not.)

## Acceptance

- On `/sulis:run-all`, when `dev` HEAD is **not** CI-green, the run stops
  before dispatching any work package and shows one blocker naming the failure
  count ("dev has N pre-existing CI failures — fix these first").
- The pre-flight verdict **matches CI's actual conclusion** for `dev` HEAD:
  no false-green when CI is red (incl. failures that only surface after a
  build/prepare step), and no false-red when CI is green. The conclusion is
  read **explicitly** — never inferred from a chained exit code after
  `gh run watch` (lesson #59).
- On `/sulis:run-all`, when `dev` HEAD **is** CI-green, the run proceeds
  exactly as today (no regression).
- On a **private free-plan** repo (protection probe → 403 "Upgrade to GitHub
  Pro…"), both `/sulis:run-all` and `/sulis:change ship` emit the one-time
  unprotected-repo warning. Shown at most once per invocation.
- On a **public / protected** repo, no unprotected-repo warning appears
  (behaviour unchanged).
- The train still pauses on red before its merge loop — unchanged, no new
  guard added.

## Constraints

- **Orchestration-side only.** Build on existing helpers — the protection
  probe in `wpx-arrival-check` (`_check_rc02_protections`) and the CI signal
  already available for a branch HEAD (as `wpx-train` polls via `_poll_ci`).
  Don't re-implement either.
- **Faithful CI reproduction (build order included).** However "is dev green"
  is determined, it must reflect the *same* pipeline CI runs. Reading `dev`
  HEAD's recorded CI conclusion is the most faithful path (GitHub already ran
  the real workflow); any local re-run would have to replicate CI's full
  build/prepare order, which is the fragile path the sharpening warns against.
- **Read CI conclusion explicitly (lesson #59).** Never trust a chained exit
  code after `gh run watch`; read the run's `conclusion` field directly.
- **Distinguish 403-unavailable from genuine misconfiguration.** The
  unprotected-repo path must trigger only on the private-free-plan 403
  ("Upgrade to GitHub Pro…"), not on a protected-but-misconfigured repo —
  otherwise the existing arrival-check RC-02 error semantics for public repos
  would change.
- **New behaviour is test-first** (CLAUDE.md non-negotiable #1): a failing
  test for the pre-flight blocker and for the 403→warning path before the
  code.

## Decided by default (inferred — flag if any is wrong)

- **Pre-flight blocker is a hard stop**, consistent with the train pausing on
  red: the founder fixes `dev`, then re-runs. (No "proceed anyway" override.)
- **"Warn once" = once per invocation** (per run-all run / per ship), not
  persisted-once-ever — a founder who hasn't fixed their plan should still be
  reminded each time, not silenced permanently.
- **"CI-green on dev HEAD" reads dev's recorded CI conclusion** for its HEAD
  SHA (the check-runs already recorded), not a fresh local re-run — cheapest,
  consistent with how the train already polls, and the most faithful
  reproduction of CI's verdict (build order and all, since GitHub ran the real
  workflow). Reinforced by the #52 sharpening + lesson #59. (Exact mechanism
  is a design-stage detail.)
