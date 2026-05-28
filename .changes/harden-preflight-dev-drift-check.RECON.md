# Recon — harden-preflight-dev-drift-check

Stage 0 completed at: 2026-05-28T14:30:00Z

This marker file's existence indicates that `/sulis:recon` has been run
for this change. The spawned Sulis's stage-inference uses this file to
distinguish "post-recon" from "pre-spawn stub only".

See `plugins/sulis/agents/sulis.md` "Change context" section for the
stage-inference rules.

## What recon found (notes for Stage 1+)

- **Repo set up correctly.** Arrival check `ok: true` (two advisory
  warnings only: RC-06 deploy-token n/a, RC-08 tag-signing not verified
  at rest — neither blocks this work).

- **The train path is already gated — confirmed.** `wpx-train` polls
  bundled-tip CI and pauses (`_pause_train_state`) before the merge loop
  if CI isn't green (`wpx-train` lines ~1378–1397). The merge loop only
  runs on green. So `/sulis:run-all → wpx-train` is safe regardless of
  GitHub branch protection. **Do NOT add a train-refuses-on-red guard —
  it already exists; that would be a no-op** (matches the intent's
  explicit instruction).

- **Branch protection is already probed.** `wpx-arrival-check`
  `_check_rc02_protections` (RC-02) hits
  `repos/{repo}/branches/{dev,main}/protection`. Today a missing/403
  protection is flagged as a hard RC-02 *error*. The unprotected-repo
  warning fix can build on / refine this probe to distinguish the
  private+free-plan 403 ("Upgrade to GitHub Pro…") case and downgrade it
  to a one-time, plain-English warning instead of a hard error.

- **The whole-tree branch-ci checks live in the consuming product
  repo's own `.github/workflows`, not in this Sulis repo.** So the fix
  here is **orchestration-side only** — no generated-workflow change.
  Two surfaces:
  1. **Pre-flight dev-clean check** on the run-all path (run-all skill /
     `wpx-train` / a shared `_wpxlib` helper): before dispatching a wave,
     check dev HEAD's CI status; if red, emit one up-front blocker
     ("dev has N pre-existing CI failures — fix first") instead of every
     WP discovering it per-branch.
  2. **Unprotected-repo detection + one-time warning** via the existing
     protection probe.

- **No `.context/` index exists** for this repo. Skipped the full
  context-discovery conversation: this is the Sulis codebase itself, the
  change is contained to known tooling (`wpx-train`,
  `wpx-arrival-check`, the run-all skill, `_wpxlib`), and the maintainer
  authored the lesson. Match recon depth to the change.

## Key files for the fix

- `plugins/sulis/scripts/wpx-train` — train gate (read-only reference; do
  not add a redundant guard).
- `plugins/sulis/scripts/wpx-arrival-check` — `_check_rc02_protections`,
  the protection probe to build the unprotected-repo warning on.
- `plugins/sulis/scripts/_wpxlib.py` — shared helpers; likely home for a
  pre-flight dev-clean check.
- `plugins/sulis/skills/run-all/SKILL.md` — the orchestration entry point
  that would invoke the pre-flight check.
