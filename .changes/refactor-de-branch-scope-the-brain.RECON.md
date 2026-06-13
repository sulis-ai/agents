# Recon — refactor-de-branch-scope-the-brain

Stage 0 completed at: 2026-06-13T11:35:45Z

This marker's existence indicates /sulis:recon has been run for this change.
The spawned Sulis's stage-inference uses it to distinguish "post-recon" from
"pre-spawn stub only".

## Key findings
- Single resolver owns brain location: plugins/sulis/scripts/_brain_location.py (brain_base_dir).
- Default (step 4) = <repo_root>/.brain/instances. When repo_root is a per-change
  worktree, the brain is created INSIDE the worktree → branch-scoped, lost at ship.
- Settings/store home is already user-level: ~/.sulis (feat-user-level-product-store-settings,
  CH-01KTNS moved product/project store there; _change_state.py default ~/.sulis).
- ~/.sulis/.brain/instances already exists alongside the worktree's .brain — split brain.
- Call sites (all route through brain_base_dir): _brain_emit_helper.py, _change_emission.py,
  _verify_requirements.py, _seam_close_gate.py.
- Override chain unchanged above the default: explicit arg > SULIS_BRAIN_BASE_DIR env >
  repo-contract brain_location > default.
